# Decisiones técnicas y glosario

Este documento registra las decisiones de implementación: qué se eligió, por qué y qué se
descartó. Las decisiones de producto (D1 a D12) están en el plan del proyecto,
`PLAN_ERP360_SIFEN_CRM.md`.

## Decisiones

### 1. Migraciones: SQL numerado que se aplica al arrancar (D10)
- **Qué:** `backend/migraciones/NNNN_nombre.sql` (variantes `.postgresql.sql` / `.sqlite.sql`). Las
  aplica `migraciones.py` al arrancar, dentro del candado de arranque, y quedan registradas en
  `migraciones_aplicadas`.
- **Por qué:** con una instancia por cliente, correr SQL a mano en pgAdmin escala mal. Se eligió
  SQL plano en lugar de Alembic porque el equipo ya trabaja con SQL.
- **Reglas:**
  - En una base nueva, `create_all` crea las tablas al día y las migraciones solo se registran,
    sin ejecutarse.
  - Una migración aplicada no se edita.
  - Si una falla, el backend no arranca y en Coolify sigue andando el contenedor anterior.
- **Tablas nuevas:** alcanza con el modelo, porque `create_all` las crea también en bases
  existentes. Las migraciones son para columnas, índices, restricciones y datos.

### 2. Varios procesos de API (`WEB_CONCURRENCY`, 2 por defecto)
- **Qué:** uvicorn con N procesos.
- **Por qué:** una consulta pesada (BI, reportes) ya no frena a las cajas.
- **Requisito:** nada de estado en la memoria del proceso. La cotización manual y los intentos de
  login van a PostgreSQL (`ajustes_sistema`, `intentos_login_fallidos`).
- **Arranque:** usa un `pg_advisory_lock`. Sin él, 15 de cada 20 arranques fallaban porque los
  procesos creaban tablas e índices al mismo tiempo.
- **Por qué PostgreSQL y no Redis:** no suma contenedores y la cotización sobrevive a los deploys.
  Redis queda para caché y colas, si hace falta.

### 3. Reportes grandes en un proceso aparte
- **Qué:** los PDF y Excel de más de 1.000 filas se arman en un proceso nuevo (`spawn`), que
  importa solo `archivos_reporte.py` y termina al devolver el archivo. Los chicos se arman en el
  mismo proceso.
- **Por qué:** en un hilo competían por el GIL y las cajas tardaban más de 1 s. Un proceso
  reutilizado se quedaba con 155 MB.
- **Costo:** crear el proceso suma ~0,4 a 1 s a los reportes grandes.

### 4. Permisos por ruta: una tabla, la misma regla que el frontend
- **Qué:** `backend/permisos_rutas.py` asigna a cada ruta los permisos de las pantallas que la usan.
- **Por qué:** se cierra el acceso directo a la API sin cambiar lo que puede hacer cada rol.
- **Control:** una ruta nueva sin entrada responde 403 y hace fallar una prueba.
- **Pendiente:** los permisos por acción (crear, editar, borrar) son una decisión aparte, porque
  cambian lo que puede hacer cada rol.

### 5. IVA por producto, copiado en cada ítem
- **Qué:** `tasa_iva` (10, 5 o 0) en el producto, y una copia en `venta_items` y
  `presupuesto_items` al momento de cargar el ítem.
- **Por qué:** cambiar la tasa de un producto no altera ventas ya hechas.
- **Cálculo:** está en `iva.py`. Con todo al 10 % da exactamente lo de antes.

### 6. Eventos para el CRM: outbox escrito por un listener de la sesión
- **Qué:** un `after_flush` de SQLAlchemy detecta los cambios y escribe en `eventos_integracion`
  dentro de la misma transacción.
- **Por qué:**
  - Ninguna ruta, actual o futura, se olvida de emitir.
  - Si el cambio se deshace, el evento también.
  - No hace falta un broker.
- **Retraso de 5 segundos:** se entregan con ese margen para no saltear transacciones que
  confirman fuera de orden. El consumidor deduplica por id.

### 7. Tokens de servicio con scopes; el ERP pone el techo
- **Qué:** tokens `ecs_…`, de los que solo se guarda el hash. Perfiles `crm-interno` y `crm-bot`.
- **Por qué:** el bot no puede ver clientes ni ventas aunque el CRM fuera comprometido.
- **Con token de usuario:** cada scope se traduce a permisos del ERP.
- **Pedidos:** van con `Idempotency-Key`, y la venta y el pedido se guardan en una sola
  transacción.

## Glosario

| Término | Significado en el sistema |
|---|---|
| **Venta BORRADOR** | Venta recién armada en la caja, sin descontar stock. Pasa a CONFIRMADA al cobrar. |
| **Venta PENDIENTE** | Venta guardada para confirmar después (presupuesto convertido o pedido del CRM). No descuenta stock ni valida crédito hasta que se confirma. |
| **Venta CONFIRMADA / ANULADA** | Confirmada: descontó stock (FIFO) y, si es a crédito, generó la deuda. Anulada: se revirtió. |
| **Boleta** | Comprobante interno de la venta (ticket de 75 mm). No es fiscal. |
| **Factura** | Comprobante fiscal de una venta, para clientes con RUC. Hoy es impresa; con SIFEN pasa a ser electrónica. |
| **Factura grupal** | Una factura que engloba varias boletas de un mismo cliente. |
| **Presupuesto** | Cotización con precios del momento. No toca stock. |
| **Tanda** | Entrada de stock con su costo. El FIFO consume las tandas más viejas primero; el aging mide cuánto hace que entró cada una. |
| **Alerta mínima** | Umbral de stock por almacén. Lo usan las alertas y la disponibilidad que informa el bot (D7). |
| **Pedido (integración)** | Lo que el CRM o el bot piden por la API. Se convierte en una venta PENDIENTE. |
| **Token de servicio / scope** | Credencial de un sistema (no de una persona) y cada permiso que tiene en la API de integración. |
| **Evento (outbox)** | Registro de un cambio del ERP que el CRM lee en orden con un cursor. |
| **Módulos** | Partes opcionales de cada instancia (`MODULOS=fe,crm,crm_ia,crm_ads`). |
| **SIFEN / DE / KuDE / CDC** | Sistema de facturación electrónica de la DNIT; documento electrónico; su representación impresa; su código de control. Llegan en la Fase 2. |
| **Timbrado / CSC** | Autorización de la DNIT para emitir, y código de seguridad del contribuyente para SIFEN. |
