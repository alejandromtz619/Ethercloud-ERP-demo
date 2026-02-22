"""
Script para verificar archivos de documentos (boletas/facturas) en el servidor.
Compara los registros en la base de datos con los archivos físicos en disco.
"""
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy import select, and_
from database import async_session
from models import DocumentoTemporal, Venta
from server import now_paraguay

# Colores para la terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

async def verificar_documentos():
    """
    Verifica la existencia de archivos de documentos y su estado de expiración
    """
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"VERIFICACIÓN DE DOCUMENTOS TEMPORALES")
    print(f"{'='*70}{Colors.END}\n")
    
    # Determinar directorio de documentos (igual que en server.py)
    # AHORA USA: ROOT_DIR / 'uploads' / 'documentos' (directorio persistente)
    root_dir = Path(__file__).parent
    docs_dir = root_dir / 'uploads' / 'documentos'
    
    print(f"📂 Directorio ROOT: {root_dir.absolute()}")
    print(f"📁 Directorio documentos: {docs_dir.absolute()}")
    print(f"✓  Directorio existe: {'Sí' if docs_dir.exists() else 'No'}")
    print(f"{Colors.GREEN}✓  Directorio persistente (no se limpia automáticamente){Colors.END}")
    
    # Listar archivos en el directorio
    if docs_dir.exists():
        archivos_disco = list(docs_dir.glob("*.pdf"))
        print(f"📄 Archivos en disco: {len(archivos_disco)}")
    else:
        archivos_disco = []
        print(f"{Colors.RED}✗  El directorio no existe{Colors.END}")
    
    print(f"\n{Colors.BOLD}Consultando base de datos...{Colors.END}")
    
    async with async_session() as db:
        # Consultar todos los documentos en la BD
        result = await db.execute(
            select(DocumentoTemporal, Venta)
            .join(Venta, DocumentoTemporal.venta_id == Venta.id)
            .order_by(DocumentoTemporal.fecha_creacion.desc())
        )
        documentos = result.all()
        
        ahora = now_paraguay()
        
        # Estadísticas
        total = len(documentos)
        vigentes = 0
        expirados = 0
        archivo_existe = 0
        archivo_falta = 0
        
        print(f"\n{Colors.BOLD}Total de documentos en BD: {total}{Colors.END}\n")
        
        if total == 0:
            print(f"{Colors.YELLOW}No hay documentos registrados en la base de datos.{Colors.END}")
            return
        
        # Tabla de resultados
        print(f"{Colors.BOLD}{'ID':<5} {'Tipo':<8} {'Venta':<7} {'Creación':<20} {'Expira':<20} {'Estado':<12} {'Archivo':<10} {'Descargas':<10}{Colors.END}")
        print("-" * 110)
        
        for doc, venta in documentos:
            expirado = doc.fecha_expiracion < ahora
            file_path = Path(doc.file_path)
            existe = file_path.exists()
            
            # Contadores
            if expirado:
                expirados += 1
            else:
                vigentes += 1
            
            if existe:
                archivo_existe += 1
            else:
                archivo_falta += 1
            
            # Estado con colores
            if expirado:
                estado_str = f"{Colors.RED}EXPIRADO{Colors.END}"
            else:
                dias_restantes = (doc.fecha_expiracion - ahora).days
                if dias_restantes < 7:
                    estado_str = f"{Colors.YELLOW}VIGENTE ({dias_restantes}d){Colors.END}"
                else:
                    estado_str = f"{Colors.GREEN}VIGENTE ({dias_restantes}d){Colors.END}"
            
            # Archivo con colores
            if existe:
                archivo_str = f"{Colors.GREEN}✓ Sí{Colors.END}"
                tamaño = file_path.stat().st_size / 1024  # KB
                archivo_str += f" ({tamaño:.1f}KB)"
            else:
                archivo_str = f"{Colors.RED}✗ No{Colors.END}"
            
            # Tipo de documento
            tipo_str = "Boleta" if doc.tipo_documento.value == "BOLETA" else "Factura"
            
            # Formatear fechas
            fecha_creacion = doc.fecha_creacion.strftime("%Y-%m-%d %H:%M")
            fecha_expiracion = doc.fecha_expiracion.strftime("%Y-%m-%d %H:%M")
            
            print(f"{doc.id:<5} {tipo_str:<8} #{venta.id:<6} {fecha_creacion:<20} {fecha_expiracion:<20} {estado_str:<25} {archivo_str:<25} {doc.descargas:<10}")
        
        # Resumen con estadísticas
        print("\n" + "=" * 110)
        print(f"\n{Colors.BOLD}RESUMEN:{Colors.END}")
        print(f"  📊 Total documentos: {total}")
        print(f"  {Colors.GREEN}✓ Vigentes: {vigentes}{Colors.END}")
        print(f"  {Colors.RED}✗ Expirados: {expirados}{Colors.END}")
        print(f"  {Colors.GREEN}📄 Archivos existentes: {archivo_existe}{Colors.END}")
        print(f"  {Colors.RED}⚠️  Archivos faltantes: {archivo_falta}{Colors.END}")
        
        if archivo_falta > 0:
            print(f"\n{Colors.YELLOW}⚠️  ADVERTENCIA: Hay {archivo_falta} documento(s) registrado(s) sin archivo físico{Colors.END}")
            print(f"   Esto puede ocurrir si:")
            print(f"   - El servidor se reinició y usa /tmp (directorio temporal)")
            print(f"   - Los archivos fueron eliminados manualmente")
            print(f"   - El sistema operativo limpió el directorio /tmp")
        
        # Archivos huérfanos (en disco pero no en BD)
        if docs_dir.exists():
            tokens_bd = {Path(doc.file_path).name for doc, _ in documentos}
            archivos_huerfanos = [f for f in archivos_disco if f.name not in tokens_bd]
            
            if archivos_huerfanos:
                print(f"\n{Colors.YELLOW}📁 Archivos en disco sin registro en BD: {len(archivos_huerfanos)}{Colors.END}")
                for archivo in archivos_huerfanos[:10]:  # Mostrar máximo 10
                    tamaño = archivo.stat().st_size / 1024
                    print(f"   - {archivo.name} ({tamaño:.1f}KB)")
                if len(archivos_huerfanos) > 10:
                    print(f"   ... y {len(archivos_huerfanos) - 10} más")
        
        # Recomendaciones
        print(f"\n{Colors.BOLD}RECOMENDACIONES:{Colors.END}")
        if expirados > 0:
            print(f"  {Colors.YELLOW}1. Hay {expirados} documento(s) expirado(s){Colors.END}")
            print(f"     Ejecutar: curl -X DELETE http://localhost:8000/api/documentos/limpiar-expirados")
            print(f"     O desde el servidor: curl -X DELETE https://tu-backend-url.onrender.com/api/documentos/limpiar-expirados")
        
        if archivo_falta > 0 and archivo_falta != expirados:
            print(f"  {Colors.RED}2. Hay {archivo_falta} archivo(s) faltante(s) que no están expirados{Colors.END}")
            print(f"     Esto puede indicar un problema de persistencia o migración")
        
        if vigentes > 0 and archivo_existe == vigentes:
            print(f"  {Colors.GREEN}✓ Todos los documentos vigentes tienen su archivo en disco{Colors.END}")
        
        print(f"\n  {Colors.BLUE}💡 Tip: Los documentos ahora se guardan en 'uploads/documentos' (persistente){Colors.END}")
        print(f"     Los enlaces duran 30 días desde su creación")
        
        print("\n" + "=" * 110 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(verificar_documentos())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Verificación cancelada por el usuario{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error durante la verificación: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
