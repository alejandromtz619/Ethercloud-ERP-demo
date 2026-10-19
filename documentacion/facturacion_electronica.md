# Facturación electrónica (SIFEN) — módulo `fe`

El ERP emite facturas electrónicas a través de **SIFEN SIS** (Guaratec). El proveedor firma el XML
con el certificado del cliente, calcula el CDC, lo envía a SIFEN y genera el KuDE. El ERP arma el
documento desde la venta, lleva la numeración y guarda cada documento con su estado. El código está
en `backend/fiscal/` y su diseño se explica en `backend/fiscal/__init__.py`.

## Activarlo en una instancia

1. **Coolify (backend, lo hace Ether):** `MODULOS=fe` (o `fe,crm`) y `CLAVE_CIFRADO` (32+ caracteres
   al azar, una por instancia; cifra las API keys guardadas en la base).
2. **Pantalla Sistema › Configuración › Facturación electrónica** (permiso `sistema.integraciones`):
   - API key de SIFEN SIS (se guarda cifrada y no se vuelve a mostrar; el ambiente lo define la key).
   - Punto de expedición (uno distinto por cada sistema que emita con el mismo RUC), establecimiento
     (vacío = el primero configurado en SIFEN SIS) y plazo de las ventas a crédito.
   - **Probar conexión** muestra ambiente, RUC, timbrado y establecimientos.

Al guardar una key nueva (por ejemplo, al pasar de SANDBOX a PRODUCCION) se usa desde la próxima
factura, sin reiniciar. La numeración es independiente por ambiente.

Las variables de entorno `SIFENSIS_API_KEY`, `SIFEN_PUNTO`, `SIFEN_ESTABLECIMIENTO` y
`SIFEN_PLAZO_CREDITO` siguen funcionando: si existen, ganan sobre la pantalla (que las muestra como
"fijadas en el servidor").

Los datos del emisor (RUC, timbrado, establecimientos, actividades, certificado, CSC) se cargan en el
portal de SIFEN SIS, no en el ERP.

## Cómo se emite

1. `POST /api/fiscal/ventas/{id}/factura` (venta confirmada; cuerpo opcional
   `{"cheque": {"numero", "banco"}}` si se pagó con cheque).
2. El ERP arma el documento (`fiscal/constructor.py`) y lo **valida con el proveedor sin consumir
   número**. Si hay un error de datos (RUC con DV equivocado, nombre muy corto…) responde 422 con la
   lista de errores y la numeración no se mueve.
3. Toma el número (fila de la secuencia bloqueada hasta el commit; probado con 50 emisiones a la vez en
   PostgreSQL) y guarda el documento `POR_ENVIAR` con el contenido exacto que se va a mandar.
4. Lo envía. Respuesta normal: `GENERADO`. Si la conexión se corta, queda `POR_ENVIAR` y el
   seguimiento lo reenvía: el proveedor reconoce la numeración y devuelve el mismo documento.
5. El seguimiento en segundo plano (cada 20 s, un solo proceso) consulta los `GENERADO` / `ENVIADO`
   hasta `APROBADO` o `RECHAZADO`. En SANDBOX se aprueba en unos segundos.

Un documento `RECHAZADO` o `INVALIDO` se corrige (p. ej. el RUC del cliente) y se reemite con el
**mismo número**: `POST /api/fiscal/documentos/{id}/reintentar`.

Si el número local ya está usado en el proveedor (p. ej. se restauró un respaldo viejo del ERP), el ERP
adelanta la numeración con la del proveedor y usa el siguiente libre.

## Cómo se arma el receptor

| El cliente tiene | Se informa como |
|---|---|
| RUC (con o sin DV; sin DV se calcula) | Contribuyente, B2B. RUC de 8 dígitos que empieza con 80 = persona jurídica |
| Sólo cédula | Consumidor final identificado (B2C) |
| Nada, o el RUC genérico 44444401-7 | "Sin Nombre" (innominado) |

Con dirección, SIFEN exige también número de casa, departamento, distrito y ciudad (códigos de su
catálogo). Hasta que esos datos se carguen en el cliente (etapa 2.1), la dirección no se informa.

Formas de pago: efectivo, cheque (con número y banco), tarjeta (marca "no especificada", el ERP no la
registra), transferencia; crédito como condición crédito a plazo.

## Pruebas

- `backend/tests/test_fiscal.py`: con el emisor falso (`fiscal/falso.py`), sin red.
- `backend/tests/test_fiscal_sandbox.py`: contra el SANDBOX real; la prueba carga la key por la
  pantalla de Configuración (no como variable del servidor). Sólo corre con la key en el entorno:

  ```bash
  SIFENSIS_API_KEY=gk_... SIFEN_PRUEBA_PUNTO=901 pytest backend/tests/test_fiscal_sandbox.py -s
  ```

## Pendiente (Fase 2)

- 2.1: datos fiscales del cliente (ubicación con los catálogos de SIFEN, tipo de contribuyente) y
  unidad de medida de los productos.
- 2.2: botón "Factura electrónica" en ventas, estado visible, imprimir KuDE; factura englobada.
- 2.3: cancelación, inutilización y nota de crédito al anular.
- 2.4: homologación con un cliente piloto.
