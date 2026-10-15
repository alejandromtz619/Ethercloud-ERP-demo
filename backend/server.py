from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as func_sql, and_, or_, update, delete, text, extract, case
from sqlalchemy.orm import selectinload
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import List, Optional
import os
import logging
import httpx
import bcrypt
import jwt
import uuid
import secrets
import time
from collections import deque, defaultdict
import shutil
import asyncio
import socket
import ipaddress
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# Local imports
from database import get_db, init_db, engine, Base, async_session_maker, DATABASE_URL
from models import (
    Empresa, Usuario, Rol, Permiso, RolPermiso, UsuarioRol,
    Cliente, CreditoCliente, PagoCredito, Proveedor, ProveedorProducto, DeudaProveedor,
    Categoria, Marca, Producto, MateriaLaboratorio, EstadoMateria,
    Almacen, StockActual, MovimientoStock, TipoMovimientoStock,
    Venta, VentaItem, EstadoVenta, TipoPago,
    Presupuesto, PresupuestoItem,
    Funcionario, AdelantoSalario, CicloSalario,
    Vehiculo, TipoVehiculo, Entrega, EstadoEntrega,
    Factura, DocumentoElectronico, PreferenciaUsuario,
    DocumentoTemporal, TipoDocumento, Gasto,
    FacturaGrupal, factura_grupal_ventas
)
from schemas import (
    EmpresaCreate, EmpresaUpdate, EmpresaResponse,
    UsuarioCreate, UsuarioResponse, UsuarioLogin, TokenResponse,
    RolCreate, RolResponse, PermisoResponse,
    ClienteCreate, ClienteResponse, CreditoClienteCreate, CreditoClienteResponse,
    ProveedorCreate, ProveedorResponse, DeudaProveedorCreate, DeudaProveedorResponse,
    ProveedorProductoCreate, ProveedorProductoUpdate, ProveedorProductoResponse,
    CategoriaCreate, CategoriaResponse, MarcaCreate, MarcaResponse,
    GastoCreate, GastoResponse, GastoUpdate,
    ProductoCreate, ProductoResponse, ProductoConStock, ProductoCodigoBarraConflicto,
    MateriaLaboratorioCreate, MateriaLaboratorioUpdate, MateriaLaboratorioResponse,
    MateriaLaboratorioPage, ProductoPagina, StockPagina, ClientePagina,
    AlmacenCreate, AlmacenResponse, StockActualCreate, StockActualResponse, StockConDetalles,
    MovimientoStockCreate, MovimientoStockResponse, TraspasoStockCreate, SalidaStockCreate,
    EntradaStockHistorialResponse,
    VentaCreate, VentaUpdate, VentaResponse, VentaConDetalles, VentaItemResponse,
    FechaImpresionUpdate,
    PresupuestoCreate, PresupuestoResponse, PresupuestoConDetalles, PresupuestoItemResponse,
    FuncionarioCreate, FuncionarioResponse,
    AdelantoSalarioCreate, AdelantoSalarioResponse,
    CicloSalarioCreate, CicloSalarioResponse,
    VehiculoCreate, VehiculoResponse,
    EntregaCreate, EntregaResponse, EntregaConDetalles, AsignarEntrega,
    FacturaCreate, FacturaResponse,
    FacturaGrupalCreate, FacturaGrupalResponse,
    PreferenciaUsuarioCreate, PreferenciaUsuarioResponse,
    DashboardStats, VentasPorHora, StockBajo, CotizacionDivisa, Alerta,
    DocumentoTemporalCreate, DocumentoTemporal as DocumentoTemporalSchema
)

# ==================== TIMEZONE CONFIGURATION ====================
# Paraguay timezone: America/Asuncion (GMT-4 standard, GMT-3 during DST)
PARAGUAY_TZ = ZoneInfo("America/Asuncion")

def now_paraguay():
    """Obtiene la fecha y hora actual en zona horaria de Paraguay"""
    return datetime.now(PARAGUAY_TZ)

def today_paraguay():
    """Obtiene la fecha actual (solo fecha) en Paraguay"""
    return now_paraguay().date()

def get_day_range_paraguay(date_obj):
    """Obtiene el rango completo de un día en Paraguay (00:00:01 - 23:59:59)"""
    # Start: 00:00:01 of the day in Paraguay
    day_start = datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
    # End: 23:59:59 of the day in Paraguay
    day_end = datetime.combine(date_obj, datetime.max.time()).replace(tzinfo=PARAGUAY_TZ)
    return day_start, day_end

def fecha_documento(venta, tipo_documento: str = 'BOLETA'):
    """Fecha que debe salir IMPRESA en el documento.

    Toma creado_en en hora Paraguay y, si el usuario corrigio la fecha de impresion
    (ventas.fecha_impresion_boleta / _factura), reemplaza solo el dia/mes/anio y
    conserva la hora original. creado_en NUNCA se modifica.

    Devuelve (datetime, bool modificada).
    """
    base = venta.creado_en
    if base is None:
        return now_paraguay(), False
    base = base.astimezone(PARAGUAY_TZ) if base.tzinfo else base.replace(tzinfo=timezone.utc).astimezone(PARAGUAY_TZ)
    override = venta.fecha_impresion_factura if tipo_documento == 'FACTURA' else venta.fecha_impresion_boleta
    if override:
        return base.replace(year=override.year, month=override.month, day=override.day), True
    return base, False

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / 'uploads' / 'productos'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# JWT Config
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '12'))
# Valores por defecto que alguna vez estuvieron publicados en el repo: firmar con ellos
# permite a cualquiera fabricar un token de administrador.
JWT_SECRETS_INSEGUROS = {
    '',
    'ethercloud-secret-key-change-in-production',
    'generate-a-strong-secret-here',
}
ES_PRODUCCION = DATABASE_URL.startswith('postgresql')
# Endpoints que borran o siembran la base (/seed, /reset-database). Sólo para desarrollo.
PERMITIR_ENDPOINTS_DESARROLLO = os.environ.get('PERMITIR_ENDPOINTS_DESARROLLO', '').lower() == 'true'

# Margen de ganancia fijo de las materias de laboratorio: su costo se registra como
# precio * (1 - margen). Regulable por variable de entorno (0.30 = 30 %).
LAB_MARGEN_GANANCIA = Decimal(os.environ.get('LAB_MARGEN_GANANCIA', '0.30'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get('JWT_SECRET', '').strip()
if JWT_SECRET in JWT_SECRETS_INSEGUROS:
    if ES_PRODUCCION:
        raise RuntimeError(
            "JWT_SECRET no está configurado o usa un valor por defecto público. "
            "Definí un valor aleatorio de 32+ caracteres (p. ej. `openssl rand -hex 32`)."
        )
    # Desarrollo (SQLite): secreto efímero; las sesiones se pierden al reiniciar.
    JWT_SECRET = secrets.token_urlsafe(48)
    logger.warning("JWT_SECRET no configurado: se usa un secreto temporal (sólo desarrollo)")
elif len(JWT_SECRET) < 32:
    logger.warning("JWT_SECRET tiene menos de 32 caracteres: conviene reemplazarlo por uno aleatorio más largo")

# Manual currency rates storage
MANUAL_CURRENCY_RATES = {
    'usd_pyg': None,
    'brl_pyg': None,
    'manual': False,
    'updated_at': None
}

# Create FastAPI app
app = FastAPI(title="Ethercloud ERP API", version="1.0.0")

# CORS Configuration
cors_origins = os.environ.get('CORS_ORIGINS', '*')
if cors_origins == '*':
    allowed_origins = ['*']
    allow_credentials = False  # Can't use credentials with wildcard
else:
    allowed_origins = [origin.strip() for origin in cors_origins.split(',')]
    allow_credentials = True

logger.info(f"CORS allowed origins: {allowed_origins}")
logger.info(f"CORS allow credentials: {allow_credentials}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=str(ROOT_DIR / 'uploads')), name="uploads")

# Rutas sin token. Sólo lo imprescindible: salud, login, la marca de la empresa para la
# pantalla de login y los enlaces públicos de documentos (llevan su propio token).
# Todo lo demás va en api_router, que exige token por defecto (se define más abajo).
public_router = APIRouter(prefix="/api")

# ==================== AUTH HELPERS ====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Security scheme for JWT Bearer tokens
security_scheme = HTTPBearer(auto_error=False)

def create_token(usuario_id: int) -> str:
    payload = {
        "sub": str(usuario_id),
        "exp": now_paraguay() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Por favor inicie sesión nuevamente."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )

async def get_current_usuario(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    """Dependency that validates JWT and returns the current user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido."
        )
    payload = decode_token(credentials.credentials)
    try:
        usuario_id = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        usuario_id = 0
    if not usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: sin identificador de usuario."
        )
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado."
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo."
        )
    return usuario

# Nombres del rol administrador: seed_data.py crea "Administrador" y el seed de la API "ADMIN"
ROLES_ADMIN = ('ADMIN', 'Administrador')

async def _es_admin(db: AsyncSession, usuario_id: int) -> bool:
    result = await db.execute(
        select(Rol.id)
        .join(UsuarioRol, Rol.id == UsuarioRol.rol_id)
        .where(UsuarioRol.usuario_id == usuario_id, Rol.nombre.in_(ROLES_ADMIN))
        .limit(1)
    )
    return result.first() is not None

async def verificar_es_admin(
    usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    """Dependency that requires the current user to have the ADMIN role."""
    if not await _es_admin(db, usuario.id):
        raise HTTPException(status_code=403, detail="Solo un administrador puede realizar esta acción")
    return usuario

def requiere_permiso(*claves: str):
    """Dependency: el usuario debe tener al menos uno de los permisos `claves`.
    Los roles administrador pasan siempre."""
    async def _verificar(
        usuario: Usuario = Depends(get_current_usuario),
        db: AsyncSession = Depends(get_db)
    ) -> Usuario:
        if await _es_admin(db, usuario.id):
            return usuario
        result = await db.execute(
            select(Permiso.id)
            .join(RolPermiso, Permiso.id == RolPermiso.permiso_id)
            .join(UsuarioRol, RolPermiso.rol_id == UsuarioRol.rol_id)
            .where(UsuarioRol.usuario_id == usuario.id, Permiso.clave.in_(claves))
            .limit(1)
        )
        if result.first() is None:
            raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción")
        return usuario
    return _verificar

# Todas las rutas de este router exigen un token válido. Una ruta nueva queda protegida
# aunque se olvide declarar get_current_usuario; las públicas van en public_router.
api_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_usuario)])

# ==================== LÍMITE DE INTENTOS DE LOGIN ====================
class LimitadorIntentos:
    """Cuenta intentos fallidos por clave dentro de una ventana deslizante (en memoria:
    el backend corre en un solo proceso por instancia)."""

    def __init__(self, maximo: int, ventana_segundos: int):
        self.maximo = maximo
        self.ventana = ventana_segundos
        self._fallos: dict[str, deque] = {}

    def _vigentes(self, clave: str) -> deque:
        fallos = self._fallos.setdefault(clave, deque())
        limite = time.monotonic() - self.ventana
        while fallos and fallos[0] < limite:
            fallos.popleft()
        return fallos

    def bloqueado(self, clave: str) -> bool:
        return len(self._vigentes(clave)) >= self.maximo

    def registrar_fallo(self, clave: str) -> None:
        if len(self._fallos) > 10_000:  # evita que claves inventadas llenen la memoria
            for vieja in [k for k in self._fallos if not self._vigentes(k)]:
                del self._fallos[vieja]
        self._vigentes(clave).append(time.monotonic())

    def limpiar(self, clave: str) -> None:
        self._fallos.pop(clave, None)

LOGIN_FALLOS_POR_EMAIL = LimitadorIntentos(maximo=5, ventana_segundos=15 * 60)

def numero_a_letras(numero):
    """Convert number to Spanish words for receipts"""
    unidades = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    decenas = ['', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
    especiales = {11: 'once', 12: 'doce', 13: 'trece', 14: 'catorce', 15: 'quince', 
                  16: 'dieciséis', 17: 'diecisiete', 18: 'dieciocho', 19: 'diecinueve'}
    centenas = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos',
                'seiscientos', 'setecientos', 'ochocientos', 'novecientos']
    
    n = int(numero)
    if n == 0:
        return 'cero'
    if n == 100:
        return 'cien'
    
    resultado = ''
    
    if n >= 1000000:
        millones = n // 1000000
        resultado += ('un millón ' if millones == 1 else numero_a_letras(millones) + ' millones ')
        n %= 1000000
    
    if n >= 1000:
        miles = n // 1000
        resultado += ('mil ' if miles == 1 else numero_a_letras(miles) + ' mil ')
        n %= 1000
    
    if n >= 100:
        resultado += centenas[n // 100] + ' '
        n %= 100
    
    if n in especiales:
        resultado += especiales[n]
    elif n >= 10:
        resultado += decenas[n // 10]
        if n % 10:
            resultado += ' y ' + unidades[n % 10]
    elif n > 0:
        resultado += unidades[n]
    
    return resultado.strip()

# ==================== ROOT ====================
@public_router.get("/")
async def root():
    return {"message": "Ethercloud ERP API v1.0"}

@public_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": now_paraguay().isoformat()}

# ==================== EMPRESA ====================
@public_router.get("/empresas/{empresa_id}/publico")
async def obtener_empresa_publico(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Nombre y logo para la pantalla de login (sin token). No expone otros datos."""
    result = await db.execute(
        select(Empresa.id, Empresa.nombre, Empresa.logo_url)
        .where(Empresa.id == empresa_id, Empresa.estado == True)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return {"id": row.id, "nombre": row.nombre, "logo_url": row.logo_url}

@api_router.post("/empresas", response_model=EmpresaResponse,
                 dependencies=[Depends(requiere_permiso("sistema.configurar"))])
async def crear_empresa(data: EmpresaCreate, db: AsyncSession = Depends(get_db)):
    empresa = Empresa(**data.model_dump())
    db.add(empresa)
    await db.commit()
    await db.refresh(empresa)
    return empresa

@api_router.get("/empresas", response_model=List[EmpresaResponse])
async def listar_empresas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Empresa).where(Empresa.estado == True))
    return result.scalars().all()

@api_router.get("/empresas/{empresa_id}", response_model=EmpresaResponse)
async def obtener_empresa(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa

@api_router.put("/empresas/{empresa_id}", response_model=EmpresaResponse)
async def actualizar_empresa(
    empresa_id: int,
    data: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(requiere_permiso("sistema.configurar"))
):
    if current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Sin permisos para modificar esta empresa")
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(empresa, key, value)
    await db.commit()
    await db.refresh(empresa)
    return empresa

# ==================== AUTH ====================
# Alta de usuarios desde la pantalla Usuarios: sólo quien gestiona usuarios.
@api_router.post("/auth/register", response_model=TokenResponse,
                 dependencies=[Depends(requiere_permiso("usuarios.gestionar"))])
async def registrar_usuario(data: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    usuario = Usuario(
        email=data.email,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        apellido=data.apellido,
        telefono=data.telefono,
        empresa_id=data.empresa_id
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    
    token = create_token(usuario.id)
    return TokenResponse(access_token=token, usuario=UsuarioResponse.model_validate(usuario))

@public_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UsuarioLogin, db: AsyncSession = Depends(get_db)):
    # Por e-mail y no por IP: detrás del proxy de Coolify todas las peticiones llegan
    # con la misma IP, y un límite por IP bloquearía a todos los usuarios a la vez.
    clave_email = data.email.strip().lower()
    if LOGIN_FALLOS_POR_EMAIL.bloqueado(clave_email):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos fallidos. Espere unos minutos e intente de nuevo."
        )

    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    usuario = result.scalar_one_or_none()

    if not usuario or not verify_password(data.password, usuario.password_hash):
        LOGIN_FALLOS_POR_EMAIL.registrar_fallo(clave_email)
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not usuario.activo:
        raise HTTPException(status_code=401, detail="Usuario inactivo")

    LOGIN_FALLOS_POR_EMAIL.limpiar(clave_email)
    token = create_token(usuario.id)
    return TokenResponse(access_token=token, usuario=UsuarioResponse.model_validate(usuario))

@api_router.get("/auth/me", response_model=UsuarioResponse)
async def obtener_usuario_actual(usuario: Usuario = Depends(get_current_usuario)):
    """Validate JWT token and return current user data."""
    return usuario

# ==================== USUARIOS ====================
@api_router.get("/usuarios", response_model=List[UsuarioResponse])
async def listar_usuarios(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.roles))
        .where(Usuario.empresa_id == empresa_id, Usuario.activo == True)
    )
    usuarios = result.scalars().all()
    
    # Agregar rol_id desde la relación usuario_roles
    usuarios_response = []
    for usuario in usuarios:
        usuario_dict = {
            "id": usuario.id,
            "empresa_id": usuario.empresa_id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "telefono": usuario.telefono,
            "activo": usuario.activo,
            "creado_en": usuario.creado_en,
            "rol_id": usuario.roles[0].rol_id if usuario.roles else None
        }
        usuarios_response.append(usuario_dict)
    
    return usuarios_response

@api_router.get("/usuarios/{usuario_id}", response_model=UsuarioResponse)
async def obtener_usuario(usuario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@api_router.put("/usuarios/{usuario_id}", response_model=UsuarioResponse,
                dependencies=[Depends(requiere_permiso("usuarios.gestionar"))])
async def actualizar_usuario(usuario_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    for key, value in data.items():
        if key == 'password' and value:
            usuario.password_hash = hash_password(value)
        elif hasattr(usuario, key) and key not in ['id', 'password_hash', 'password']:
            setattr(usuario, key, value)
    
    await db.commit()
    await db.refresh(usuario)
    return usuario

@api_router.delete("/usuarios/{usuario_id}", dependencies=[Depends(requiere_permiso("usuarios.gestionar"))])
async def eliminar_usuario(usuario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    usuario.activo = False
    await db.commit()
    return {"message": "Usuario desactivado"}

# ==================== ROLES Y PERMISOS ====================
@api_router.post("/roles", response_model=RolResponse, dependencies=[Depends(requiere_permiso("usuarios.gestionar", "roles.gestionar"))])
async def crear_rol(data: RolCreate, db: AsyncSession = Depends(get_db)):
    rol = Rol(**data.model_dump())
    db.add(rol)
    await db.commit()
    await db.refresh(rol)
    return rol

@api_router.get("/roles", response_model=List[RolResponse])
async def listar_roles(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rol).where(Rol.empresa_id == empresa_id))
    return result.scalars().all()

@api_router.get("/permisos", response_model=List[PermisoResponse])
async def listar_permisos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Permiso))
    return result.scalars().all()

@api_router.post("/permisos", response_model=PermisoResponse, dependencies=[Depends(requiere_permiso("usuarios.gestionar", "roles.gestionar"))])
async def crear_permiso(data: dict, db: AsyncSession = Depends(get_db)):
    permiso = Permiso(clave=data['clave'], descripcion=data.get('descripcion'))
    db.add(permiso)
    await db.commit()
    await db.refresh(permiso)
    return permiso

@api_router.post("/roles/{rol_id}/permisos/{permiso_id}", dependencies=[Depends(requiere_permiso("usuarios.gestionar", "roles.gestionar"))])
async def asignar_permiso_rol(rol_id: int, permiso_id: int, db: AsyncSession = Depends(get_db)):
    # Check if already exists
    existing = await db.execute(
        select(RolPermiso).where(RolPermiso.rol_id == rol_id, RolPermiso.permiso_id == permiso_id)
    )
    if existing.scalar_one_or_none():
        return {"message": "Permiso ya asignado"}
    
    rol_permiso = RolPermiso(rol_id=rol_id, permiso_id=permiso_id)
    db.add(rol_permiso)
    await db.commit()
    return {"message": "Permiso asignado"}

@api_router.delete("/roles/{rol_id}/permisos/{permiso_id}", dependencies=[Depends(requiere_permiso("usuarios.gestionar", "roles.gestionar"))])
async def quitar_permiso_rol(rol_id: int, permiso_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RolPermiso).where(RolPermiso.rol_id == rol_id, RolPermiso.permiso_id == permiso_id)
    )
    rol_permiso = result.scalar_one_or_none()
    if rol_permiso:
        await db.delete(rol_permiso)
        await db.commit()
    return {"message": "Permiso quitado"}

@api_router.get("/roles/{rol_id}/permisos")
async def obtener_permisos_rol(rol_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Permiso)
        .join(RolPermiso, Permiso.id == RolPermiso.permiso_id)
        .where(RolPermiso.rol_id == rol_id)
    )
    return result.scalars().all()

@api_router.post("/usuarios/{usuario_id}/roles/{rol_id}", dependencies=[Depends(requiere_permiso("usuarios.gestionar"))])
async def asignar_rol_usuario(usuario_id: int, rol_id: int, db: AsyncSession = Depends(get_db)):
    # Check if already exists
    existing = await db.execute(
        select(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id, UsuarioRol.rol_id == rol_id)
    )
    if existing.scalar_one_or_none():
        return {"message": "Rol ya asignado"}
    
    usuario_rol = UsuarioRol(usuario_id=usuario_id, rol_id=rol_id)
    db.add(usuario_rol)
    await db.commit()
    return {"message": "Rol asignado"}

@api_router.delete("/usuarios/{usuario_id}/roles/{rol_id}", dependencies=[Depends(requiere_permiso("usuarios.gestionar"))])
async def quitar_rol_usuario(usuario_id: int, rol_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id, UsuarioRol.rol_id == rol_id)
    )
    usuario_rol = result.scalar_one_or_none()
    if usuario_rol:
        await db.delete(usuario_rol)
        await db.commit()
    return {"message": "Rol quitado"}

@api_router.get("/usuarios/{usuario_id}/permisos")
async def obtener_permisos_usuario(usuario_id: int, db: AsyncSession = Depends(get_db)):
    """Get all permissions for a user through their roles"""
    result = await db.execute(
        select(Permiso)
        .join(RolPermiso, Permiso.id == RolPermiso.permiso_id)
        .join(UsuarioRol, RolPermiso.rol_id == UsuarioRol.rol_id)
        .where(UsuarioRol.usuario_id == usuario_id)
        .distinct()
    )
    permisos = result.scalars().all()
    return [{"id": p.id, "clave": p.clave, "descripcion": p.descripcion} for p in permisos]

# ==================== CLIENTES ====================
@api_router.post("/clientes", response_model=ClienteResponse)
async def crear_cliente(data: ClienteCreate, db: AsyncSession = Depends(get_db)):
    ruc = (data.ruc or "").strip()
    cedula = (data.cedula or "").strip()

    if ruc:
        existing = await db.execute(
            select(Cliente).where(
                Cliente.empresa_id == data.empresa_id,
                Cliente.estado == True,
                Cliente.ruc == ruc,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe un cliente registrado con el RUC {ruc}")

    if cedula:
        existing = await db.execute(
            select(Cliente).where(
                Cliente.empresa_id == data.empresa_id,
                Cliente.estado == True,
                Cliente.cedula == cedula,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Ya existe un cliente registrado con la cédula {cedula}")

    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente

@api_router.get("/clientes", response_model=List[ClienteResponse])
async def listar_clientes(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Cliente).where(Cliente.empresa_id == empresa_id, Cliente.estado == True)
    )
    return result.scalars().all()

@api_router.get("/clientes/buscar", response_model=ClientePagina)
async def buscar_clientes(
    empresa_id: int,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Búsqueda paginada de clientes activos: q "contiene" en nombre, apellido, RUC, cédula
    o teléfono, o ID exacto si es un número. Ordenados por nombre."""
    filtros = [Cliente.empresa_id == empresa_id, Cliente.estado == True]
    texto = (q or '').strip()
    id_buscado = int(texto) if texto.isdigit() and int(texto) < 2**31 else None
    if texto:
        patron = _patron_contiene(texto)
        coincide = [campo.ilike(patron, escape='\\') for campo in
                    (Cliente.nombre, Cliente.apellido, Cliente.ruc, Cliente.cedula, Cliente.telefono)]
        # "Juan Pérez": también nombre + apellido juntos
        coincide.append((Cliente.nombre + ' ' + func_sql.coalesce(Cliente.apellido, '')).ilike(patron, escape='\\'))
        if id_buscado is not None:
            coincide.append(Cliente.id == id_buscado)
        filtros.append(or_(*coincide))

    total = await db.scalar(select(func_sql.count(Cliente.id)).where(*filtros))
    orden = [Cliente.nombre, Cliente.apellido, Cliente.id]
    if id_buscado is not None:
        orden.insert(0, case((Cliente.id == id_buscado, 0), else_=1))
    result = await db.execute(select(Cliente).where(*filtros).order_by(*orden).limit(limit).offset(offset))
    return ClientePagina(
        items=[ClienteResponse.model_validate(c) for c in result.scalars().all()],
        total=total or 0, limit=limit, offset=offset,
    )

@api_router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
async def obtener_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

@api_router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
async def actualizar_cliente(cliente_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if 'ruc' in data:
        ruc = (data['ruc'] or "").strip()
        if ruc:
            existing = await db.execute(
                select(Cliente).where(
                    Cliente.empresa_id == cliente.empresa_id,
                    Cliente.estado == True,
                    Cliente.ruc == ruc,
                    Cliente.id != cliente_id,
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Ya existe un cliente registrado con el RUC {ruc}")

    if 'cedula' in data:
        cedula = (data['cedula'] or "").strip()
        if cedula:
            existing = await db.execute(
                select(Cliente).where(
                    Cliente.empresa_id == cliente.empresa_id,
                    Cliente.estado == True,
                    Cliente.cedula == cedula,
                    Cliente.id != cliente_id,
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Ya existe un cliente registrado con la cédula {cedula}")

    for key, value in data.items():
        if hasattr(cliente, key) and key != 'id':
            setattr(cliente, key, value)
    
    await db.commit()
    await db.refresh(cliente)
    return cliente

@api_router.delete("/clientes/{cliente_id}")
async def eliminar_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente.estado = False
    await db.commit()
    return {"message": "Cliente desactivado"}

# ==================== CREDITOS CLIENTES ====================
@api_router.get("/clientes/{cliente_id}/credito-disponible")
async def obtener_credito_disponible(cliente_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene el crédito usado y disponible de un cliente"""
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Calcular crédito usado (suma de monto_pendiente de créditos no pagados)
    creditos_result = await db.execute(
        select(func_sql.coalesce(func_sql.sum(CreditoCliente.monto_pendiente), 0))
        .where(CreditoCliente.cliente_id == cliente_id, CreditoCliente.pagado == False)
    )
    credito_usado = creditos_result.scalar() or Decimal('0')
    
    limite = cliente.limite_credito or Decimal('0')
    disponible = max(Decimal('0'), limite - credito_usado)
    
    return {
        "cliente_id": cliente_id,
        "limite_credito": float(limite),
        "credito_usado": float(credito_usado),
        "credito_disponible": float(disponible)
    }

@api_router.post("/clientes/{cliente_id}/creditos", response_model=CreditoClienteResponse)
async def crear_credito_cliente(cliente_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Registra una nueva transacción a crédito"""
    monto = Decimal(str(data.get('monto_original', 0)))
    
    # Verificar límite de crédito
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Calcular crédito actual
    creditos_result = await db.execute(
        select(func_sql.coalesce(func_sql.sum(CreditoCliente.monto_pendiente), 0))
        .where(CreditoCliente.cliente_id == cliente_id, CreditoCliente.pagado == False)
    )
    credito_usado = creditos_result.scalar() or Decimal('0')
    
    limite = cliente.limite_credito or Decimal('0')
    # Si el límite es 0, no se permite crédito
    if limite <= 0:
        raise HTTPException(
            status_code=400,
            detail="El cliente no tiene crédito habilitado. Asigne un límite de crédito mayor a 0 para habilitar compras a crédito."
        )
    if (credito_usado + monto) > limite:
        raise HTTPException(
            status_code=400, 
            detail=f"Crédito excede el límite. Disponible: {float(limite - credito_usado):,.0f} Gs"
        )
    
    credito = CreditoCliente(
        cliente_id=cliente_id,
        venta_id=data.get('venta_id'),
        monto_original=monto,
        monto_pendiente=monto,
        descripcion=data.get('descripcion'),
        fecha_venta=today_paraguay(),
        creado_en=now_paraguay()
    )
    db.add(credito)
    await db.commit()
    await db.refresh(credito)
    return credito

@api_router.get("/clientes/{cliente_id}/creditos")
async def listar_creditos_cliente(cliente_id: int, solo_pendientes: bool = False, db: AsyncSession = Depends(get_db)):
    """Lista todos los créditos de un cliente con sus pagos"""
    query = select(CreditoCliente).where(CreditoCliente.cliente_id == cliente_id).order_by(CreditoCliente.fecha_venta.desc())
    if solo_pendientes:
        query = query.where(CreditoCliente.pagado == False)
    
    result = await db.execute(query)
    creditos = result.scalars().all()
    
    response = []
    for credito in creditos:
        # Get pagos for this credito
        pagos_result = await db.execute(
            select(PagoCredito).where(PagoCredito.credito_id == credito.id).order_by(PagoCredito.fecha_pago.desc())
        )
        pagos = pagos_result.scalars().all()
        
        response.append({
            "id": credito.id,
            "cliente_id": credito.cliente_id,
            "venta_id": credito.venta_id,
            "monto_original": float(credito.monto_original),
            "monto_pendiente": float(credito.monto_pendiente),
            "descripcion": credito.descripcion,
            "fecha_venta": credito.fecha_venta.isoformat() if credito.fecha_venta else None,
            "pagado": credito.pagado,
            "creado_en": credito.creado_en.isoformat() if credito.creado_en else None,
            "pagos": [
                {
                    "id": p.id,
                    "monto": float(p.monto),
                    "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
                    "observacion": p.observacion
                }
                for p in pagos
            ]
        })
    
    return response

@api_router.post("/creditos/{credito_id}/pagar")
async def pagar_credito(credito_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Registra un pago parcial o total a un crédito"""
    result = await db.execute(select(CreditoCliente).where(CreditoCliente.id == credito_id))
    credito = result.scalar_one_or_none()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
    
    if credito.pagado:
        raise HTTPException(status_code=400, detail="Este crédito ya está pagado")
    
    monto_pago = Decimal(str(data.get('monto', 0)))
    if monto_pago <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
    
    if monto_pago > credito.monto_pendiente:
        raise HTTPException(status_code=400, detail=f"El monto excede la deuda pendiente de {float(credito.monto_pendiente):,.0f} Gs")
    
    # Create payment record
    pago = PagoCredito(
        credito_id=credito_id,
        monto=monto_pago,
        observacion=data.get('observacion'),
        fecha_pago=now_paraguay()
    )
    db.add(pago)
    
    # Update credito
    credito.monto_pendiente = credito.monto_pendiente - monto_pago
    if credito.monto_pendiente <= 0:
        credito.pagado = True
        credito.monto_pendiente = Decimal('0')
    
    await db.commit()
    await db.refresh(credito)
    
    return {
        "message": "Pago registrado exitosamente",
        "credito_id": credito_id,
        "monto_pagado": float(monto_pago),
        "monto_pendiente": float(credito.monto_pendiente),
        "pagado": credito.pagado
    }

# ==================== PROVEEDORES ====================
@api_router.post("/proveedores", response_model=ProveedorResponse)
async def crear_proveedor(data: ProveedorCreate, db: AsyncSession = Depends(get_db)):
    proveedor = Proveedor(**data.model_dump())
    db.add(proveedor)
    await db.commit()
    await db.refresh(proveedor)
    return proveedor

@api_router.get("/proveedores", response_model=List[ProveedorResponse])
async def listar_proveedores(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Proveedor).where(Proveedor.empresa_id == empresa_id, Proveedor.estado == True)
    )
    return result.scalars().all()

@api_router.get("/proveedores/comparacion-mercado")
async def comparacion_mercado(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Returns pivot table: products x suppliers with cost, SKU and link per cell."""
    prov_result = await db.execute(
        select(Proveedor).where(Proveedor.empresa_id == empresa_id, Proveedor.estado == True)
        .order_by(Proveedor.nombre)
    )
    proveedores = prov_result.scalars().all()
    prov_ids = [p.id for p in proveedores]

    if not prov_ids:
        return {"proveedores": [], "filas": []}

    pp_result = await db.execute(
        select(ProveedorProducto, Producto)
        .join(Producto, ProveedorProducto.producto_id == Producto.id)
        .where(ProveedorProducto.proveedor_id.in_(prov_ids), Producto.activo == True)
        .order_by(Producto.nombre)
    )
    rows = pp_result.all()

    product_map: dict = {}
    for pp, prod in rows:
        if prod.id not in product_map:
            product_map[prod.id] = {"producto_id": prod.id, "producto_nombre": prod.nombre, "precios": {}}
        product_map[prod.id]["precios"][str(pp.proveedor_id)] = {
            "pp_id": pp.id,
            "costo": float(pp.costo) if pp.costo is not None else None,
            "sku": pp.sku,
            "link": pp.link,
        }

    return {
        "proveedores": [{"id": p.id, "nombre": p.nombre} for p in proveedores],
        "filas": list(product_map.values()),
    }

@api_router.get("/proveedores/comparacion-mercado/excel")
async def comparacion_mercado_excel(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Export market comparison as Excel file."""
    prov_result = await db.execute(
        select(Proveedor).where(Proveedor.empresa_id == empresa_id, Proveedor.estado == True)
        .order_by(Proveedor.nombre)
    )
    proveedores = prov_result.scalars().all()
    prov_ids = [p.id for p in proveedores]

    pp_result = None
    if prov_ids:
        pp_result = await db.execute(
            select(ProveedorProducto, Producto)
            .join(Producto, ProveedorProducto.producto_id == Producto.id)
            .where(ProveedorProducto.proveedor_id.in_(prov_ids), Producto.activo == True)
            .order_by(Producto.nombre)
        )

    product_map: dict = {}
    if pp_result:
        for pp, prod in pp_result.all():
            if prod.id not in product_map:
                product_map[prod.id] = {"nombre": prod.nombre, "precios": {}}
            product_map[prod.id]["precios"][pp.proveedor_id] = {
                "costo": float(pp.costo) if pp.costo is not None else None,
                "sku": pp.sku or "",
            }

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comparación de Mercado"

    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hfill = PatternFill(start_color="0044CC", end_color="0044CC", fill_type="solid")
    hfont = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    total_cols = 1 + len(proveedores) * 2
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(total_cols, 2))
    t = ws.cell(row=1, column=1, value="Comparación de Precios por Proveedor")
    t.font = Font(name="Calibri", size=14, bold=True, color="0044CC")
    t.alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 26

    ws.cell(row=3, column=1, value="Producto").font = hfont
    ws.cell(row=3, column=1).fill = hfill
    ws.cell(row=3, column=1).border = border
    ws.cell(row=3, column=1).alignment = Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 35

    for ci, prov in enumerate(proveedores):
        col_precio = 2 + ci * 2
        col_sku = 3 + ci * 2
        c1 = ws.cell(row=3, column=col_precio, value=f"{prov.nombre} - Costo (₲)")
        c2 = ws.cell(row=3, column=col_sku, value=f"{prov.nombre} - SKU")
        for c in [c1, c2]:
            c.font = hfont
            c.fill = hfill
            c.border = border
            c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col_precio)].width = 20
        ws.column_dimensions[get_column_letter(col_sku)].width = 18

    for ri, (prod_id, prod_data) in enumerate(product_map.items(), 1):
        rn = 3 + ri
        bg = "FFFFFF" if ri % 2 == 1 else "F5F7FF"
        fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        c = ws.cell(row=rn, column=1, value=prod_data["nombre"])
        c.font = Font(name="Calibri", size=9)
        c.fill = fill
        c.border = border
        for ci, prov in enumerate(proveedores):
            col_precio = 2 + ci * 2
            col_sku = 3 + ci * 2
            precio_data = prod_data["precios"].get(prov.id)
            costo_val = precio_data["costo"] if precio_data else None
            sku_val = precio_data["sku"] if precio_data else ""
            cp = ws.cell(row=rn, column=col_precio, value=costo_val)
            cs = ws.cell(row=rn, column=col_sku, value=sku_val)
            for cc in [cp, cs]:
                cc.font = Font(name="Calibri", size=9)
                cc.fill = fill
                cc.border = border
                cc.alignment = Alignment(horizontal="right")

    buf = io.BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=comparacion_mercado.xlsx"}
    )

@api_router.get("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
async def obtener_proveedor(proveedor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Proveedor).where(Proveedor.id == proveedor_id))
    proveedor = result.scalar_one_or_none()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor

@api_router.put("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
async def actualizar_proveedor(proveedor_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Proveedor).where(Proveedor.id == proveedor_id))
    proveedor = result.scalar_one_or_none()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    for key, value in data.items():
        if hasattr(proveedor, key) and key != 'id':
            setattr(proveedor, key, value)
    
    await db.commit()
    await db.refresh(proveedor)
    return proveedor

@api_router.delete("/proveedores/{proveedor_id}")
async def eliminar_proveedor(proveedor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Proveedor).where(Proveedor.id == proveedor_id))
    proveedor = result.scalar_one_or_none()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    proveedor.estado = False
    await db.commit()
    return {"message": "Proveedor desactivado"}

# ==================== DEUDAS PROVEEDORES ====================
@api_router.post("/proveedores/{proveedor_id}/deudas", response_model=DeudaProveedorResponse)
async def crear_deuda_proveedor(proveedor_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    # Parse fecha_limite if provided as string
    fecha_limite_parsed = None
    if data.get('fecha_limite'):
        try:
            fecha_limite_parsed = date.fromisoformat(data['fecha_limite'])
        except (ValueError, TypeError):
            fecha_limite_parsed = None
    
    deuda = DeudaProveedor(
        proveedor_id=proveedor_id,
        monto=Decimal(str(data['monto'])),
        descripcion=data.get('descripcion'),
        fecha_emision=today_paraguay(),
        fecha_limite=fecha_limite_parsed,
        pagado=False
    )
    db.add(deuda)
    await db.commit()
    await db.refresh(deuda)
    return deuda

@api_router.get("/proveedores/{proveedor_id}/deudas", response_model=List[DeudaProveedorResponse])
async def listar_deudas_proveedor(proveedor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeudaProveedor)
        .where(DeudaProveedor.proveedor_id == proveedor_id)
        .order_by(DeudaProveedor.creado_en.desc())
    )
    return result.scalars().all()

@api_router.put("/deudas/{deuda_id}/pagar")
async def pagar_deuda(deuda_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeudaProveedor).where(DeudaProveedor.id == deuda_id))
    deuda = result.scalar_one_or_none()
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    
    deuda.pagado = True
    deuda.fecha_pago = today_paraguay()
    await db.commit()
    return {"message": "Deuda marcada como pagada"}

@api_router.delete("/deudas/{deuda_id}")
async def eliminar_deuda(deuda_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeudaProveedor).where(DeudaProveedor.id == deuda_id))
    deuda = result.scalar_one_or_none()
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    await db.delete(deuda)
    await db.commit()
    return{"message": "Deuda eliminada"}



# ==================== PROVEEDOR PRODUCTOS (Vinculación) ====================
@api_router.get("/proveedores/{proveedor_id}/productos", response_model=List[ProveedorProductoResponse])
async def listar_proveedor_productos(proveedor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProveedorProducto, Producto)
        .join(Producto, ProveedorProducto.producto_id == Producto.id)
        .where(ProveedorProducto.proveedor_id == proveedor_id)
        .order_by(Producto.nombre)
    )
    rows = result.all()
    out = []
    for pp, prod in rows:
        out.append(ProveedorProductoResponse(
            id=pp.id,
            proveedor_id=pp.proveedor_id,
            producto_id=pp.producto_id,
            sku=pp.sku,
            costo=pp.costo,
            link=pp.link,
            producto_nombre=prod.nombre,
            producto_codigo=prod.codigo_barra,
        ))
    return out

@api_router.post("/proveedores/{proveedor_id}/productos", response_model=ProveedorProductoResponse)
async def vincular_proveedor_producto(proveedor_id: int, data: ProveedorProductoCreate, db: AsyncSession = Depends(get_db)):
    # Check if already linked
    existing = await db.execute(
        select(ProveedorProducto).where(
            ProveedorProducto.proveedor_id == proveedor_id,
            ProveedorProducto.producto_id == data.producto_id
        )
    )
    existing = existing.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Este producto ya está vinculado a este proveedor")

    prod_result = await db.execute(select(Producto).where(Producto.id == data.producto_id))
    prod = prod_result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    pp = ProveedorProducto(
        proveedor_id=proveedor_id,
        producto_id=data.producto_id,
        sku=data.sku,
        costo=data.costo,
        link=data.link,
    )
    db.add(pp)
    await db.commit()
    await db.refresh(pp)
    return ProveedorProductoResponse(
        id=pp.id,
        proveedor_id=pp.proveedor_id,
        producto_id=pp.producto_id,
        sku=pp.sku,
        costo=pp.costo,
        link=pp.link,
        producto_nombre=prod.nombre,
        producto_codigo=prod.codigo_barra,
    )

@api_router.put("/proveedor-productos/{pp_id}", response_model=ProveedorProductoResponse)
async def actualizar_proveedor_producto(pp_id: int, data: ProveedorProductoUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProveedorProducto, Producto)
        .join(Producto, ProveedorProducto.producto_id == Producto.id)
        .where(ProveedorProducto.id == pp_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Vinculación no encontrada")
    pp, prod = row
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pp, key, value)
    await db.commit()
    await db.refresh(pp)
    return ProveedorProductoResponse(
        id=pp.id,
        proveedor_id=pp.proveedor_id,
        producto_id=pp.producto_id,
        sku=pp.sku,
        costo=pp.costo,
        link=pp.link,
        producto_nombre=prod.nombre,
        producto_codigo=prod.codigo_barra,
    )

@api_router.delete("/proveedor-productos/{pp_id}")
async def eliminar_proveedor_producto(pp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProveedorProducto).where(ProveedorProducto.id == pp_id))
    pp = result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Vinculación no encontrada")
    await db.delete(pp)
    await db.commit()
    return {"message": "Vinculación eliminada"}

# ==================== CATEGORIAS ====================
@api_router.post("/categorias", response_model=CategoriaResponse)
async def crear_categoria(data: CategoriaCreate, db: AsyncSession = Depends(get_db)):
    categoria = Categoria(**data.model_dump())
    db.add(categoria)
    await db.commit()
    await db.refresh(categoria)
    return categoria

@api_router.get("/categorias", response_model=List[CategoriaResponse])
async def listar_categorias(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Categoria).where(Categoria.empresa_id == empresa_id))
    return result.scalars().all()

@api_router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
async def actualizar_categoria(categoria_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Categoria).where(Categoria.id == categoria_id))
    categoria = result.scalar_one_or_none()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if 'nombre' in data:
        categoria.nombre = data['nombre']
    await db.commit()
    await db.refresh(categoria)
    return categoria

@api_router.delete("/categorias/{categoria_id}")
async def eliminar_categoria(categoria_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Categoria).where(Categoria.id == categoria_id))
    categoria = result.scalar_one_or_none()
    if categoria:
        await db.delete(categoria)
        await db.commit()
    return {"message": "Categoría eliminada"}

# ==================== MARCAS ====================
@api_router.post("/marcas", response_model=MarcaResponse)
async def crear_marca(data: MarcaCreate, db: AsyncSession = Depends(get_db)):
    marca = Marca(**data.model_dump())
    db.add(marca)
    await db.commit()
    await db.refresh(marca)
    return marca

@api_router.get("/marcas", response_model=List[MarcaResponse])
async def listar_marcas(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Marca).where(Marca.empresa_id == empresa_id))
    return result.scalars().all()

@api_router.delete("/marcas/{marca_id}")
async def eliminar_marca(marca_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Marca).where(Marca.id == marca_id))
    marca = result.scalar_one_or_none()
    if marca:
        await db.delete(marca)
        await db.commit()
    return {"message": "Marca eliminada"}

@api_router.put("/marcas/{marca_id}", response_model=MarcaResponse)
async def actualizar_marca(marca_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Marca).where(Marca.id == marca_id))
    marca = result.scalar_one_or_none()
    if not marca:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    
    if 'nombre' in data:
        marca.nombre = data['nombre']
    
    await db.commit()
    await db.refresh(marca)
    return marca

# ==================== GASTOS ====================




# ==================== PRODUCTOS ====================
@api_router.post("/productos", response_model=ProductoResponse)
async def crear_producto(data: ProductoCreate, db: AsyncSession = Depends(get_db)):
    dump = data.model_dump()
    # Convert empty strings to NULL for unique-constrained fields
    if not dump.get('codigo_barra') or not str(dump['codigo_barra']).strip():
        dump['codigo_barra'] = None
    else:
        dump['codigo_barra'] = str(dump['codigo_barra']).strip()
        existing = await db.execute(
            select(Producto).where(Producto.codigo_barra == dump['codigo_barra'])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Código de barra ya existe")
    if not dump.get('imagen_url') or not str(dump['imagen_url']).strip():
        dump['imagen_url'] = None
    else:
        # Si pegan una URL de un tercero, se trae a local en el momento: asi no
        # se vuelve a llenar el catalogo de enlaces externos lentos o rotos.
        dump['imagen_url'] = await _localizar_si_es_externa(str(dump['imagen_url']).strip())
    producto = Producto(**dump)
    db.add(producto)
    await db.commit()
    await db.refresh(producto)
    return producto

@api_router.get("/productos/verificar-codigo-barra", response_model=Optional[ProductoCodigoBarraConflicto])
async def verificar_codigo_barra(
    codigo_barra: str,
    exclude_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Verifica si un código de barra ya está en uso por otro producto y devuelve sus detalles."""
    codigo = codigo_barra.strip()
    if not codigo:
        return None
    query = select(Producto).where(Producto.codigo_barra == codigo)
    if exclude_id:
        query = query.where(Producto.id != exclude_id)
    result = await db.execute(query)
    producto = result.scalar_one_or_none()
    if not producto:
        return None

    tres_meses_atras = now_paraguay() - timedelta(days=90)
    mov_result = await db.execute(
        select(func_sql.count(MovimientoStock.id))
        .where(
            MovimientoStock.producto_id == producto.id,
            MovimientoStock.creado_en >= tres_meses_atras
        )
    )
    tuvo_movimientos = (mov_result.scalar() or 0) > 0

    return ProductoCodigoBarraConflicto(
        id=producto.id,
        nombre=producto.nombre,
        creado_en=producto.creado_en,
        activo=producto.activo,
        tuvo_movimientos_3_meses=tuvo_movimientos
    )

@api_router.patch("/productos/{producto_id}/limpiar-codigo-barra", response_model=ProductoResponse)
async def limpiar_codigo_barra_producto(
    producto_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(verificar_es_admin)
):
    """Quita el código de barra de un producto en conflicto. Solo administradores."""
    result = await db.execute(select(Producto).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.codigo_barra = None
    await db.commit()
    await db.refresh(producto)
    return producto

def _select_productos_con_stock():
    """Productos con categoría, marca, proveedor y stock total en una sola consulta.
    El stock se agrega en una subconsulta: antes se lanzaba un SELECT por
    producto dentro del bucle (1 + N consultas, ~1.400ms con 1.200 productos)."""
    stock_sq = (
        select(
            StockActual.producto_id.label("producto_id"),
            func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0).label("stock_total"),
        )
        .group_by(StockActual.producto_id)
        .subquery()
    )
    return (
        select(
            Producto,
            Categoria.nombre,
            Marca.nombre,
            Proveedor.nombre,
            func_sql.coalesce(stock_sq.c.stock_total, 0),
        )
        .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
        .outerjoin(Marca, Producto.marca_id == Marca.id)
        .outerjoin(Proveedor, Producto.proveedor_id == Proveedor.id)
        .outerjoin(stock_sq, stock_sq.c.producto_id == Producto.id)
    )

def _producto_con_stock(producto, categoria_nombre, marca_nombre, proveedor_nombre, stock_total) -> ProductoConStock:
    prod = ProductoConStock.model_validate(producto)
    prod.stock_total = int(stock_total or 0)
    prod.categoria_nombre = categoria_nombre
    prod.marca_nombre = marca_nombre
    prod.proveedor_nombre = proveedor_nombre
    return prod

def _patron_contiene(valor: str) -> str:
    """Patrón LIKE para "contiene", con % y _ del usuario tomados literalmente (escape '\\')."""
    v = valor.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return f"%{v}%"

@api_router.get("/productos", response_model=List[ProductoConStock])
async def listar_productos(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Catálogo completo. Con miles de productos pesa decenas de MB: las pantallas usan
    GET /productos/buscar (paginado); esta ruta queda por compatibilidad."""
    result = await db.execute(
        _select_productos_con_stock()
        .where(Producto.empresa_id == empresa_id, Producto.activo == True)
    )
    return [_producto_con_stock(*row) for row in result.all()]

@api_router.get("/productos/buscar", response_model=ProductoPagina)
async def buscar_productos(
    empresa_id: int,
    q: Optional[str] = None,          # nombre o código de barras (selectores)
    nombre: Optional[str] = None,
    producto_id: Optional[int] = None,
    codigo: Optional[str] = None,
    marca: Optional[str] = None,
    categoria: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Búsqueda paginada de productos activos. Todos los filtros de texto son "contiene",
    sin distinguir mayúsculas; producto_id es exacto."""
    filtros = [Producto.empresa_id == empresa_id, Producto.activo == True]
    texto = (q or '').strip()
    # Un número también puede ser el ID del producto (el buscador de Ventas lo acepta)
    id_buscado = int(texto) if texto.isdigit() and int(texto) < 2**31 else None
    if texto:
        patron = _patron_contiene(texto)
        coincide = [Producto.nombre.ilike(patron, escape='\\'),
                    Producto.codigo_barra.ilike(patron, escape='\\')]
        if id_buscado is not None:
            coincide.append(Producto.id == id_buscado)
        filtros.append(or_(*coincide))
    if nombre and nombre.strip():
        filtros.append(Producto.nombre.ilike(_patron_contiene(nombre), escape='\\'))
    if producto_id is not None:
        filtros.append(Producto.id == producto_id)
    if codigo and codigo.strip():
        filtros.append(Producto.codigo_barra.ilike(_patron_contiene(codigo), escape='\\'))
    if marca and marca.strip():
        filtros.append(Marca.nombre.ilike(_patron_contiene(marca), escape='\\'))
    if categoria and categoria.strip():
        filtros.append(Categoria.nombre.ilike(_patron_contiene(categoria), escape='\\'))

    total = await db.scalar(
        select(func_sql.count(Producto.id))
        .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
        .outerjoin(Marca, Producto.marca_id == Marca.id)
        .where(*filtros)
    )
    if texto:
        # Primero los que empiezan con lo buscado (o código exacto), después el resto por nombre
        relevancia = case(
            (Producto.id == (id_buscado if id_buscado is not None else -1), 0),
            (Producto.codigo_barra == texto, 0),
            (Producto.nombre.ilike(f"{_patron_contiene(texto)[1:]}", escape='\\'), 1),
            else_=2,
        )
        orden = (relevancia, Producto.nombre, Producto.id)
    else:
        orden = (Producto.id,)
    result = await db.execute(
        _select_productos_con_stock().where(*filtros).order_by(*orden).limit(limit).offset(offset)
    )
    return ProductoPagina(
        items=[_producto_con_stock(*row) for row in result.all()],
        total=total or 0, limit=limit, offset=offset,
    )

@api_router.get("/productos/{producto_id}", response_model=ProductoConStock)
async def obtener_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Producto, Categoria, Marca, Proveedor)
        .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
        .outerjoin(Marca, Producto.marca_id == Marca.id)
        .outerjoin(Proveedor, Producto.proveedor_id == Proveedor.id)
        .where(Producto.id == producto_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto, categoria, marca, proveedor = row
    stock_result = await db.execute(
        select(func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0))
        .where(StockActual.producto_id == producto.id)
    )
    stock_total = stock_result.scalar() or 0
    
    prod_dict = ProductoResponse.model_validate(producto).model_dump()
    prod_dict['stock_total'] = stock_total
    prod_dict['categoria_nombre'] = categoria.nombre if categoria else None
    prod_dict['marca_nombre'] = marca.nombre if marca else None
    prod_dict['proveedor_nombre'] = proveedor.nombre if proveedor else None
    return ProductoConStock(**prod_dict)

@api_router.get("/productos/codigo/{codigo_barra}", response_model=ProductoConStock)
async def buscar_producto_por_codigo(codigo_barra: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Producto, Categoria, Marca, Proveedor)
        .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
        .outerjoin(Marca, Producto.marca_id == Marca.id)
        .outerjoin(Proveedor, Producto.proveedor_id == Proveedor.id)
        .where(Producto.codigo_barra == codigo_barra)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto, categoria, marca, proveedor = row
    stock_result = await db.execute(
        select(func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0))
        .where(StockActual.producto_id == producto.id)
    )
    stock_total = stock_result.scalar() or 0
    
    prod_dict = ProductoResponse.model_validate(producto).model_dump()
    prod_dict['stock_total'] = stock_total
    prod_dict['categoria_nombre'] = categoria.nombre if categoria else None
    prod_dict['marca_nombre'] = marca.nombre if marca else None
    prod_dict['proveedor_nombre'] = proveedor.nombre if proveedor else None
    return ProductoConStock(**prod_dict)

@api_router.put("/productos/{producto_id}", response_model=ProductoResponse)
async def actualizar_producto(producto_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Producto).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    for key, value in data.items():
        if hasattr(producto, key) and key != 'id':
            # Handle codigo_barra specially - treat empty strings as NULL
            if key == 'codigo_barra':
                if value == '' or value is None:
                    value = None
                elif value and value.strip():
                    # Check for uniqueness of non-empty codigo_barra
                    existing = await db.execute(
                        select(Producto).where(
                            Producto.codigo_barra == value.strip(),
                            Producto.id != producto_id
                        )
                    )
                    if existing.scalar_one_or_none():
                        raise HTTPException(status_code=400, detail="Código de barra ya existe")
                    value = value.strip()
            elif key == 'imagen_url' and value:
                value = await _localizar_si_es_externa(str(value).strip())
            setattr(producto, key, value)
    
    await db.commit()
    await db.refresh(producto)
    return producto

@api_router.delete("/productos/{producto_id}")
async def eliminar_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Producto).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Eliminar registros de stock asociados
    await db.execute(delete(StockActual).where(StockActual.producto_id == producto_id))
    
    # Eliminar movimientos de stock asociados
    await db.execute(delete(MovimientoStock).where(MovimientoStock.producto_id == producto_id))
    
    # Desactivar el producto
    producto.activo = False
    await db.commit()
    return {"message": "Producto y stock asociado eliminados"}

# ==================== UPLOAD IMAGEN PRODUCTO ====================
@api_router.post("/productos/{producto_id}/imagen")
async def subir_imagen_producto(producto_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Producto).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = UPLOADS_DIR / filename
    
    # Save file
    with open(filepath, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    
    # Update product
    producto.imagen_url = f"/uploads/productos/{filename}"
    await db.commit()
    await db.refresh(producto)
    
    return {"imagen_url": producto.imagen_url}

# ==================== LOCALIZAR IMAGENES EXTERNAS ====================
# Muchos productos tienen imagen_url apuntando a dominios de terceros (tiendas
# ajenas, miniaturas de buscadores). Cada uno es un handshake nuevo desde el
# navegador y muchos estan caidos o bloquean el hotlinking, lo que dejaba la
# pantalla de ventas cargando indefinidamente. Estas utilidades traen esas
# imagenes a uploads/productos para servirlas desde el propio backend.

IMAGEN_MAX_BYTES = 5 * 1024 * 1024
IMAGEN_TIMEOUT = 12.0
IMAGEN_USER_AGENT = "Mozilla/5.0 (compatible; EthercloudERP/1.0)"
IMAGEN_EXTENSIONES = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/pjpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
    'image/gif': 'gif',
    'image/avif': 'avif',
    'image/bmp': 'bmp',
}


def _host_es_interno(host: str) -> bool:
    """True si el host resuelve a una direccion de la red interna. Impide que una
    URL escrita en el formulario de producto use al backend como proxy hacia
    servicios privados (SSRF)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return True  # si no resuelve, no la tocamos
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return True
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return True
    return False


async def descargar_imagen_a_local(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """Descarga una imagen externa a uploads/productos y devuelve su ruta local
    (/uploads/productos/...). Devuelve None si no se puede: el llamador conserva
    entonces la URL original en lugar de perder la imagen."""
    if not url or not url.startswith(('http://', 'https://')):
        return None
    try:
        host = httpx.URL(url).host
    except Exception:
        return None
    if not host or _host_es_interno(host):
        return None

    try:
        async with client.stream('GET', url) as resp:
            if resp.status_code != 200:
                return None
            tipo = resp.headers.get('content-type', '').split(';')[0].strip().lower()
            if tipo not in IMAGEN_EXTENSIONES:
                return None
            datos = bytearray()
            async for trozo in resp.aiter_bytes():
                datos.extend(trozo)
                if len(datos) > IMAGEN_MAX_BYTES:
                    return None  # imagen desproporcionada: se deja como esta
    except Exception:
        return None

    if not datos:
        return None

    filename = f"{uuid.uuid4()}.{IMAGEN_EXTENSIONES[tipo]}"
    try:
        (UPLOADS_DIR / filename).write_bytes(bytes(datos))
    except Exception as e:
        logger.warning(f"No se pudo guardar la imagen descargada de {url}: {e}")
        return None
    return f"/uploads/productos/{filename}"


def _cliente_imagenes() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=IMAGEN_TIMEOUT,
        follow_redirects=True,
        headers={'User-Agent': IMAGEN_USER_AGENT},
    )


async def _localizar_si_es_externa(url: Optional[str]) -> Optional[str]:
    """Devuelve la ruta local si consigue descargar la imagen; si no, la URL tal cual.
    Nunca falla el guardado del producto por un problema de red."""
    if not url or not url.startswith(('http://', 'https://')):
        return url
    try:
        async with _cliente_imagenes() as client:
            return await descargar_imagen_a_local(url, client) or url
    except Exception as e:
        logger.warning(f"No se pudo localizar la imagen {url}: {e}")
        return url


@api_router.post("/admin/localizar-imagenes-productos")
async def localizar_imagenes_productos(
    empresa_id: int,
    limite: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_usuario),
):
    """Trae a local las imagenes de producto todavia alojadas en terceros.

    Es idempotente y reanudable: solo mira los productos cuya imagen_url sigue
    siendo http(s), asi que se puede llamar repetidamente en tandas hasta que
    'restantes' llegue a 0. Los que fallan (enlace muerto, hotlink bloqueado)
    conservan su URL original y se listan en la respuesta.
    """
    result = await db.execute(
        select(Producto)
        .where(
            Producto.empresa_id == empresa_id,
            Producto.imagen_url.is_not(None),
            Producto.imagen_url.like('http%'),
        )
        .order_by(Producto.id)
        .limit(limite)
    )
    productos = result.scalars().all()

    semaforo = asyncio.Semaphore(8)  # no saturar la red ni los hosts remotos

    async def procesar(producto):
        async with semaforo:
            return producto, await descargar_imagen_a_local(producto.imagen_url, client)

    async with _cliente_imagenes() as client:
        resultados = await asyncio.gather(*(procesar(p) for p in productos))

    migradas = 0
    fallidas = []
    for producto, ruta_local in resultados:
        if ruta_local:
            producto.imagen_url = ruta_local
            migradas += 1
        else:
            fallidas.append({"id": producto.id, "nombre": producto.nombre, "url": producto.imagen_url})
    await db.commit()

    restantes = await db.scalar(
        select(func_sql.count())
        .select_from(Producto)
        .where(
            Producto.empresa_id == empresa_id,
            Producto.imagen_url.is_not(None),
            Producto.imagen_url.like('http%'),
        )
    )

    logger.info(f"Localizar imagenes: {migradas} migradas, {len(fallidas)} fallidas, {restantes} restantes")
    return {
        "procesadas": len(productos),
        "migradas": migradas,
        "fallidas": len(fallidas),
        "restantes": restantes or 0,
        "detalle_fallidas": fallidas,
    }

# ==================== MATERIAS LABORATORIO ====================
import uuid as _uuid

@api_router.post("/materias-laboratorio", response_model=MateriaLaboratorioResponse)
async def crear_materia_laboratorio(data: MateriaLaboratorioCreate, db: AsyncSession = Depends(get_db)):
    # Auto-generate unique barcode if not provided
    if not data.codigo_barra:
        while True:
            codigo = f"LAB{_uuid.uuid4().hex[:8].upper()}"
            dup_mat = await db.execute(
                select(MateriaLaboratorio).where(MateriaLaboratorio.codigo_barra == codigo)
            )
            dup_prod = await db.execute(
                select(Producto).where(Producto.codigo_barra == codigo)
            )
            if not dup_mat.scalar_one_or_none() and not dup_prod.scalar_one_or_none():
                data.codigo_barra = codigo
                break
    else:
        existing = await db.execute(
            select(MateriaLaboratorio).where(MateriaLaboratorio.codigo_barra == data.codigo_barra)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Código de barra ya existe")
        
        existing_prod = await db.execute(
            select(Producto).where(Producto.codigo_barra == data.codigo_barra)
        )
        if existing_prod.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Código de barra ya existe en productos")
    
    materia = MateriaLaboratorio(**data.model_dump(), creado_en=now_paraguay())
    db.add(materia)
    await db.commit()
    await db.refresh(materia)
    return materia

@api_router.get("/materias-laboratorio", response_model=MateriaLaboratorioPage)
async def listar_materias_laboratorio(
    empresa_id: int,
    search: Optional[str] = None,
    estado: Optional[EstadoMateria] = None,
    orden: str = Query("newest", pattern="^(newest|oldest)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Listado paginado. El filtrado y el orden se resuelven en la base de datos:
    antes se devolvían todas las materias de la empresa (miles de filas) y el
    frontend las filtraba en memoria.
    """
    filtros = [MateriaLaboratorio.empresa_id == empresa_id]
    if search:
        filtros.append(MateriaLaboratorio.nombre.ilike(f"%{search.strip()}%"))
    if estado is not None:
        filtros.append(MateriaLaboratorio.estado == estado)

    total = await db.scalar(
        select(func_sql.count()).select_from(MateriaLaboratorio).where(*filtros)
    )

    orden_col = (
        MateriaLaboratorio.creado_en.desc() if orden == "newest"
        else MateriaLaboratorio.creado_en.asc()
    )
    result = await db.execute(
        select(MateriaLaboratorio)
        .where(*filtros)
        # id como desempate: creado_en se repite y sin él la paginación baila
        .order_by(orden_col, MateriaLaboratorio.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return MateriaLaboratorioPage(
        items=result.scalars().all(),
        total=total or 0,
        limit=limit,
        offset=offset,
    )

@api_router.get("/materias-laboratorio/disponibles", response_model=List[MateriaLaboratorioResponse])
async def listar_materias_disponibles(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MateriaLaboratorio).where(
            MateriaLaboratorio.empresa_id == empresa_id,
            MateriaLaboratorio.estado == EstadoMateria.DISPONIBLE
        )
    )
    return result.scalars().all()

@api_router.put("/materias-laboratorio/{materia_id}", response_model=MateriaLaboratorioResponse)
async def actualizar_materia_laboratorio(materia_id: int, data: MateriaLaboratorioUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MateriaLaboratorio).where(MateriaLaboratorio.id == materia_id))
    materia = result.scalar_one_or_none()
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    if materia.estado != EstadoMateria.DISPONIBLE:
        raise HTTPException(status_code=400, detail="Solo se pueden editar materias con estado DISPONIBLE")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(materia, field, value)
    await db.commit()
    await db.refresh(materia)
    return materia

@api_router.delete("/materias-laboratorio/{materia_id}", status_code=204)
async def eliminar_materia_laboratorio(materia_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MateriaLaboratorio).where(MateriaLaboratorio.id == materia_id))
    materia = result.scalar_one_or_none()
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    if materia.estado != EstadoMateria.DISPONIBLE:
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar materias con estado DISPONIBLE")
    await db.delete(materia)
    await db.commit()

# ==================== ALMACENES ====================
@api_router.post("/almacenes", response_model=AlmacenResponse)
async def crear_almacen(data: AlmacenCreate, db: AsyncSession = Depends(get_db)):
    almacen = Almacen(**data.model_dump())
    db.add(almacen)
    await db.commit()
    await db.refresh(almacen)
    return almacen

@api_router.get("/almacenes", response_model=List[AlmacenResponse])
async def listar_almacenes(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Almacen).where(Almacen.empresa_id == empresa_id))
    return result.scalars().all()

# ==================== STOCK FIFO HELPERS ====================



# ==================== STOCK ====================
@api_router.post("/stock", response_model=StockActualResponse)
async def crear_actualizar_stock(data: StockActualCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StockActual).where(
            StockActual.producto_id == data.producto_id,
            StockActual.almacen_id == data.almacen_id
        )
    )
    stock = result.scalar_one_or_none()
    
    if stock:
        stock.cantidad = data.cantidad
        if data.alerta_minima is not None:
            stock.alerta_minima = data.alerta_minima
    else:
        stock = StockActual(**data.model_dump())
        db.add(stock)
    
    await db.commit()
    await db.refresh(stock)
    return stock

@api_router.get("/stock", response_model=List[StockConDetalles])
async def listar_stock(empresa_id: int, almacen_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    query = (
        select(StockActual, Producto, Almacen)
        .join(Producto, StockActual.producto_id == Producto.id)
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .where(Producto.empresa_id == empresa_id)
    )
    if almacen_id:
        query = query.where(StockActual.almacen_id == almacen_id)
    
    result = await db.execute(query)
    return [_stock_con_detalles(*row) for row in result.all()]

def _stock_con_detalles(stock, producto, almacen) -> StockConDetalles:
    stock_dict = StockActualResponse.model_validate(stock).model_dump()
    stock_dict['producto_nombre'] = producto.nombre
    stock_dict['producto_codigo_barra'] = producto.codigo_barra
    stock_dict['almacen_nombre'] = almacen.nombre
    return StockConDetalles(**stock_dict)

@api_router.get("/stock/totales-por-almacen")
async def stock_totales_por_almacen(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Unidades en stock por almacén, para las tarjetas de la pantalla Stock
    (antes se sumaban en el navegador sobre el inventario completo)."""
    result = await db.execute(
        select(StockActual.almacen_id, func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0))
        .join(Producto, StockActual.producto_id == Producto.id)
        .where(Producto.empresa_id == empresa_id)
        .group_by(StockActual.almacen_id)
    )
    return [{"almacen_id": almacen_id, "total_unidades": int(total)} for almacen_id, total in result.all()]

@api_router.get("/stock/buscar", response_model=StockPagina)
async def buscar_stock(
    empresa_id: int,
    almacen_id: Optional[int] = None,
    nombre: Optional[str] = None,
    producto_id: Optional[int] = None,
    codigo: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Inventario paginado, ordenado por producto y almacén. Mismos filtros que la pantalla
    Stock: nombre y código "contiene", producto_id exacto."""
    filtros = [Producto.empresa_id == empresa_id]
    if almacen_id:
        filtros.append(StockActual.almacen_id == almacen_id)
    if nombre and nombre.strip():
        filtros.append(Producto.nombre.ilike(_patron_contiene(nombre), escape='\\'))
    if producto_id is not None:
        filtros.append(StockActual.producto_id == producto_id)
    if codigo and codigo.strip():
        filtros.append(Producto.codigo_barra.ilike(_patron_contiene(codigo), escape='\\'))

    total = await db.scalar(
        select(func_sql.count(StockActual.id))
        .join(Producto, StockActual.producto_id == Producto.id)
        .where(*filtros)
    )
    result = await db.execute(
        select(StockActual, Producto, Almacen)
        .join(Producto, StockActual.producto_id == Producto.id)
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .where(*filtros)
        .order_by(Producto.nombre, Almacen.nombre, StockActual.id)
        .limit(limit).offset(offset)
    )
    return StockPagina(
        items=[_stock_con_detalles(*row) for row in result.all()],
        total=total or 0, limit=limit, offset=offset,
    )


async def _consume_entrada_fifo(db: AsyncSession, producto_id: int, almacen_id: int, cantidad_consumida: int):
    """Reduce cantidad_restante on ENTRADA batches using FIFO (oldest batch first)."""
    result = await db.execute(
        select(MovimientoStock)
        .where(
            MovimientoStock.producto_id == producto_id,
            MovimientoStock.almacen_id == almacen_id,
            MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
            MovimientoStock.cantidad_restante > 0
        )
        .order_by(MovimientoStock.creado_en.asc())
    )
    batches = result.scalars().all()
    remaining = cantidad_consumida
    for batch in batches:
        if remaining <= 0:
            break
        consumable = min(batch.cantidad_restante, remaining)
        batch.cantidad_restante -= consumable
        remaining -= consumable


async def _restore_entrada_fifo(db: AsyncSession, producto_id: int, almacen_id: int, cantidad_restaurar: int):
    """Restore cantidad_restante on ENTRADA batches — newest first (FIFO reversal)."""
    result = await db.execute(
        select(MovimientoStock)
        .where(
            MovimientoStock.producto_id == producto_id,
            MovimientoStock.almacen_id == almacen_id,
            MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
            MovimientoStock.cantidad_restante < MovimientoStock.cantidad
        )
        .order_by(MovimientoStock.creado_en.desc())
    )
    batches = result.scalars().all()
    remaining = cantidad_restaurar
    for batch in batches:
        if remaining <= 0:
            break
        can_restore = min(batch.cantidad - batch.cantidad_restante, remaining)
        batch.cantidad_restante += can_restore
        remaining -= can_restore


async def _recalculate_precio_costo_fifo(db: AsyncSession, producto_id: int):
    """After a consumption, recalculate producto.precio_costo based on remaining active ENTRADA batches.
    - 1 active batch  → use its real costo_unitario
    - Multiple batches → weighted average CPP across all active batches
    - 0 active batches → no change
    """
    result = await db.execute(
        select(MovimientoStock)
        .where(
            MovimientoStock.producto_id == producto_id,
            MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
            MovimientoStock.cantidad_restante > 0,
            MovimientoStock.costo_unitario.isnot(None),
        )
        .order_by(MovimientoStock.creado_en.asc())
    )
    active_batches = result.scalars().all()

    if not active_batches:
        return  # nothing to recalculate

    if len(active_batches) == 1:
        new_costo = active_batches[0].costo_unitario
    else:
        total_qty = sum(b.cantidad_restante for b in active_batches)
        if total_qty == 0:
            return
        total_value = sum(
            Decimal(str(b.costo_unitario)) * Decimal(str(b.cantidad_restante))
            for b in active_batches
        )
        new_costo = round(total_value / Decimal(str(total_qty)))

    prod_result = await db.execute(select(Producto).where(Producto.id == producto_id))
    producto_obj = prod_result.scalar_one_or_none()
    if producto_obj:
        producto_obj.precio_costo = new_costo


@api_router.post("/stock/entrada")
async def entrada_stock(data: MovimientoStockCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StockActual).where(
            StockActual.producto_id == data.producto_id,
            StockActual.almacen_id == data.almacen_id
        )
    )
    stock = result.scalar_one_or_none()
    
    if stock:
        stock.cantidad += data.cantidad
    else:
        stock = StockActual(
            producto_id=data.producto_id,
            almacen_id=data.almacen_id,
            cantidad=data.cantidad
        )
        db.add(stock)
    
    # Actualizar precio_costo y/o proveedor del producto si se proporcionan
    if data.costo_unitario is not None or data.costo_ponderado is not None or data.proveedor_id is not None or data.precio_venta is not None:
        prod_result = await db.execute(select(Producto).where(Producto.id == data.producto_id))
        producto_obj = prod_result.scalar_one_or_none()
        if producto_obj:
            # Use CPP if provided, otherwise fall back to real unit cost
            costo_para_producto = data.costo_ponderado if data.costo_ponderado is not None else data.costo_unitario
            if costo_para_producto is not None:
                producto_obj.precio_costo = costo_para_producto
            if data.proveedor_id is not None:
                producto_obj.proveedor_id = data.proveedor_id
            if data.precio_venta is not None:
                producto_obj.precio_venta = data.precio_venta

    movimiento = MovimientoStock(
        producto_id=data.producto_id,
        almacen_id=data.almacen_id,
        tipo=TipoMovimientoStock.ENTRADA,
        cantidad=data.cantidad,
        referencia_tipo=data.referencia_tipo,
        referencia_id=data.referencia_id,
        proveedor_id=data.proveedor_id,
        costo_unitario=data.costo_unitario,
        costo_ponderado=data.costo_ponderado,
        condicion_pago=data.condicion_pago,
        fecha_limite_pago=data.fecha_limite_pago,
        notas=data.notas,
        cantidad_restante=data.cantidad,
        creado_en=now_paraguay()
    )
    db.add(movimiento)

    # Si la condición de pago es crédito, crear deuda al proveedor
    if data.condicion_pago == 'credito' and data.proveedor_id and data.costo_unitario is not None:
        total_deuda = Decimal(str(data.costo_unitario)) * Decimal(str(data.cantidad))
        # Obtener nombre del producto para la descripción
        prod_res = await db.execute(select(Producto.nombre).where(Producto.id == data.producto_id))
        prod_nombre = prod_res.scalar_one_or_none() or 'Producto'
        deuda = DeudaProveedor(
            proveedor_id=data.proveedor_id,
            monto=total_deuda,
            descripcion=f"Entrada de stock: {data.cantidad} x {prod_nombre}" + (f" - {data.notas}" if data.notas else ""),
            fecha_emision=now_paraguay().date(),
            fecha_limite=data.fecha_limite_pago,
            pagado=False
        )
        db.add(deuda)
    
    await db.commit()
    await db.refresh(movimiento)
    return movimiento

@api_router.post("/stock/traspaso")
async def traspasar_stock(data: TraspasoStockCreate, db: AsyncSession = Depends(get_db)):
    result_origen = await db.execute(
        select(StockActual).where(
            StockActual.producto_id == data.producto_id,
            StockActual.almacen_id == data.almacen_origen_id
        )
    )
    stock_origen = result_origen.scalar_one_or_none()
    
    if not stock_origen or stock_origen.cantidad < data.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente en almacén origen")
    
    stock_origen.cantidad -= data.cantidad
    
    result_destino = await db.execute(
        select(StockActual).where(
            StockActual.producto_id == data.producto_id,
            StockActual.almacen_id == data.almacen_destino_id
        )
    )
    stock_destino = result_destino.scalar_one_or_none()
    
    if stock_destino:
        stock_destino.cantidad += data.cantidad
    else:
        stock_destino = StockActual(
            producto_id=data.producto_id,
            almacen_id=data.almacen_destino_id,
            cantidad=data.cantidad
        )
        db.add(stock_destino)
    
    mov_salida = MovimientoStock(
        producto_id=data.producto_id,
        almacen_id=data.almacen_origen_id,
        tipo=TipoMovimientoStock.TRASPASO,
        cantidad=-data.cantidad,
        creado_en=now_paraguay()
    )
    mov_entrada = MovimientoStock(
        producto_id=data.producto_id,
        almacen_id=data.almacen_destino_id,
        tipo=TipoMovimientoStock.TRASPASO,
        cantidad=data.cantidad,
        creado_en=now_paraguay()
    )
    db.add(mov_salida)
    db.add(mov_entrada)
    
    await db.commit()
    return {"message": "Traspaso realizado correctamente"}

@api_router.post("/stock/salida")
async def registrar_salida_stock(data: SalidaStockCreate, db: AsyncSession = Depends(get_db)):
    """Registra unasalida/eliminación de stock (rotura, robo, etc.)"""
    
    result = await db.execute(
        select(StockActual).where(
            StockActual.producto_id == data.producto_id,
            StockActual.almacen_id == data.almacen_id
        )
    )
    stock = result.scalar_one_or_none()
    
    if not stock:
        raise HTTPException(status_code=404, detail="No hay stock disponible en este almacén")
    
    if stock.cantidad < data.cantidad:
        raise HTTPException(
            status_code=400, 
            detail=f"Stock insuficiente. Disponible: {stock.cantidad}, solicitado: {data.cantidad}"
        )
    
    # Consume from FIFO batches
    await _consume_entrada_fifo(db, data.producto_id, data.almacen_id, data.cantidad)
    
    # Update stock quantity
    stock.cantidad -= data.cantidad
    
    # Recalculate average cost
    await _recalculate_precio_costo_fifo(db, data.producto_id)
    
    # Register movement
    movimiento = MovimientoStock(
        producto_id=data.producto_id,
        almacen_id=data.almacen_id,
        tipo=TipoMovimientoStock.SALIDA,
        cantidad=-data.cantidad,
        notas=data.motivo,
        creado_en=now_paraguay()
    )
    db.add(movimiento)

    await db.commit()
    return {"message": "Salida registrada correctamente", "stock_restante": stock.cantidad}

@api_router.put("/stock/{stock_id}/alerta", response_model=StockActualResponse)
async def configurar_alerta_stock(stock_id: int, alerta_minima: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StockActual).where(StockActual.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock no encontrado")
    
    stock.alerta_minima = alerta_minima
    await db.commit()
    await db.refresh(stock)
    return stock

@api_router.get("/stock/historial/{producto_id}", response_model=List[EntradaStockHistorialResponse])
async def historial_stock_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna el historial de movimientos de stock para un producto específico"""
    result = await db.execute(
        select(MovimientoStock)
        .where(MovimientoStock.producto_id == producto_id)
        .order_by(MovimientoStock.creado_en.desc())
    )
    movimientos = result.scalars().all()

    response = []
    for mov in movimientos:
        # Obtener nombre del proveedor
        proveedor_nombre = None
        if mov.proveedor_id:
            prov_result = await db.execute(select(Proveedor.nombre).where(Proveedor.id == mov.proveedor_id))
            proveedor_nombre = prov_result.scalar_one_or_none()

        # Obtener nombre del almacén
        almacen_nombre = None
        if mov.almacen_id:
            alm_result = await db.execute(select(Almacen.nombre).where(Almacen.id == mov.almacen_id))
            almacen_nombre = alm_result.scalar_one_or_none()

        # Calcular total de compra
        total_compra = None
        if mov.costo_unitario is not None:
            total_compra = Decimal(str(mov.costo_unitario)) * Decimal(str(abs(mov.cantidad)))

        response.append(EntradaStockHistorialResponse(
            id=mov.id,
            producto_id=mov.producto_id,
            almacen_id=mov.almacen_id,
            tipo=mov.tipo,
            cantidad=mov.cantidad,
            costo_unitario=mov.costo_unitario,
            costo_ponderado=mov.costo_ponderado,
            total_compra=total_compra,
            condicion_pago=mov.condicion_pago,
            fecha_limite_pago=mov.fecha_limite_pago,
            notas=mov.notas,
            proveedor_id=mov.proveedor_id,
            proveedor_nombre=proveedor_nombre,
            almacen_nombre=almacen_nombre,
            referencia_tipo=mov.referencia_tipo,
            referencia_id=mov.referencia_id,
            creado_en=mov.creado_en,
            cantidad_restante=mov.cantidad_restante,
            estado=(
                "Activo" if (mov.cantidad_restante or 0) > 0
                else "Agotado" if mov.cantidad_restante == 0
                else "Activo"  # old records without tracking
            ) if mov.tipo == TipoMovimientoStock.ENTRADA else None
        ))

    return response

# ==================== VENTAS ====================
@api_router.post("/ventas", response_model=VentaResponse)
async def crear_venta(data: VentaCreate, crear_pendiente: bool = False, db: AsyncSession = Depends(get_db)):
    # Get client
    cliente_result = await db.execute(select(Cliente).where(Cliente.id == data.cliente_id))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Si hay representante, usar sus privilegios (descuento y crédito)
    cliente_privilegios = cliente
    if data.representante_cliente_id:
        rep_result = await db.execute(select(Cliente).where(Cliente.id == data.representante_cliente_id))
        representante = rep_result.scalar_one_or_none()
        if representante:
            cliente_privilegios = representante
    
    # Si es venta pendiente, no validar stock ni crédito todavía
    if not crear_pendiente:
        # Validate cheque payment - usar privilegios del cliente efectivo
        if data.tipo_pago == TipoPago.CHEQUE and not cliente_privilegios.acepta_cheque:
            raise HTTPException(status_code=400, detail="Este cliente no tiene habilitado el pago con cheque")
    
    descuento_porcentaje = cliente_privilegios.descuento_porcentaje or Decimal('0')
    
    subtotal = Decimal('0')
    costo_total = Decimal('0')
    items_data = []
    
    # Solo validar stock si no es venta pendiente
    for item in data.items:
        item_total = Decimal(str(item.cantidad)) * item.precio_unitario
        subtotal += item_total

        # Fetch precio_costo: productos usan costo real, materias laboratorio usan precio * (1 - LAB_MARGEN_GANANCIA)
        precio_costo = Decimal('0')
        if item.producto_id:
            prod_costo_res = await db.execute(
                select(Producto.precio_costo).where(Producto.id == item.producto_id)
            )
            raw_costo = prod_costo_res.scalar_one_or_none()
            precio_costo = Decimal(str(raw_costo or 0))
        elif item.materia_laboratorio_id:
            precio_costo = item.precio_unitario * (Decimal('1') - LAB_MARGEN_GANANCIA)
        costo_total += Decimal(str(item.cantidad)) * precio_costo

        items_data.append({
            **item.model_dump(),
            'total': item_total,
            'precio_costo': precio_costo,
        })
        
        if not crear_pendiente and item.producto_id:
            stock_result = await db.execute(
                select(func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0))
                .where(StockActual.producto_id == item.producto_id)
            )
            stock_total = stock_result.scalar() or 0
            if stock_total < item.cantidad:
                prod_result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
                prod = prod_result.scalar_one_or_none()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stock insuficiente para {prod.nombre if prod else 'producto'}. Disponible: {stock_total}"
                )
    
    descuento = subtotal * descuento_porcentaje / Decimal('100')
    subtotal_con_descuento = subtotal - descuento
    iva = subtotal_con_descuento * Decimal('10') / Decimal('110')
    total = subtotal_con_descuento
    ganancia = total - costo_total
    
    # Validar crédito si es venta a crédito y no es pendiente
    if not crear_pendiente and data.tipo_pago == TipoPago.CREDITO:
        # Calcular crédito usado del cliente que tiene los privilegios
        creditos_result = await db.execute(
            select(func_sql.coalesce(func_sql.sum(CreditoCliente.monto_pendiente), 0))
            .where(CreditoCliente.cliente_id == cliente_privilegios.id, CreditoCliente.pagado == False)
        )
        credito_usado = creditos_result.scalar() or Decimal('0')
        limite = cliente_privilegios.limite_credito or Decimal('0')
        
        if limite > 0 and (credito_usado + total) > limite:
            disponible = max(Decimal('0'), limite - credito_usado)
            raise HTTPException(
                status_code=400, 
                detail=f"Crédito insuficiente. Límite: {float(limite):,.0f}, Usado: {float(credito_usado):,.0f}, Disponible: {float(disponible):,.0f} Gs"
            )
    
    venta = Venta(
        empresa_id=data.empresa_id,
        cliente_id=data.cliente_id,
        usuario_id=data.usuario_id,
        representante_cliente_id=data.representante_cliente_id,
        total=total,
        iva=iva,
        descuento=descuento,
        costo_total=costo_total,
        ganancia=ganancia,
        tipo_pago=data.tipo_pago,
        es_delivery=data.es_delivery,
        estado=EstadoVenta.PENDIENTE if crear_pendiente else EstadoVenta.BORRADOR,
        creado_en=now_paraguay()
    )
    db.add(venta)
    await db.flush()
    
    for item_data in items_data:
        venta_item = VentaItem(venta_id=venta.id, **item_data)
        db.add(venta_item)
    
    await db.commit()
    await db.refresh(venta)
    return venta

@api_router.post("/ventas/{venta_id}/confirmar", response_model=VentaResponse)
async def confirmar_venta(venta_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Venta).options(selectinload(Venta.items)).where(Venta.id == venta_id)
    )
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if venta.estado != EstadoVenta.BORRADOR:
        raise HTTPException(status_code=400, detail="La venta ya fue procesada")
    
    for item in venta.items:
        if item.producto_id:
            stock_result = await db.execute(
                select(StockActual)
                .where(StockActual.producto_id == item.producto_id, StockActual.cantidad > 0)
                .order_by(StockActual.cantidad.desc())
            )
            stocks = stock_result.scalars().all()
            
            cantidad_restante = item.cantidad
            for stock in stocks:
                if cantidad_restante <= 0:
                    break
                    
                a_descontar = min(stock.cantidad, cantidad_restante)
                stock.cantidad -= a_descontar
                cantidad_restante -= a_descontar
                
                await _consume_entrada_fifo(db, item.producto_id, stock.almacen_id, a_descontar)
                
                mov = MovimientoStock(
                    producto_id=item.producto_id,
                    almacen_id=stock.almacen_id,
                    tipo=TipoMovimientoStock.SALIDA,
                    cantidad=-a_descontar,
                    referencia_tipo='venta',
                    referencia_id=venta.id,
                    creado_en=now_paraguay()
                )
                db.add(mov)
        
            await _recalculate_precio_costo_fifo(db, item.producto_id)

        elif item.materia_laboratorio_id:
            materia_result = await db.execute(
                select(MateriaLaboratorio).where(MateriaLaboratorio.id == item.materia_laboratorio_id)
            )
            materia = materia_result.scalar_one_or_none()
            if materia:
                materia.estado = EstadoMateria.VENDIDO
    
    venta.estado = EstadoVenta.CONFIRMADA
    
    # Si es venta a crédito, crear registro de crédito
    if venta.tipo_pago == TipoPago.CREDITO:
        # Determinar el cliente que tiene los privilegios de crédito
        cliente_credito_id = venta.representante_cliente_id or venta.cliente_id
        
        credito = CreditoCliente(
            cliente_id=cliente_credito_id,
            venta_id=venta.id,
            monto_original=venta.total,
            monto_pendiente=venta.total,
            descripcion=f"Venta #{venta.id}",
            fecha_venta=today_paraguay()
        )
        db.add(credito)
    
    # Si es delivery, crear entrega automáticamente en estado PENDIENTE
    if venta.es_delivery:
        # Verificar si ya existe entrega para esta venta
        entrega_existente = await db.execute(
            select(Entrega).where(Entrega.venta_id == venta.id)
        )
        if not entrega_existente.scalar_one_or_none():
            entrega = Entrega(
                venta_id=venta.id,
                vehiculo_id=None,
                responsable_usuario_id=None,
                estado=EstadoEntrega.PENDIENTE
            )
            db.add(entrega)
    
    await db.commit()
    await db.refresh(venta)
    return venta

@api_router.put("/ventas/{venta_id}", response_model=VentaResponse)
async def actualizar_venta_pendiente(venta_id: int, data: VentaUpdate, db: AsyncSession = Depends(get_db)):
    """Permite editar una venta PENDIENTE: cambiar cliente, items, descuentos, tipo de pago"""
    result = await db.execute(
        select(Venta).options(selectinload(Venta.items)).where(Venta.id == venta_id)
    )
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if venta.estado != EstadoVenta.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden editar ventas PENDIENTES")
    
    # Update cliente if provided
    if data.cliente_id is not None:
        cliente_result = await db.execute(select(Cliente).where(Cliente.id == data.cliente_id))
        cliente = cliente_result.scalar_one_or_none()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        venta.cliente_id = data.cliente_id
    
    # Update representante if provided
    if data.representante_cliente_id is not None:
        venta.representante_cliente_id = data.representante_cliente_id
    
    # Update tipo_pago if provided
    if data.tipo_pago is not None:
        venta.tipo_pago = data.tipo_pago
    
    # Update es_delivery if provided
    if data.es_delivery is not None:
        venta.es_delivery = data.es_delivery
    
    # Update items if provided
    if data.items is not None:
        # Delete existing items
        for item in venta.items:
            await db.delete(item)
        await db.flush()
        
        # Get cliente para descuento
        cliente_result = await db.execute(select(Cliente).where(Cliente.id == venta.cliente_id))
        cliente = cliente_result.scalar_one_or_none()
        
        # Si hay representante, usar sus privilegios
        cliente_privilegios = cliente
        if venta.representante_cliente_id:
            rep_result = await db.execute(select(Cliente).where(Cliente.id == venta.representante_cliente_id))
            representante = rep_result.scalar_one_or_none()
            if representante:
                cliente_privilegios = representante
        
        descuento_porcentaje = cliente_privilegios.descuento_porcentaje or Decimal('0')
        
        # Recalculate totals with new items
        subtotal = Decimal('0')
        costo_total = Decimal('0')
        for item in data.items:
            item_total = Decimal(str(item.cantidad)) * item.precio_unitario
            subtotal += item_total

            # Fetch precio_costo: productos usan costo real, materias laboratorio usan precio * (1 - LAB_MARGEN_GANANCIA)
            precio_costo = Decimal('0')
            if item.producto_id:
                prod_costo_res = await db.execute(
                    select(Producto.precio_costo).where(Producto.id == item.producto_id)
                )
                raw_costo = prod_costo_res.scalar_one_or_none()
                precio_costo = Decimal(str(raw_costo or 0))
            elif item.materia_laboratorio_id:
                precio_costo = item.precio_unitario * (Decimal('1') - LAB_MARGEN_GANANCIA)
            costo_total += Decimal(str(item.cantidad)) * precio_costo
            
            venta_item = VentaItem(
                venta_id=venta.id,
                producto_id=item.producto_id,
                materia_laboratorio_id=item.materia_laboratorio_id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                precio_costo=precio_costo,
                total=item_total,
                observaciones=item.observaciones
            )
            db.add(venta_item)
        
        descuento = subtotal * descuento_porcentaje / Decimal('100')
        subtotal_con_descuento = subtotal - descuento
        iva = subtotal_con_descuento * Decimal('10') / Decimal('110')
        
        venta.descuento = descuento
        venta.iva = iva
        venta.total = subtotal_con_descuento
        venta.costo_total = costo_total
        venta.ganancia = subtotal_con_descuento - costo_total
    
    await db.commit()
    await db.refresh(venta)
    return venta

@api_router.get("/ventas/{venta_id}/fechas-impresion")
async def obtener_fechas_impresion(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Fecha real de la venta + fechas de impresion corregidas (si las hay)"""
    result = await db.execute(select(Venta).where(Venta.id == venta_id))
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    creado_en_py = None
    if venta.creado_en:
        creado_en_py = (
            venta.creado_en.astimezone(PARAGUAY_TZ) if venta.creado_en.tzinfo
            else venta.creado_en.replace(tzinfo=timezone.utc).astimezone(PARAGUAY_TZ)
        )

    return {
        "venta_id": venta.id,
        "fecha_original": creado_en_py.strftime('%Y-%m-%d') if creado_en_py else None,
        "hora_original": creado_en_py.strftime('%I:%M %p') if creado_en_py else None,
        "fecha_impresion_boleta": venta.fecha_impresion_boleta.isoformat() if venta.fecha_impresion_boleta else None,
        "fecha_impresion_factura": venta.fecha_impresion_factura.isoformat() if venta.fecha_impresion_factura else None,
    }

@api_router.put("/ventas/{venta_id}/fecha-impresion")
async def actualizar_fecha_impresion(venta_id: int, data: FechaImpresionUpdate, db: AsyncSession = Depends(get_db)):
    """Cambia SOLO la fecha que se imprime en la boleta o factura.

    La fecha real de la venta (creado_en) no se modifica: reportes, cierres,
    filtros y stock siguen usando la fecha original.
    """
    tipo = (data.tipo_documento or '').upper()
    if tipo not in ('BOLETA', 'FACTURA'):
        raise HTTPException(status_code=400, detail="tipo_documento debe ser BOLETA o FACTURA")

    result = await db.execute(select(Venta).where(Venta.id == venta_id))
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    if tipo == 'FACTURA':
        venta.fecha_impresion_factura = data.fecha
    else:
        venta.fecha_impresion_boleta = data.fecha

    # Invalidar el PDF ya generado para WhatsApp: si no, se reutiliza el viejo
    # con la fecha anterior (generar_enlace_documento devuelve ya_existia=True).
    docs_result = await db.execute(
        select(DocumentoTemporal).where(
            and_(
                DocumentoTemporal.venta_id == venta_id,
                DocumentoTemporal.tipo_documento == TipoDocumento[tipo]
            )
        )
    )
    for doc in docs_result.scalars().all():
        try:
            if doc.file_path and Path(doc.file_path).exists():
                Path(doc.file_path).unlink()
        except Exception as e:
            logger.warning(f"No se pudo eliminar el PDF {doc.file_path}: {e}")
        await db.delete(doc)

    await db.commit()
    await db.refresh(venta)

    return {
        "venta_id": venta.id,
        "tipo_documento": tipo,
        "fecha_impresion_boleta": venta.fecha_impresion_boleta.isoformat() if venta.fecha_impresion_boleta else None,
        "fecha_impresion_factura": venta.fecha_impresion_factura.isoformat() if venta.fecha_impresion_factura else None,
    }

@api_router.post("/ventas/{venta_id}/confirmar-pendiente", response_model=VentaResponse)
async def confirmar_venta_pendiente(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Confirma una venta PENDIENTE: valida stock, genera movimientos, crea crédito si aplica"""
    result = await db.execute(
        select(Venta).options(selectinload(Venta.items)).where(Venta.id == venta_id)
    )
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if venta.estado != EstadoVenta.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden confirmar ventas PENDIENTES")
    
    # Get cliente para validaciones
    cliente_result = await db.execute(select(Cliente).where(Cliente.id == venta.cliente_id))
    cliente = cliente_result.scalar_one_or_none()
    
    # Si hay representante, usar sus privilegios
    cliente_privilegios = cliente
    if venta.representante_cliente_id:
        rep_result = await db.execute(select(Cliente).where(Cliente.id == venta.representante_cliente_id))
        representante = rep_result.scalar_one_or_none()
        if representante:
            cliente_privilegios = representante
    
    # Validate cheque payment
    if venta.tipo_pago == TipoPago.CHEQUE and not cliente_privilegios.acepta_cheque:
        raise HTTPException(status_code=400, detail="Este cliente no tiene habilitado el pago con cheque")
    
    # Validate stock for each item
    for item in venta.items:
        if item.producto_id:
            stock_result = await db.execute(
                select(func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0))
                .where(StockActual.producto_id == item.producto_id)
            )
            stock_total = stock_result.scalar() or 0
            if stock_total < item.cantidad:
                prod_result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
                prod = prod_result.scalar_one_or_none()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stock insuficiente para {prod.nombre if prod else 'producto'}. Disponible: {stock_total}"
                )
    
    # Validate crédito if applicable
    if venta.tipo_pago == TipoPago.CREDITO:
        creditos_result = await db.execute(
            select(func_sql.coalesce(func_sql.sum(CreditoCliente.monto_pendiente), 0))
            .where(CreditoCliente.cliente_id == cliente_privilegios.id, CreditoCliente.pagado == False)
        )
        credito_usado = creditos_result.scalar() or Decimal('0')
        limite = cliente_privilegios.limite_credito or Decimal('0')
        
        if limite > 0 and (credito_usado + venta.total) > limite:
            disponible = max(Decimal('0'), limite - credito_usado)
            raise HTTPException(
                status_code=400, 
                detail=f"Crédito insuficiente. Límite: {float(limite):,.0f}, Usado: {float(credito_usado):,.0f}, Disponible: {float(disponible):,.0f} Gs"
            )
    
    # Process stock movements
    for item in venta.items:
        if item.producto_id:
            stock_result = await db.execute(
                select(StockActual)
                .where(StockActual.producto_id == item.producto_id, StockActual.cantidad > 0)
                .order_by(StockActual.cantidad.desc())
            )
            stocks = stock_result.scalars().all()
            
            cantidad_restante = item.cantidad
            for stock in stocks:
                if cantidad_restante <= 0:
                    break
                    
                a_descontar = min(stock.cantidad, cantidad_restante)
                stock.cantidad -= a_descontar
                cantidad_restante -= a_descontar
                
                await _consume_entrada_fifo(db, item.producto_id, stock.almacen_id, a_descontar)
                
                mov = MovimientoStock(
                    producto_id=item.producto_id,
                    almacen_id=stock.almacen_id,
                    tipo=TipoMovimientoStock.SALIDA,
                    cantidad=-a_descontar,
                    referencia_tipo='venta',
                    referencia_id=venta.id,
                    creado_en=now_paraguay()
                )
                db.add(mov)

            await _recalculate_precio_costo_fifo(db, item.producto_id)

        elif item.materia_laboratorio_id:
            materia_result = await db.execute(
                select(MateriaLaboratorio).where(MateriaLaboratorio.id == item.materia_laboratorio_id)
            )
            materia = materia_result.scalar_one_or_none()
            if materia:
                materia.estado = EstadoMateria.VENDIDO
    
    venta.estado = EstadoVenta.CONFIRMADA
    
    # Si es venta a crédito, crear registro de crédito
    if venta.tipo_pago == TipoPago.CREDITO:
        cliente_credito_id = venta.representante_cliente_id or venta.cliente_id
        
        credito = CreditoCliente(
            cliente_id=cliente_credito_id,
            venta_id=venta.id,
            monto_original=venta.total,
            monto_pendiente=venta.total,
            descripcion=f"Venta #{venta.id}",
            fecha_venta=today_paraguay()
        )
        db.add(credito)
    
    # Si es delivery, crear entrega automáticamente en estado PENDIENTE
    if venta.es_delivery:
        entrega_existente = await db.execute(
            select(Entrega).where(Entrega.venta_id == venta.id)
        )
        if not entrega_existente.scalar_one_or_none():
            entrega = Entrega(
                venta_id=venta.id,
                vehiculo_id=None,
                responsable_usuario_id=None,
                estado=EstadoEntrega.PENDIENTE
            )
            db.add(entrega)
    
    await db.commit()
    await db.refresh(venta)
    return venta

async def _items_por_venta(db: AsyncSession, venta_ids) -> dict:
    """Ítems de varias ventas con el nombre del producto o de la materia, en una consulta
    por cada 5000 ventas (en vez de una por venta y otra por ítem).
    Devuelve {venta_id: [(item, producto_nombre, materia_nombre, materia_descripcion)]}."""
    por_venta = defaultdict(list)
    ids = list(venta_ids)
    for i in range(0, len(ids), 5000):
        result = await db.execute(
            select(VentaItem, Producto.nombre, MateriaLaboratorio.nombre, MateriaLaboratorio.descripcion)
            .outerjoin(Producto, VentaItem.producto_id == Producto.id)
            .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
            .where(VentaItem.venta_id.in_(ids[i:i + 5000]))
            .order_by(VentaItem.id)
        )
        for item, producto_nombre, materia_nombre, materia_descripcion in result.all():
            por_venta[item.venta_id].append((item, producto_nombre, materia_nombre, materia_descripcion))
    return por_venta

def _venta_item_dict(item, producto_nombre, materia_nombre, materia_descripcion) -> dict:
    item_dict = VentaItemResponse.model_validate(item).model_dump()
    if item.producto_id:
        if producto_nombre:
            item_dict['producto_nombre'] = producto_nombre
            item_dict['descripcion'] = producto_nombre
    elif item.materia_laboratorio_id and materia_nombre:
        item_dict['materia_nombre'] = materia_nombre
        item_dict['descripcion'] = f"{materia_nombre} - {materia_descripcion or ''}"
    return item_dict

@api_router.get("/ventas", response_model=List[VentaConDetalles])
async def listar_ventas(
    empresa_id: int,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
    estado: Optional[str] = None,
    monto_min: Optional[float] = None,
    monto_max: Optional[float] = None,
    limit: Optional[int] = 100,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Venta, Cliente)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .where(Venta.empresa_id == empresa_id)
        .order_by(Venta.creado_en.desc())
    )
    
    if fecha_desde:
        query = query.where(Venta.creado_en >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.where(Venta.creado_en < datetime.fromisoformat(fecha_hasta) + timedelta(days=1))
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)
    if usuario_id:
        query = query.where(Venta.usuario_id == usuario_id)
    if estado:
        try:
            query = query.where(Venta.estado == EstadoVenta[estado])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
    if monto_min:
        query = query.where(Venta.total >= monto_min)
    if monto_max:
        query = query.where(Venta.total <= monto_max)
    
    if limit and limit > 0:
        query = query.limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    items_por_venta = await _items_por_venta(db, [venta.id for venta, _ in rows])
    ventas = []
    for venta, cliente in rows:
        venta_dict = VentaResponse.model_validate(venta).model_dump()
        venta_dict['items'] = [_venta_item_dict(*fila) for fila in items_por_venta.get(venta.id, [])]
        venta_dict['cliente_nombre'] = f"{cliente.nombre} {cliente.apellido or ''}"
        venta_dict['cliente_ruc'] = cliente.ruc
        ventas.append(VentaConDetalles(**venta_dict))
    
    return ventas

@api_router.get("/ventas/{venta_id}", response_model=VentaConDetalles)
async def obtener_venta(venta_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Venta, Cliente)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .where(Venta.id == venta_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    venta, cliente = row
    items_por_venta = await _items_por_venta(db, [venta.id])
    venta_dict = VentaResponse.model_validate(venta).model_dump()
    venta_dict['items'] = [_venta_item_dict(*fila) for fila in items_por_venta.get(venta.id, [])]
    venta_dict['cliente_nombre'] = f"{cliente.nombre} {cliente.apellido or ''}"
    venta_dict['cliente_ruc'] = cliente.ruc
    return VentaConDetalles(**venta_dict)

@api_router.post("/ventas/{venta_id}/anular", response_model=VentaResponse)
async def anular_venta(venta_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Venta).where(Venta.id == venta_id))
        venta = result.scalar_one_or_none()
        if not venta:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        if venta.estado == EstadoVenta.ANULADA:
            raise HTTPException(status_code=400, detail="La venta ya está anulada")
        
        # 1. Devolver stock de productos
        items_result = await db.execute(
            select(VentaItem).where(VentaItem.venta_id == venta_id)
        )
        items = items_result.scalars().all()
        
        for item in items:
            if item.producto_id:
                # Buscar los movimientos de VENTA/SALIDA de esta venta para devolver al mismo almacén
                movimientos_salida_result = await db.execute(
                    select(MovimientoStock).where(
                        MovimientoStock.referencia_tipo == 'venta',
                        MovimientoStock.referencia_id == venta_id,
                        MovimientoStock.producto_id == item.producto_id,
                        MovimientoStock.tipo == TipoMovimientoStock.SALIDA
                    )
                )
                movimientos_salida = movimientos_salida_result.scalars().all()
                
                # Devolver stock a los almacenes originales
                for mov_salida in movimientos_salida:
                    # Actualizar stock
                    stock_result = await db.execute(
                        select(StockActual).where(
                            StockActual.producto_id == item.producto_id,
                            StockActual.almacen_id == mov_salida.almacen_id
                        )
                    )
                    stock = stock_result.scalar_one_or_none()
                    
                    cantidad_devolver = abs(mov_salida.cantidad)
                    
                    if stock:
                        stock.cantidad += cantidad_devolver
                    else:
                        # Crear stock si no existe
                        stock = StockActual(
                            producto_id=item.producto_id,
                            almacen_id=mov_salida.almacen_id,
                            cantidad=cantidad_devolver
                        )
                        db.add(stock)
                    
                    # Restore FIFO batches
                    await _restore_entrada_fifo(db, item.producto_id, mov_salida.almacen_id, cantidad_devolver)
                    
                    # Registrar movimiento de ENTRADA (devolución)
                    movimiento = MovimientoStock(
                        almacen_id=mov_salida.almacen_id,
                        producto_id=item.producto_id,
                        tipo=TipoMovimientoStock.ENTRADA,
                        cantidad=cantidad_devolver,
                        referencia_tipo="ANULACION_VENTA",
                        referencia_id=venta_id,
                        # Sin lote FIFO propio: las unidades ya se devolvieron a sus
                        # lotes de origen con _restore_entrada_fifo (si no, se contarían dos veces)
                        cantidad_restante=None,
                        creado_en=now_paraguay()
                    )
                    db.add(movimiento)

                await _recalculate_precio_costo_fifo(db, item.producto_id)
            
            elif item.materia_laboratorio_id:
                # Devolver materia de laboratorio a estado DISPONIBLE
                materia_result = await db.execute(
                    select(MateriaLaboratorio).where(MateriaLaboratorio.id == item.materia_laboratorio_id)
                )
                materia = materia_result.scalar_one_or_none()
                if materia:
                    materia.estado = EstadoMateria.DISPONIBLE
        
        # 2. Devolver crédito si fue venta a crédito
        if venta.tipo_pago == TipoPago.CREDITO:
            credito_result = await db.execute(
                select(CreditoCliente).where(CreditoCliente.venta_id == venta_id)
            )
            credito = credito_result.scalar_one_or_none()
            if credito:
                # Eliminar el crédito (o marcarlo como anulado si tiene pagos)
                pagos_result = await db.execute(
                    select(PagoCredito).where(PagoCredito.credito_id == credito.id)
                )
                pagos = pagos_result.scalars().all()
                
                if pagos:
                    # Si tiene pagos, marcar como anulado pero mantener el registro
                    credito.monto_pendiente = 0
                    credito.descripcion += " (ANULADO)"
                else:
                    # Si no tiene pagos, eliminar el crédito
                    await db.delete(credito)
        
        # 3. Marcar venta como anulada
        venta.estado = EstadoVenta.ANULADA
        
        # 4. Si tiene entrega asociada, siempre eliminarla (al anular venta)
        entrega_result = await db.execute(select(Entrega).where(Entrega.venta_id == venta_id))
        entrega = entrega_result.scalar_one_or_none()
        if entrega:
            await db.delete(entrega)
        
        await db.commit()
        await db.refresh(venta)
        return venta
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        error_detail = f"Error anulando venta: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Esto aparecerá en los logs
        raise HTTPException(status_code=500, detail=error_detail)

# ==================== PRESUPUESTOS ====================
# Cotizaciones comerciales para clientes. A diferencia de una venta pendiente,
# un presupuesto NUNCA toca stock ni aparece en historial/reportes de ventas.

def numero_presupuesto(presupuesto_id: int) -> str:
    return f"presupuesto-{presupuesto_id:03d}"

async def _presupuesto_a_response(presupuesto: Presupuesto, cliente_nombre: str, con_items: bool = False):
    data = {
        'id': presupuesto.id,
        'numero': numero_presupuesto(presupuesto.id),
        'empresa_id': presupuesto.empresa_id,
        'cliente_id': presupuesto.cliente_id,
        'usuario_id': presupuesto.usuario_id,
        'cliente_nombre': cliente_nombre,
        'subtotal': presupuesto.subtotal,
        'total': presupuesto.total,
        'notas': presupuesto.notas,
        'creado_en': presupuesto.creado_en,
    }
    if con_items:
        data['items'] = [PresupuestoItemResponse.model_validate(item) for item in presupuesto.items]
        return PresupuestoConDetalles(**data)
    return PresupuestoResponse(**data)

@api_router.post("/presupuestos", response_model=PresupuestoConDetalles)
async def crear_presupuesto(data: PresupuestoCreate, db: AsyncSession = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="El presupuesto debe tener al menos un producto")

    cliente_result = await db.execute(select(Cliente).where(Cliente.id == data.cliente_id))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    presupuesto = Presupuesto(
        empresa_id=data.empresa_id,
        cliente_id=data.cliente_id,
        usuario_id=data.usuario_id,
        notas=data.notas,
        subtotal=0,
        total=0
    )
    db.add(presupuesto)
    await db.flush()

    total = Decimal('0')
    for item_data in data.items:
        prod_result = await db.execute(select(Producto).where(Producto.id == item_data.producto_id))
        producto = prod_result.scalar_one_or_none()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item_data.producto_id} no encontrado")
        if item_data.cantidad <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")
        if item_data.precio_venta_unitario is not None and item_data.precio_venta_unitario < 0:
            raise HTTPException(status_code=400, detail="El precio no puede ser negativo")

        precio_unitario = item_data.precio_venta_unitario if item_data.precio_venta_unitario is not None else producto.precio_venta
        subtotal_item = precio_unitario * item_data.cantidad
        total += subtotal_item
        db.add(PresupuestoItem(
            presupuesto_id=presupuesto.id,
            producto_id=producto.id,
            nombre_producto=producto.nombre,
            imagen_url=producto.imagen_url,
            cantidad=item_data.cantidad,
            precio_venta_unitario=precio_unitario,
            subtotal=subtotal_item
        ))

    presupuesto.subtotal = total
    presupuesto.total = total

    await db.commit()

    result = await db.execute(
        select(Presupuesto).options(selectinload(Presupuesto.items)).where(Presupuesto.id == presupuesto.id)
    )
    presupuesto = result.scalar_one()
    cliente_nombre = f"{cliente.nombre} {cliente.apellido or ''}".strip()
    return await _presupuesto_a_response(presupuesto, cliente_nombre, con_items=True)

@api_router.get("/presupuestos", response_model=List[PresupuestoResponse])
async def listar_presupuestos(
    empresa_id: int,
    numero: Optional[str] = None,
    cliente_id: Optional[int] = None,
    monto_desde: Optional[float] = None,
    monto_hasta: Optional[float] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Sin limit devuelve todos (compatibilidad); la pantalla pide de a páginas."""
    query = (
        select(Presupuesto, Cliente)
        .join(Cliente, Presupuesto.cliente_id == Cliente.id)
        .where(Presupuesto.empresa_id == empresa_id)
        .order_by(Presupuesto.creado_en.desc(), Presupuesto.id.desc())
    )

    if numero:
        digitos = ''.join(ch for ch in numero if ch.isdigit())
        if digitos:
            query = query.where(Presupuesto.id == int(digitos))
        else:
            # Sin dígitos válidos: no puede coincidir ningún presupuesto
            query = query.where(Presupuesto.id == -1)
    if cliente_id:
        query = query.where(Presupuesto.cliente_id == cliente_id)
    if monto_desde is not None:
        query = query.where(Presupuesto.total >= monto_desde)
    if monto_hasta is not None:
        query = query.where(Presupuesto.total <= monto_hasta)
    if fecha_desde:
        query = query.where(Presupuesto.creado_en >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.where(Presupuesto.creado_en < datetime.fromisoformat(fecha_hasta) + timedelta(days=1))
    if limit:
        query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    respuesta = []
    for presupuesto, cliente in result.all():
        cliente_nombre = f"{cliente.nombre} {cliente.apellido or ''}".strip()
        respuesta.append(await _presupuesto_a_response(presupuesto, cliente_nombre))
    return respuesta

async def _get_presupuesto_con_cliente(presupuesto_id: int, db: AsyncSession):
    result = await db.execute(
        select(Presupuesto, Cliente, Empresa)
        .join(Cliente, Presupuesto.cliente_id == Cliente.id)
        .join(Empresa, Presupuesto.empresa_id == Empresa.id)
        .options(selectinload(Presupuesto.items))
        .where(Presupuesto.id == presupuesto_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return row

@api_router.get("/presupuestos/{presupuesto_id}", response_model=PresupuestoConDetalles)
async def obtener_presupuesto(presupuesto_id: int, db: AsyncSession = Depends(get_db)):
    presupuesto, cliente, empresa = await _get_presupuesto_con_cliente(presupuesto_id, db)
    cliente_nombre = f"{cliente.nombre} {cliente.apellido or ''}".strip()
    return await _presupuesto_a_response(presupuesto, cliente_nombre, con_items=True)

@api_router.delete("/presupuestos/{presupuesto_id}")
async def eliminar_presupuesto(presupuesto_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Presupuesto).where(Presupuesto.id == presupuesto_id))
    presupuesto = result.scalar_one_or_none()
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    await db.execute(delete(PresupuestoItem).where(PresupuestoItem.presupuesto_id == presupuesto_id))
    await db.delete(presupuesto)
    await db.commit()
    return {"message": "Presupuesto eliminado"}

async def _obtener_imagen_bytes(imagen_url: Optional[str]) -> Optional[bytes]:
    """Obtiene los bytes de la imagen de un producto, sea un upload propio o una URL externa
    (Productos.js permite cargar cualquiera de los dos como imagen_url)."""
    if not imagen_url:
        return None
    if imagen_url.startswith('/uploads/'):
        path = ROOT_DIR / imagen_url.lstrip('/')
        if not path.exists():
            return None
        try:
            return path.read_bytes()
        except Exception:
            return None
    if imagen_url.startswith('http://') or imagen_url.startswith('https://'):
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(imagen_url)
                if resp.status_code == 200:
                    return resp.content
        except Exception:
            logger.warning(f"No se pudo descargar imagen de producto para presupuesto: {imagen_url}")
        return None
    return None

# Logo por defecto del PDF de presupuesto cuando la empresa no cargó uno propio
# (Sistema > Logo de la Empresa).
LOGO_DEFAULT_PATH = ROOT_DIR / 'assets' / 'logo_ether_pdf.png'

async def _obtener_logo_empresa(empresa: Empresa) -> Optional[bytes]:
    logo = await _obtener_imagen_bytes(empresa.logo_url) if empresa.logo_url else None
    if not logo and LOGO_DEFAULT_PATH.exists():
        logo = LOGO_DEFAULT_PATH.read_bytes()
    return logo

def generar_pdf_presupuesto(presupuesto: Presupuesto, cliente: Cliente, empresa: Empresa, imagenes: dict,
                            logo_bytes: Optional[bytes] = None) -> bytes:
    """Genera el PDF A4 del presupuesto. Diseño moderno, deliberadamente distinto
    de la boleta (matricial) y la factura (papel pre-impreso).
    `imagenes` es un dict {presupuesto_item_id: bytes | None} ya resuelto de antemano
    (la resolución de imágenes es async y esta función es sync)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm
    )
    ancho_util = A4[0] - doc.leftMargin - doc.rightMargin

    elements = []

    azul = colors.HexColor('#1E3A8A')
    gris = colors.HexColor('#6B7280')
    gris_claro = colors.HexColor('#F3F4F6')
    texto = colors.HexColor('#1F2937')

    # Nota: cada ParagraphStyle fija su propio 'leading' explícitamente (ReportLab
    # usa 12pt por defecto sin importar el fontSize, lo que solapaba líneas grandes).
    empresa_style = ParagraphStyle('Empresa', fontName='Helvetica-Bold', fontSize=16, leading=19, textColor=azul)
    subtitulo_style = ParagraphStyle('SubtituloEmpresa', fontName='Helvetica', fontSize=8.5, leading=13, textColor=gris)
    titulo_doc_style = ParagraphStyle('TituloDoc', fontName='Helvetica-Bold', fontSize=18, leading=21, alignment=TA_RIGHT, textColor=azul)
    numero_style = ParagraphStyle('NumeroDoc', fontName='Helvetica', fontSize=9.5, leading=14, alignment=TA_RIGHT, textColor=gris)
    seccion_style = ParagraphStyle('Seccion', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=gris)
    cliente_style = ParagraphStyle('Cliente', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=texto)
    normal_style = ParagraphStyle('NormalP', fontName='Helvetica', fontSize=9, leading=13, textColor=texto)
    item_nombre_style = ParagraphStyle('ItemNombre', fontName='Helvetica', fontSize=9.5, leading=13, textColor=texto)

    # ---- Encabezado: logo + datos de la empresa a la izquierda, título a la derecha ----
    logo_size = 35 * mm  # 20mm * 1.75
    logo_col_gap = 4 * mm
    logo_flowable = ''
    if logo_bytes:
        try:
            # Encajar el logo en un cuadro de logo_size x logo_size sin deformarlo
            ancho_img, alto_img = ImageReader(io.BytesIO(logo_bytes)).getSize()
            escala = min(logo_size / ancho_img, logo_size / alto_img)
            logo_flowable = Image(io.BytesIO(logo_bytes), width=ancho_img * escala, height=alto_img * escala)
        except Exception:
            logo_flowable = ''

    datos_empresa = [
        Paragraph(empresa.nombre or '', empresa_style),
    ]
    if empresa.direccion:
        datos_empresa.append(Paragraph(empresa.direccion, subtitulo_style))
    if empresa.ruc:
        datos_empresa.append(Paragraph(f"RUC: {empresa.ruc}", subtitulo_style))
    if empresa.telefono:
        datos_empresa.append(Paragraph(f"Tel: {empresa.telefono}", subtitulo_style))

    logo_col_width = logo_size + logo_col_gap
    empresa_block = Table([[logo_flowable, datos_empresa]], colWidths=[logo_col_width, (ancho_util - 70 * mm) - logo_col_width])
    empresa_block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    titulo_block = [
        Paragraph('PRESUPUESTO', titulo_doc_style),
        Spacer(1, 2 * mm),
        Paragraph(f"N° {numero_presupuesto(presupuesto.id)}", numero_style),
        Paragraph(f"Fecha: {presupuesto.creado_en.strftime('%d/%m/%Y') if presupuesto.creado_en else ''}", numero_style),
    ]

    header_table = Table([[empresa_block, titulo_block]], colWidths=[ancho_util - 70 * mm, 70 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Table([['']], colWidths=[ancho_util], style=TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, azul),
    ])))
    elements.append(Spacer(1, 4 * mm))

    # ---- Cliente ----
    elements.append(Paragraph('CLIENTE', seccion_style))
    elements.append(Spacer(1, 1.5 * mm))
    elements.append(Paragraph(f"{cliente.nombre} {cliente.apellido or ''}".strip(), cliente_style))
    detalle_cliente = []
    if cliente.ruc:
        detalle_cliente.append(f"RUC: {cliente.ruc}")
    if cliente.telefono:
        detalle_cliente.append(f"Tel: {cliente.telefono}")
    if cliente.direccion:
        detalle_cliente.append(cliente.direccion)
    if detalle_cliente:
        elements.append(Paragraph('   ·   '.join(detalle_cliente), normal_style))
    elements.append(Spacer(1, 5 * mm))

    # ---- Tabla de productos ----
    col_imagen = 20 * mm
    col_cant = 20 * mm
    col_precio = 32 * mm
    col_subtotal = 34 * mm
    col_producto = ancho_util - col_imagen - col_cant - col_precio - col_subtotal

    encabezado_style = ParagraphStyle('EncTabla', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white)
    encabezado_style_r = ParagraphStyle('EncTablaR', parent=encabezado_style, alignment=TA_RIGHT)
    encabezado_style_c = ParagraphStyle('EncTablaC', parent=encabezado_style, alignment=TA_CENTER)
    precio_style = ParagraphStyle('Precio', fontName='Helvetica', fontSize=9.5, leading=13, alignment=TA_RIGHT, textColor=texto)
    cant_style = ParagraphStyle('Cant', fontName='Helvetica', fontSize=9.5, leading=13, alignment=TA_CENTER, textColor=texto)

    # Fila con altura fija (imagen 15mm + padding reducido). El nombre del producto se
    # trunca a como mucho 2 líneas para que ninguna fila pueda crecer más de lo previsto
    # (nombres muy largos no deben poder "empujar" filas fuera de la hoja y romper el
    # límite de 10 productos por página).
    FILA_ALTURA = 17.5 * mm
    FILA_PADDING_V = 3  # puntos, arriba y abajo
    ITEM_MAX_LINEAS = 2

    def _truncar_nombre(texto_item):
        ancho_disponible = col_producto - 12  # resta LEFTPADDING+RIGHTPADDING (6pt c/u)
        ancho_por_linea = ancho_disponible / max(1, stringWidth('M', 'Helvetica', 9.5))
        max_chars = int(ancho_por_linea) * ITEM_MAX_LINEAS
        if len(texto_item) <= max_chars:
            return texto_item
        return texto_item[:max(1, max_chars - 1)].rstrip() + '…'

    def _construir_tabla_items(items_chunk):
        tabla_datos = [[
            '',
            Paragraph('Producto', encabezado_style),
            Paragraph('Cant.', encabezado_style_c),
            Paragraph('Precio Unit.', encabezado_style_r),
            Paragraph('Subtotal', encabezado_style_r),
        ]]
        row_heights = [9 * mm]
        for item in items_chunk:
            img_bytes = imagenes.get(item.id)
            celda_imagen = ''
            if img_bytes:
                try:
                    celda_imagen = Image(io.BytesIO(img_bytes), width=15 * mm, height=15 * mm)
                except Exception:
                    celda_imagen = ''
            tabla_datos.append([
                celda_imagen,
                Paragraph(_truncar_nombre(item.nombre_producto), item_nombre_style),
                Paragraph(str(item.cantidad), cant_style),
                Paragraph(f"Gs. {int(item.precio_venta_unitario):,}", precio_style),
                Paragraph(f"Gs. {int(item.subtotal):,}", precio_style),
            ])
            row_heights.append(FILA_ALTURA)

        tabla = Table(
            tabla_datos,
            colWidths=[col_imagen, col_producto, col_cant, col_precio, col_subtotal],
            rowHeights=row_heights
        )
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), azul),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_claro]),
            ('LINEBELOW', (0, 0), (-1, 0), 0.75, azul),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, azul),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), FILA_PADDING_V),
            ('BOTTOMPADDING', (0, 0), (-1, -1), FILA_PADDING_V),
            ('BOX', (0, 0), (-1, -1), 0.75, azul),
        ]))
        return tabla

    # Máximo 10 productos por hoja: coincide con el límite del carrito de Ventas,
    # para que al convertir un presupuesto en venta el vendedor no se confunda
    # viendo más ítems por página de los que puede cargar en una sola venta.
    FILAS_POR_PAGINA = 10
    items_lista = presupuesto.items
    paginas = [items_lista[i:i + FILAS_POR_PAGINA] for i in range(0, len(items_lista), FILAS_POR_PAGINA)] or [[]]

    continuacion_style = ParagraphStyle('Continuacion', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=gris)
    for idx, pagina_items in enumerate(paginas):
        if idx > 0:
            elements.append(PageBreak())
            elements.append(Paragraph(
                f"PRESUPUESTO {numero_presupuesto(presupuesto.id)} — {cliente.nombre} {cliente.apellido or ''} "
                f"(continuación, página {idx + 1} de {len(paginas)})",
                continuacion_style
            ))
            elements.append(Spacer(1, 4 * mm))
        elements.append(_construir_tabla_items(pagina_items))
    elements.append(Spacer(1, 5 * mm))

    # ---- Resumen: Subtotal / IVA incluido (precios ya incluyen IVA, igual que en Ventas) ----
    iva_incluido = (presupuesto.total * Decimal('10') / Decimal('110')).quantize(Decimal('1'))
    subtotal_sin_iva = presupuesto.total - iva_incluido
    resumen_label_style = ParagraphStyle('ResumenLabel', fontName='Helvetica', fontSize=9.5, leading=13, alignment=TA_RIGHT, textColor=gris)
    resumen_value_style = ParagraphStyle('ResumenValue', fontName='Helvetica', fontSize=9.5, leading=13, alignment=TA_RIGHT, textColor=texto)
    resumen_table = Table(
        [
            [Paragraph('Subtotal (sin IVA)', resumen_label_style), Paragraph(f"Gs. {int(subtotal_sin_iva):,}", resumen_value_style)],
            [Paragraph('IVA (10%, incluido)', resumen_label_style), Paragraph(f"Gs. {int(iva_incluido):,}", resumen_value_style)],
        ],
        colWidths=[ancho_util - 55 * mm, 55 * mm]
    )
    resumen_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 2 * mm))

    # ---- Total ----
    total_label_style = ParagraphStyle('TotalLabel', fontName='Helvetica-Bold', fontSize=11, leading=14, alignment=TA_RIGHT, textColor=colors.white)
    total_value_style = ParagraphStyle('TotalValue', fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=TA_RIGHT, textColor=colors.white)
    total_table = Table(
        [[Paragraph('TOTAL', total_label_style), Paragraph(f"Gs. {int(presupuesto.total):,}", total_value_style)]],
        colWidths=[ancho_util - 55 * mm, 55 * mm]
    )
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), azul),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(total_table)

    if presupuesto.notas:
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph('NOTAS', seccion_style))
        elements.append(Spacer(1, 1.5 * mm))
        elements.append(Paragraph(presupuesto.notas, normal_style))

    elements.append(Spacer(1, 12 * mm))
    elements.append(Table([['']], colWidths=[ancho_util], style=TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#E5E7EB')),
    ])))
    elements.append(Spacer(1, 3 * mm))
    footer_style = ParagraphStyle('Footer', fontName='Helvetica-Oblique', fontSize=7.5, leading=10, textColor=gris)
    elements.append(Paragraph(
        'Este documento es un presupuesto de referencia y no constituye una factura ni una venta confirmada. '
        'Precios sujetos a disponibilidad de stock al momento de la compra.',
        footer_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

@api_router.get("/presupuestos/{presupuesto_id}/pdf")
async def descargar_pdf_presupuesto(presupuesto_id: int, db: AsyncSession = Depends(get_db)):
    presupuesto, cliente, empresa = await _get_presupuesto_con_cliente(presupuesto_id, db)
    imagenes = {item.id: await _obtener_imagen_bytes(item.imagen_url) for item in presupuesto.items}
    logo_bytes = await _obtener_logo_empresa(empresa)
    pdf_bytes = generar_pdf_presupuesto(presupuesto, cliente, empresa, imagenes, logo_bytes)
    filename = f"{numero_presupuesto(presupuesto.id)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/presupuestos/{presupuesto_id}/xlsx")
async def descargar_xlsx_presupuesto(presupuesto_id: int, db: AsyncSession = Depends(get_db)):
    presupuesto, cliente, empresa = await _get_presupuesto_con_cliente(presupuesto_id, db)

    columnas = ['Producto', 'Cantidad', 'Precio Unitario', 'Subtotal']
    datos = [
        [item.nombre_producto, item.cantidad, float(item.precio_venta_unitario), float(item.subtotal)]
        for item in presupuesto.items
    ]
    cliente_nombre = f"{cliente.nombre} {cliente.apellido or ''}".strip()
    totales = ['', '', 'TOTAL:', float(presupuesto.total)]
    subtitulo = f"Cliente: {cliente_nombre} | Fecha: {presupuesto.creado_en.strftime('%d/%m/%Y') if presupuesto.creado_en else ''}"

    excel_bytes = crear_excel_reporte(numero_presupuesto(presupuesto.id).upper(), subtitulo, columnas, datos, totales)
    filename = f"{numero_presupuesto(presupuesto.id)}.xlsx"
    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== BOLETA Y FACTURA ====================
@api_router.get("/ventas/{venta_id}/boleta")
async def generar_boleta(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Generate boleta data for printing"""
    try:
        result = await db.execute(
            select(Venta, Cliente, Usuario, Empresa)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .join(Usuario, Venta.usuario_id == Usuario.id)
            .join(Empresa, Venta.empresa_id == Empresa.id)
            .where(Venta.id == venta_id)
        )
        row = result.first()
        if not row:
            logger.warning(f"Venta {venta_id} no encontrada o datos relacionados eliminados")
            raise HTTPException(status_code=404, detail="Venta no encontrada o datos relacionados faltantes")
        
        venta, cliente, usuario, empresa = row
        
        items_result = await db.execute(
            select(VentaItem, Producto, MateriaLaboratorio)
            .outerjoin(Producto, VentaItem.producto_id == Producto.id)
            .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
            .where(VentaItem.venta_id == venta_id)
        )
        
        items = []
        for item_row in items_result.all():
            item, producto, materia = item_row
            
            if producto:
                codigo = producto.codigo_barra or str(producto.id)
                descripcion = producto.nombre
            elif materia:
                codigo = f"LAB-{materia.id}"
                descripcion = f"{materia.nombre} - {materia.descripcion or ''}"
            else:
                codigo = 'N/A'
                descripcion = 'Item'
            
            items.append({
                'codigo': codigo,
                'cantidad': float(item.cantidad),
                'descripcion': descripcion,
                'iva': 10,
                'precio': float(item.precio_unitario),
                'total': float(item.total)
            })
        
        # Fecha de impresion (respeta correccion manual, hora original intacta)
        creado_en_py, fecha_modificada = fecha_documento(venta, 'BOLETA')
        return {
            'tipo': 'BOLETA',
            'numero': venta.id,
            'fecha': creado_en_py.strftime('%d/%m/%Y %I:%M %p'),
            'fecha_modificada': fecha_modificada,
            'estado': venta.estado.value if venta.estado else 'BORRADOR',
            'tipo_pago': venta.tipo_pago.value if venta.tipo_pago else 'CONTADO',
            'empresa': {
                'nombre': empresa.nombre,
                'ruc': empresa.ruc,
                'telefono': empresa.telefono,
                'direccion': empresa.direccion
            },
            'cliente': {
                'nombre': f"{cliente.nombre} {cliente.apellido or ''}".strip(),
                'ruc': cliente.ruc or '0',
                'direccion': cliente.direccion or '0',
                'telefono': cliente.telefono or '0'
            },
            'vendedor': f"{usuario.nombre} {usuario.apellido or ''}".strip(),
            'items': items,
            'subtotal_sin_descuento': float(venta.total + venta.descuento),
            'descuento': float(venta.descuento),
            'descuento_porcentaje': float(cliente.descuento_porcentaje) if cliente.descuento_porcentaje else 0,
            'subtotal': float(venta.total + venta.descuento),
            'iva': float(venta.iva),
            'total': float(venta.total),
            'total_letras': numero_a_letras(int(venta.total)) + ' Guaraníes'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando datos de boleta para venta {venta_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar boleta: {str(e)}")

@api_router.get("/ventas/{venta_id}/factura")
async def generar_factura(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Generate factura data for printing and mark the venta as facturada"""
    try:
        result = await db.execute(
            select(Venta, Cliente, Usuario, Empresa)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .join(Usuario, Venta.usuario_id == Usuario.id)
            .join(Empresa, Venta.empresa_id == Empresa.id)
            .where(Venta.id == venta_id)
        )
        row = result.first()
        if not row:
            logger.warning(f"Venta {venta_id} no encontrada o datos relacionados eliminados")
            raise HTTPException(status_code=404, detail="Venta no encontrada o datos relacionados faltantes")
        
        venta, cliente, usuario, empresa = row
        
        # Check if client has RUC for factura
        if not cliente.ruc:
            raise HTTPException(status_code=400, detail="El cliente no tiene RUC para emitir factura")

        items_result = await db.execute(
            select(VentaItem, Producto, MateriaLaboratorio)
            .outerjoin(Producto, VentaItem.producto_id == Producto.id)
            .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
            .where(VentaItem.venta_id == venta_id)
        )
        
        items = []
        for item_row in items_result.all():
            item, producto, materia = item_row
            
            if producto:
                descripcion = producto.nombre
            elif materia:
                descripcion = f"{materia.nombre} - {materia.descripcion or ''}"
            else:
                descripcion = 'Item'
            
            items.append({
                'cantidad': float(item.cantidad),
                'descripcion': descripcion,
                'precio_unitario': float(item.precio_unitario),
                'exenta': 0,
                'iva_5': 0,
                'iva_10': float(item.total)
            })
        
        # Calculate IVA breakdown
        base_imponible = float(venta.total) / 1.10
        iva_10 = float(venta.total) - base_imponible
        
        # Fecha de impresion (respeta correccion manual, hora original intacta)
        creado_en_py_f, fecha_modificada_f = fecha_documento(venta, 'FACTURA')
        return {
            'tipo': 'FACTURA',
            'numero': f"{venta.id:07d}",
            'fecha': creado_en_py_f.strftime('%d de %B de %Y'),
            'fecha_modificada': fecha_modificada_f,
            'condicion': venta.tipo_pago.value if venta.tipo_pago else 'CONTADO',
            'empresa': {
                'nombre': empresa.nombre,
                'ruc': empresa.ruc,
                'telefono': empresa.telefono,
                'direccion': empresa.direccion
            },
            'cliente': {
                'nombre': f"{cliente.nombre} {cliente.apellido or ''}".strip(),
                'ruc': cliente.ruc,
                'direccion': cliente.direccion or '',
                'telefono': cliente.telefono or ''
            },
            'items': items,
            'subtotal_exenta': 0,
            'subtotal_iva_5': 0,
            'subtotal_iva_10': float(venta.total + venta.descuento),
            'descuento': float(venta.descuento),
            'descuento_porcentaje': float(cliente.descuento_porcentaje) if cliente.descuento_porcentaje else 0,
            'iva_10': round(iva_10, 0),
            'total': float(venta.total),
            'total_letras': numero_a_letras(int(venta.total)),
            'liquidacion_iva': {
                'iva_5': 0,
                'iva_10': round(iva_10, 0),
                'total_iva': round(iva_10, 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando datos de factura para venta {venta_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar factura: {str(e)}")

# ==================== DOCUMENTOS TEMPORALES ====================
# Configuración de directorio para documentos temporales
# IMPORTANTE: Usar directorio persistente dentro de uploads/ para que los enlaces
# funcionen por 30 días. NO usar /tmp ya que se limpia automáticamente.
DOCS_DIR = ROOT_DIR / 'uploads' / 'documentos'
DOCS_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Directorio de documentos temporales (persistente): {DOCS_DIR}")

@api_router.post("/ventas/{venta_id}/generar-enlace")
async def generar_enlace_documento(
    venta_id: int,
    tipo_documento: TipoDocumento = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Genera un PDF del documento (boleta o factura), lo guarda en disco
    y retorna un enlace público de descarga válido por 30 días
    """
    try:
        logger.info(f"Iniciando generación de enlace para venta {venta_id}, tipo {tipo_documento}")
        
        # Verificar que la venta exista y esté confirmada
        result = await db.execute(
            select(Venta).where(Venta.id == venta_id)
        )
        venta = result.scalar_one_or_none()
        if not venta:
            logger.warning(f"Venta {venta_id} no encontrada")
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        logger.info(f"Venta encontrada con estado: {venta.estado}")
        
        if venta.estado != EstadoVenta.CONFIRMADA:
            logger.warning(f"Venta {venta_id} no está confirmada, estado: {venta.estado}")
            raise HTTPException(status_code=400, detail="Solo se pueden generar enlaces para ventas confirmadas")
        
        logger.info("Verificando documentos existentes...")
        
        # Verificar si ya existe un documento temporal para esta venta y tipo
        existing = await db.execute(
            select(DocumentoTemporal).where(
                and_(
                    DocumentoTemporal.venta_id == venta_id,
                    DocumentoTemporal.tipo_documento == tipo_documento,
                    DocumentoTemporal.fecha_expiracion > now_paraguay()
                )
            )
        )
        existing_doc = existing.scalar_one_or_none()
        
        # Si existe y no ha expirado, verificar que el archivo también exista en disco
        if existing_doc:
            file_exists = Path(existing_doc.file_path).exists() if existing_doc.file_path else False
            if file_exists:
                logger.info(f"Documento existente encontrado con archivo en disco: {existing_doc.token}")
                base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                return {
                    "url": f"{base_url}/api/documentos/{existing_doc.token}",
                    "token": existing_doc.token,
                    "tipo_documento": tipo_documento.value,
                    "fecha_expiracion": existing_doc.fecha_expiracion,
                    "ya_existia": True
                }
            else:
                # El registro existe pero el archivo fue eliminado (Render limpió el filesystem)
                # Eliminar el registro viejo para regenerar abajo
                logger.warning(f"Documento {existing_doc.token} existe en BD pero archivo no encontrado en disco. Regenerando...")
                await db.delete(existing_doc)
                await db.commit()
        
        logger.info("Generando nuevo documento PDF...")
        
        # Generar datos del documento según tipo
        if tipo_documento == TipoDocumento.BOLETA:
            # Reutilizar lógica del endpoint /ventas/{venta_id}/boleta
            result = await db.execute(
                select(Venta, Cliente, Usuario, Empresa)
                .join(Cliente, Venta.cliente_id == Cliente.id)
                .join(Usuario, Venta.usuario_id == Usuario.id)
                .join(Empresa, Venta.empresa_id == Empresa.id)
                .where(Venta.id == venta_id)
            )
            row = result.first()
            if not row:
                raise HTTPException(status_code=404, detail="Error al cargar datos de venta")
            
            venta_obj, cliente, vendedor, empresa = row
            pdf_content = await generar_pdf_boleta(venta_obj, cliente, vendedor, empresa, db)
            filename_prefix = f"boleta_{venta_id}"
        else:  # FACTURA
            result = await db.execute(
                select(Venta, Cliente, Usuario, Empresa)
                .join(Cliente, Venta.cliente_id == Cliente.id)
                .join(Usuario, Venta.usuario_id == Usuario.id)
                .join(Empresa, Venta.empresa_id == Empresa.id)
                .where(Venta.id == venta_id)
            )
            row = result.first()
            if not row:
                raise HTTPException(status_code=404, detail="Error al cargar datos de venta")
            
            venta_obj, cliente, vendedor, empresa = row
            
            if not cliente.ruc:
                raise HTTPException(status_code=400, detail="El cliente no tiene RUC para emitir factura")

            pdf_content = await generar_pdf_factura(venta_obj, cliente, vendedor, empresa, db)
            filename_prefix = f"factura_{venta_id}"
        
        logger.info(f"PDF generado exitosamente, tamaño: {len(pdf_content)} bytes")
        
        # Generar token único
        token = str(uuid.uuid4())
        filename = f"{filename_prefix}_{token}.pdf"
        file_path = DOCS_DIR / filename
        
        logger.info(f"Guardando PDF en: {file_path}")
        
        # Guardar PDF en disco
        with open(file_path, "wb") as f:
            f.write(pdf_content)
        
        logger.info(f"PDF guardado exitosamente")
        
        # Crear registro en base de datos
        fecha_expiracion = now_paraguay() + timedelta(days=30)
        logger.info(f"Creando registro en base de datos...")
        
        nuevo_doc = DocumentoTemporal(
            token=token,
            venta_id=venta_id,
            tipo_documento=tipo_documento,
            file_path=str(file_path),
            fecha_creacion=now_paraguay(),
            fecha_expiracion=fecha_expiracion,
            empresa_id=venta.empresa_id
        )
        
        db.add(nuevo_doc)
        await db.commit()
        await db.refresh(nuevo_doc)
        
        logger.info(f"Documento guardado en BD con ID: {nuevo_doc.id}, token: {token}")
        
        # Retornar URL pública
        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        logger.info(f"Enlace generado: {base_url}/api/documentos/{token}")
        
        return {
            "url": f"{base_url}/api/documentos/{token}",
            "token": token,
            "tipo_documento": tipo_documento.value,
            "fecha_expiracion": fecha_expiracion,
            "ya_existia": False
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando enlace de documento: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar documento: {str(e)}")


@public_router.get("/documentos/{token}")
async def descargar_documento(token: str, db: AsyncSession = Depends(get_db)):
    """
    Endpoint público para descargar documentos mediante token único.
    No requiere autenticación - cualquiera con el enlace puede descargar.
    Si el archivo no existe en disco (ej: Render limpió el filesystem),
    se regenera automáticamente desde los datos de la venta en la BD.
    """
    # Buscar documento por token
    result = await db.execute(
        select(DocumentoTemporal, Venta)
        .join(Venta, DocumentoTemporal.venta_id == Venta.id)
        .where(DocumentoTemporal.token == token)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento, venta = row
    
    # Verificar que no haya expirado
    if documento.fecha_expiracion < now_paraguay():
        raise HTTPException(status_code=410, detail="Este enlace ha expirado")
    
    # Verificar que el archivo existe; si no, regenerarlo desde los datos de la venta
    file_path = Path(documento.file_path)
    if not file_path.exists():
        logger.warning(f"Archivo no encontrado en disco: {file_path}. Regenerando PDF desde datos de venta...")
        try:
            # Cargar datos necesarios para regenerar el PDF
            regen_result = await db.execute(
                select(Venta, Cliente, Usuario, Empresa)
                .join(Cliente, Venta.cliente_id == Cliente.id)
                .join(Usuario, Venta.usuario_id == Usuario.id)
                .join(Empresa, Venta.empresa_id == Empresa.id)
                .where(Venta.id == documento.venta_id)
            )
            regen_row = regen_result.first()
            if not regen_row:
                raise HTTPException(status_code=404, detail="No se pudieron cargar los datos de la venta para regenerar el documento")
            
            venta_obj, cliente, vendedor, empresa = regen_row
            
            if documento.tipo_documento == TipoDocumento.BOLETA:
                pdf_content = await generar_pdf_boleta(venta_obj, cliente, vendedor, empresa, db)
            else:  # FACTURA
                pdf_content = await generar_pdf_factura(venta_obj, cliente, vendedor, empresa, db)
            
            # Asegurar que el directorio existe (puede haberse perdido también)
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Guardar el PDF regenerado en disco
            with open(file_path, "wb") as f:
                f.write(pdf_content)
            
            logger.info(f"PDF regenerado exitosamente y guardado en: {file_path} ({len(pdf_content)} bytes)")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al regenerar PDF para token {token}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error al regenerar el documento. Intente generar un nuevo enlace.")
    
    # Incrementar contador de descargas
    documento.descargas += 1
    await db.commit()
    
    # Servir el archivo
    tipo_doc = "Boleta" if documento.tipo_documento == TipoDocumento.BOLETA else "Factura"
    filename = f"{tipo_doc}_Venta_{venta.id}.pdf"
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename
    )


@api_router.delete("/documentos/limpiar-expirados")
async def limpiar_documentos_expirados(
    db: AsyncSession = Depends(get_db)
):
    """
    Tarea de limpieza: Elimina documentos expirados tanto de la BD como del disco.
    Endpoint para ser llamado por cronjobs o tareas programadas.
    """
    # Buscar documentos expirados
    result = await db.execute(
        select(DocumentoTemporal).where(
            DocumentoTemporal.fecha_expiracion < now_paraguay()
        )
    )
    documentos_expirados = result.scalars().all()
    
    eliminados_bd = 0
    eliminados_disco = 0
    errores = []
    
    for doc in documentos_expirados:
        try:
            # Eliminar archivo del disco
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
                eliminados_disco += 1
        except Exception as e:
            errores.append(f"Error al eliminar {doc.file_path}: {str(e)}")
        
        # Eliminar registro de BD
        await db.delete(doc)
        eliminados_bd += 1
    
    await db.commit()
    
    return {
        "mensaje": "Limpieza completada",
        "documentos_eliminados_bd": eliminados_bd,
        "archivos_eliminados_disco": eliminados_disco,
        "errores": errores
    }


# Funciones auxiliares para generar PDFs
async def generar_pdf_boleta(venta: Venta, cliente: Cliente, vendedor: Usuario, empresa: Empresa, db: AsyncSession) -> bytes:
    """Genera PDF de boleta con formato similar a matriz de puntos"""
    # Obtener items
    items_result = await db.execute(
        select(VentaItem, Producto, MateriaLaboratorio)
        .outerjoin(Producto, VentaItem.producto_id == Producto.id)
        .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
        .where(VentaItem.venta_id == venta.id)
    )
    
    buffer = io.BytesIO()

    elements = []

    # Estilos con fuente monoespaciada (Courier) optimizados para térmica 75mm
    title_style = ParagraphStyle(
        'CustomTitle',
        fontName='Courier-Bold',
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=2,
        textDecoration='underline'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        fontName='Courier',
        fontSize=8,
        alignment=TA_CENTER,
        spaceAfter=1
    )

    # Encabezado (usar nombre de la empresa si está disponible)
    elements.append(Paragraph(empresa.nombre or '', title_style))
    if empresa.telefono:
        elements.append(Paragraph(empresa.telefono, normal_style))
    elements.append(Spacer(1, 3*mm))
    
    # Número de nota (alineado a la derecha)
    nota_style = ParagraphStyle('Nota', fontName='Courier-Bold', fontSize=10, alignment=TA_RIGHT)
    elements.append(Paragraph(f'<b>NOTA NRO: {venta.id}</b>', nota_style))
    elements.append(Spacer(1, 2*mm))
    
    # Información del cliente
    info_data = [
        ['Razon Social:', f"{cliente.nombre} {cliente.apellido or ''}".strip()],
        ['Dirección:', cliente.direccion or '0'],
        ['Telefono:', cliente.telefono or '0'],
        ['Ruc:', cliente.ruc or '0'],
        ['Fecha de Venta:', fecha_documento(venta, 'BOLETA')[0].strftime('%d/%m/%Y %I:%M %p')],
        ['Tipo Comprob:', 'SOLO PRESUPUESTO' if venta.estado and venta.estado.value == 'PENDIENTE' else (venta.tipo_pago.value if venta.tipo_pago else 'CONTADO')]
    ]
    
    # Ajuste de columnas para ancho de 75mm (rollo térmico)
    info_table = Table(info_data, colWidths=[30*mm, 40*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 3*mm))
    
    # Items
    items_data = [['Cod', 'Cant', 'Descripción', 'IVA', 'Precio', 'Total']]
    
    for item_row in items_result.all():
        item, producto, materia = item_row
        
        if producto:
            codigo = producto.codigo_barra or str(producto.id)
            descripcion = producto.nombre
        elif materia:
            codigo = f"LAB-{materia.id}"
            descripcion = f"{materia.nombre} - {materia.descripcion or ''}"
        else:
            codigo = 'N/A'
            descripcion = 'Item'
        
        items_data.append([
            codigo[:10],  # Limitar código
            f"{item.cantidad:.2f}",
            descripcion[:30],  # Limitar descripción para caber en 75mm
            '10',
            f"{int(item.precio_unitario):,}",
            f"{int(item.total):,}"
        ])
    
    # Column widths recalculadas para 75mm total
    items_table = Table(items_data, colWidths=[12*mm, 10*mm, 30*mm, 6*mm, 8*mm, 9*mm])
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Código
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Cantidad
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),  # Descripción
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),  # IVA
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),  # Precio y Total
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))
    
    # Totales
    subtotal_sin_descuento = float(venta.total + venta.descuento)
    descuento_porcentaje = float(cliente.descuento_porcentaje) if cliente.descuento_porcentaje else 0
    total_letras = numero_a_letras(int(venta.total)) + ' Guaraníes'
    
    totales_data = [
        ['Subtotal:', f"{int(subtotal_sin_descuento):,}"]
    ]
    
    if venta.descuento > 0:
        totales_data.append([f'Descuento ({descuento_porcentaje}%):', f"-{int(venta.descuento):,}"])
    
    totales_data.append(['En Letras:', total_letras.upper()])
    totales_data.append(['TOTAL A PAGAR:', f'Gs. {int(venta.total):,}'])
    
    # Totales: ajustar anchos para rollo 75mm
    totales_table = Table(totales_data, colWidths=[50*mm, 25*mm])
    totales_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Courier-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 8),
        ('FONTSIZE', (0, -1), (-1, -1), 10),
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(totales_table)
    elements.append(Spacer(1, 5*mm))
    
    # Firma
    firma_style = ParagraphStyle('Firma', fontName='Courier', fontSize=8, alignment=TA_CENTER)
    elements.append(Paragraph('_' * 40, firma_style))
    elements.append(Paragraph('<b>Firma Cliente</b>', firma_style))
    elements.append(Spacer(1, 2*mm))

    footer_style = ParagraphStyle('Footer', fontName='Courier', fontSize=7, alignment=TA_CENTER, fontStyle='italic')
    if venta.estado and venta.estado.value == 'PENDIENTE':
        elements.append(Paragraph('<b>Este documento es solo una cotizacion, la venta no esta confirmada y no es valida en stock ni credito del cliente.</b>', footer_style))
    else:
        elements.append(Paragraph('<b>Favor Conferir Su Mercaderia !!! No Aceptamos Reclamos Posteriores.</b>', footer_style))
    
    # Calcular altura dinámica según cantidad de filas para rollo continuo
    rows_count = max(1, len(items_data))
    per_row_mm = 6  # espacio por fila
    base_mm = 50    # espacio fijo para encabezado/totales
    totals_mm = 30
    page_height = (base_mm + rows_count * per_row_mm + totals_mm) * mm

    # Crear documento con ancho 75mm y altura calculada
    page_width = 75 * mm
    custom_size = (page_width, page_height)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=custom_size,
        leftMargin=4*mm,
        rightMargin=4*mm,
        topMargin=4*mm,
        bottomMargin=4*mm
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


async def generar_pdf_factura(venta: Venta, cliente: Cliente, vendedor: Usuario, empresa: Empresa, db: AsyncSession) -> bytes:
    """Genera PDF de factura con formato similar a matriz de puntos"""
    # Obtener items
    items_result = await db.execute(
        select(VentaItem, Producto, MateriaLaboratorio)
        .outerjoin(Producto, VentaItem.producto_id == Producto.id)
        .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
        .where(VentaItem.venta_id == venta.id)
    )
    
    buffer = io.BytesIO()
    # Tamaño de papel: 240mm x 200mm para factura
    page_width = 240 * mm
    page_height = 200 * mm
    custom_size = (page_width, page_height)
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=custom_size,
        leftMargin=12*mm,
        rightMargin=12*mm,
        topMargin=10*mm,
        bottomMargin=10*mm
    )
    
    elements = []
    
    # Estilos
    title_style = ParagraphStyle(
        'CustomTitle',
        fontName='Courier-Bold',
        fontSize=16,
        alignment=TA_LEFT,
        spaceAfter=1,
        textDecoration='underline'
    )
    
    normal_bold = ParagraphStyle(
        'NormalBold',
        fontName='Courier-Bold',
        fontSize=9,
        alignment=TA_LEFT
    )
    
    # Header con empresa y número de factura
    header_data = [
        [
            Paragraph(f'<b>{empresa.nombre or ""}</b>', title_style),
            Paragraph('<b>FACTURA</b>', ParagraphStyle('FacturaTit', fontName='Courier-Bold', fontSize=14, alignment=TA_CENTER))
        ],
        [
            Paragraph(f'<b>RUC:</b> {empresa.ruc}', normal_bold),
            Paragraph(f'<b>N° {venta.id:07d}</b>', ParagraphStyle('FacturaNum', fontName='Courier-Bold', fontSize=11, alignment=TA_CENTER))
        ],
        [
            Paragraph(f'<b>{empresa.direccion}</b>', normal_bold),
            ''
        ],
        [
            Paragraph(f'<b>Tel:</b> {empresa.telefono}', normal_bold),
            ''
        ]
    ]
    
    header_table = Table(header_data, colWidths=[140*mm, 56*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (1, 0), (1, 1), 2, colors.black),
        ('ALIGN', (1, 0), (1, 1), 'CENTER'),
        ('VALIGN', (1, 0), (1, 1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4*mm))
    
    # Información del cliente
    cliente_data = [
        [
            f'Señor(es): {cliente.nombre} {cliente.apellido or ""}',
            f'Fecha: {fecha_documento(venta, "FACTURA")[0].strftime("%d/%m/%Y")}'
        ],
        [
            f'Dirección: {cliente.direccion or ""}',
            f'RUC: {cliente.ruc}'
        ],
        [
            f'Teléfono: {cliente.telefono or ""}',
            f'Condición: {venta.tipo_pago.value if venta.tipo_pago else "CONTADO"}'
        ]
    ]
    
    cliente_table = Table(cliente_data, colWidths=[140*mm, 56*mm])
    cliente_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(cliente_table)
    elements.append(Spacer(1, 3*mm))
    
    # Items
    items_data = [['Cant.', 'Descripción', 'P. Unit.', 'Exenta', 'IVA 5%', 'IVA 10%']]
    subtotal_iva_10 = 0
    
    for item_row in items_result.all():
        item, producto, materia = item_row
        
        if producto:
            descripcion = producto.nombre
        elif materia:
            descripcion = f"{materia.nombre} - {materia.descripcion or ''}"
        else:
            descripcion = 'Item'
        
        subtotal_iva_10 += float(item.total)
        
        items_data.append([
            f"{item.cantidad:.2f}",
            descripcion[:40],  # Limitar descripción
            f"{int(item.precio_unitario):,}",
            '0',
            '0',
            f"{int(item.total):,}"
        ])
    
    items_table = Table(items_data, colWidths=[18*mm, 95*mm, 25*mm, 18*mm, 18*mm, 25*mm])
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Cantidad
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Descripción
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Resto a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))
    
    # Totales
    base_imponible = float(venta.total) / 1.10
    iva_10 = float(venta.total) - base_imponible
    descuento_porcentaje = float(cliente.descuento_porcentaje) if cliente.descuento_porcentaje else 0
    total_letras = numero_a_letras(int(venta.total))
    
    totales_data = [
        ['Subtotal IVA 10%:', f"Gs. {int(subtotal_iva_10 + venta.descuento):,}"]
    ]
    
    if venta.descuento > 0:
        totales_data.append([f'Descuento ({descuento_porcentaje}%):', f"-Gs. {int(venta.descuento):,}"])
    
    totales_data.extend([
        ['Liquidación IVA 10%:', f"Gs. {round(iva_10, 0):,.0f}"],
        ['Son:', f"{total_letras.upper()} GUARANÍES"],
        ['TOTAL A PAGAR:', f'Gs. {int(venta.total):,}']
    ])
    
    totales_table = Table(totales_data, colWidths=[100*mm, 80*mm])
    totales_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Courier-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 8),
        ('FONTSIZE', (0, -1), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('LINEABOVE', (0, -2), (-1, -2), 1, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(totales_table)
    elements.append(Spacer(1, 8*mm))
    
    # Firmas
    firmas_data = [
        ['Firma y Sello Empresa', 'Firma Cliente']
    ]
    firmas_table = Table(firmas_data, colWidths=[90*mm, 90*mm])
    firmas_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(firmas_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ==================== FUNCIONARIOS ====================
@api_router.post("/funcionarios", response_model=FuncionarioResponse)
async def crear_funcionario(data: FuncionarioCreate, db: AsyncSession = Depends(get_db)):
    funcionario = Funcionario(**data.model_dump())
    db.add(funcionario)
    await db.commit()
    await db.refresh(funcionario)
    return funcionario

@api_router.get("/funcionarios")
async def listar_funcionarios(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Funcionario).where(Funcionario.empresa_id == empresa_id, Funcionario.activo == True)
        .order_by(Funcionario.nombre)
    )
    funcionarios = result.scalars().all()
    
    # Get current month adelantos for each funcionario
    response = []
    
    for funcionario in funcionarios:
        # Calculate total adelantos this month
        adelantos_result = await db.execute(
            select(func_sql.coalesce(func_sql.sum(AdelantoSalario.monto), 0))
            .where(
                AdelantoSalario.funcionario_id == funcionario.id,
                func_sql.extract('year', AdelantoSalario.creado_en) == today_paraguay().year,
                func_sql.extract('month', AdelantoSalario.creado_en) == today_paraguay().month
            )
        )
        total_adelantos = adelantos_result.scalar() or Decimal('0')
        salario_restante = (funcionario.salario_base or Decimal('0')) - total_adelantos
        
        func_dict = FuncionarioResponse.model_validate(funcionario).model_dump()
        func_dict['total_adelantos_mes'] = float(total_adelantos)
        func_dict['salario_restante'] = float(salario_restante)
        response.append(func_dict)
    
    return response

@api_router.get("/funcionarios/{funcionario_id}", response_model=FuncionarioResponse)
async def obtener_funcionario(funcionario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Funcionario).where(Funcionario.id == funcionario_id))
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")
    return funcionario

@api_router.put("/funcionarios/{funcionario_id}", response_model=FuncionarioResponse)
async def actualizar_funcionario(funcionario_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Funcionario).where(Funcionario.id == funcionario_id))
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")
    
    for key, value in data.items():
        if hasattr(funcionario, key) and key != 'id':
            setattr(funcionario, key, value)
    
    await db.commit()
    await db.refresh(funcionario)
    return funcionario

@api_router.delete("/funcionarios/{funcionario_id}")
async def eliminar_funcionario(funcionario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Funcionario).where(Funcionario.id == funcionario_id))
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")
    
    funcionario.activo = False
    await db.commit()
    return {"message": "Funcionario desactivado"}

# ==================== ADELANTOS ====================
@api_router.post("/funcionarios/{funcionario_id}/adelantos", response_model=AdelantoSalarioResponse)
async def crear_adelanto(funcionario_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    # Verify funcionario exists
    func_result = await db.execute(select(Funcionario).where(Funcionario.id == funcionario_id))
    funcionario = func_result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")
    
    monto = data.get('monto')
    if not monto:
        raise HTTPException(status_code=400, detail="El monto es requerido")
    
    adelanto = AdelantoSalario(
        funcionario_id=funcionario_id,
        monto=Decimal(str(monto))
    )
    db.add(adelanto)
    await db.commit()
    await db.refresh(adelanto)
    return adelanto

@api_router.get("/funcionarios/{funcionario_id}/adelantos", response_model=List[AdelantoSalarioResponse])
async def listar_adelantos(funcionario_id: int, periodo: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(AdelantoSalario).where(AdelantoSalario.funcionario_id == funcionario_id)
    
    if periodo:
        year, month = map(int, periodo.split('-'))
        start_date = datetime(year, month, 1, tzinfo=PARAGUAY_TZ)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=PARAGUAY_TZ)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=PARAGUAY_TZ)
        query = query.where(
            AdelantoSalario.creado_en >= start_date,
            AdelantoSalario.creado_en < end_date
        )
    
    result = await db.execute(query.order_by(AdelantoSalario.creado_en.desc()))
    return result.scalars().all()

# ==================== VEHICULOS ====================
@api_router.post("/vehiculos", response_model=VehiculoResponse)
async def crear_vehiculo(data: VehiculoCreate, db: AsyncSession = Depends(get_db)):
    vehiculo = Vehiculo(**data.model_dump())
    db.add(vehiculo)
    await db.commit()
    await db.refresh(vehiculo)
    return vehiculo

@api_router.get("/vehiculos", response_model=List[VehiculoResponse])
async def listar_vehiculos(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehiculo).where(Vehiculo.empresa_id == empresa_id))
    return result.scalars().all()

@api_router.put("/vehiculos/{vehiculo_id}", response_model=VehiculoResponse)
async def actualizar_vehiculo(vehiculo_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    vehiculo = result.scalar_one_or_none()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    for key, value in data.items():
        if hasattr(vehiculo, key) and key != 'id':
            setattr(vehiculo, key, value)
    
    await db.commit()
    await db.refresh(vehiculo)
    return vehiculo

@api_router.delete("/vehiculos/{vehiculo_id}")
async def eliminar_vehiculo(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    vehiculo = result.scalar_one_or_none()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    await db.delete(vehiculo)
    await db.commit()
    return {"message": "Vehículo eliminado"}

# ==================== ENTREGAS ====================
@api_router.post("/entregas", response_model=EntregaResponse)
async def crear_entrega(data: EntregaCreate, db: AsyncSession = Depends(get_db)):
    entrega = Entrega(**data.model_dump())
    db.add(entrega)
    await db.commit()
    await db.refresh(entrega)
    return entrega

@api_router.get("/entregas", response_model=List[EntregaConDetalles])
async def listar_entregas(
    empresa_id: int,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    vehiculo_id: Optional[int] = None,
    responsable_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Sin limit devuelve todas (compatibilidad); la pantalla pide de a páginas."""
    query = (
        select(Entrega, Venta, Cliente, Vehiculo, Usuario)
        .join(Venta, Entrega.venta_id == Venta.id)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .outerjoin(Vehiculo, Entrega.vehiculo_id == Vehiculo.id)
        .outerjoin(Usuario, Entrega.responsable_usuario_id == Usuario.id)
        .where(Venta.empresa_id == empresa_id)
    )
    
    if fecha_desde:
        query = query.where(Entrega.fecha_entrega >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.where(Entrega.fecha_entrega <= datetime.fromisoformat(fecha_hasta))
    if vehiculo_id:
        query = query.where(Entrega.vehiculo_id == vehiculo_id)
    if responsable_id:
        query = query.where(Entrega.responsable_usuario_id == responsable_id)
    if estado:
        query = query.where(Entrega.estado == EstadoEntrega(estado))
    
    query = query.order_by(Entrega.id.desc())
    if limit:
        query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()
    items_por_venta = await _items_por_venta(db, {venta.id for _, venta, _, _, _ in rows})
    entregas = []
    for entrega, venta, cliente, vehiculo, usuario in rows:
        items = [
            {
                'cantidad': item.cantidad,
                'precio_unitario': float(item.precio_unitario),
                'total': float(item.total),
                'producto_nombre': producto_nombre if item.producto_id else None,
                'materia_nombre': materia_nombre if not item.producto_id and item.materia_laboratorio_id else None,
            }
            for item, producto_nombre, materia_nombre, _ in items_por_venta.get(venta.id, [])
        ]

        entrega_dict = EntregaResponse.model_validate(entrega).model_dump()
        entrega_dict['cliente_nombre'] = f"{cliente.nombre} {cliente.apellido or ''}"
        entrega_dict['cliente_telefono'] = cliente.telefono
        entrega_dict['cliente_direccion'] = cliente.direccion
        entrega_dict['vehiculo_chapa'] = vehiculo.chapa if vehiculo else None
        entrega_dict['responsable_nombre'] = f"{usuario.nombre} {usuario.apellido or ''}" if usuario else None
        entrega_dict['items'] = items
        entregas.append(EntregaConDetalles(**entrega_dict))
    
    return entregas

@api_router.put("/entregas/{entrega_id}/asignar", response_model=EntregaResponse)
async def asignar_entrega(entrega_id: int, data: AsignarEntrega, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Entrega).where(Entrega.id == entrega_id))
    entrega = result.scalar_one_or_none()
    if not entrega:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    
    # Actualizar vehículo y responsable
    entrega.vehiculo_id = data.vehiculo_id
    entrega.responsable_usuario_id = data.responsable_usuario_id
    
    # Si estaba PENDIENTE, cambiar a EN_CAMINO
    if entrega.estado == EstadoEntrega.PENDIENTE:
        entrega.estado = EstadoEntrega.EN_CAMINO
    
    await db.commit()
    await db.refresh(entrega)
    return entrega

@api_router.put("/entregas/{entrega_id}/estado")
async def actualizar_estado_entrega(entrega_id: int, estado: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Entrega).where(Entrega.id == entrega_id))
    entrega = result.scalar_one_or_none()
    if not entrega:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    
    entrega.estado = EstadoEntrega(estado)
    await db.commit()
    return {"message": "Estado actualizado"}

@api_router.delete("/entregas/{entrega_id}")
async def eliminar_entrega(entrega_id: int, db: AsyncSession = Depends(get_db)):
    """Delete delivery order"""
    result = await db.execute(select(Entrega).where(Entrega.id == entrega_id))
    entrega = result.scalar_one_or_none()
    if not entrega:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    
    await db.delete(entrega)
    await db.commit()
    return {"message": "Entrega eliminada"}

# ==================== FACTURAS ====================
@api_router.post("/facturas", response_model=FacturaResponse)
async def crear_factura(data: FacturaCreate, db: AsyncSession = Depends(get_db)):
    factura = Factura(**data.model_dump(), creado_en=now_paraguay())
    db.add(factura)
    await db.commit()
    await db.refresh(factura)
    return factura

@api_router.get("/facturas", response_model=List[FacturaResponse])
async def listar_facturas(empresa_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Factura)
        .join(Venta, Factura.venta_id == Venta.id)
        .where(Venta.empresa_id == empresa_id)
        .order_by(Factura.creado_en.desc())
    )
    return result.scalars().all()

@api_router.get("/facturas/clientes-pendientes")
async def clientes_con_boletas_pendientes(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Clientes que tienen boletas CONFIRMADAS no facturadas"""
    result = await db.execute(
        select(
            Cliente.id,
            Cliente.nombre,
            Cliente.apellido,
            Cliente.ruc,
            func_sql.count(Venta.id).label('boletas_count'),
            func_sql.sum(Venta.total).label('total_pendiente')
        )
        .join(Venta, Venta.cliente_id == Cliente.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.facturada == False
        )
        .group_by(Cliente.id, Cliente.nombre, Cliente.apellido, Cliente.ruc)
        .having(func_sql.count(Venta.id) > 0)
        .order_by(Cliente.nombre)
    )
    rows = result.all()
    return [
        {
            "cliente_id": r.id,
            "nombre": f"{r.nombre} {r.apellido or ''}".strip(),
            "ruc": r.ruc or '',
            "boletas_count": r.boletas_count,
            "total_pendiente": float(r.total_pendiente or 0)
        }
        for r in rows
    ]

@api_router.get("/facturas/boletas-pendientes/{cliente_id}")
async def boletas_pendientes_cliente(cliente_id: int, empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Boletas CONFIRMADAS no facturadas de un cliente"""
    result = await db.execute(
        select(Venta)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.cliente_id == cliente_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.facturada == False
        )
        .order_by(Venta.creado_en.asc())
    )
    ventas = result.scalars().all()
    return [
        {
            "id": v.id,
            "total": float(v.total),
            "tipo_pago": v.tipo_pago.value if v.tipo_pago else "EFECTIVO",
            "creado_en": v.creado_en.isoformat() if v.creado_en else None
        }
        for v in ventas
    ]

@api_router.post("/facturas/grupal", response_model=FacturaGrupalResponse)
async def crear_factura_grupal(data: FacturaGrupalCreate, db: AsyncSession = Depends(get_db)):
    """Crea una factura que engloba múltiples boletas de un cliente y las marca como facturadas"""
    if not data.venta_ids:
        raise HTTPException(status_code=400, detail="Seleccione al menos una boleta")

    # Validate client has RUC
    cliente_result = await db.execute(select(Cliente).where(Cliente.id == data.cliente_id))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if not cliente.ruc:
        raise HTTPException(status_code=400, detail="El cliente no tiene RUC para emitir factura")

    # Validate all ventas belong to client, are CONFIRMADA, and not yet facturada
    result = await db.execute(
        select(Venta)
        .where(
            Venta.id.in_(data.venta_ids),
            Venta.empresa_id == data.empresa_id,
            Venta.cliente_id == data.cliente_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.facturada == False
        )
    )
    ventas = result.scalars().all()
    if len(ventas) != len(data.venta_ids):
        raise HTTPException(status_code=400, detail="Algunas boletas no son válidas o ya fueron facturadas")

    # Si es factura a crédito (sin cobrar), todas las boletas deben ser CREDITO
    if not data.cobrar_credito:
        no_credito = [v.id for v in ventas if v.tipo_pago != TipoPago.CREDITO]
        if no_credito:
            raise HTTPException(
                status_code=400,
                detail="Para generar factura a crédito todas las boletas seleccionadas deben ser de tipo CRÉDITO. Separe las boletas de contado y fáctúrelas por separado."
            )

    # Calculate totals
    total = sum(v.total for v in ventas)
    base_imponible = total / Decimal('1.10')
    iva = total - base_imponible

    # Generate numero based on current count
    count_result = await db.execute(select(func_sql.count(FacturaGrupal.id)))
    count = count_result.scalar() or 0
    numero = f"FG-{(count + 1):07d}"

    # Create factura grupal
    condicion = 'CREDITO' if not data.cobrar_credito else 'CONTADO'
    factura = FacturaGrupal(
        empresa_id=data.empresa_id,
        cliente_id=data.cliente_id,
        numero=numero,
        condicion=condicion,
        total=total,
        iva=iva,
        creado_en=now_paraguay()
    )
    db.add(factura)
    await db.flush()

    # Link ventas and mark as facturadas (insert directly to avoid async lazy-load)
    for venta in ventas:
        venta.facturada = True
    await db.execute(
        factura_grupal_ventas.insert(),
        [{"factura_grupal_id": factura.id, "venta_id": v.id} for v in ventas]
    )

    # Cobrar créditos pendientes de las boletas con tipo_pago CREDITO (solo si se pidió cobrar)
    if data.cobrar_credito:
        venta_ids_credito = [v.id for v in ventas if v.tipo_pago == TipoPago.CREDITO]
        if venta_ids_credito:
            creditos_result = await db.execute(
                select(CreditoCliente).where(
                    CreditoCliente.venta_id.in_(venta_ids_credito),
                    CreditoCliente.pagado == False
                )
            )
            creditos_pendientes = creditos_result.scalars().all()
            for credito in creditos_pendientes:
                pago = PagoCredito(
                    credito_id=credito.id,
                    monto=credito.monto_pendiente,
                    observacion=f"Cobrado al facturar {factura.numero}",
                    fecha_pago=now_paraguay()
                )
                db.add(pago)
                credito.monto_pendiente = Decimal('0')
                credito.pagado = True

    await db.commit()
    await db.refresh(factura)
    return factura

@api_router.get("/facturas/grupal/{factura_id}/imprimir")
async def imprimir_factura_grupal(factura_id: int, db: AsyncSession = Depends(get_db)):
    """Datos de impresión para una factura grupal"""
    result = await db.execute(
        select(FacturaGrupal)
        .options(
            selectinload(FacturaGrupal.ventas),
            selectinload(FacturaGrupal.cliente),
            selectinload(FacturaGrupal.empresa)
        )
        .where(FacturaGrupal.id == factura_id)
    )
    factura = result.scalar_one_or_none()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    ventas_sorted = sorted(factura.ventas, key=lambda v: v.id)
    nums_boletas = [f"#{v.id}" for v in ventas_sorted]
    total_general = float(factura.total)
    NUMS_POR_LINEA = 6

    items = []
    # Fila principal: descripción + total agrupado
    items.append({
        'cantidad': 1,
        'descripcion': 'Compras de insumos y materiales',
        'precio_unitario': total_general,
        'exenta': 0,
        'iva_5': 0,
        'iva_10': total_general
    })
    # Filas de continuación con los números de boletas agrupados
    for i in range(0, len(nums_boletas), NUMS_POR_LINEA):
        chunk = nums_boletas[i:i + NUMS_POR_LINEA]
        prefix = 'Boletas: ' if i == 0 else ''
        items.append({
            'cantidad': '',
            'descripcion': prefix + ' '.join(chunk),
            'precio_unitario': None,
            'exenta': None,
            'iva_5': None,
            'iva_10': None,
            'es_continuacion': True
        })

    iva_10 = round(float(factura.iva), 0)
    return {
        'tipo': 'FACTURA',
        'numero': factura.numero,
        'fecha': factura.creado_en.strftime('%d de %B de %Y'),
        'condicion': factura.condicion or 'CONTADO',
        'empresa': {
            'nombre': factura.empresa.nombre,
            'ruc': factura.empresa.ruc,
            'telefono': factura.empresa.telefono,
            'direccion': factura.empresa.direccion
        },
        'cliente': {
            'nombre': f"{factura.cliente.nombre} {factura.cliente.apellido or ''}".strip(),
            'ruc': factura.cliente.ruc,
            'direccion': factura.cliente.direccion or '',
            'telefono': factura.cliente.telefono or ''
        },
        'items': items,
        'subtotal_exenta': 0,
        'subtotal_iva_5': 0,
        'subtotal_iva_10': float(factura.total),
        'descuento': 0,
        'total': float(factura.total),
        'total_letras': numero_a_letras(int(factura.total)),
        'creado_en': factura.creado_en.isoformat(),
        'liquidacion_iva': {
            'iva_5': 0,
            'iva_10': iva_10,
            'total_iva': iva_10
        }
    }

@api_router.get("/facturas/grupales")
async def listar_facturas_grupales(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Lista facturas grupales emitidas"""
    result = await db.execute(
        select(FacturaGrupal)
        .options(selectinload(FacturaGrupal.ventas), selectinload(FacturaGrupal.cliente))
        .where(FacturaGrupal.empresa_id == empresa_id)
        .order_by(FacturaGrupal.creado_en.desc())
    )
    facturas = result.scalars().all()
    return [
        {
            "id": f.id,
            "numero": f.numero,
            "cliente_id": f.cliente_id,
            "cliente_nombre": f"{f.cliente.nombre} {f.cliente.apellido or ''}".strip(),
            "cliente_ruc": f.cliente.ruc or '',
            "total": float(f.total),
            "iva": float(f.iva),
            "boletas_count": len(f.ventas),
            "creado_en": f.creado_en.isoformat() if f.creado_en else None
        }
        for f in facturas
    ]


@api_router.post("/preferencias", response_model=PreferenciaUsuarioResponse)
async def crear_actualizar_preferencias(data: PreferenciaUsuarioCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PreferenciaUsuario).where(PreferenciaUsuario.usuario_id == data.usuario_id)
    )
    pref = result.scalar_one_or_none()
    
    if pref:
        pref.tema = data.tema
        pref.color_primario = data.color_primario
    else:
        pref = PreferenciaUsuario(**data.model_dump())
        db.add(pref)
    
    await db.commit()
    await db.refresh(pref)
    return pref

@api_router.get("/preferencias/{usuario_id}", response_model=PreferenciaUsuarioResponse)
async def obtener_preferencias(usuario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PreferenciaUsuario).where(PreferenciaUsuario.usuario_id == usuario_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        return PreferenciaUsuarioResponse(
            id=0,
            usuario_id=usuario_id,
            tema="light",
            color_primario="#0044CC"
        )
    return pref

# ==================== COTIZACION DIVISAS ====================
@api_router.get("/cotizacion", response_model=CotizacionDivisa)
async def obtener_cotizacion():
    """Get USD/PYG and BRL/PYG exchange rates"""
    global MANUAL_CURRENCY_RATES
    
    # If manual mode is set, return manual rates
    if MANUAL_CURRENCY_RATES['manual'] and MANUAL_CURRENCY_RATES['usd_pyg']:
        return CotizacionDivisa(
            usd_pyg=Decimal(str(MANUAL_CURRENCY_RATES['usd_pyg'])),
            brl_pyg=Decimal(str(MANUAL_CURRENCY_RATES['brl_pyg'])),
            manual=True,
            fecha_actualizacion=MANUAL_CURRENCY_RATES['updated_at'] or now_paraguay()
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=10.0
            )
            data = response.json()
            
            usd_pyg = Decimal(str(data['rates'].get('PYG', 7500)))
            brl_rate = Decimal(str(data['rates'].get('BRL', 5.0)))
            brl_pyg = usd_pyg / brl_rate
            
            return CotizacionDivisa(
                usd_pyg=usd_pyg,
                brl_pyg=brl_pyg.quantize(Decimal('0.01')),
                manual=False,
                fecha_actualizacion=now_paraguay()
            )
    except Exception as e:
        logger.error(f"Error fetching exchange rates: {e}")
        # Return default or cached values
        if MANUAL_CURRENCY_RATES['usd_pyg']:
            return CotizacionDivisa(
                usd_pyg=Decimal(str(MANUAL_CURRENCY_RATES['usd_pyg'])),
                brl_pyg=Decimal(str(MANUAL_CURRENCY_RATES['brl_pyg'])),
                manual=True,
                fecha_actualizacion=MANUAL_CURRENCY_RATES['updated_at'] or now_paraguay()
            )
        return CotizacionDivisa(
            usd_pyg=Decimal('7500'),
            brl_pyg=Decimal('1500'),
            manual=True,
            fecha_actualizacion=now_paraguay()
        )

@api_router.post("/cotizacion/manual", dependencies=[Depends(requiere_permiso("sistema.configurar"))])
async def establecer_cotizacion_manual(data: dict):
    """Set manual exchange rates"""
    global MANUAL_CURRENCY_RATES
    
    MANUAL_CURRENCY_RATES['usd_pyg'] = data.get('usd_pyg')
    MANUAL_CURRENCY_RATES['brl_pyg'] = data.get('brl_pyg')
    MANUAL_CURRENCY_RATES['manual'] = data.get('manual', True)
    MANUAL_CURRENCY_RATES['updated_at'] = now_paraguay()
    
    return {"message": "Cotización manual establecida", "data": MANUAL_CURRENCY_RATES}

@api_router.post("/cotizacion/auto", dependencies=[Depends(requiere_permiso("sistema.configurar"))])
async def activar_cotizacion_automatica():
    """Switch back to automatic exchange rates"""
    global MANUAL_CURRENCY_RATES
    MANUAL_CURRENCY_RATES['manual'] = False
    return {"message": "Cotización automática activada"}

# ==================== DASHBOARD ====================
@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def obtener_estadisticas_dashboard(empresa_id: int, db: AsyncSession = Depends(get_db)):
    today = today_paraguay()
    today_start, today_end = get_day_range_paraguay(today)
    
    ventas_hoy_result = await db.execute(
        select(
            func_sql.coalesce(func_sql.sum(Venta.total), 0),
            func_sql.count(Venta.id)
        )
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.creado_en >= today_start,
            Venta.creado_en <= today_end
        )
    )
    ventas_row = ventas_hoy_result.first()
    ventas_hoy = ventas_row[0] if ventas_row else Decimal('0')
    cantidad_ventas = ventas_row[1] if ventas_row else 0
    
    # Ventas del mes corriente
    month_start = datetime.combine(today.replace(day=1), datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
    month_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=PARAGUAY_TZ)
    
    ventas_mes_result = await db.execute(
        select(
            func_sql.coalesce(func_sql.sum(Venta.total), 0),
            func_sql.count(Venta.id)
        )
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.creado_en >= month_start,
            Venta.creado_en <= month_end
        )
    )
    ventas_mes_row = ventas_mes_result.first()
    ventas_mes = ventas_mes_row[0] if ventas_mes_row else Decimal('0')
    cantidad_ventas_mes = ventas_mes_row[1] if ventas_mes_row else 0
    
    deliverys_result = await db.execute(
        select(func_sql.count(Entrega.id))
        .join(Venta, Entrega.venta_id == Venta.id)
        .where(
            Venta.empresa_id == empresa_id,
            Entrega.estado == EstadoEntrega.PENDIENTE
        )
    )
    deliverys_pendientes = deliverys_result.scalar() or 0
    
    stock_bajo_result = await db.execute(
        select(Producto.id, Producto.nombre, func_sql.sum(StockActual.cantidad), StockActual.alerta_minima)
        .join(StockActual, Producto.id == StockActual.producto_id)
        .where(
            Producto.empresa_id == empresa_id,
            Producto.activo == True,
            StockActual.alerta_minima.isnot(None)
        )
        .group_by(Producto.id, Producto.nombre, StockActual.alerta_minima)
        .having(func_sql.sum(StockActual.cantidad) <= StockActual.alerta_minima)
    )
    productos_bajo_stock = [
        StockBajo(
            producto_id=row[0],
            producto_nombre=row[1],
            stock_total=row[2] or 0,
            alerta_minima=row[3] or 0
        )
        for row in stock_bajo_result.all()
    ]
    
    ventas_por_hora_result = await db.execute(
        select(
            func_sql.extract('hour', Venta.creado_en).label('hora'),
            func_sql.count(Venta.id),
            func_sql.coalesce(func_sql.sum(Venta.total), 0)
        )
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.creado_en >= today_start,
            Venta.creado_en <= today_end
        )
        .group_by(func_sql.extract('hour', Venta.creado_en))
        .order_by('hora')
    )
    
    # Obtener unidades por hora
    unidades_por_hora_result = await db.execute(
        select(
            func_sql.extract('hour', Venta.creado_en).label('hora'),
            func_sql.coalesce(func_sql.sum(VentaItem.cantidad), 0).label('unidades')
        )
        .join(VentaItem, VentaItem.venta_id == Venta.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.creado_en >= today_start,
            Venta.creado_en <= today_end
        )
        .group_by(func_sql.extract('hour', Venta.creado_en))
    )
    unidades_dict = {int(row[0]): int(row[1] or 0) for row in unidades_por_hora_result.all()}
    
    ventas_por_hora = [
        VentasPorHora(
            hora=int(row[0]),
            cantidad=row[1],
            monto=row[2],
            unidades=unidades_dict.get(int(row[0]), 0)
        )
        for row in ventas_por_hora_result.all()
    ]
    
    alto_stock_result = await db.execute(
        select(Producto.id, Producto.nombre, func_sql.sum(StockActual.cantidad))
        .join(StockActual, Producto.id == StockActual.producto_id)
        .where(Producto.empresa_id == empresa_id, Producto.activo == True)
        .group_by(Producto.id, Producto.nombre)
        .order_by(func_sql.sum(StockActual.cantidad).desc())
        .limit(5)
    )
    productos_alto_stock = [
        {"producto_id": row[0], "producto_nombre": row[1], "stock_total": row[2] or 0}
        for row in alto_stock_result.all()
    ]
    
    return DashboardStats(
        ventas_hoy=ventas_hoy,
        cantidad_ventas_hoy=cantidad_ventas,
        ventas_mes=ventas_mes,
        cantidad_ventas_mes=cantidad_ventas_mes,
        deliverys_pendientes=deliverys_pendientes,
        productos_stock_bajo=len(productos_bajo_stock),
        creditos_por_vencer=0,
        ventas_por_hora=ventas_por_hora,
        productos_bajo_stock=productos_bajo_stock,
        productos_alto_stock=productos_alto_stock
    )

@api_router.get("/dashboard/ventas-periodo")
async def obtener_ventas_por_periodo(
    empresa_id: int,
    periodo: str = "dia",
    tipo_pago: Optional[str] = None,  # 'credito', 'contado', o None para todos
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener ventas agrupadas por período
    periodo: dia, semana, mes, trimestre, semestre, anio
    tipo_pago: credito (solo CREDITO), contado (EFECTIVO, CHEQUE, TRANSFERENCIA, TARJETA), None (todos)
    """
    now = now_paraguay()
    today = now.date()
    
    # Build base filters
    base_filters = [
        Venta.empresa_id == empresa_id,
        Venta.estado == EstadoVenta.CONFIRMADA
    ]
    
    # Add tipo_pago filter
    if tipo_pago == 'credito':
        base_filters.append(Venta.tipo_pago == TipoPago.CREDITO)
    elif tipo_pago == 'contado':
        base_filters.append(Venta.tipo_pago.in_([
            TipoPago.EFECTIVO,
            TipoPago.CHEQUE,
            TipoPago.TRANSFERENCIA,
            TipoPago.TARJETA
        ]))
    
    if periodo == "dia":
        # Ventas por hora del día actual en zona horaria de Paraguay
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
        today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=PARAGUAY_TZ)
        
        base_filters.extend([
            Venta.creado_en >= today_start,
            Venta.creado_en <= today_end
        ])
        
        # Para PostgreSQL: convertir a zona horaria de Paraguay antes de extraer la hora
        # func_sql.timezone('America/Asuncion', ...) convierte a hora local
        hora_paraguay = func_sql.extract(
            'hour', 
            func_sql.timezone(text("'America/Asuncion'"), Venta.creado_en)
        )
        
        result = await db.execute(
            select(
                hora_paraguay.label('hora'),
                func_sql.count(Venta.id).label('cantidad'),
                func_sql.coalesce(func_sql.sum(Venta.total), 0).label('monto'),
                func_sql.coalesce(func_sql.sum(
                    select(func_sql.sum(VentaItem.cantidad))
                    .where(VentaItem.venta_id == Venta.id)
                    .correlate(Venta)
                    .scalar_subquery()
                ), 0).label('unidades')
            )
            .where(and_(*base_filters))
            .group_by(hora_paraguay)
            .order_by('hora')
        )
        return [
            {"label": f"{int(row[0])}:00", "cantidad": row[1], "monto": float(row[2]), "unidades": int(row[3] or 0)}
            for row in result.all()
        ]
    
    elif periodo == "semana":
        # Últimos 7 días
        fecha_inicio = today - timedelta(days=6)
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
        
        base_filters.append(Venta.creado_en >= fecha_inicio_dt)
        
        # Primero obtenemos los datos agregados
        result = await db.execute(
            select(
                func_sql.date(Venta.creado_en).label('fecha'),
                func_sql.count(Venta.id).label('cantidad'),
                func_sql.coalesce(func_sql.sum(Venta.total), 0).label('monto')
            )
            .where(and_(*base_filters))
            .group_by(func_sql.date(Venta.creado_en))
            .order_by('fecha')
        )
        ventas_dict = {row[0]: {"cantidad": row[1], "monto": float(row[2])} for row in result.all()}
        
        # Obtener unidades por fecha
        unidades_result = await db.execute(
            select(
                func_sql.date(Venta.creado_en).label('fecha'),
                func_sql.coalesce(func_sql.sum(VentaItem.cantidad), 0).label('unidades')
            )
            .join(VentaItem, VentaItem.venta_id == Venta.id)
            .where(and_(*base_filters))
            .group_by(func_sql.date(Venta.creado_en))
        )
        unidades_dict = {row[0]: int(row[1] or 0) for row in unidades_result.all()}
        
        # Asegurar que todos los días estén representados
        return [
            {
                "label": (fecha_inicio + timedelta(days=i)).strftime("%d/%m"),
                "cantidad": ventas_dict.get(fecha_inicio + timedelta(days=i), {}).get("cantidad", 0),
                "monto": ventas_dict.get(fecha_inicio + timedelta(days=i), {}).get("monto", 0),
                "unidades": unidades_dict.get(fecha_inicio + timedelta(days=i), 0)
            }
            for i in range(7)
        ]
    
    elif periodo == "mes":
        # Último mes (30 días) agrupado por día
        fecha_inicio = today - timedelta(days=29)
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
        
        base_filters.append(Venta.creado_en >= fecha_inicio_dt)
        
        result = await db.execute(
            select(
                func_sql.date(Venta.creado_en).label('fecha'),
                func_sql.count(Venta.id).label('cantidad'),
                func_sql.coalesce(func_sql.sum(Venta.total), 0).label('monto')
            )
            .where(and_(*base_filters))
            .group_by(func_sql.date(Venta.creado_en))
            .order_by('fecha')
        )
        ventas_dict = {row[0]: {"cantidad": row[1], "monto": float(row[2])} for row in result.all()}
        
        # Obtener unidades por fecha
        unidades_result = await db.execute(
            select(
                func_sql.date(Venta.creado_en).label('fecha'),
                func_sql.coalesce(func_sql.sum(VentaItem.cantidad), 0).label('unidades')
            )
            .join(VentaItem, VentaItem.venta_id == Venta.id)
            .where(and_(*base_filters))
            .group_by(func_sql.date(Venta.creado_en))
        )
        unidades_dict = {row[0]: int(row[1] or 0) for row in unidades_result.all()}
        
        return [
            {
                "label": (fecha_inicio + timedelta(days=i)).strftime("%d/%m"),
                "cantidad": ventas_dict.get(fecha_inicio + timedelta(days=i), {}).get("cantidad", 0),
                "monto": ventas_dict.get(fecha_inicio + timedelta(days=i), {}).get("monto", 0),
                "unidades": unidades_dict.get(fecha_inicio + timedelta(days=i), 0)
            }
            for i in range(30)
        ]
    
    elif periodo == "trimestre":
        # Últimos 3 meses agrupado por semana
        fecha_inicio = today - timedelta(days=90)
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
        
        base_filters.append(Venta.creado_en >= fecha_inicio_dt)
        
        result = await db.execute(
            select(
                func_sql.extract('week', Venta.creado_en).label('semana'),
                func_sql.extract('year', Venta.creado_en).label('anio'),
                func_sql.count(Venta.id).label('cantidad'),
                func_sql.coalesce(func_sql.sum(Venta.total), 0).label('monto')
            )
            .where(and_(*base_filters))
            .group_by('semana', 'anio')
            .order_by('anio', 'semana')
        )
        
        # Obtener unidades por semana
        unidades_result = await db.execute(
            select(
                func_sql.extract('week', Venta.creado_en).label('semana'),
                func_sql.extract('year', Venta.creado_en).label('anio'),
                func_sql.coalesce(func_sql.sum(VentaItem.cantidad), 0).label('unidades')
            )
            .join(VentaItem, VentaItem.venta_id == Venta.id)
            .where(and_(*base_filters))
            .group_by('semana', 'anio')
        )
        unidades_dict = {(int(row[0]), int(row[1])): int(row[2] or 0) for row in unidades_result.all()}
        
        return [
            {
                "label": f"Sem {int(row[0])}",
                "cantidad": row[2],
                "monto": float(row[3]),
                "unidades": unidades_dict.get((int(row[0]), int(row[1])), 0)
            }
            for row in result.all()
        ]
    
    elif periodo == "semestre":
        # Últimos 6 meses agrupado por mes
        fecha_inicio = today - timedelta(days=180)
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
        
        base_filters.append(Venta.creado_en >= fecha_inicio_dt)
        
        result = await db.execute(
            select(
                func_sql.extract('month', Venta.creado_en).label('mes'),
                func_sql.extract('year', Venta.creado_en).label('anio'),
                func_sql.count(Venta.id).label('cantidad'),
                func_sql.coalesce(func_sql.sum(Venta.total), 0).label('monto')
            )
            .where(and_(*base_filters))
            .group_by('mes', 'anio')
            .order_by('anio', 'mes')
        )
        
        # Obtener unidades por mes
        unidades_result = await db.execute(
            select(
                func_sql.extract('month', Venta.creado_en).label('mes'),
                func_sql.extract('year', Venta.creado_en).label('anio'),
                func_sql.coalesce(func_sql.sum(VentaItem.cantidad), 0).label('unidades')
            )
            .join(VentaItem, VentaItem.venta_id == Venta.id)
            .where(and_(*base_filters))
            .group_by('mes', 'anio')
        )
        unidades_dict = {(int(row[0]), int(row[1])): int(row[2] or 0) for row in unidades_result.all()}
        
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return [
            {
                "label": meses[int(row[0]) - 1],
                "cantidad": row[2],
                "monto": float(row[3]),
                "unidades": unidades_dict.get((int(row[0]), int(row[1])), 0)
            }
            for row in result.all()
        ]
    
    elif periodo == "anio":
        # Último año agrupado por mes
        fecha_inicio = today - timedelta(days=365)
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(tzinfo=PARAGUAY_TZ)
        
        base_filters.append(Venta.creado_en >= fecha_inicio_dt)
        
        result = await db.execute(
            select(
                func_sql.extract('month', Venta.creado_en).label('mes'),
                func_sql.extract('year', Venta.creado_en).label('anio'),
                func_sql.count(Venta.id).label('cantidad'),
                func_sql.coalesce(func_sql.sum(Venta.total), 0).label('monto')
            )
            .where(and_(*base_filters))
            .group_by('mes', 'anio')
            .order_by('anio', 'mes')
        )
        
        # Obtener unidades por mes
        unidades_result = await db.execute(
            select(
                func_sql.extract('month', Venta.creado_en).label('mes'),
                func_sql.extract('year', Venta.creado_en).label('anio'),
                func_sql.coalesce(func_sql.sum(VentaItem.cantidad), 0).label('unidades')
            )
            .join(VentaItem, VentaItem.venta_id == Venta.id)
            .where(and_(*base_filters))
            .group_by('mes', 'anio')
        )
        unidades_dict = {(int(row[0]), int(row[1])): int(row[2] or 0) for row in unidades_result.all()}
        
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return [
            {
                "label": meses[int(row[0]) - 1],
                "cantidad": row[2],
                "monto": float(row[3]),
                "unidades": unidades_dict.get((int(row[0]), int(row[1])), 0)
            }
            for row in result.all()
        ]
    
    return []

# ==================== BUSINESS INTELLIGENCE ====================







# ==================== ALERTAS ====================
@api_router.get("/alertas", response_model=List[Alerta])
async def obtener_alertas(empresa_id: int, db: AsyncSession = Depends(get_db)):
    alertas = []
    today = today_paraguay()
    
    fecha_limite = today + timedelta(days=30)
    productos_vencimiento = await db.execute(
        select(Producto)
        .where(
            Producto.empresa_id == empresa_id,
            Producto.activo == True,
            Producto.fecha_vencimiento.isnot(None),
            Producto.fecha_vencimiento <= fecha_limite
        )
    )
    for prod in productos_vencimiento.scalars().all():
        dias = (prod.fecha_vencimiento - today).days
        nivel = "danger" if dias <= 7 else "warning"
        alertas.append(Alerta(
            tipo="vencimiento_producto",
            mensaje=f"{prod.nombre} vence en {dias} días",
            nivel=nivel,
            referencia_id=prod.id
        ))
    
    vehiculos_result = await db.execute(
        select(Vehiculo)
        .where(
            Vehiculo.empresa_id == empresa_id,
            or_(
                and_(
                    Vehiculo.vencimiento_habilitacion.isnot(None),
                    Vehiculo.vencimiento_habilitacion <= fecha_limite
                ),
                and_(
                    Vehiculo.vencimiento_cedula_verde.isnot(None),
                    Vehiculo.vencimiento_cedula_verde <= fecha_limite
                )
            )
        )
    )
    for veh in vehiculos_result.scalars().all():
        if veh.vencimiento_habilitacion and veh.vencimiento_habilitacion <= fecha_limite:
            dias = (veh.vencimiento_habilitacion - today).days
            nivel = "danger" if dias <= 7 else "warning"
            alertas.append(Alerta(
                tipo="vencimiento_habilitacion",
                mensaje=f"Habilitación de {veh.chapa} vence en {dias} días",
                nivel=nivel,
                referencia_id=veh.id
            ))
        if veh.vencimiento_cedula_verde and veh.vencimiento_cedula_verde <= fecha_limite:
            dias = (veh.vencimiento_cedula_verde - today).days
            nivel = "danger" if dias <= 7 else "warning"
            alertas.append(Alerta(
                tipo="vencimiento_cedula_verde",
                mensaje=f"Cédula verde de {veh.chapa} vence en {dias} días",
                nivel=nivel,
                referencia_id=veh.id
            ))
    
    stock_bajo = await db.execute(
        select(Producto.id, Producto.nombre, func_sql.sum(StockActual.cantidad), StockActual.alerta_minima)
        .join(StockActual, Producto.id == StockActual.producto_id)
        .where(
            Producto.empresa_id == empresa_id,
            Producto.activo == True,
            StockActual.alerta_minima.isnot(None)
        )
        .group_by(Producto.id, Producto.nombre, StockActual.alerta_minima)
        .having(func_sql.sum(StockActual.cantidad) <= StockActual.alerta_minima)
    )
    for row in stock_bajo.all():
        alertas.append(Alerta(
            tipo="stock_bajo",
            mensaje=f"{row[1]} tiene stock bajo ({row[2]} unidades)",
            nivel="warning",
            referencia_id=row[0]
        ))
    
    return alertas

# ==================== REPORTES PDF ====================
def crear_pdf_reporte(titulo, subtitulo, columnas, datos, totales=None, col_widths=None):
    """Genera un PDF con tabla de datos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=6, alignment=TA_CENTER)
    elements.append(Paragraph(titulo, title_style))
    
    # Subtitle
    subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Normal'], fontSize=10, spaceAfter=20, alignment=TA_CENTER, textColor=colors.grey)
    elements.append(Paragraph(subtitulo, subtitle_style))
    
    # Table
    table_data = [columnas] + datos
    
    if totales:
        table_data.append(totales)
    
    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0044CC')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    
    if totales:
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E0E0E0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
    
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    elements.append(Paragraph(f"Generado el {now_paraguay().strftime('%d/%m/%Y %H:%M')} - Ethercloud ERP", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def crear_excel_reporte(titulo, subtitulo, columnas, datos, totales=None):
    """Genera un Excel (.xlsx) con tabla de datos estilizada"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"

    num_cols = len(columnas)
    last_col = get_column_letter(num_cols)

    # Title row (row 1)
    ws.merge_cells(f"A1:{last_col}1")
    title_cell = ws["A1"]
    title_cell.value = titulo
    title_cell.font = Font(name="Calibri", size=16, bold=True, color="0044CC")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Subtitle row (row 2)
    ws.merge_cells(f"A2:{last_col}2")
    sub_cell = ws["A2"]
    sub_cell.value = subtitulo
    sub_cell.font = Font(name="Calibri", size=10, color="808080")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    # Empty row 3 (spacer)
    ws.row_dimensions[3].height = 6

    # Headers (row 4)
    HEADER_ROW = 4
    header_fill = PatternFill(start_color="0044CC", end_color="0044CC", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, col_name in enumerate(columnas, 1):
        cell = ws.cell(row=HEADER_ROW, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    ws.row_dimensions[HEADER_ROW].height = 20

    # Data rows
    for row_offset, row_data in enumerate(datos, 1):
        row_num = HEADER_ROW + row_offset
        bg = "FFFFFF" if row_offset % 2 == 1 else "F5F5F5"
        fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=value)
            cell.fill = fill
            cell.font = Font(name="Calibri", size=9)
            cell.border = border
            cell.alignment = Alignment(horizontal="left" if col_idx < num_cols else "right", vertical="center")

    # Totals row
    if totales:
        tot_row = HEADER_ROW + len(datos) + 1
        tot_fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
        tot_font = Font(name="Calibri", size=9, bold=True)
        for col_idx, value in enumerate(totales, 1):
            cell = ws.cell(row=tot_row, column=col_idx, value=value)
            cell.fill = tot_fill
            cell.font = tot_font
            cell.border = border
            cell.alignment = Alignment(horizontal="right", vertical="center")

    # Auto-size columns
    for col_idx in range(1, num_cols + 1):
        max_len = len(str(columnas[col_idx - 1]))
        for row_data in datos:
            if col_idx <= len(row_data):
                max_len = max(max_len, len(str(row_data[col_idx - 1])))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 45)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

@api_router.get("/reportes/ventas")
async def reporte_ventas(
    empresa_id: int,
    fecha_desde: str,
    fecha_hasta: str,
    tipo_pago: str = None,
    estado: str = None,
    cliente_id: int = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte PDF de ventas por rango de fechas con filtros"""
    try:
        fecha_ini = datetime.fromisoformat(fecha_desde).replace(tzinfo=PARAGUAY_TZ)
        fecha_fin = (datetime.fromisoformat(fecha_hasta) + timedelta(days=1)).replace(tzinfo=PARAGUAY_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    query = (
        select(Venta, Cliente)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.creado_en >= fecha_ini,
            Venta.creado_en < fecha_fin
        )
    )
    
    # Apply cliente_id filter if provided
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)
    
    # Apply estado filter - None or 'TODOS' means all states; specific value filters by that state
    if estado and estado != 'TODOS':
        try:
            query = query.where(Venta.estado == EstadoVenta[estado])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
    
    # Apply tipo_pago filter - support CONTADO (all non-credit) and CREDITO
    if tipo_pago:
        if tipo_pago == 'CONTADO':
            # CONTADO = all payment types except CREDITO
            query = query.where(Venta.tipo_pago.in_([TipoPago.EFECTIVO, TipoPago.TARJETA, TipoPago.TRANSFERENCIA, TipoPago.CHEQUE]))
        elif tipo_pago == 'CREDITO':
            query = query.where(Venta.tipo_pago == TipoPago.CREDITO)
        else:
            # Support specific payment types if provided
            try:
                query = query.where(Venta.tipo_pago == TipoPago[tipo_pago])
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Tipo de pago '{tipo_pago}' no válido")
    
    query = query.order_by(Venta.creado_en)
    result = await db.execute(query)
    ventas = result.all()
    
    if not ventas:
        raise HTTPException(status_code=404, detail="No se encontraron ventas para los filtros seleccionados")
    
    columnas = ['ID', 'Fecha', 'Cliente', 'Tipo Pago', 'Total', 'Costo', 'Ganancia']
    datos = []
    total_general = Decimal('0')
    costo_general = Decimal('0')
    ganancia_general = Decimal('0')
    
    for venta, cliente in ventas:
        total_general += venta.total
        costo_v = venta.costo_total or Decimal('0')
        ganancia_v = venta.ganancia or Decimal('0')
        costo_general += costo_v
        ganancia_general += ganancia_v
        datos.append([
            str(venta.id),
            venta.creado_en.strftime('%d/%m/%Y'),
            f"{cliente.nombre} {cliente.apellido or ''}".strip()[:25],
            venta.tipo_pago.value if venta.tipo_pago else 'EFECTIVO',
            f"{float(venta.total):,.0f}",
            f"{float(costo_v):,.0f}",
            f"{float(ganancia_v):,.0f}"
        ])
    
    totales = ['', '', '', 'TOTAL:', f"{float(total_general):,.0f}", f"{float(costo_general):,.0f}", f"{float(ganancia_general):,.0f}"]
    
    # Build subtitle with filters
    subtitle = f"Período: {fecha_desde} al {fecha_hasta}"
    if tipo_pago:
        if tipo_pago == 'CONTADO':
            subtitle += " | Tipo: CONTADO"
        elif tipo_pago == 'CREDITO':
            subtitle += " | Tipo: CRÉDITO"
        else:
            subtitle += f" | Pago: {tipo_pago}"
    if estado:
        subtitle += f" | Estado: {estado}"
    subtitle += f" | Total ventas: {len(datos)}"
    
    pdf_bytes = crear_pdf_reporte(
        "Reporte de Ventas",
        subtitle,
        columnas,
        datos,
        totales
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_ventas_{fecha_desde}_{fecha_hasta}.pdf"}
    )

@api_router.get("/reportes/ventas/excel")
async def reporte_ventas_excel(
    empresa_id: int,
    fecha_desde: str,
    fecha_hasta: str,
    tipo_pago: str = None,
    estado: str = None,
    cliente_id: int = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte Excel de ventas por rango de fechas con filtros"""
    try:
        fecha_ini = datetime.fromisoformat(fecha_desde).replace(tzinfo=PARAGUAY_TZ)
        fecha_fin = (datetime.fromisoformat(fecha_hasta) + timedelta(days=1)).replace(tzinfo=PARAGUAY_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    query = (
        select(Venta, Cliente)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.creado_en >= fecha_ini,
            Venta.creado_en < fecha_fin
        )
    )
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)
    if estado and estado != 'TODOS':
        try:
            query = query.where(Venta.estado == EstadoVenta[estado])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
    if tipo_pago:
        if tipo_pago == 'CONTADO':
            query = query.where(Venta.tipo_pago.in_([TipoPago.EFECTIVO, TipoPago.TARJETA, TipoPago.TRANSFERENCIA, TipoPago.CHEQUE]))
        elif tipo_pago == 'CREDITO':
            query = query.where(Venta.tipo_pago == TipoPago.CREDITO)
        else:
            try:
                query = query.where(Venta.tipo_pago == TipoPago[tipo_pago])
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Tipo de pago '{tipo_pago}' no válido")
    query = query.order_by(Venta.creado_en)
    result = await db.execute(query)
    ventas = result.all()

    if not ventas:
        raise HTTPException(status_code=404, detail="No se encontraron ventas para los filtros seleccionados")

    columnas = ['ID', 'Fecha', 'Cliente', 'Tipo Pago', 'Total', 'Costo', 'Ganancia']
    datos = []
    total_general = Decimal('0')
    costo_general = Decimal('0')
    ganancia_general = Decimal('0')
    for venta, cliente in ventas:
        total_general += venta.total
        costo_v = venta.costo_total or Decimal('0')
        ganancia_v = venta.ganancia or Decimal('0')
        costo_general += costo_v
        ganancia_general += ganancia_v
        datos.append([
            str(venta.id),
            venta.creado_en.strftime('%d/%m/%Y'),
            f"{cliente.nombre} {cliente.apellido or ''}".strip(),
            venta.tipo_pago.value if venta.tipo_pago else 'EFECTIVO',
            float(venta.total),
            float(costo_v),
            float(ganancia_v)
        ])
    totales = ['', '', '', 'TOTAL:', float(total_general), float(costo_general), float(ganancia_general)]

    subtitle = f"Período: {fecha_desde} al {fecha_hasta}"
    if tipo_pago:
        subtitle += f" | Tipo: {tipo_pago}"
    if estado:
        subtitle += f" | Estado: {estado}"
    subtitle += f" | Total ventas: {len(datos)}"

    excel_bytes = crear_excel_reporte("Reporte de Ventas", subtitle, columnas, datos, totales)
    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename=reporte_ventas_{fecha_desde}_{fecha_hasta}.xlsx"}
    )

@api_router.get("/reportes/historial-ventas")
async def reporte_historial_ventas(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    cliente_id: int = None,
    usuario_id: int = None,
    estado: str = None,
    monto_min: float = None,
    monto_max: float = None,
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte PDF del historial de ventas con filtros aplicados"""
    query = (
        select(Venta, Cliente)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .where(Venta.empresa_id == empresa_id)
        .order_by(Venta.creado_en.desc())
    )
    
    # Apply filters
    if fecha_desde:
        query = query.where(Venta.creado_en >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.where(Venta.creado_en < datetime.fromisoformat(fecha_hasta) + timedelta(days=1))
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)
    if usuario_id:
        query = query.where(Venta.usuario_id == usuario_id)
    if estado:
        try:
            query = query.where(Venta.estado == EstadoVenta[estado])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
    if monto_min:
        query = query.where(Venta.total >= monto_min)
    if monto_max:
        query = query.where(Venta.total <= monto_max)
    
    result = await db.execute(query)
    ventas = result.all()
    
    if not ventas:
        # Return empty PDF
        subtitle = "Sin registros para los filtros aplicados"
        pdf_bytes = crear_pdf_reporte("Historial de Ventas", subtitle, ['Info'], [['No se encontraron ventas']], None)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=historial_ventas_vacio.pdf"}
        )
    
    # Build table data
    columnas = ['ID', 'Fecha', 'Cliente', 'Tipo Pago', 'Estado', 'Total', 'Costo', 'Ganancia']
    datos = []
    total_general = Decimal('0')
    costo_general = Decimal('0')
    ganancia_general = Decimal('0')
    cantidad_confirmadas = 0
    
    for venta, cliente in ventas:
        es_confirmada = venta.estado == EstadoVenta.CONFIRMADA
        if es_confirmada:
            total_general += venta.total
            costo_general += venta.costo_total or Decimal('0')
            ganancia_general += venta.ganancia or Decimal('0')
            cantidad_confirmadas += 1
        costo_v = venta.costo_total or Decimal('0')
        ganancia_v = venta.ganancia or Decimal('0')
        estado_text = venta.estado.value if venta.estado else 'N/A'
        datos.append([
            str(venta.id),
            venta.creado_en.strftime('%d/%m/%Y %H:%M'),
            f"{cliente.nombre} {cliente.apellido or ''}".strip()[:20],
            venta.tipo_pago.value if venta.tipo_pago else 'EFECTIVO',
            estado_text,
            f"{float(venta.total):,.0f}",
            f"{float(costo_v) if es_confirmada else 0:,.0f}",
            f"{float(ganancia_v) if es_confirmada else 0:,.0f}"
        ])
    
    # Build subtitle with filters and summary
    subtitle_parts = []
    if fecha_desde:
        subtitle_parts.append(f"Desde: {fecha_desde}")
    if fecha_hasta:
        subtitle_parts.append(f"Hasta: {fecha_hasta}")
    if estado:
        subtitle_parts.append(f"Estado: {estado}")
    
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else "Todas las ventas"
    subtitle += f" | Total registros: {len(ventas)} | Confirmadas: {cantidad_confirmadas}"
    
    totales = ['', '', '', '', 'TOTAL CONFIRMADO:', f"{float(total_general):,.0f}", f"{float(costo_general):,.0f}", f"{float(ganancia_general):,.0f}"]
    
    pdf_bytes = crear_pdf_reporte("Historial de Ventas", subtitle, columnas, datos, totales)
    
    filename = f"historial_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/reportes/historial-ventas/excel")
async def reporte_historial_ventas_excel(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    cliente_id: int = None,
    usuario_id: int = None,
    estado: str = None,
    monto_min: float = None,
    monto_max: float = None,
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte Excel del historial de ventas con filtros aplicados"""
    query = (
        select(Venta, Cliente)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .where(Venta.empresa_id == empresa_id)
        .order_by(Venta.creado_en.desc())
    )
    if fecha_desde:
        query = query.where(Venta.creado_en >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.where(Venta.creado_en < datetime.fromisoformat(fecha_hasta) + timedelta(days=1))
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)
    if usuario_id:
        query = query.where(Venta.usuario_id == usuario_id)
    if estado:
        try:
            query = query.where(Venta.estado == EstadoVenta[estado])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
    if monto_min:
        query = query.where(Venta.total >= monto_min)
    if monto_max:
        query = query.where(Venta.total <= monto_max)

    result = await db.execute(query)
    ventas = result.all()

    columnas = ['ID', 'Fecha', 'Cliente', 'Tipo Pago', 'Estado', 'Total', 'Costo', 'Ganancia']
    datos = []
    total_general = Decimal('0')
    costo_general = Decimal('0')
    ganancia_general = Decimal('0')
    cantidad_confirmadas = 0

    for venta, cliente in ventas:
        es_confirmada = venta.estado == EstadoVenta.CONFIRMADA
        if es_confirmada:
            total_general += venta.total
            costo_general += venta.costo_total or Decimal('0')
            ganancia_general += venta.ganancia or Decimal('0')
            cantidad_confirmadas += 1
        costo_v = venta.costo_total or Decimal('0')
        ganancia_v = venta.ganancia or Decimal('0')
        datos.append([
            str(venta.id),
            venta.creado_en.strftime('%d/%m/%Y %H:%M'),
            f"{cliente.nombre} {cliente.apellido or ''}".strip(),
            venta.tipo_pago.value if venta.tipo_pago else 'EFECTIVO',
            venta.estado.value if venta.estado else 'N/A',
            float(venta.total),
            float(costo_v) if es_confirmada else 0,
            float(ganancia_v) if es_confirmada else 0
        ])

    subtitle_parts = []
    if fecha_desde:
        subtitle_parts.append(f"Desde: {fecha_desde}")
    if fecha_hasta:
        subtitle_parts.append(f"Hasta: {fecha_hasta}")
    if estado:
        subtitle_parts.append(f"Estado: {estado}")
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else "Todas las ventas"
    subtitle += f" | Total registros: {len(ventas)} | Confirmadas: {cantidad_confirmadas}"

    totales = ['', '', '', '', 'TOTAL CONF.:', float(total_general), float(costo_general), float(ganancia_general)]
    excel_bytes = crear_excel_reporte("Historial de Ventas", subtitle, columnas, datos, totales)
    filename = f"historial_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/reportes/stock")
async def reporte_stock(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    solo_alertas: str = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte PDF de stock actual con filtros"""
    try:
        # Get products with aggregated stock and the minimum alerta_minima
        result = await db.execute(
            select(
                Producto, 
                func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0).label('stock_total'),
                func_sql.min(StockActual.alerta_minima).label('alerta_minima_val')
            )
            .outerjoin(StockActual, Producto.id == StockActual.producto_id)
            .where(Producto.empresa_id == empresa_id, Producto.activo == True)
            .group_by(Producto.id)
            .order_by(Producto.nombre)
        )
        productos = result.all()
        
        if not productos:
            raise HTTPException(status_code=404, detail="No se encontraron productos activos en el inventario")
        
        # A4 width 595pt - 60pt margins = 535pt available
        # ID=35, Código=70, Producto=190, Stock=45, P.Venta=95, P.Costo=95 → total=530
        col_widths_stock = [35, 70, 190, 45, 95, 95]
        columnas = ['ID', 'Código', 'Producto', 'Stock', 'Precio Venta', 'Precio Costo']
        datos = []
        
        for producto, stock, alerta_minima_val in productos:
            # Use alerta_minima from StockActual if available, else use stock_minimo from Producto, else default to 10
            stock_minimo = alerta_minima_val if alerta_minima_val is not None else (producto.stock_minimo if producto.stock_minimo is not None else 10)
            es_alerta = stock <= stock_minimo
            
            # Filter by solo_alertas if specified
            if solo_alertas == 'true' and not es_alerta:
                continue
            
            estado = " (!)" if es_alerta else ""
            datos.append([
                str(producto.id),
                producto.codigo_barra or '-',
                f"{producto.nombre}{estado}",
                str(int(stock)),
                f"{float(producto.precio_venta):,.0f}",
                f"{float(producto.precio_costo or 0):,.0f}"
            ])
        
        if not datos:
            raise HTTPException(status_code=404, detail="No se encontraron productos con los filtros seleccionados")

        # Build subtitle
        subtitle = f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"
        if solo_alertas == 'true':
            subtitle += " | Solo stock bajo"
        subtitle += f" | Total productos: {len(datos)}"
        
        pdf_bytes = crear_pdf_reporte(
            "Reporte de Stock Actual",
            subtitle,
            columnas,
            datos,
            col_widths=col_widths_stock
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte de stock: {str(e)}")
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_stock_{today_paraguay().isoformat()}.pdf"}
    )

@api_router.get("/reportes/stock/excel")
async def reporte_stock_excel(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    solo_alertas: str = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte Excel de stock actual con filtros"""
    try:
        result = await db.execute(
            select(
                Producto,
                func_sql.coalesce(func_sql.sum(StockActual.cantidad), 0).label('stock_total'),
                func_sql.min(StockActual.alerta_minima).label('alerta_minima_val')
            )
            .outerjoin(StockActual, Producto.id == StockActual.producto_id)
            .where(Producto.empresa_id == empresa_id, Producto.activo == True)
            .group_by(Producto.id)
            .order_by(Producto.nombre)
        )
        productos = result.all()

        if not productos:
            raise HTTPException(status_code=404, detail="No se encontraron productos activos en el inventario")

        columnas = ['ID', 'Código', 'Producto', 'Stock', 'Precio Venta', 'Precio Costo', 'Alerta']
        datos = []
        for producto, stock, alerta_minima_val in productos:
            stock_minimo = alerta_minima_val if alerta_minima_val is not None else (producto.stock_minimo if producto.stock_minimo is not None else 10)
            es_alerta = stock <= stock_minimo
            if solo_alertas == 'true' and not es_alerta:
                continue
            datos.append([
                producto.id,
                producto.codigo_barra or '-',
                producto.nombre,
                int(stock),
                float(producto.precio_venta),
                float(producto.precio_costo or 0),
                'Stock bajo' if es_alerta else 'OK'
            ])

        if not datos:
            raise HTTPException(status_code=404, detail="No se encontraron productos con los filtros seleccionados")

        subtitle = f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"
        if solo_alertas == 'true':
            subtitle += " | Solo stock bajo"
        subtitle += f" | Total productos: {len(datos)}"

        excel_bytes = crear_excel_reporte("Reporte de Stock Actual", subtitle, columnas, datos)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte de stock: {str(e)}")

    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename=reporte_stock_{today_paraguay().isoformat()}.xlsx"}
    )

@api_router.get("/reportes/deudas-proveedores")
async def reporte_deudas_proveedores(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    estado: str = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte PDF de deudas a proveedores con filtros"""
    try:
        query = (
            select(DeudaProveedor, Proveedor)
            .join(Proveedor, DeudaProveedor.proveedor_id == Proveedor.id)
            .where(Proveedor.empresa_id == empresa_id)
        )
        
        # Filter by estado (default: PENDIENTE if not specified)
        if estado:
            if estado == 'TODOS':
                # No filter, show all
                pass
            elif estado == 'PENDIENTE':
                query = query.where(DeudaProveedor.pagado == False)
            elif estado == 'PAGADO':
                query = query.where(DeudaProveedor.pagado == True)
            else:
                raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido. Use PENDIENTE, PAGADO o TODOS")
        else:
            # Default to PENDIENTE if estado is None
            query = query.where(DeudaProveedor.pagado == False)
        
        # Filter by fecha_emision range
        if fecha_desde:
            try:
                fecha_ini = datetime.fromisoformat(fecha_desde)
                query = query.where(DeudaProveedor.fecha_emision >= fecha_ini.date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        if fecha_hasta:
            try:
                fecha_fin = datetime.fromisoformat(fecha_hasta)
                query = query.where(DeudaProveedor.fecha_emision <= fecha_fin.date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        
        query = query.order_by(DeudaProveedor.fecha_limite)
        result = await db.execute(query)
        deudas = result.all()
        
        if not deudas:
            raise HTTPException(status_code=404, detail="No se encontraron deudas con los filtros seleccionados")
        
        columnas = ['Proveedor', 'Descripción', 'Monto', 'Emisión', 'Vencimiento']
        datos = []
        total_deuda = Decimal('0')
        
        for deuda, proveedor in deudas:
            total_deuda += deuda.monto
            vencido = "⚠️" if deuda.fecha_limite and deuda.fecha_limite < today_paraguay() else ""
            datos.append([
                proveedor.nombre[:25],
                (deuda.descripcion or '-')[:30],
                f"{float(deuda.monto):,.0f}",
                deuda.fecha_emision.strftime('%d/%m/%Y') if deuda.fecha_emision else '-',
                f"{deuda.fecha_limite.strftime('%d/%m/%Y') if deuda.fecha_limite else '-'}{vencido}"
            ])
        
        totales = ['', '', f"{float(total_deuda):,.0f}", '', '']
        
        # Build subtitle
        subtitle = f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"
        if fecha_desde and fecha_hasta:
            subtitle += f" | Período: {fecha_desde} al {fecha_hasta}"
        if estado:
            subtitle += f" | Estado: {estado}"
        subtitle += f" | Total deudas: {len(datos)}"
        
        pdf_bytes = crear_pdf_reporte(
            "Reporte de Deudas a Proveedores",
            subtitle,
            columnas,
            datos,
            totales
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte de deudas: {str(e)}")
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_deudas_proveedores_{today_paraguay().isoformat()}.pdf"}
    )

@api_router.get("/reportes/deudas-proveedores/excel")
async def reporte_deudas_proveedores_excel(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    estado: str = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte Excel de deudas a proveedores con filtros"""
    try:
        query = (
            select(DeudaProveedor, Proveedor)
            .join(Proveedor, DeudaProveedor.proveedor_id == Proveedor.id)
            .where(Proveedor.empresa_id == empresa_id)
        )
        if estado:
            if estado == 'TODOS':
                pass
            elif estado == 'PENDIENTE':
                query = query.where(DeudaProveedor.pagado == False)
            elif estado == 'PAGADO':
                query = query.where(DeudaProveedor.pagado == True)
            else:
                raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
        else:
            query = query.where(DeudaProveedor.pagado == False)
        if fecha_desde:
            try:
                query = query.where(DeudaProveedor.fecha_emision >= datetime.fromisoformat(fecha_desde).date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        if fecha_hasta:
            try:
                query = query.where(DeudaProveedor.fecha_emision <= datetime.fromisoformat(fecha_hasta).date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        query = query.order_by(DeudaProveedor.fecha_limite)
        result = await db.execute(query)
        deudas = result.all()

        if not deudas:
            raise HTTPException(status_code=404, detail="No se encontraron deudas con los filtros seleccionados")

        columnas = ['Proveedor', 'Descripción', 'Monto', 'Emisión', 'Vencimiento', 'Estado']
        datos = []
        total_deuda = Decimal('0')
        for deuda, proveedor in deudas:
            total_deuda += deuda.monto
            vencido = deuda.fecha_limite and deuda.fecha_limite < today_paraguay()
            datos.append([
                proveedor.nombre,
                deuda.descripcion or '-',
                float(deuda.monto),
                deuda.fecha_emision.strftime('%d/%m/%Y') if deuda.fecha_emision else '-',
                deuda.fecha_limite.strftime('%d/%m/%Y') if deuda.fecha_limite else '-',
                'VENCIDO' if vencido else ('PAGADO' if deuda.pagado else 'PENDIENTE')
            ])

        totales = ['', '', float(total_deuda), '', '', '']
        subtitle = f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"
        if fecha_desde and fecha_hasta:
            subtitle += f" | Período: {fecha_desde} al {fecha_hasta}"
        if estado:
            subtitle += f" | Estado: {estado}"
        subtitle += f" | Total deudas: {len(datos)}"

        excel_bytes = crear_excel_reporte("Reporte de Deudas a Proveedores", subtitle, columnas, datos, totales)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte de deudas: {str(e)}")

    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename=reporte_deudas_proveedores_{today_paraguay().isoformat()}.xlsx"}
    )

@api_router.get("/reportes/creditos-clientes")
async def reporte_creditos_clientes(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    estado: str = None,
    cliente_id: int = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte PDF de créditos de clientes con filtros"""
    try:
        query = (
            select(CreditoCliente, Cliente)
            .join(Cliente, CreditoCliente.cliente_id == Cliente.id)
            .where(Cliente.empresa_id == empresa_id)
        )
        if cliente_id:
            query = query.where(CreditoCliente.cliente_id == cliente_id)
        
        # Filter by estado (default: PENDIENTE if not specified)
        if estado:
            if estado == 'TODOS':
                # No filter, show all
                pass
            elif estado == 'PENDIENTE':
                query = query.where(CreditoCliente.pagado == False)
            elif estado == 'PAGADO':
                query = query.where(CreditoCliente.pagado == True)
            else:
                raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido. Use PENDIENTE, PAGADO o TODOS")
        else:
            # Default to PENDIENTE if estado is None
            query = query.where(CreditoCliente.pagado == False)
        
        # Filter by fecha_venta range
        if fecha_desde:
            try:
                fecha_ini = datetime.fromisoformat(fecha_desde)
                query = query.where(CreditoCliente.fecha_venta >= fecha_ini.date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        if fecha_hasta:
            try:
                fecha_fin = datetime.fromisoformat(fecha_hasta)
                query = query.where(CreditoCliente.fecha_venta <= fecha_fin.date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        
        query = query.order_by(CreditoCliente.fecha_venta)
        result = await db.execute(query)
        creditos = result.all()
        
        if not creditos:
            raise HTTPException(status_code=404, detail="No se encontraron créditos con los filtros seleccionados")
        
        columnas = ['Cliente', 'Venta #', 'Original', 'Pagado', 'Pendiente', 'Fecha']
        datos = []
        total_pendiente = Decimal('0')
        total_pagado = Decimal('0')
        total_original = Decimal('0')
        
        for credito, cliente in creditos:
            monto_pagado = credito.monto_original - credito.monto_pendiente
            total_pendiente += credito.monto_pendiente
            total_pagado += monto_pagado
            total_original += credito.monto_original
            datos.append([
                f"{cliente.nombre} {cliente.apellido or ''}".strip()[:25],
                str(credito.venta_id or '-'),
                f"{float(credito.monto_original):,.0f}",
                f"{float(monto_pagado):,.0f}",
                f"{float(credito.monto_pendiente):,.0f}",
                credito.fecha_venta.strftime('%d/%m/%Y') if credito.fecha_venta else '-'
            ])
        
        totales = ['', 'TOTAL:', f"{float(total_original):,.0f}", f"{float(total_pagado):,.0f}", f"{float(total_pendiente):,.0f}", '']
        
        # Build subtitle
        subtitle = f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"
        if fecha_desde and fecha_hasta:
            subtitle += f" | Período: {fecha_desde} al {fecha_hasta}"
        if estado:
            subtitle += f" | Estado: {estado}"
        subtitle += f" | Total créditos: {len(datos)}"
        
        pdf_bytes = crear_pdf_reporte(
            "Reporte de Créditos de Clientes",
            subtitle,
            columnas,
            datos,
            totales
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte de créditos: {str(e)}")
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_creditos_clientes_{today_paraguay().isoformat()}.pdf"}
    )

@api_router.get("/reportes/creditos-clientes/excel")
async def reporte_creditos_clientes_excel(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    estado: str = None,
    cliente_id: int = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte Excel de créditos de clientes con filtros"""
    try:
        query = (
            select(CreditoCliente, Cliente)
            .join(Cliente, CreditoCliente.cliente_id == Cliente.id)
            .where(Cliente.empresa_id == empresa_id)
        )
        if cliente_id:
            query = query.where(CreditoCliente.cliente_id == cliente_id)
        if estado:
            if estado == 'TODOS':
                pass
            elif estado == 'PENDIENTE':
                query = query.where(CreditoCliente.pagado == False)
            elif estado == 'PAGADO':
                query = query.where(CreditoCliente.pagado == True)
            else:
                raise HTTPException(status_code=400, detail=f"Estado '{estado}' no válido")
        else:
            query = query.where(CreditoCliente.pagado == False)
        if fecha_desde:
            try:
                query = query.where(CreditoCliente.fecha_venta >= datetime.fromisoformat(fecha_desde).date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        if fecha_hasta:
            try:
                query = query.where(CreditoCliente.fecha_venta <= datetime.fromisoformat(fecha_hasta).date())
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        query = query.order_by(CreditoCliente.fecha_venta)
        result = await db.execute(query)
        creditos = result.all()

        if not creditos:
            raise HTTPException(status_code=404, detail="No se encontraron créditos con los filtros seleccionados")

        columnas = ['Cliente', 'Venta #', 'Monto Original', 'Pagado', 'Pendiente', 'Fecha']
        datos = []
        total_pendiente = Decimal('0')
        total_pagado = Decimal('0')
        total_original = Decimal('0')
        for credito, cliente in creditos:
            monto_pagado = credito.monto_original - credito.monto_pendiente
            total_pendiente += credito.monto_pendiente
            total_pagado += monto_pagado
            total_original += credito.monto_original
            datos.append([
                f"{cliente.nombre} {cliente.apellido or ''}".strip(),
                str(credito.venta_id or '-'),
                float(credito.monto_original),
                float(monto_pagado),
                float(credito.monto_pendiente),
                credito.fecha_venta.strftime('%d/%m/%Y') if credito.fecha_venta else '-'
            ])

        totales = ['', 'TOTAL:', float(total_original), float(total_pagado), float(total_pendiente), '']
        subtitle = f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"
        if fecha_desde and fecha_hasta:
            subtitle += f" | Período: {fecha_desde} al {fecha_hasta}"
        if estado:
            subtitle += f" | Estado: {estado}"
        subtitle += f" | Total créditos: {len(datos)}"

        excel_bytes = crear_excel_reporte("Reporte de Créditos de Clientes", subtitle, columnas, datos, totales)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte de créditos: {str(e)}")

    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename=reporte_creditos_clientes_{today_paraguay().isoformat()}.xlsx"}
    )

@api_router.get("/reportes/venta-items")
async def reporte_venta_items(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    categoria_id: int = None,
    producto_id: int = None,
    cliente_id: int = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte PDF de ventas de items agrupadas por producto/materia de laboratorio"""
    from collections import defaultdict
    query = (
        select(VentaItem, Venta, Producto, Categoria, MateriaLaboratorio)
        .join(Venta, VentaItem.venta_id == Venta.id)
        .outerjoin(Producto, VentaItem.producto_id == Producto.id)
        .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
        .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA
        )
    )
    if fecha_desde:
        try:
            query = query.where(Venta.creado_en >= datetime.fromisoformat(fecha_desde).replace(tzinfo=PARAGUAY_TZ))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
    if fecha_hasta:
        try:
            query = query.where(Venta.creado_en < (datetime.fromisoformat(fecha_hasta) + timedelta(days=1)).replace(tzinfo=PARAGUAY_TZ))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
    if categoria_id:
        query = query.where(Producto.categoria_id == categoria_id)
    if producto_id:
        query = query.where(VentaItem.producto_id == producto_id)
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No se encontraron ventas de items para los filtros seleccionados")

    agg = defaultdict(lambda: {'cantidad': 0, 'total': Decimal('0'), 'categoria': '-'})
    for item, venta, producto, categoria, materia in rows:
        if producto:
            key = producto.nombre
            agg[key]['cantidad'] += item.cantidad
            agg[key]['total'] += item.total
            agg[key]['categoria'] = categoria.nombre if categoria else 'Sin categoría'
        elif materia:
            key = f"[LAB] {materia.nombre}"
            agg[key]['cantidad'] += item.cantidad
            agg[key]['total'] += item.total
            agg[key]['categoria'] = 'Laboratorio'

    sorted_items = sorted(agg.items(), key=lambda x: x[1]['total'], reverse=True)

    columnas = ['Producto / Item', 'Categoría', 'Cant. Vendida', 'Monto Total (Gs.)']
    datos = []
    total_cant = 0
    total_monto = Decimal('0')
    for nombre, data in sorted_items:
        total_cant += data['cantidad']
        total_monto += data['total']
        datos.append([
            nombre[:40],
            data['categoria'],
            str(data['cantidad']),
            f"{float(data['total']):,.0f}"
        ])

    totales = ['TOTAL', '', str(total_cant), f"{float(total_monto):,.0f}"]

    subtitle_parts = []
    if fecha_desde and fecha_hasta:
        subtitle_parts.append(f"Período: {fecha_desde} al {fecha_hasta}")
    elif fecha_desde:
        subtitle_parts.append(f"Desde: {fecha_desde}")
    elif fecha_hasta:
        subtitle_parts.append(f"Hasta: {fecha_hasta}")
    subtitle_parts.append(f"Items distintos: {len(datos)}")
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"

    pdf_bytes = crear_pdf_reporte("Reporte de Venta de Items", subtitle, columnas, datos, totales)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_venta_items_{today_paraguay().isoformat()}.pdf"}
    )

@api_router.get("/reportes/venta-items/excel")
async def reporte_venta_items_excel(
    empresa_id: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    categoria_id: int = None,
    producto_id: int = None,
    cliente_id: int = None,
    current_user: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Genera reporte Excel de ventas de items agrupadas por producto/materia de laboratorio"""
    from collections import defaultdict
    query = (
        select(VentaItem, Venta, Producto, Categoria, MateriaLaboratorio)
        .join(Venta, VentaItem.venta_id == Venta.id)
        .outerjoin(Producto, VentaItem.producto_id == Producto.id)
        .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
        .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA
        )
    )
    if fecha_desde:
        try:
            query = query.where(Venta.creado_en >= datetime.fromisoformat(fecha_desde).replace(tzinfo=PARAGUAY_TZ))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
    if fecha_hasta:
        try:
            query = query.where(Venta.creado_en < (datetime.fromisoformat(fecha_hasta) + timedelta(days=1)).replace(tzinfo=PARAGUAY_TZ))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
    if categoria_id:
        query = query.where(Producto.categoria_id == categoria_id)
    if producto_id:
        query = query.where(VentaItem.producto_id == producto_id)
    if cliente_id:
        query = query.where(Venta.cliente_id == cliente_id)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No se encontraron ventas de items para los filtros seleccionados")

    agg = defaultdict(lambda: {'cantidad': 0, 'total': Decimal('0'), 'categoria': '-'})
    for item, venta, producto, categoria, materia in rows:
        if producto:
            key = producto.nombre
            agg[key]['cantidad'] += item.cantidad
            agg[key]['total'] += item.total
            agg[key]['categoria'] = categoria.nombre if categoria else 'Sin categoría'
        elif materia:
            key = f"[LAB] {materia.nombre}"
            agg[key]['cantidad'] += item.cantidad
            agg[key]['total'] += item.total
            agg[key]['categoria'] = 'Laboratorio'

    sorted_items = sorted(agg.items(), key=lambda x: x[1]['total'], reverse=True)

    columnas = ['Producto / Item', 'Categoría', 'Cant. Vendida', 'Monto Total (Gs.)']
    datos = []
    total_cant = 0
    total_monto = Decimal('0')
    for nombre, data in sorted_items:
        total_cant += data['cantidad']
        total_monto += data['total']
        datos.append([
            nombre,
            data['categoria'],
            data['cantidad'],
            float(data['total'])
        ])

    totales = ['TOTAL', '', total_cant, float(total_monto)]

    subtitle_parts = []
    if fecha_desde and fecha_hasta:
        subtitle_parts.append(f"Período: {fecha_desde} al {fecha_hasta}")
    elif fecha_desde:
        subtitle_parts.append(f"Desde: {fecha_desde}")
    elif fecha_hasta:
        subtitle_parts.append(f"Hasta: {fecha_hasta}")
    subtitle_parts.append(f"Items distintos: {len(datos)}")
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else f"Fecha: {today_paraguay().strftime('%d/%m/%Y')}"

    excel_bytes = crear_excel_reporte("Reporte de Venta de Items", subtitle, columnas, datos, totales)
    return Response(
        content=excel_bytes,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename=reporte_venta_items_{today_paraguay().isoformat()}.xlsx"}
    )

# ==================== CICLOS DE SALARIO ====================
@api_router.post("/ciclos-salario/generar")
async def generar_ciclo_salario(empresa_id: int, mes: str, db: AsyncSession = Depends(get_db)):
    """Genera ciclos de salario para todos los funcionarios activos del mes especificado (formato: YYYY-MM)"""
    # Check if cycles already exist for this month
    existing = await db.execute(
        select(CicloSalario).where(CicloSalario.periodo == mes)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Ya existen ciclos de salario para {mes}")
    
    # Get all active funcionarios
    func_result = await db.execute(
        select(Funcionario).where(Funcionario.empresa_id == empresa_id, Funcionario.activo == True)
    )
    funcionarios = func_result.scalars().all()
    
    if not funcionarios:
        raise HTTPException(status_code=404, detail="No hay funcionarios activos")
    
    # Parse month
    año, mes_num = mes.split('-')
    fecha_inicio = date(int(año), int(mes_num), 1)
    if int(mes_num) == 12:
        fecha_fin = date(int(año) + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = date(int(año), int(mes_num) + 1, 1) - timedelta(days=1)
    
    ciclos_creados = []
    for funcionario in funcionarios:
        # Calculate adelantos for this funcionario in previous month
        # (Adelantos del mes anterior se descuentan del salario actual)
        mes_anterior = fecha_inicio - timedelta(days=1)
        periodo_anterior = mes_anterior.strftime('%Y-%m')
        
        adelantos_result = await db.execute(
            select(func_sql.coalesce(func_sql.sum(AdelantoSalario.monto), 0))
            .where(
                AdelantoSalario.funcionario_id == funcionario.id,
                func_sql.extract('year', AdelantoSalario.creado_en) == mes_anterior.year,
                func_sql.extract('month', AdelantoSalario.creado_en) == mes_anterior.month
            )
        )
        total_adelantos = adelantos_result.scalar() or Decimal('0')
        
        salario_neto = (funcionario.salario_base or Decimal('0')) - total_adelantos
        
        ciclo = CicloSalario(
            funcionario_id=funcionario.id,
            periodo=mes,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            salario_base=funcionario.salario_base or Decimal('0'),
            descuentos=total_adelantos,
            salario_neto=salario_neto,
            pagado=False
        )
        db.add(ciclo)
        ciclos_creados.append({
            "funcionario": f"{funcionario.nombre} {funcionario.apellido or ''}",
            "salario_base": float(funcionario.salario_base or 0),
            "adelantos": float(total_adelantos),
            "salario_neto": float(salario_neto)
        })
    
    await db.commit()
    
    return {
        "message": f"Ciclos de salario generados para {mes}",
        "ciclos_creados": len(ciclos_creados),
        "detalle": ciclos_creados
    }

@api_router.get("/ciclos-salario")
async def listar_ciclos_salario(empresa_id: int, periodo: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Lista los ciclos de salario"""
    query = (
        select(CicloSalario, Funcionario)
        .join(Funcionario, CicloSalario.funcionario_id == Funcionario.id)
        .where(Funcionario.empresa_id == empresa_id)
        .order_by(CicloSalario.periodo.desc(), Funcionario.nombre)
    )
    
    if periodo:
        query = query.where(CicloSalario.periodo == periodo)
    
    result = await db.execute(query)
    ciclos = result.all()
    
    return [
        {
            "id": ciclo.id,
            "funcionario_id": ciclo.funcionario_id,
            "funcionario_nombre": f"{func.nombre} {func.apellido or ''}".strip(),
            "periodo": ciclo.periodo,
            "fecha_inicio": ciclo.fecha_inicio.isoformat() if ciclo.fecha_inicio else None,
            "fecha_fin": ciclo.fecha_fin.isoformat() if ciclo.fecha_fin else None,
            "salario_base": float(ciclo.salario_base),
            "descuentos": float(ciclo.descuentos),
            "salario_neto": float(ciclo.salario_neto),
            "pagado": ciclo.pagado,
            "fecha_pago": ciclo.fecha_pago.isoformat() if ciclo.fecha_pago else None
        }
        for ciclo, func in ciclos
    ]

@api_router.post("/ciclos-salario/{ciclo_id}/pagar")
async def pagar_ciclo_salario(ciclo_id: int, db: AsyncSession = Depends(get_db)):
    """Marca un ciclo de salario como pagado"""
    result = await db.execute(select(CicloSalario).where(CicloSalario.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo no encontrado")
    
    if ciclo.pagado:
        raise HTTPException(status_code=400, detail="Este ciclo ya fue pagado")
    
    ciclo.pagado = True
    ciclo.fecha_pago = now_paraguay()
    
    await db.commit()
    return {"message": "Salario marcado como pagado", "ciclo_id": ciclo_id}

@api_router.get("/ciclos-salario/alertas")
async def alertas_salarios_pendientes(empresa_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene alertas de salarios pendientes de pago"""
    # Get current period
    hoy = today_paraguay()
    periodo_actual = hoy.strftime('%Y-%m')
    
    # Get unpaid cycles
    result = await db.execute(
        select(CicloSalario, Funcionario)
        .join(Funcionario, CicloSalario.funcionario_id == Funcionario.id)
        .where(
            Funcionario.empresa_id == empresa_id,
            CicloSalario.pagado == False
        )
        .order_by(CicloSalario.periodo)
    )
    ciclos_pendientes = result.all()
    
    alertas = []
    for ciclo, func in ciclos_pendientes:
        alertas.append({
            "tipo": "salario_pendiente",
            "mensaje": f"Salario pendiente: {func.nombre} {func.apellido or ''} - {ciclo.periodo}",
            "monto": float(ciclo.salario_neto),
            "funcionario_id": func.id,
            "ciclo_id": ciclo.id,
            "periodo": ciclo.periodo,
            "urgente": ciclo.periodo < periodo_actual
        })
    
    return alertas

# ==================== GASTOS OPERATIVOS ====================

@api_router.get("/gastos")
async def list_gastos(
    empresa_id: int,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_usuario),
):
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    q = select(Gasto).where(Gasto.empresa_id == empresa_id)
    if fecha_desde:
        q = q.where(Gasto.fecha >= datetime.fromisoformat(fecha_desde).date())
    if fecha_hasta:
        q = q.where(Gasto.fecha <= datetime.fromisoformat(fecha_hasta).date())
    q = q.order_by(Gasto.fecha.desc(), Gasto.id.desc())
    result = await db.execute(q)
    return result.scalars().all()


@api_router.post("/gastos", response_model=GastoResponse, status_code=201)
async def create_gasto(
    gasto: GastoCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_usuario),
):
    db_gasto = Gasto(**gasto.model_dump())
    db.add(db_gasto)
    await db.commit()
    await db.refresh(db_gasto)
    return db_gasto


@api_router.put("/gastos/{gasto_id}", response_model=GastoResponse)
async def update_gasto(
    gasto_id: int,
    gasto: GastoUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_usuario),
):
    result = await db.execute(select(Gasto).where(Gasto.id == gasto_id))
    db_gasto = result.scalar_one_or_none()
    if not db_gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    for field, value in gasto.model_dump().items():
        setattr(db_gasto, field, value)
    await db.commit()
    await db.refresh(db_gasto)
    return db_gasto


@api_router.delete("/gastos/{gasto_id}", status_code=204)
async def delete_gasto(
    gasto_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_usuario),
):
    result = await db.execute(select(Gasto).where(Gasto.id == gasto_id))
    db_gasto = result.scalar_one_or_none()
    if not db_gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    await db.delete(db_gasto)
    await db.commit()


# ==================== BUSINESS INTELLIGENCE ====================

@api_router.get("/bi/estadisticas-productos")
async def bi_estadisticas_productos(
    empresa_id: int,
    periodo: str = "semanal",  # semanal | mensual
    periodos: int = 8,
    db: AsyncSession = Depends(get_db)
):
    """Estadísticas de ventas por producto con promedio y comparativa de período."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    now = datetime.now(PARAGUAY_TZ)
    if periodo == "semanal":
        delta = timedelta(weeks=periodos)
    else:
        delta = timedelta(days=periodos * 30)
    fecha_inicio = now - delta

    # Overall stats per product
    stats_q = (
        select(
            VentaItem.producto_id,
            Producto.nombre.label("producto_nombre"),
            func_sql.sum(VentaItem.cantidad).label("total_unidades"),
            func_sql.sum(VentaItem.total).label("total_ventas"),
            func_sql.sum(VentaItem.precio_costo * VentaItem.cantidad).label("total_costo"),
            func_sql.count(func_sql.distinct(Venta.id)).label("num_ventas"),
        )
        .join(Venta, VentaItem.venta_id == Venta.id)
        .join(Producto, VentaItem.producto_id == Producto.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.creado_en >= fecha_inicio,
            VentaItem.producto_id.isnot(None),
        )
        .group_by(VentaItem.producto_id, Producto.nombre)
        .order_by(func_sql.sum(VentaItem.total).desc())
        .limit(200)
    )

    # Current period (latest period)
    if periodo == "semanal":
        current_inicio = now - timedelta(weeks=1)
        prev_inicio = now - timedelta(weeks=2)
        prev_fin = current_inicio
    else:
        import calendar as cal_mod
        first_this = datetime(now.year, now.month, 1, tzinfo=PARAGUAY_TZ)
        m = now.month - 1 if now.month > 1 else 12
        y = now.year if now.month > 1 else now.year - 1
        first_prev = datetime(y, m, 1, tzinfo=PARAGUAY_TZ)
        current_inicio = first_this
        prev_inicio = first_prev
        prev_fin = first_this

    cur_q = (
        select(VentaItem.producto_id,
               func_sql.sum(VentaItem.cantidad).label("unidades"),
               func_sql.sum(VentaItem.total).label("ventas"))
        .join(Venta, VentaItem.venta_id == Venta.id)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= current_inicio, VentaItem.producto_id.isnot(None))
        .group_by(VentaItem.producto_id)
    )
    prev_q = (
        select(VentaItem.producto_id,
               func_sql.sum(VentaItem.cantidad).label("unidades"),
               func_sql.sum(VentaItem.total).label("ventas"))
        .join(Venta, VentaItem.venta_id == Venta.id)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= prev_inicio, Venta.creado_en < prev_fin,
               VentaItem.producto_id.isnot(None))
        .group_by(VentaItem.producto_id)
    )
    stock_q = (
        select(StockActual.producto_id, func_sql.sum(StockActual.cantidad).label("stock_total"))
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .where(Almacen.empresa_id == empresa_id)
        .group_by(StockActual.producto_id)
    )

    stats_r, cur_r, prev_r, stock_r = await db.execute(stats_q), await db.execute(cur_q), await db.execute(prev_q), await db.execute(stock_q)
    cur_map = {r.producto_id: r for r in cur_r.all()}
    prev_map = {r.producto_id: r for r in prev_r.all()}
    stock_map = {r.producto_id: int(r.stock_total) for r in stock_r.all()}

    productos = []
    for row in stats_r.all():
        pid = row.producto_id
        cu = cur_map.get(pid)
        pv = prev_map.get(pid)
        cu_uni = int(cu.unidades) if cu else 0
        pv_uni = int(pv.unidades) if pv else 0
        if pv_uni > 0:
            variacion = round(((cu_uni - pv_uni) / pv_uni) * 100, 1)
        elif cu_uni > 0:
            variacion = 100.0
        else:
            variacion = 0.0
        total_u = int(row.total_unidades)
        total_v = float(row.total_ventas or 0)
        total_c = float(row.total_costo or 0)
        productos.append({
            "producto_id": pid,
            "producto_nombre": row.producto_nombre,
            "total_unidades": total_u,
            "total_ventas": total_v,
            "total_costo": total_c,
            "ganancia_bruta": round(total_v - total_c, 2),
            "num_ventas": int(row.num_ventas),
            "promedio_por_periodo": round(total_u / periodos, 1),
            "periodo_actual_unidades": cu_uni,
            "periodo_anterior_unidades": pv_uni,
            "variacion_pct": variacion,
            "stock_actual": stock_map.get(pid, 0),
        })

    # Build trend bars (one per period)
    tendencia = []
    for i in range(periodos - 1, -1, -1):
        if periodo == "semanal":
            t_ini = now - timedelta(weeks=i + 1)
            t_fin = now - timedelta(weeks=i)
            label = f"Sem -{i}" if i > 0 else "Esta sem."
        else:
            import calendar as cal_mod
            m_off = now.month - i - 1
            yr = now.year + (m_off // 12 if m_off >= 0 else (m_off - 11) // 12)
            mo = m_off % 12
            if mo <= 0:
                mo += 12
                yr -= 1
            days_m = cal_mod.monthrange(yr, mo)[1]
            t_ini = datetime(yr, mo, 1, tzinfo=PARAGUAY_TZ)
            t_fin = datetime(yr, mo, days_m, 23, 59, 59, tzinfo=PARAGUAY_TZ)
            label = f"{yr}-{mo:02d}" if i > 0 else f"{now.year}-{now.month:02d}"
        t_q = (
            select(func_sql.sum(VentaItem.total).label("ventas"),
                   func_sql.sum(VentaItem.cantidad).label("unidades"))
            .join(Venta, VentaItem.venta_id == Venta.id)
            .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
                   Venta.creado_en >= t_ini, Venta.creado_en < t_fin,
                   VentaItem.producto_id.isnot(None))
        )
        t_r = await db.execute(t_q)
        t_row = t_r.one()
        tendencia.append({"label": label, "ventas": float(t_row.ventas or 0), "unidades": int(t_row.unidades or 0)})

    return {"periodo": periodo, "periodos": periodos, "productos": productos, "tendencia": tendencia}


@api_router.get("/bi/cierre")
async def bi_cierre(
    empresa_id: int,
    fecha_desde: str,
    fecha_hasta: str,
    db: AsyncSession = Depends(get_db)
):
    """Balance de cierre: ventas/ganancias vs compras de mercadería vs salarios."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    try:
        f_ini = datetime.fromisoformat(fecha_desde).replace(tzinfo=PARAGUAY_TZ)
        f_fin = datetime.fromisoformat(fecha_hasta).replace(hour=23, minute=59, second=59, tzinfo=PARAGUAY_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido (YYYY-MM-DD)")

    # Ventas confirmadas
    venta_q = (
        select(func_sql.sum(Venta.total).label("total_ventas"),
               func_sql.sum(Venta.ganancia).label("total_ganancia"),
               func_sql.sum(Venta.costo_total).label("total_costo_ventas"),
               func_sql.sum(Venta.iva).label("total_iva"),
               func_sql.count(Venta.id).label("cantidad_ventas"))
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= f_ini, Venta.creado_en <= f_fin)
    )

    # Compras de mercadería (entradas de stock con costo)
    compras_q = (
        select(func_sql.sum(MovimientoStock.costo_unitario * MovimientoStock.cantidad).label("total_compras"),
               func_sql.count(MovimientoStock.id).label("num_entradas"))
        .join(Almacen, MovimientoStock.almacen_id == Almacen.id)
        .where(Almacen.empresa_id == empresa_id,
               MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
               MovimientoStock.costo_unitario.isnot(None),
               MovimientoStock.creado_en >= f_ini, MovimientoStock.creado_en <= f_fin)
    )

    # Salarios pagados (ciclos)
    salarios_q = (
        select(func_sql.sum(CicloSalario.salario_neto).label("total_salarios"),
               func_sql.count(CicloSalario.id).label("num_ciclos"))
        .join(Funcionario, CicloSalario.funcionario_id == Funcionario.id)
        .where(Funcionario.empresa_id == empresa_id, CicloSalario.pagado == True,
               CicloSalario.fecha_pago >= f_ini, CicloSalario.fecha_pago <= f_fin)
    )

    # Deudas proveedores pendientes (registradas en el período)
    deudas_q = (
        select(func_sql.sum(DeudaProveedor.monto).label("total_deudas"),
               func_sql.count(DeudaProveedor.id).label("num_deudas"))
        .join(Proveedor, DeudaProveedor.proveedor_id == Proveedor.id)
        .where(Proveedor.empresa_id == empresa_id, DeudaProveedor.pagado == False)
    )

    # Monthly breakdown of sales — Python-side grouping for cross-DB compatibility
    ventas_mes_q = (
        select(Venta.creado_en, Venta.total, Venta.ganancia, Venta.costo_total)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= f_ini, Venta.creado_en <= f_fin)
    )

    # Gastos operativos en el período
    gastos_q = (
        select(func_sql.sum(Gasto.monto).label("total_gastos"),
               func_sql.count(Gasto.id).label("num_gastos"))
        .where(Gasto.empresa_id == empresa_id,
               Gasto.fecha >= f_ini.date(), Gasto.fecha <= f_fin.date())
    )

    # Valor excedente de stock (FIFO): suma de tandas con unidades restantes × costo de compra
    # No filtrado por fecha — representa el estado actual del inventario como snapshot
    stock_valor_q = (
        select(
            func_sql.sum(
                MovimientoStock.cantidad_restante * MovimientoStock.costo_unitario
            ).label("valor_total"),
            func_sql.count(MovimientoStock.id).label("num_tandas"),
            func_sql.count(func_sql.distinct(MovimientoStock.producto_id)).label("num_productos"),
        )
        .join(Almacen, MovimientoStock.almacen_id == Almacen.id)
        .where(
            Almacen.empresa_id == empresa_id,
            MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
            MovimientoStock.cantidad_restante > 0,
            MovimientoStock.costo_unitario.isnot(None),
        )
    )

    vr = await db.execute(venta_q)
    cr = await db.execute(compras_q)
    sr = await db.execute(salarios_q)
    dr = await db.execute(deudas_q)
    vmr = await db.execute(ventas_mes_q)
    gr = await db.execute(gastos_q)
    svr = await db.execute(stock_valor_q)

    vrow = vr.one()
    crow = cr.one()
    srow = sr.one()
    drow = dr.one()
    grow = gr.one()
    svrow = svr.one()

    total_ventas = float(vrow.total_ventas or 0)
    total_ganancia = float(vrow.total_ganancia or 0)
    total_costo_ventas = float(vrow.total_costo_ventas or 0)
    total_iva = float(vrow.total_iva or 0)
    total_compras = float(crow.total_compras or 0)
    total_salarios = float(srow.total_salarios or 0)
    total_deudas_pendientes = float(drow.total_deudas or 0)
    total_gastos_op = float(grow.total_gastos or 0)
    valor_stock = float(svrow.valor_total or 0)
    num_tandas = int(svrow.num_tandas or 0)
    num_productos_stock = int(svrow.num_productos or 0)

    total_egresos = total_compras + total_salarios + total_gastos_op
    balance_neto = total_ventas - total_egresos

    # Group ventas by month in Python
    from collections import defaultdict
    mes_map = defaultdict(lambda: {"ventas": 0.0, "ganancia": 0.0, "costo": 0.0})
    for row in vmr.all():
        key = row.creado_en.strftime('%Y-%m') if row.creado_en else None
        if key:
            mes_map[key]["ventas"] += float(row.total or 0)
            mes_map[key]["ganancia"] += float(row.ganancia or 0)
            mes_map[key]["costo"] += float(row.costo_total or 0)
    meses = [{"mes": k, "ventas": v["ventas"], "ganancia": v["ganancia"], "costo": v["costo"]}
             for k, v in sorted(mes_map.items())]

    return {
        "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
        "ventas": {
            "total": total_ventas,
            "ganancia": total_ganancia,
            "costo": total_costo_ventas,
            "iva": total_iva,
            "cantidad": int(vrow.cantidad_ventas or 0),
        },
        "compras_mercaderia": {
            "total": total_compras,
            "num_entradas": int(crow.num_entradas or 0),
        },
        "salarios": {
            "total_pagado": total_salarios,
            "num_ciclos": int(srow.num_ciclos or 0),
        },
        "gastos_operativos": {
            "total": total_gastos_op,
            "cantidad": int(grow.num_gastos or 0),
        },
        "deudas_pendientes": {
            "total": total_deudas_pendientes,
            "cantidad": int(drow.num_deudas or 0),
        },
        "valor_stock_actual": {
            "total": valor_stock,
            "num_tandas": num_tandas,
            "num_productos": num_productos_stock,
        },
        "resumen": {
            "total_ingresos": total_ventas,
            "total_egresos": total_egresos,
            "balance_neto": balance_neto,
            "margen_bruto_pct": round((total_ganancia / total_ventas * 100) if total_ventas > 0 else 0, 1),
        },
        "evolucion_mensual": meses,
    }


@api_router.get("/bi/sugerencias-compra")
async def bi_sugerencias_compra(
    empresa_id: int,
    semanas_analisis: int = 4,
    semanas_cobertura: int = 4,
    db: AsyncSession = Depends(get_db)
):
    """Sugerencias de compra basadas en velocidad de venta histórica."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    now = datetime.now(PARAGUAY_TZ)
    fecha_inicio = now - timedelta(weeks=semanas_analisis)

    # Sales velocity per product
    vel_q = (
        select(VentaItem.producto_id, Producto.nombre.label("producto_nombre"),
               func_sql.sum(VentaItem.cantidad).label("total_unidades"),
               func_sql.count(func_sql.distinct(Venta.id)).label("num_ventas"))
        .join(Venta, VentaItem.venta_id == Venta.id)
        .join(Producto, VentaItem.producto_id == Producto.id)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= fecha_inicio, VentaItem.producto_id.isnot(None))
        .group_by(VentaItem.producto_id, Producto.nombre)
        .order_by(func_sql.sum(VentaItem.cantidad).desc())
    )

    # Current stock
    stock_q = (
        select(StockActual.producto_id, func_sql.sum(StockActual.cantidad).label("stock_total"),
               Producto.nombre.label("producto_nombre"), Producto.precio_costo.label("precio_costo"))
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .join(Producto, StockActual.producto_id == Producto.id)
        .where(Almacen.empresa_id == empresa_id)
        .group_by(StockActual.producto_id, Producto.nombre, Producto.precio_costo)
    )

    vel_r = await db.execute(vel_q)
    stock_r = await db.execute(stock_q)

    stock_map = {r.producto_id: {"stock": int(r.stock_total), "nombre": r.producto_nombre,
                                  "precio_costo": float(r.precio_costo or 0)}
                 for r in stock_r.all()}

    sugerencias = []
    for row in vel_r.all():
        pid = row.producto_id
        total_u = int(row.total_unidades)
        vel_semanal = round(total_u / semanas_analisis, 1)
        stock_recomendado = round(vel_semanal * semanas_cobertura)
        stock_actual = stock_map.get(pid, {}).get("stock", 0)
        compra_sugerida = max(0, stock_recomendado - stock_actual)
        precio_costo = stock_map.get(pid, {}).get("precio_costo", 0)
        if compra_sugerida > 0:
            sugerencias.append({
                "producto_id": pid,
                "producto_nombre": row.producto_nombre,
                "velocidad_semanal": vel_semanal,
                "stock_actual": stock_actual,
                "stock_recomendado": stock_recomendado,
                "compra_sugerida": int(compra_sugerida),
                "costo_estimado": round(compra_sugerida * precio_costo, 2),
                "cobertura_actual_semanas": round(stock_actual / vel_semanal, 1) if vel_semanal > 0 else None,
                "urgencia": "ALTA" if stock_actual <= 0 else ("MEDIA" if stock_actual < vel_semanal else "BAJA"),
            })

    sugerencias.sort(key=lambda x: (x["urgencia"] != "ALTA", x["urgencia"] != "MEDIA", -x["velocidad_semanal"]))
    costo_total = sum(s["costo_estimado"] for s in sugerencias)

    return {
        "parametros": {"semanas_analisis": semanas_analisis, "semanas_cobertura": semanas_cobertura},
        "sugerencias": sugerencias,
        "resumen": {
            "productos_con_necesidad": len(sugerencias),
            "costo_total_estimado": round(costo_total, 2),
            "urgentes": sum(1 for s in sugerencias if s["urgencia"] == "ALTA"),
            "media_urgencia": sum(1 for s in sugerencias if s["urgencia"] == "MEDIA"),
        }
    }


@api_router.get("/bi/exceso-compras")
async def bi_exceso_compras(
    empresa_id: int,
    semanas_referencia: int = 4,
    limite: int = Query(100, ge=1, le=10000),
    db: AsyncSession = Depends(get_db)
):
    """Detección de compras en exceso: productos con stock alto respecto a su velocidad de venta.
    Cada lista trae los `limite` de mayor valor inmovilizado; el resumen cubre todos
    (con miles de productos sin ventas, devolverlos todos pesaba decenas de MB)."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    now = datetime.now(PARAGUAY_TZ)
    fecha_inicio = now - timedelta(weeks=semanas_referencia)

    # Sales velocity últimas N semanas
    vel_q = (
        select(VentaItem.producto_id,
               func_sql.sum(VentaItem.cantidad).label("total_unidades"))
        .join(Venta, VentaItem.venta_id == Venta.id)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= fecha_inicio, VentaItem.producto_id.isnot(None))
        .group_by(VentaItem.producto_id)
    )

    # Entradas de stock recientes
    entradas_q = (
        select(MovimientoStock.producto_id,
               func_sql.sum(MovimientoStock.cantidad).label("total_comprado"),
               func_sql.sum(MovimientoStock.costo_unitario * MovimientoStock.cantidad).label("total_costo"))
        .join(Almacen, MovimientoStock.almacen_id == Almacen.id)
        .where(Almacen.empresa_id == empresa_id,
               MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
               MovimientoStock.creado_en >= fecha_inicio)
        .group_by(MovimientoStock.producto_id)
    )

    # Stock actual + product info
    stock_q = (
        select(StockActual.producto_id, func_sql.sum(StockActual.cantidad).label("stock_total"),
               Producto.nombre.label("nombre"), Producto.precio_venta.label("precio_venta"),
               Producto.precio_costo.label("precio_costo"))
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .join(Producto, StockActual.producto_id == Producto.id)
        .where(Almacen.empresa_id == empresa_id)
        .group_by(StockActual.producto_id, Producto.nombre, Producto.precio_venta, Producto.precio_costo)
    )

    vel_r = await db.execute(vel_q)
    ent_r = await db.execute(entradas_q)
    stk_r = await db.execute(stock_q)

    vel_map = {r.producto_id: int(r.total_unidades) for r in vel_r.all()}
    ent_map = {r.producto_id: {"comprado": int(r.total_comprado),
                                "costo": float(r.total_costo or 0)} for r in ent_r.all()}

    excesos = []
    sin_movimiento = []

    for row in stk_r.all():
        pid = row.producto_id
        stock = int(row.stock_total)
        vendido = vel_map.get(pid, 0)
        vel_semanal = round(vendido / semanas_referencia, 1)
        entrada = ent_map.get(pid, {})
        comprado = entrada.get("comprado", 0)
        costo_sobrante = float(row.precio_costo or 0)

        if stock <= 0:
            continue

        # Sin ventas recientes pero con stock
        if vendido == 0 and stock > 0:
            sin_movimiento.append({
                "producto_id": pid,
                "producto_nombre": row.nombre,
                "stock_actual": stock,
                "vendido_periodo": 0,
                "velocidad_semanal": 0,
                "dias_para_agotar": None,
                "valor_inmovilizado": round(stock * costo_sobrante, 2),
                "tipo": "SIN_VENTAS",
            })
        # Stock alto comparado con velocidad de venta
        elif vel_semanal > 0:
            semanas_para_agotar = stock / vel_semanal
            if semanas_para_agotar > semanas_referencia * 2:
                excesos.append({
                    "producto_id": pid,
                    "producto_nombre": row.nombre,
                    "stock_actual": stock,
                    "vendido_periodo": vendido,
                    "velocidad_semanal": vel_semanal,
                    "semanas_para_agotar": round(semanas_para_agotar, 1),
                    "comprado_periodo": comprado,
                    "exceso_vs_venta": max(0, comprado - vendido),
                    "valor_inmovilizado": round(stock * costo_sobrante, 2),
                    "tipo": "EXCESO_STOCK",
                })

    excesos.sort(key=lambda x: -x["valor_inmovilizado"])
    sin_movimiento.sort(key=lambda x: -x["valor_inmovilizado"])

    return {
        "parametros": {"semanas_referencia": semanas_referencia},
        "exceso_stock": excesos[:limite],
        "sin_ventas_recientes": sin_movimiento[:limite],
        "resumen": {
            "productos_exceso": len(excesos),
            "productos_sin_ventas": len(sin_movimiento),
            "valor_total_inmovilizado": round(
                sum(e["valor_inmovilizado"] for e in excesos) +
                sum(s["valor_inmovilizado"] for s in sin_movimiento), 2
            ),
        }
    }


@api_router.get("/bi/producto-evolucion")
async def bi_producto_evolucion(
    empresa_id: int,
    producto_id: int,
    periodo: str = "semanal",
    periodos: int = 12,
    db: AsyncSession = Depends(get_db)
):
    """Retorna la evolución por período (semana/mes) de un producto específico."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    now = datetime.now(PARAGUAY_TZ)

    prod_q = select(Producto.nombre).where(Producto.id == producto_id)
    prod_r = await db.execute(prod_q)
    prod_nombre = prod_r.scalar_one_or_none()
    if not prod_nombre:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    tendencia = []
    for i in range(periodos - 1, -1, -1):
        if periodo == "semanal":
            t_ini = now - timedelta(weeks=i + 1)
            t_fin = now - timedelta(weeks=i)
            label = f"Sem -{i}" if i > 0 else "Esta sem."
        else:
            import calendar as cal_mod
            m_off = now.month - i - 1
            yr = now.year + (m_off // 12 if m_off >= 0 else (m_off - 11) // 12)
            mo = m_off % 12
            if mo <= 0:
                mo += 12
                yr -= 1
            days_m = cal_mod.monthrange(yr, mo)[1]
            t_ini = datetime(yr, mo, 1, tzinfo=PARAGUAY_TZ)
            t_fin = datetime(yr, mo, days_m, 23, 59, 59, tzinfo=PARAGUAY_TZ)
            label = f"{yr}-{mo:02d}" if i > 0 else f"{now.year}-{now.month:02d}"
        t_q = (
            select(
                func_sql.sum(VentaItem.total).label("ventas"),
                func_sql.sum(VentaItem.cantidad).label("unidades"),
                func_sql.sum(
                    VentaItem.total - (VentaItem.precio_costo * VentaItem.cantidad)
                ).label("ganancia"),
            )
            .join(Venta, VentaItem.venta_id == Venta.id)
            .where(
                Venta.empresa_id == empresa_id,
                Venta.estado == EstadoVenta.CONFIRMADA,
                VentaItem.producto_id == producto_id,
                Venta.creado_en >= t_ini,
                Venta.creado_en < t_fin,
            )
        )
        t_r = await db.execute(t_q)
        t_row = t_r.one()
        tendencia.append({
            "label": label,
            "ventas": float(t_row.ventas or 0),
            "unidades": int(t_row.unidades or 0),
            "ganancia": float(t_row.ganancia or 0),
        })

    return {
        "producto_id": producto_id,
        "producto_nombre": prod_nombre,
        "periodo": periodo,
        "periodos": periodos,
        "tendencia": tendencia,
    }


@api_router.get("/bi/estadisticas-productos/excel")
async def bi_estadisticas_productos_excel(
    empresa_id: int,
    periodo: str = "semanal",
    periodos: int = 8,
    metrica: str = "ventas",  # ventas | unidades | ganancia
    db: AsyncSession = Depends(get_db)
):
    """Exporta ranking completo de productos B.I. a Excel con gráfico embebido."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    now = datetime.now(PARAGUAY_TZ)
    if periodo == "semanal":
        delta = timedelta(weeks=periodos)
    else:
        delta = timedelta(days=periodos * 30)
    fecha_inicio = now - delta

    if periodo == "semanal":
        current_inicio = now - timedelta(weeks=1)
        prev_inicio = now - timedelta(weeks=2)
        prev_fin = current_inicio
    else:
        import calendar as cal_mod
        first_this = datetime(now.year, now.month, 1, tzinfo=PARAGUAY_TZ)
        m = now.month - 1 if now.month > 1 else 12
        y = now.year if now.month > 1 else now.year - 1
        first_prev = datetime(y, m, 1, tzinfo=PARAGUAY_TZ)
        current_inicio = first_this
        prev_inicio = first_prev
        prev_fin = first_this

    stats_q = (
        select(
            VentaItem.producto_id,
            Producto.nombre.label("producto_nombre"),
            func_sql.sum(VentaItem.cantidad).label("total_unidades"),
            func_sql.sum(VentaItem.total).label("total_ventas"),
            func_sql.sum(VentaItem.precio_costo * VentaItem.cantidad).label("total_costo"),
            func_sql.count(func_sql.distinct(Venta.id)).label("num_ventas"),
        )
        .join(Venta, VentaItem.venta_id == Venta.id)
        .join(Producto, VentaItem.producto_id == Producto.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.estado == EstadoVenta.CONFIRMADA,
            Venta.creado_en >= fecha_inicio,
            VentaItem.producto_id.isnot(None),
        )
        .group_by(VentaItem.producto_id, Producto.nombre)
        .order_by(func_sql.sum(VentaItem.total).desc())
    )
    cur_q = (
        select(VentaItem.producto_id,
               func_sql.sum(VentaItem.cantidad).label("unidades"),
               func_sql.sum(VentaItem.total).label("ventas"))
        .join(Venta, VentaItem.venta_id == Venta.id)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= current_inicio, VentaItem.producto_id.isnot(None))
        .group_by(VentaItem.producto_id)
    )
    prev_q = (
        select(VentaItem.producto_id,
               func_sql.sum(VentaItem.cantidad).label("unidades"),
               func_sql.sum(VentaItem.total).label("ventas"))
        .join(Venta, VentaItem.venta_id == Venta.id)
        .where(Venta.empresa_id == empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
               Venta.creado_en >= prev_inicio, Venta.creado_en < prev_fin,
               VentaItem.producto_id.isnot(None))
        .group_by(VentaItem.producto_id)
    )
    stock_q = (
        select(StockActual.producto_id, func_sql.sum(StockActual.cantidad).label("stock_total"))
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .where(Almacen.empresa_id == empresa_id)
        .group_by(StockActual.producto_id)
    )

    stats_r = await db.execute(stats_q)
    cur_r = await db.execute(cur_q)
    prev_r = await db.execute(prev_q)
    stock_r = await db.execute(stock_q)
    cur_map = {r.producto_id: r for r in cur_r.all()}
    prev_map = {r.producto_id: r for r in prev_r.all()}
    stock_map = {r.producto_id: int(r.stock_total) for r in stock_r.all()}

    productos = []
    for row in stats_r.all():
        pid = row.producto_id
        cu = cur_map.get(pid)
        pv = prev_map.get(pid)
        cu_uni = int(cu.unidades) if cu else 0
        pv_uni = int(pv.unidades) if pv else 0
        if pv_uni > 0:
            variacion = round(((cu_uni - pv_uni) / pv_uni) * 100, 1)
        elif cu_uni > 0:
            variacion = 100.0
        else:
            variacion = 0.0
        total_u = int(row.total_unidades)
        total_v = float(row.total_ventas or 0)
        total_c = float(row.total_costo or 0)
        ganancia = round(total_v - total_c, 0)
        prom = round(total_u / periodos, 1)
        stock = stock_map.get(pid, 0)
        productos.append({
            "nombre": row.producto_nombre,
            "ventas": total_v,
            "ganancia": ganancia,
            "unidades": total_u,
            "prom": prom,
            "stock": stock,
            "variacion": variacion,
        })

    # Sort by chosen metric
    sort_key = {"ventas": "ventas", "ganancia": "ganancia", "unidades": "unidades"}.get(metrica, "ventas")
    productos.sort(key=lambda x: -x[sort_key])

    metrica_label = {"ventas": "Ventas (₲)", "ganancia": "Ganancia (₲)", "unidades": "Unidades"}[metrica]
    periodo_label = "semana" if periodo == "semanal" else "mes"
    titulo = f"B.I. — Ranking de Productos por {metrica_label}"
    subtitulo = f"Período: últimos {periodos} {periodo_label}s | Ordenado por: {metrica_label}"

    # Build workbook manually (with chart)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ranking Productos"

    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Title
    ws.merge_cells("A1:H1")
    t = ws["A1"]
    t.value = titulo
    t.font = Font(name="Calibri", size=14, bold=True, color="0044CC")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Subtitle
    ws.merge_cells("A2:H2")
    s = ws["A2"]
    s.value = subtitulo
    s.font = Font(name="Calibri", size=9, color="808080")
    s.alignment = Alignment(horizontal="center")

    # Headers row 4
    headers = ["#", "Producto", "Ventas (₲)", "Ganancia (₲)", "Unidades",
               f"Prom. uds/{periodo_label}", "Stock actual", "Variación %"]
    hfill = PatternFill(start_color="0044CC", end_color="0044CC", fill_type="solid")
    hfont = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=ci, value=h)
        cell.fill = hfill
        cell.font = hfont
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    ws.row_dimensions[4].height = 20

    # Data rows
    for ri, p in enumerate(productos, 1):
        rn = 4 + ri
        bg = "FFFFFF" if ri % 2 == 1 else "F5F7FF"
        fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        row_vals = [ri, p["nombre"], p["ventas"], p["ganancia"], p["unidades"],
                    p["prom"], p["stock"], p["variacion"]]
        for ci, val in enumerate(row_vals, 1):
            cell = ws.cell(row=rn, column=ci, value=val)
            cell.fill = fill
            cell.font = Font(name="Calibri", size=9)
            cell.border = border
            cell.alignment = Alignment(horizontal="right" if ci > 1 else "center", vertical="center")
        
    # Column widths
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 35
    for col in ["C", "D", "E", "F", "G", "H"]:
        ws.column_dimensions[col].width = 16

    # Totals row
    tot_rn = 4 + len(productos) + 1
    tot_fill = PatternFill(start_color="E8EDF5", end_color="E8EDF5", fill_type="solid")
    tot_font = Font(name="Calibri", size=9, bold=True)
    totals = [
        "", "TOTAL",
        sum(p["ventas"] for p in productos),
        sum(p["ganancia"] for p in productos),
        sum(p["unidades"] for p in productos),
        "", "", ""
    ]
    for ci, val in enumerate(totals, 1):
        cell = ws.cell(row=tot_rn, column=ci, value=val)
        cell.fill = tot_fill
        cell.font = tot_font
        cell.border = border
        cell.alignment = Alignment(horizontal="right", vertical="center")

    # Embedded BarChart (top 20)
    chart_data_count = min(20, len(productos))
    chart_col = {"ventas": 3, "ganancia": 4, "unidades": 5}[metrica]
    chart = BarChart()
    chart.type = "bar"  # horizontal
    chart.title = f"Top {chart_data_count} — {metrica_label}"
    chart.y_axis.title = "Producto"
    chart.x_axis.title = metrica_label
    chart.style = 10
    chart.width = 22
    chart.height = 14

    data_ref = Reference(ws, min_col=chart_col, min_row=4, max_row=4 + chart_data_count)
    cats_ref = Reference(ws, min_col=2, min_row=5, max_row=4 + chart_data_count)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.series[0].graphicalProperties.solidFill = "0044CC"

    # Place chart to the right of data (column J, row 4)
    ws.add_chart(chart, "J4")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    today_str = now.strftime("%Y%m%d")
    return Response(
        content=buffer.getvalue(),
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename=bi_productos_{metrica}_{today_str}.xlsx"}
    )


# ==================== BI AGING TANDAS ====================
@api_router.get("/bi/aging-tandas")
async def bi_aging_tandas(
    empresa_id: int,
    orden: str = "mas_antiguo",  # mas_antiguo | mas_nuevo | mayor_valor | nombre
    q: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Aging de tandas activas: cada lote ENTRADA con unidades restantes y sus días de permanencia.
    El resumen cubre todos los productos; la lista viene paginada (con miles de productos,
    devolver todas las tandas pesaba decenas de MB)."""
    PARAGUAY_TZ = ZoneInfo("America/Asuncion")
    hoy = datetime.now(PARAGUAY_TZ).date()

    consulta = (
        select(
            MovimientoStock.id.label("tanda_id"),
            MovimientoStock.producto_id,
            Producto.nombre.label("producto_nombre"),
            MovimientoStock.cantidad.label("cantidad_original"),
            MovimientoStock.cantidad_restante,
            MovimientoStock.costo_unitario,
            MovimientoStock.almacen_id,
            Almacen.nombre.label("almacen_nombre"),
            MovimientoStock.proveedor_id,
            Proveedor.nombre.label("proveedor_nombre"),
            MovimientoStock.creado_en,
            MovimientoStock.notas,
        )
        .join(Producto, MovimientoStock.producto_id == Producto.id)
        .join(Almacen, MovimientoStock.almacen_id == Almacen.id)
        .outerjoin(Proveedor, MovimientoStock.proveedor_id == Proveedor.id)
        .where(
            Almacen.empresa_id == empresa_id,
            Producto.empresa_id == empresa_id,
            Producto.activo == True,
            MovimientoStock.tipo == TipoMovimientoStock.ENTRADA,
            # Include batches with remaining units OR NULL (pre-FIFO batches treated as fully active)
            or_(
                MovimientoStock.cantidad_restante > 0,
                MovimientoStock.cantidad_restante == None,
            ),
            # Las devoluciones por anulación no son lotes: sus unidades vuelven a los lotes de origen
            or_(
                MovimientoStock.referencia_tipo == None,
                MovimientoStock.referencia_tipo != "ANULACION_VENTA",
            ),
        )
        .order_by(MovimientoStock.producto_id, MovimientoStock.creado_en.asc())
    )

    result = await db.execute(consulta)
    rows = result.all()

    # Real stock per product (from StockActual) to detect FIFO vs actual discrepancies
    stock_real_q = (
        select(StockActual.producto_id, func_sql.sum(StockActual.cantidad).label("stock_real"))
        .join(Almacen, StockActual.almacen_id == Almacen.id)
        .where(Almacen.empresa_id == empresa_id)
        .group_by(StockActual.producto_id)
    )
    stock_real_r = await db.execute(stock_real_q)
    stock_real_map = {r.producto_id: int(r.stock_real or 0) for r in stock_real_r.all()}

    # Una pasada sobre las tandas: agregados por producto, y las filas guardadas para armar el
    # detalle sólo de los productos de la página (armar un dict por cada una de las ~100.000
    # tandas costaba más de 1 s y después se descartaban casi todas).
    resumenes: dict = {}
    for row in rows:
        if row.creado_en:
            entrada_date = row.creado_en.date() if hasattr(row.creado_en, "date") else row.creado_en
            dias = (hoy - entrada_date).days
        else:
            dias = 0
        original = int(row.cantidad_original or 0)
        # NULL cantidad_restante = pre-FIFO batch, treat as fully remaining
        restante = int(row.cantidad_restante) if row.cantidad_restante is not None else original
        valor = round(float(row.costo_unitario or 0) * restante, 0)
        r = resumenes.get(row.producto_id)
        if r is None:
            r = resumenes[row.producto_id] = {
                "nombre": row.producto_nombre, "filas": [], "max": dias, "min": dias, "valor": 0, "restante": 0,
            }
        r["filas"].append((row, dias, original, restante, valor))
        r["max"] = max(r["max"], dias)
        r["min"] = min(r["min"], dias)
        r["valor"] += valor
        r["restante"] += restante

    def _tanda(row, dias, original, restante, valor):
        return {
            "tanda_id": row.tanda_id,
            "fecha_entrada": row.creado_en.isoformat() if row.creado_en else None,
            "dias_aging": dias,
            "cantidad_original": original,
            "cantidad_restante": restante,
            "porcentaje_consumido": round((1 - restante / original) * 100, 1) if original > 0 else 0.0,
            "costo_unitario": float(row.costo_unitario or 0),
            "valor_inmovilizado": valor,
            "almacen": row.almacen_nombre,
            "proveedor": row.proveedor_nombre or "Sin proveedor",
            "notas": row.notas,
            "sin_fifo": row.cantidad_restante is None,
        }

    productos = []
    for pid, r in resumenes.items():
        stock_real = stock_real_map.get(pid, r["restante"])
        fifo_diferencia = r["restante"] - stock_real
        productos.append({
            "producto_id": pid,
            "producto_nombre": r["nombre"],
            "num_tandas": len(r["filas"]),
            "dias_aging_max": r["max"],
            "dias_aging_min": r["min"],
            "total_unidades_restantes": r["restante"],
            "stock_real": stock_real,
            "fifo_concuerda": abs(fifo_diferencia) <= 1,
            "fifo_diferencia": fifo_diferencia,
            "valor_total_inmovilizado": r["valor"],
        })

    sort_map = {
        "mas_antiguo": lambda x: -x["dias_aging_max"],
        "mas_nuevo": lambda x: x["dias_aging_min"],
        "mayor_valor": lambda x: -x["valor_total_inmovilizado"],
        "nombre": lambda x: x["producto_nombre"].lower(),
    }
    productos.sort(key=sort_map.get(orden, sort_map["mas_antiguo"]))

    filtrados = productos
    if q and q.strip():
        texto = q.strip().lower()
        filtrados = [p for p in productos if texto in p["producto_nombre"].lower()]

    return {
        "orden": orden,
        "fecha_calculo": hoy.isoformat(),
        "resumen": {
            "productos_activos_con_stock": len(productos),
            "total_tandas_activas": sum(p["num_tandas"] for p in productos),
            "valor_stock_activo": sum(p["valor_total_inmovilizado"] for p in productos),
        },
        "total_productos": len(filtrados),
        "limit": limit,
        "offset": offset,
        "productos": [
            {**p, "tandas": [_tanda(*f) for f in resumenes[p["producto_id"]]["filas"]]}
            for p in filtrados[offset:offset + limit]
        ],
    }


# ==================== SYNC PERMISSIONS ====================
# Permisos agregados después de la primera versión del sistema. Las instalaciones
# existentes los reciben al arrancar (ensure_permisos) o desde Sistema > Sincronizar.
PERMISOS_REQUERIDOS = [
    ("dashboard.ver", "Ver dashboard"),
    ("bi.ver", "Ver Business Intelligence"),
    ("gastos.ver", "Ver gastos operativos"),
    ("gastos.gestionar", "Gestionar gastos operativos"),
    ("delivery.eliminar", "Eliminar entregas"),
    ("laboratorio.editar", "Editar materias de laboratorio"),
    ("laboratorio.eliminar", "Eliminar materias de laboratorio"),
    ("presupuestos.ver", "Ver presupuestos"),
    ("presupuestos.crear", "Crear presupuestos"),
    ("presupuestos.editar", "Editar presupuestos"),
    ("presupuestos.eliminar", "Eliminar presupuestos"),
]

async def _asignar_permisos_requeridos_a_admins(db: AsyncSession) -> int:
    """Asigna a los roles administrador los permisos requeridos que les falten.
    Devuelve cuántas asignaciones se crearon (no hace commit)."""
    assigned = 0
    claves = [clave for clave, _ in PERMISOS_REQUERIDOS]
    perms = (await db.execute(select(Permiso).where(Permiso.clave.in_(claves)))).scalars().all()
    roles = (await db.execute(select(Rol).where(Rol.nombre.in_(ROLES_ADMIN)))).scalars().all()
    for rol in roles:
        for perm in perms:
            existing_rp = await db.execute(
                select(RolPermiso).where(RolPermiso.rol_id == rol.id, RolPermiso.permiso_id == perm.id)
            )
            if not existing_rp.scalar_one_or_none():
                db.add(RolPermiso(rol_id=rol.id, permiso_id=perm.id))
                assigned += 1
    return assigned

@api_router.post("/sistema/sync-permisos", dependencies=[Depends(requiere_permiso("sistema.configurar"))])
async def sync_permisos(db: AsyncSession = Depends(get_db)):
    """Add any missing permissions and assign them to all ADMIN roles. Safe to run on production."""
    added_perms = []
    for clave, desc in PERMISOS_REQUERIDOS:
        existing = await db.execute(select(Permiso).where(Permiso.clave == clave))
        if not existing.scalar_one_or_none():
            perm = Permiso(clave=clave, descripcion=desc)
            db.add(perm)
            await db.flush()
            added_perms.append(clave)

    assigned = await _asignar_permisos_requeridos_a_admins(db)
    await db.commit()
    return {
        "permisos_added": added_perms,
        "rol_permisos_assigned": assigned,
        "message": "Sincronización de permisos completada" if (added_perms or assigned) else "No hay permisos nuevos para agregar"
    }


# ==================== SEED DATA ====================
# Sin token porque se usa sobre una base vacía (aún no hay usuarios), por eso sólo existe
# con PERMITIR_ENDPOINTS_DESARROLLO=true. En producción, el primer admin se crea con
# `python seed_data.py` dentro del contenedor.
@public_router.post("/seed")
async def seed_data(db: AsyncSession = Depends(get_db)):
    """Create initial data for testing"""
    if not PERMITIR_ENDPOINTS_DESARROLLO:
        raise HTTPException(status_code=404, detail="Not Found")
    existing = await db.execute(select(Empresa))
    if existing.scalar_one_or_none():
        return {"message": "Data already seeded"}
    
    empresa = Empresa(
        nombre="Ether Soluciones Tecnológicas",
        ruc="5244360-4",
        direccion="Asunción, Paraguay",
        telefono="000000000",
        email="contacto@empresa.com"
    )
    db.add(empresa)
    await db.flush()
    
    admin = Usuario(
        empresa_id=empresa.id,
        email="admin@ether.com",
        password_hash=hash_password("admin123"),
        nombre="Administrador",
        apellido="Sistema"
    )
    db.add(admin)
    
    # Create comprehensive permissions
    permisos_data = [
        # Dashboard
        ("dashboard.ver", "Ver dashboard"),
        # Ventas
        ("ventas.crear", "Crear ventas"),
        ("ventas.ver", "Ver ventas"),
        ("ventas.anular", "Anular ventas"),
        ("ventas.modificar_precio", "Modificar precios en ventas"),
        ("ventas.aplicar_descuento", "Aplicar descuentos"),
        ("ventas.imprimir_boleta", "Imprimir boletas"),
        ("ventas.imprimir_factura", "Imprimir facturas"),
        # Productos
        ("productos.crear", "Crear productos"),
        ("productos.editar", "Editar productos"),
        ("productos.eliminar", "Eliminar productos"),
        ("productos.modificar_precio", "Modificar precios de productos"),
        ("productos.ver_costo", "Ver costos de productos"),
        # Stock
        ("stock.ver", "Ver inventario"),
        ("stock.entrada", "Registrar entradas de stock"),
        ("stock.salida", "Registrar salidas de stock"),
        ("stock.ajustar", "Ajustar stock"),
        ("stock.traspasar", "Traspasar entre almacenes"),
        ("stock.configurar_alertas", "Configurar alertas de stock"),
        # Clientes
        ("clientes.crear", "Crear clientes"),
        ("clientes.editar", "Editar clientes"),
        ("clientes.eliminar", "Eliminar clientes"),
        ("clientes.ver_creditos", "Ver créditos de clientes"),
        ("clientes.modificar_descuento", "Modificar descuento de cliente"),
        # Proveedores
        ("proveedores.crear", "Crear proveedores"),
        ("proveedores.editar", "Editar proveedores"),
        ("proveedores.eliminar", "Eliminar proveedores"),
        ("proveedores.gestionar_deudas", "Gestionar deudas a proveedores"),
        # Funcionarios
        ("funcionarios.ver", "Ver funcionarios"),
        ("funcionarios.crear", "Crear funcionarios"),
        ("funcionarios.editar", "Editar funcionarios"),
        ("funcionarios.ver_salarios", "Ver salarios"),
        ("funcionarios.adelantos", "Registrar adelantos de salario"),
        ("funcionarios.pagar_salarios", "Marcar salarios como pagados"),
        # Delivery
        ("delivery.ver", "Ver entregas"),
        ("delivery.crear", "Crear entregas"),
        ("delivery.actualizar_estado", "Actualizar estado de entregas"),
        # Flota
        ("flota.ver", "Ver flota"),
        ("flota.gestionar", "Gestionar vehículos"),
        # Laboratorio
        ("laboratorio.crear", "Crear materias de laboratorio"),
        ("laboratorio.ver", "Ver materias de laboratorio"),
        ("laboratorio.editar", "Editar materias de laboratorio"),
        ("laboratorio.eliminar", "Eliminar materias de laboratorio"),
        # Sistema
        ("usuarios.ver", "Ver usuarios"),
        ("usuarios.gestionar", "Gestionar usuarios"),
        ("roles.gestionar", "Gestionar roles y permisos"),
        ("sistema.configurar", "Configurar sistema"),
        ("reportes.ver", "Ver reportes"),
        ("reportes.exportar", "Exportar reportes"),
        # Business Intelligence
        ("bi.ver", "Ver Business Intelligence"),
        # Additional view permissions
        ("productos.ver", "Ver productos"),
        ("proveedores.ver", "Ver proveedores"),
        ("clientes.ver", "Ver clientes"),
        ("facturas.ver", "Ver facturas"),
        ("ventas.ver_historial", "Ver historial de ventas"),
        # Gastos operativos
        ("gastos.ver", "Ver gastos operativos"),
        ("gastos.gestionar", "Gestionar gastos operativos"),
        # Presupuestos
        ("presupuestos.ver", "Ver presupuestos"),
        ("presupuestos.crear", "Crear presupuestos"),
        ("presupuestos.editar", "Editar presupuestos"),
        ("presupuestos.eliminar", "Eliminar presupuestos"),
    ]
    # El arranque (ensure_permisos) ya crea algunos: sólo se agregan los que falten
    existentes = set((await db.execute(select(Permiso.clave))).scalars().all())
    for clave, desc in permisos_data:
        if clave not in existentes:
            db.add(Permiso(clave=clave, descripcion=desc))
    
    # Create roles
    for rol_nombre in ["ADMIN", "GERENTE", "VENDEDOR", "DELIVERY"]:
        db.add(Rol(empresa_id=empresa.id, nombre=rol_nombre, descripcion=f"Rol {rol_nombre}"))
    
    await db.flush()  # Flush to get IDs
    
    # Assign all permissions to ADMIN role
    admin_rol_result = await db.execute(select(Rol).where(Rol.nombre == "ADMIN", Rol.empresa_id == empresa.id))
    admin_rol = admin_rol_result.scalar_one_or_none()
    
    if admin_rol:
        permisos_result = await db.execute(select(Permiso))
        all_permisos = permisos_result.scalars().all()
        for permiso in all_permisos:
            db.add(RolPermiso(rol_id=admin_rol.id, permiso_id=permiso.id))
        db.add(UsuarioRol(usuario_id=admin.id, rol_id=admin_rol.id))
    
    # Assign permissions to GERENTE role
    gerente_rol_result = await db.execute(select(Rol).where(Rol.nombre == "GERENTE", Rol.empresa_id == empresa.id))
    gerente_rol = gerente_rol_result.scalar_one_or_none()
    gerente_permisos = [
        "dashboard.ver",
        "ventas.crear", "ventas.ver", "ventas.anular", "ventas.modificar_precio", "ventas.aplicar_descuento",
        "ventas.imprimir_boleta", "ventas.imprimir_factura", "ventas.ver_historial",
        "productos.ver", "productos.crear", "productos.editar", "productos.modificar_precio",
        "stock.ver", "stock.entrada", "stock.salida", "stock.traspasar",
        "clientes.ver", "clientes.crear", "clientes.editar", "clientes.ver_creditos",
        "proveedores.ver", "proveedores.gestionar_deudas",
        "funcionarios.ver", "funcionarios.ver_salarios", "funcionarios.adelantos",
        "delivery.ver", "delivery.crear", "delivery.actualizar_estado",
        "flota.ver", "laboratorio.ver", "laboratorio.crear", "laboratorio.editar",
        "reportes.ver", "reportes.exportar",
        "bi.ver",
        "gastos.ver", "gastos.gestionar",
        "presupuestos.ver", "presupuestos.crear", "presupuestos.editar", "presupuestos.eliminar"
    ]
    if gerente_rol:
        for perm_clave in gerente_permisos:
            perm_result = await db.execute(select(Permiso).where(Permiso.clave == perm_clave))
            perm = perm_result.scalar_one_or_none()
            if perm:
                db.add(RolPermiso(rol_id=gerente_rol.id, permiso_id=perm.id))
    
    # Assign permissions to VENDEDOR role
    vendedor_rol_result = await db.execute(select(Rol).where(Rol.nombre == "VENDEDOR", Rol.empresa_id == empresa.id))
    vendedor_rol = vendedor_rol_result.scalar_one_or_none()
    vendedor_permisos = [
        "dashboard.ver",
        "ventas.crear", "ventas.ver", "ventas.imprimir_boleta", "ventas.imprimir_factura", "ventas.ver_historial",
        "productos.ver", "stock.ver",
        "clientes.ver", "clientes.crear",
        "delivery.ver", "delivery.crear",
        "laboratorio.ver",
        "presupuestos.ver", "presupuestos.crear", "presupuestos.editar"
    ]
    if vendedor_rol:
        for perm_clave in vendedor_permisos:
            perm_result = await db.execute(select(Permiso).where(Permiso.clave == perm_clave))
            perm = perm_result.scalar_one_or_none()
            if perm:
                db.add(RolPermiso(rol_id=vendedor_rol.id, permiso_id=perm.id))
    
    # Assign permissions to DELIVERY role
    delivery_rol_result = await db.execute(select(Rol).where(Rol.nombre == "DELIVERY", Rol.empresa_id == empresa.id))
    delivery_rol = delivery_rol_result.scalar_one_or_none()
    delivery_permisos = [
        "delivery.ver", "delivery.actualizar_estado",
        "flota.ver"
    ]
    if delivery_rol:
        for perm_clave in delivery_permisos:
            perm_result = await db.execute(select(Permiso).where(Permiso.clave == perm_clave))
            perm = perm_result.scalar_one_or_none()
            if perm:
                db.add(RolPermiso(rol_id=delivery_rol.id, permiso_id=perm.id))
    
    # Assign admin user to ADMIN role
    admin.rol_id = admin_rol.id if admin_rol else None
    
    # Create categories
    categorias = ["Pinturas", "Herramientas", "Materiales", "Accesorios"]
    for cat in categorias:
        db.add(Categoria(empresa_id=empresa.id, nombre=cat))
    
    # Create brands
    marcas = ["Alba", "Sherwin Williams", "Sinteplast", "Tersuave", "3M"]
    for marca in marcas:
        db.add(Marca(empresa_id=empresa.id, nombre=marca))
    
    # Create warehouses
    db.add(Almacen(empresa_id=empresa.id, nombre="Depósito Principal", ubicacion="Planta Baja"))
    db.add(Almacen(empresa_id=empresa.id, nombre="Tienda", ubicacion="Local Comercial"))
    
    # Create occasional client
    db.add(Cliente(
        empresa_id=empresa.id,
        nombre="Cliente",
        apellido="Ocasional",
        ruc="00000000-0"
    ))
    
    await db.commit()
    return {"message": "Data seeded successfully", "empresa_id": empresa.id}

@api_router.post("/reset-database", dependencies=[Depends(verificar_es_admin)])
async def reset_database(db: AsyncSession = Depends(get_db)):
    """
    PELIGRO: Elimina y recrea todas las tablas
    Solo usar en desarrollo o primera configuración
    """
    if not PERMITIR_ENDPOINTS_DESARROLLO:
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database reset completed")
        
        # Create default empresa
        empresa = Empresa(
            ruc="5244360-4",
            nombre="Ether Soluciones Tecnológicas",
            direccion="Dirección Principal 123",
            telefono="000000000",
            email="contacto@empresa.com",
            estado=True
        )
        db.add(empresa)
        await db.flush()
        
        # Create admin role
        rol_admin = Rol(
            empresa_id=empresa.id,
            nombre="ADMIN",
            descripcion="Administrador del sistema",
            estado=True
        )
        db.add(rol_admin)
        await db.flush()
        
        # Create admin user
        admin = Usuario(
            empresa_id=empresa.id,
            email="admin@ether.com",
            password_hash=hash_password("admin123"),
            nombre="Admin",
            apellido="Sistema",
            telefono="123456789",
            activo=True
        )
        db.add(admin)
        await db.flush()
        
        # Assign role to user via UsuarioRol
        usuario_rol = UsuarioRol(
            usuario_id=admin.id,
            rol_id=rol_admin.id
        )
        db.add(usuario_rol)
        
        # Create permissions
        permisos_data = [
            ("ventas.crear", "Crear ventas"),
            ("ventas.ver", "Ver ventas"),
            ("ventas.anular", "Anular ventas"),
            ("productos.crear", "Crear productos"),
            ("productos.editar", "Editar productos"),
            ("productos.eliminar", "Eliminar productos"),
            ("stock.ajustar", "Ajustar stock"),
            ("clientes.crear", "Crear clientes"),
            ("clientes.editar", "Editar clientes"),
            ("funcionarios.ver", "Ver funcionarios"),
            ("funcionarios.editar", "Editar funcionarios"),
            ("usuarios.gestionar", "Gestionar usuarios"),
            ("sistema.configurar", "Configurar sistema"),
            ("gastos.ver", "Ver gastos operativos"),
            ("gastos.gestionar", "Gestionar gastos operativos"),
            ("presupuestos.ver", "Ver presupuestos"),
            ("presupuestos.crear", "Crear presupuestos"),
            ("presupuestos.editar", "Editar presupuestos"),
            ("presupuestos.eliminar", "Eliminar presupuestos"),
        ]
        permisos_creados = {}
        for clave, desc in permisos_data:
            permiso = Permiso(clave=clave, descripcion=desc, estado=True)
            db.add(permiso)
            await db.flush()
            permisos_creados[clave] = permiso

            # Assign all permissions to admin role
            rol_permiso = RolPermiso(rol_id=rol_admin.id, permiso_id=permiso.id)
            db.add(rol_permiso)

        # Create other roles
        rol_gerente = Rol(
            empresa_id=empresa.id,
            nombre="GERENTE",
            descripcion="Rol GERENTE",
            estado=True
        )
        db.add(rol_gerente)
        await db.flush()
        for clave in ("presupuestos.ver", "presupuestos.crear", "presupuestos.editar", "presupuestos.eliminar"):
            db.add(RolPermiso(rol_id=rol_gerente.id, permiso_id=permisos_creados[clave].id))

        rol_vendedor = Rol(
            empresa_id=empresa.id,
            nombre="VENDEDOR",
            descripcion="Rol VENDEDOR",
            estado=True
        )
        db.add(rol_vendedor)
        await db.flush()
        for clave in ("presupuestos.ver", "presupuestos.crear", "presupuestos.editar"):
            db.add(RolPermiso(rol_id=rol_vendedor.id, permiso_id=permisos_creados[clave].id))

        db.add(Rol(
            empresa_id=empresa.id,
            nombre="DELIVERY",
            descripcion="Rol DELIVERY",
            estado=True
        ))

        # Create categories
        categorias = ["Pinturas", "Herramientas", "Materiales", "Accesorios"]
        for cat in categorias:
            db.add(Categoria(empresa_id=empresa.id, nombre=cat, estado=True))
        
        # Create brands
        marcas = ["Alba", "Sherwin Williams", "Sinteplast", "Tersuave"]
        for marca in marcas:
            db.add(Marca(empresa_id=empresa.id, nombre=marca, estado=True))
        
        # Create warehouses
        db.add(Almacen(empresa_id=empresa.id, nombre="Depósito Principal", ubicacion="Planta Baja", estado=True))
        db.add(Almacen(empresa_id=empresa.id, nombre="Tienda", ubicacion="Local Comercial", estado=True))
        
        # Create occasional client
        db.add(Cliente(
            empresa_id=empresa.id,
            nombre="Cliente",
            apellido="Ocasional",
            ruc="00000000-0",
            estado=True
        ))
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "Base de datos reseteada y poblada exitosamente",
            "credentials": {
                "email": "admin@ether.com",
                "password": "admin123"
            },
            "empresa_id": empresa.id
        }
    except Exception as e:
        logger.error(f"Error al resetear base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al resetear base de datos: {str(e)}")

# Include routers
app.include_router(public_router)
app.include_router(api_router)

# Health check sin datos internos (rutas de disco ni variables de entorno)
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Startup event
@app.on_event("startup")
async def startup():
    await init_db()
    await ensure_columnas()

    # Auto-migration: ensure bi.ver permission exists and is assigned to ADMIN roles
    try:
        async with async_session_maker() as db:
            # Insert permission if missing
            existing = await db.execute(select(Permiso).where(Permiso.clave == "bi.ver"))
            if not existing.scalar_one_or_none():
                bi_perm = Permiso(clave="bi.ver", descripcion="Ver Business Intelligence")
                db.add(bi_perm)
                await db.flush()
                # Assign to every ADMIN rol found
                admin_roles = await db.execute(select(Rol).where(Rol.nombre.in_(ROLES_ADMIN)))
                for admin_rol in admin_roles.scalars().all():
                    db.add(RolPermiso(rol_id=admin_rol.id, permiso_id=bi_perm.id))
                # Assign to every GERENTE rol found
                gerente_roles = await db.execute(select(Rol).where(Rol.nombre == "GERENTE"))
                for g_rol in gerente_roles.scalars().all():
                    db.add(RolPermiso(rol_id=g_rol.id, permiso_id=bi_perm.id))
                await db.commit()
                logger.info("BI migration: bi.ver permission created and assigned")
            else:
                logger.info("BI migration: bi.ver already exists, skipping")
    except Exception as e:
        logger.warning(f"BI permission migration warning: {e}")

    await ensure_indices()
    await ensure_permisos()
    logger.info("Database initialized")

# Columnas agregadas a tablas que ya existían. create_all() sólo crea tablas nuevas,
# así que se agregan aquí de forma idempotente (mismo SQL que
# documentacion/migracion_sync_luzbrill_2026-10.sql).
COLUMNAS_REQUERIDAS = [
    ("movimientos_stock", "costo_ponderado", "NUMERIC(15,2)"),
    ("movimientos_stock", "cantidad_restante", "INTEGER"),
    ("proveedor_productos", "sku", "VARCHAR(100)"),
    ("proveedor_productos", "link", "VARCHAR(1000)"),
    ("ventas", "facturada", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("ventas", "fecha_impresion_boleta", "DATE"),
    ("ventas", "fecha_impresion_factura", "DATE"),
    ("productos", "creado_en", "TIMESTAMP WITH TIME ZONE"),
    ("facturas_grupales", "condicion", "VARCHAR(10) NOT NULL DEFAULT 'CONTADO'"),
]

async def ensure_columnas():
    es_postgres = 'postgresql' in str(engine.url)
    for tabla, columna, tipo in COLUMNAS_REQUERIDAS:
        try:
            async with engine.begin() as conn:
                if es_postgres:
                    await conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}"))
                else:
                    columnas = await conn.execute(text(f"PRAGMA table_info({tabla})"))
                    if columna not in {fila[1] for fila in columnas}:
                        await conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"))
        except Exception as e:
            # Una columna que no se pudo agregar no debe impedir el arranque
            logger.warning(f"No se pudo asegurar la columna {tabla}.{columna}: {e}")
    if es_postgres:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("ALTER TABLE proveedor_productos ALTER COLUMN costo DROP NOT NULL"))
        except Exception as e:
            logger.warning(f"No se pudo hacer opcional proveedor_productos.costo: {e}")

# Índices sobre las claves foráneas más consultadas. create_all() no los añade a
# tablas que ya existen, así que se crean aquí de forma idempotente.
INDICES_REQUERIDOS = [
    ("ix_materias_laboratorio_empresa_id", "materias_laboratorio", "empresa_id"),
    ("ix_materias_laboratorio_estado", "materias_laboratorio", "estado"),
    ("ix_materias_laboratorio_creado_en", "materias_laboratorio", "creado_en"),
    ("ix_productos_empresa_id", "productos", "empresa_id"),
    ("ix_productos_activo", "productos", "activo"),
    ("ix_stock_actual_producto_id", "stock_actual", "producto_id"),
    ("ix_movimientos_stock_producto_id", "movimientos_stock", "producto_id"),
    ("ix_clientes_empresa_id", "clientes", "empresa_id"),
    ("ix_ventas_empresa_id", "ventas", "empresa_id"),
    ("ix_venta_items_venta_id", "venta_items", "venta_id"),
]

async def ensure_indices():
    """Crea los índices que faltan. CREATE INDEX IF NOT EXISTS funciona en PostgreSQL y SQLite."""
    async with engine.begin() as conn:
        for nombre, tabla, columna in INDICES_REQUERIDOS:
            try:
                await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla} ({columna})"))
            except Exception as e:
                # Una tabla ausente no debe impedir el arranque
                logger.warning(f"No se pudo crear el índice {nombre}: {e}")

async def ensure_permisos():
    """Ensure all required permissions exist in the DB (handles migrations for existing installs)"""
    async with async_session_maker() as db:
        for clave, descripcion in PERMISOS_REQUERIDOS:
            existing = await db.execute(select(Permiso).where(Permiso.clave == clave))
            if not existing.scalar_one_or_none():
                db.add(Permiso(clave=clave, descripcion=descripcion))
                logger.info(f"Created missing permission: {clave}")
        await db.flush()
        asignados = await _asignar_permisos_requeridos_a_admins(db)
        if asignados:
            logger.info(f"Asignados {asignados} permisos requeridos a roles administrador")
        await db.commit()

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    logger.info("Database connection closed")
