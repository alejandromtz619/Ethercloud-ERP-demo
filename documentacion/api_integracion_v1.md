# API de integración v1

Contrato entre el ERP y los servicios que lo usan: el CRM y su bot. Código en
`backend/integracion.py`, pruebas en `backend/tests/test_integracion.py`. El esquema OpenAPI
completo está en `GET /openapi.json` de cada instancia, con el tag `integracion`.

Base: `https://<backend de la instancia>/api/integracion/v1`

## Autenticación

`Authorization: Bearer <token>`, con una de estas dos credenciales:

| Credencial | Cuándo | Permisos |
|---|---|---|
| **Token de servicio** (`ecs_…`) | Procesos en segundo plano del CRM y el bot | Los scopes de su perfil (abajo) |
| **Token de usuario** (el JWT que devuelve `POST /api/auth/login`) | Una persona usando el CRM | Cada scope se traduce a permisos del ERP; el ERP le aplica los de esa persona |

Los tokens de servicio los crea un administrador (permiso `sistema.configurar`):

- `POST /api/integracion/tokens` con `{"nombre": "...", "perfil": "crm-interno" | "crm-bot", "usuario_id": <opcional>}`.
  Responde el token **una sola vez**: después solo se puede revocar y crear otro.
- `GET /api/integracion/tokens` lista los tokens (prefijo, scopes, último uso), sin el token.
- `DELETE /api/integracion/tokens/{id}` revoca el token.

`usuario_id` es el usuario a cuyo nombre quedan los pedidos que crea el token (por ejemplo, un
usuario "Bot WhatsApp"). Un token sin usuario no puede crear pedidos.

Para que el CRM valide el login de una persona: `GET /api/auth/me` con su JWT. Devuelve el usuario,
`permisos` (lista de claves) y `es_admin`.

### Scopes y perfiles

| Scope | `crm-interno` | `crm-bot` | Con token de usuario, alcanza con alguno de estos permisos |
|---|:-:|:-:|---|
| `catalogo.publico` | ✓ | ✓ | (cualquier usuario) |
| `pedidos.crear` | ✓ | ✓ | `ventas.crear`, `presupuestos.crear` |
| `pedidos.leer` | ✓ | ✓ (solo los suyos) | `ventas.crear`, `ventas.ver`, `ventas.ver_historial`, `presupuestos.ver` |
| `clientes.leer` | ✓ | | `clientes.ver` |
| `clientes.escribir` | ✓ | | `clientes.crear`, `clientes.editar` |
| `metricas.leer` | ✓ | | `bi.ver`, `dashboard.ver` |
| `eventos.leer` | ✓ | | `sistema.configurar` |

El ERP pone el límite: aunque el CRM fuera comprometido, el token del bot no puede leer clientes,
ventas, costos ni eventos.

### Errores

`401` si falta el token o no es válido. `403` si falta el scope. `404` si el recurso no existe **o
es de otra empresa**. `400` y `409` según la ruta. `422` si el cuerpo no tiene el formato esperado.

## Rutas

### `GET /yo`
Devuelve con qué credencial se está llamando: `{tipo: "servicio"|"usuario", empresa_id, nombre, scopes}`.

### Catálogo (`catalogo.publico`)

**`GET /catalogo/productos?q=&categoria_id=&limit=20&offset=0`**: productos activos. `q` busca
en el nombre, el código de barras y la marca.

```json
{"items": [{"id": 12, "nombre": "Pintura Látex Blanco 4 L", "descripcion": null,
            "categoria": "Pinturas", "marca": "Acme", "precio_venta": 85000.0,
            "disponibilidad": {"estado": "ultimas_unidades", "cantidad": 3},
            "imagen_url": "/api/uploads/productos/12.jpg"}],
 "total": 1, "limit": 20, "offset": 0}
```

**`GET /catalogo/productos/{id}`**: devuelve un producto con el mismo formato.

La **disponibilidad** (decisión D7) la calcula el ERP. El umbral es la alerta mínima más baja entre
los almacenes del producto o, si no tiene alerta, el stock mínimo del producto:

| `estado` | Cuándo | `cantidad` |
|---|---|---|
| `sin_stock` | stock ≤ 0 | `null` |
| `ultimas_unidades` | stock ≤ umbral | la cantidad exacta |
| `disponible` | stock > umbral | `null` (no se revela) |

Nunca devuelve costos, proveedores ni márgenes.

### Clientes

**`GET /clientes?telefono=…`** o **`?documento=…`** (`clientes.leer`): devuelve
`{"items": [cliente…]}`.
- Teléfono: se comparan los últimos 9 dígitos, así que `0981 555-123`, `595981555123` y
  `+595 981 555 123` son el mismo número.
- Documento: el RUC con o sin dígito verificador, o la cédula.

Cada cliente tiene esta forma:
`{id, nombre, apellido, ruc, cedula, telefono, email, direccion, activo}`.

**`POST /clientes`** (`clientes.escribir`) con `{nombre, apellido?, telefono?, ruc?, cedula?, email?, direccion?}`.
Si el RUC o la cédula ya existen, responde `409` con `{"detail": {"mensaje": ..., "cliente_id": <existente>}}`:
hay que vincular ese cliente en lugar de crear otro.

**`GET /clientes/{id}/resumen-360`** (`clientes.leer`): devuelve
`{cliente, compras: {total, cantidad, ticket_promedio, ultima_compra}, productos_mas_comprados[5],
ventas_recientes[5], presupuestos_recientes[5], entregas_pendientes, credito?}`.
`credito` (`{limite, usado, disponible}`) solo aparece con token de servicio o si el usuario tiene
`clientes.ver_creditos`.

### Métricas (`metricas.leer`)

**`GET /metricas/ventas?desde=AAAA-MM-DD&hasta=AAAA-MM-DD&por=dia|semana|mes&cliente_id=`**: ventas
confirmadas en hora de Paraguay. Las semanas empiezan en lunes y el rango admite hasta 366 días.
```json
{"por": "dia", "desde": "2026-10-01", "hasta": "2026-10-17",
 "series": [{"periodo": "2026-10-01", "total": 1250000.0, "cantidad": 14, "ticket_promedio": 89286}]}
```

### Pedidos

**`POST /pedidos`** (`pedidos.crear`). Requiere el encabezado **`Idempotency-Key`** (hasta 100 caracteres).
```json
{"cliente_id": 51, "items": [{"producto_id": 12, "cantidad": 2}],
 "tipo_pago": "EFECTIVO", "es_delivery": false}
```
- Crea una **venta PENDIENTE** que confirma un vendedor desde el ERP (decisión D8, modo por defecto).
- Los precios los pone el ERP: el precio de venta actual y el descuento del cliente. El pedido no
  trae precios ni descuentos.
- `tipo_pago` admite `EFECTIVO`, `TARJETA` o `TRANSFERENCIA`. **Crédito no**: lo maneja siempre un
  vendedor.
- Idempotencia: la misma clave con el mismo pedido devuelve el mismo pedido, sin crear otra venta,
  aunque lleguen varias peticiones a la vez. La misma clave con otro contenido responde `409`.
  Conviene usar una clave por intención de compra (por ejemplo, el id del mensaje).

**`GET /pedidos/{id}`** (`pedidos.leer`): un token sin `clientes.leer` (el bot) solo ve los pedidos
creados con ese mismo token.
```json
{"pedido_id": 7, "venta_id": 302, "cliente_id": 51, "estado": "PENDIENTE",
 "tipo_pago": "EFECTIVO", "es_delivery": false,
 "items": [{"producto_id": 12, "nombre": "...", "cantidad": 2, "precio_unitario": 85000.0, "total": 170000.0}],
 "descuento": 0.0, "total": 170000.0, "creado_en": "..."}
```
`estado` es `PENDIENTE` hasta que lo confirma un vendedor. Después pasa a `CONFIRMADA` o, si se
anula, a `ANULADA`.

### Eventos (`eventos.leer`)

**`GET /eventos?desde=<cursor>&limite=100`**: eventos de la empresa con id mayor a `desde`, en orden
de id. Para seguir leyendo, se pasa como `desde` el `cursor` devuelto.
```json
{"eventos": [{"id": 981, "tipo": "venta.confirmada", "entidad_id": 302,
              "datos": {"venta_id": 302, "cliente_id": 51, "total": 170000.0,
                        "tipo_pago": "EFECTIVO", "es_delivery": false},
              "creado_en": "2026-10-17T14:03:11+00:00"}],
 "cursor": 981}
```

| `tipo` | `datos` |
|---|---|
| `venta.confirmada`, `venta.anulada` | `venta_id, cliente_id, total, tipo_pago, es_delivery` |
| `cliente.creado` | `cliente_id` |
| `cliente.actualizado` | `cliente_id, activo` |
| `presupuesto.creado` | `presupuesto_id, cliente_id` |
| `entrega.estado` | `entrega_id, venta_id, estado` |
| `stock.entrada` | `producto_id, almacen_id, cantidad` (útil para avisar "volvió a haber stock") |

Garantías:
- **Sin pérdidas.** El evento se escribe en la misma transacción que el cambio. Si el cambio se
  deshace, el evento también, y si el CRM está apagado, los eventos lo esperan.
- **Retraso de unos 5 segundos.** Dos transacciones pueden confirmarse en otro orden que el de sus
  ids, y el margen evita saltear la más lenta.
- **Al menos una vez.** El consumidor tiene que ser idempotente por `id` de evento.
- **Retención de 30 días.** Si el CRM está apagado más tiempo, tiene que resincronizar con las rutas
  de clientes y pedidos.

## Pendiente

- `GET /catalogo/recomendaciones` (lista curada del mes): falta definir dónde la carga el cliente.
- Modos de cierre de pedidos D8 "confirma el cliente" y "automático hasta un monto". Hoy todo
  pedido queda pendiente de un vendedor.
- Límite de peticiones por token, cuando el bot esté en producción.
