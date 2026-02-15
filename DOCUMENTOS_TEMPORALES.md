# Gestión de Documentos Temporales (Boletas/Facturas) - 30 Días de Duración

## Problema Resuelto
**Antes**: Los PDFs de boletas/facturas se guardaban en `/tmp/documentos`, un directorio que el sistema operativo limpia automáticamente (cada 24 horas o al reiniciar). Los enlaces dejaban de funcionar en menos de un día.

**Ahora**: Los archivos se guardan en `backend/uploads/documentos/`, un directorio persistente que NO se limpia automáticamente. Los enlaces funcionan por **30 días** desde su creación.

---

## Flujo de Documentos

### 1. Generación de Enlace
Cuando se genera un enlace de boleta/factura desde el frontend (botón WhatsApp):

```
POST /api/ventas/{venta_id}/generar-enlace?tipo_documento=BOLETA
```

El sistema:
1. ✅ Genera el PDF con reportlab
2. ✅ Crea un token único (UUID)
3. ✅ Guarda el PDF en: `backend/uploads/documentos/boleta_{venta_id}_{token}.pdf`
4. ✅ Registra en tabla `documentos_temporales`:
   - `fecha_creacion`: Ahora
   - `fecha_expiracion`: Ahora + 30 días
   - `file_path`: Ruta completa del archivo
   - `descargas`: 0
5. ✅ Retorna URL pública: `https://tu-backend.onrender.com/api/documentos/{token}`

### 2. Descarga de Documento
Cuando alguien abre el enlace:

```
GET /api/documentos/{token}
```

El sistema:
1. ✅ Verifica que el token existe en la BD
2. ✅ Verifica que NO esté expirado (fecha_expiracion > ahora)
3. ✅ Verifica que el archivo físico existe
4. ✅ Incrementa contador de `descargas`
5. ✅ Sirve el PDF con nombre amigable

**Errores posibles**:
- `404`: Token no encontrado
- `410`: Enlace expirado (más de 30 días)
- `404`: Archivo no existe en disco

### 3. Expiración y Limpieza
Los documentos se marcan como expirados automáticamente por fecha, pero **los archivos NO se eliminan solos**.

---

## Verificación de Archivos

### Script de Verificación
Ejecutar desde `backend/`:

```bash
python verificar_documentos.py
```

**Muestra**:
- 📊 Total documentos registrados
- ✅ Documentos vigentes vs expirados
- 📄 Archivos existentes en disco
- ⚠️ Archivos faltantes
- 📁 Archivos huérfanos (en disco sin registro)
- Tabla detallada con ID, tipo, fecha creación, expiración, estado, archivo

**Ejemplo de salida**:
```
======================================================================
VERIFICACIÓN DE DOCUMENTOS TEMPORALES
======================================================================

📂 Directorio ROOT: /opt/render/project/src/backend
📁 Directorio documentos: /opt/render/project/src/backend/uploads/documentos
✓  Directorio existe: Sí
✓  Directorio persistente (no se limpia automáticamente)

Total de documentos en BD: 15

ID    Tipo     Venta   Creación             Expira               Estado        Archivo       Descargas
--------------------------------------------------------------------------------------------------------------
45    Boleta   #1234   2026-02-12 14:30     2026-03-14 14:30     VIGENTE (27d)  ✓ Sí (45.2KB)  3
44    Factura  #1233   2026-01-10 10:15     2026-02-09 10:15     EXPIRADO       ✗ No           0
...
```

---

## Limpieza Manual de Archivos Expirados

### Endpoint de Limpieza
Elimina documentos expirados (BD + disco):

```bash
# Desarrollo local
curl -X DELETE http://localhost:8000/api/documentos/limpiar-expirados

# Producción
curl -X DELETE https://luzbrill-backend.onrender.com/api/documentos/limpiar-expirados
```

**Respuesta**:
```json
{
  "documentos_eliminados_bd": 5,
  "archivos_eliminados_disco": 5,
  "errores": []
}
```

---

## Limpieza Automática (Recomendado)

Para limpiar automáticamente los archivos expirados, configura un cronjob o tarea programada.

### Opción 1: Cron Job en Render (usando cron-job.org)
Render free tier no incluye cron, pero puedes usar servicios externos gratuitos:

**Servicio recomendado**: [cron-job.org](https://cron-job.org) (gratis)

1. Crear cuenta en cron-job.org
2. Crear nuevo cronjob:
   - **URL**: `https://luzbrill-backend.onrender.com/api/documentos/limpiar-expirados`
   - **Method**: DELETE
   - **Schedule**: Diariamente a las 3:00 AM
   - **Cron expression**: `0 3 * * *`
3. Guardar y activar

### Opción 2: GitHub Actions (gratis)
Crear archivo `.github/workflows/cleanup-docs.yml`:

```yaml
name: Cleanup Expired Documents

on:
  schedule:
    # Ejecutar todos los días a las 3:00 UTC
    - cron: '0 3 * * *'
  workflow_dispatch: # Permitir ejecución manual

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Call cleanup endpoint
        run: |
          curl -X DELETE https://luzbrill-backend.onrender.com/api/documentos/limpiar-expirados
```

### Opción 3: Render Cron (Paid plan)
Si tienes plan pago de Render, agregar en `render.yaml`:

```yaml
services:
  - type: cron
    name: cleanup-expired-docs
    env: docker
    schedule: "0 3 * * *"  # Diariamente a las 3 AM
    dockerCommand: curl -X DELETE http://localhost:8000/api/documentos/limpiar-expirados
```

### Opción 4: Script manual (Windows Task Scheduler / Linux Cron)
**Windows**: Crear tarea programada que ejecute:
```powershell
curl -X DELETE https://luzbrill-backend.onrender.com/api/documentos/limpiar-expirados
```

**Linux**: Agregar a crontab (`crontab -e`):
```bash
0 3 * * * curl -X DELETE https://luzbrill-backend.onrender.com/api/documentos/limpiar-expirados
```

---

## Monitoreo y Métricas

### Verificar estado del sistema
```bash
python verificar_documentos.py
```

### Consultar estadísticas en la BD
```sql
-- Total documentos
SELECT COUNT(*) FROM documentos_temporales;

-- Documentos vigentes
SELECT COUNT(*) FROM documentos_temporales
WHERE fecha_expiracion > NOW();

-- Documentos más descargados
SELECT venta_id, tipo_documento, descargas, fecha_creacion
FROM documentos_temporales
ORDER BY descargas DESC
LIMIT 10;

-- Documentos próximos a expirar (menos de 7 días)
SELECT venta_id, tipo_documento, fecha_expiracion,
       EXTRACT(DAY FROM (fecha_expiracion - NOW())) as dias_restantes
FROM documentos_temporales
WHERE fecha_expiracion > NOW()
  AND fecha_expiracion < NOW() + INTERVAL '7 days'
ORDER BY fecha_expiracion;
```

---

## Migración de Archivos Antiguos

Si tienes archivos en `/tmp/documentos` o en el antiguo directorio, NO se migrarán automáticamente. Los enlaces antiguos dejarán de funcionar.

**Solución**: Los usuarios deben generar nuevos enlaces desde el frontend (botón WhatsApp en ventas).

---

## Estructura de Directorios

```
backend/
├── uploads/
│   ├── productos/          # Imágenes de productos
│   │   └── producto_123.jpg
│   └── documentos/         # PDFs de boletas/facturas (30 días)
│       ├── boleta_1234_ab12cd34-...uuid.pdf
│       ├── factura_5678_ef56gh78-...uuid.pdf
│       └── ...
├── server.py
├── verificar_documentos.py
└── ...
```

**Importante**: El directorio `uploads/` se monta como `/uploads` en el servidor web (StaticFiles), por lo que los archivos son accesibles públicamente por URL, pero solo si conoces el token UUID.

---

## Preguntas Frecuentes (FAQ)

### ¿Por qué 30 días?
Es un balance entre:
- ✅ Dejar tiempo suficiente para que clientes accedan a sus boletas
- ✅ No acumular archivos indefinidamente
- ✅ Cumplir con prácticas de retención de documentos temporales

### ¿Puedo cambiar la duración?
Sí, editar en `server.py` línea ~2095:
```python
fecha_expiracion = now_paraguay() + timedelta(days=30)  # Cambiar 30 por el número deseado
```

### ¿Los archivos ocupan mucho espacio?
- Boleta promedio: ~45 KB
- Factura promedio: ~50 KB
- 1000 documentos ≈ 50 MB
- Con limpieza mensual: ~100 MB máximo

### ¿Qué pasa si se elimina el archivo pero existe el registro en BD?
El endpoint `/api/documentos/{token}` retornará error 404 "El archivo ya no está disponible". El usuario debe generar un nuevo enlace.

### ¿Los enlaces son seguros?
Sí:
- ✅ Usan UUID v4 (128 bits de entropía) - prácticamente imposible de adivinar
- ✅ No contienen información sensible en la URL
- ✅ Se invalidan automáticamente después de 30 días
- ⚠️ Cualquiera con el enlace puede descargar (diseñado así para compartir por WhatsApp sin login)

### ¿Qué pasa si borro manualmente un archivo?
- El registro en BD sigue existiendo
- Al intentar descargar: Error 404
- La limpieza automática NO lo detectará (solo limpia expirados)
- Recomendación: Usar siempre el endpoint de limpieza

---

## Troubleshooting

### Problema: "El archivo ya no está disponible"
**Causa**: Archivo eliminado del disco pero registro existe en BD.

**Solución**:
1. Verificar con `python verificar_documentos.py`
2. Si está expirado: Ejecutar limpieza
3. Si no está expirado: Generar nuevo enlace desde frontend

### Problema: Enlaces dejan de funcionar después de 1 día
**Causa**: El código aún usa `/tmp` (versión antigua).

**Verificación**:
```bash
grep -n "DOCS_DIR" backend/server.py
```

Debe mostrar:
```python
DOCS_DIR = ROOT_DIR / 'uploads' / 'documentos'
```

NO debe mostrar:
```python
DOCS_DIR = Path("/tmp/documentos")  # ❌ Versión antigua
```

### Problema: No se crean archivos
**Causa**: Permisos del directorio `uploads/documentos/`.

**Solución**:
```bash
cd backend
mkdir -p uploads/documentos
chmod 755 uploads/documentos
```

### Problema: Error al limpiar archivos
**Causa**: Base de datos tiene rutas antiguas (`/tmp/`).

**Solución**: Ejecutar SQL para limpiar registros huérfanos:
```sql
DELETE FROM documentos_temporales
WHERE fecha_expiracion < NOW();
```

---

## Resumen de Cambios Realizados

### ✅ Código Modificado
1. **server.py** (líneas 1971-1977):
   - Cambió de `/tmp/documentos` a `ROOT_DIR / 'uploads' / 'documentos'`
   - Directorio ahora es persistente

2. **verificar_documentos.py** (nuevo archivo):
   - Script para auditar estado de archivos
   - Muestra tabla detallada con colores
   - Detecta archivos faltantes y huérfanos

3. **DOCUMENTOS_TEMPORALES.md** (este archivo):
   - Documentación completa del sistema
   - Guías de limpieza automática
   - Troubleshooting

### ✅ Sistema de Expiración
- Ya existía en el código (30 días)
- Ahora funciona correctamente con almacenamiento persistente

### ✅ Compatibilidad
- Los enlaces antiguos (si existen) dejarán de funcionar
- Generar nuevos enlaces desde el frontend
- No hay migración automática

---

## Next Steps (Recomendado)

1. ✅ **Desplegar cambios a Render**
   ```bash
   git add .
   git commit -m "fix: usar directorio persistente para documentos temporales (30 días)"
   git push origin main
   ```

2. ✅ **Configurar limpieza automática**
   - Opción recomendada: cron-job.org (5 minutos de setup)
   - Alternativa: GitHub Actions workflow

3. ✅ **Probar sistema**
   ```bash
   # Localmente
   python verificar_documentos.py
   
   # Generar enlace de prueba desde frontend
   # Verificar que el archivo existe en uploads/documentos/
   ```

4. ✅ **Monitorear semanalmente**
   - Ejecutar script de verificación
   - Revisar cantidad de archivos
   - Confirmar que limpieza automática funciona

---

**Fecha de implementación**: 15 de febrero de 2026  
**Autor**: Sistema de gestión Luz Brill ERP
