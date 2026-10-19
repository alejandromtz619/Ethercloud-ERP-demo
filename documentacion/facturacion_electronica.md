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

**Cuenta de SIFEN SIS** (Configuración, con `sistema.integraciones`): estado de la cuenta (lista para
emitir, avisos, vencimiento del certificado, documentos del período) con cualquier key; y, con una key
**"Emisión + configuración"**, desde el ERP: diseño y logo del KuDE con vista previa (A4 y ticket),
certificado digital (.p12 con su contraseña, que el ERP no guarda), envío del KuDE por correo (con correo de
prueba) y timbrado por ambiente. Cada cambio queda en el historial de Configuración. Lo demás (CSC,
establecimientos, actividades, SMTP propio, plantillas de correo) se carga en el portal de SIFEN SIS.

## Cómo se emite

**Desde las pantallas:** Historial de ventas › Imprimir › **Factura electrónica** (emitir, ver el estado,
imprimir el KuDE en ticket de 80 mm o A4, reintentar). Facturas › Emitidas › **Electrónica** para una
factura agrupada (una factura con varias boletas; "Pagos varios" si se pagaron de formas distintas). En
el historial, cada venta facturada muestra su estado. Una venta incluida en una factura agrupada no se
factura sola.

Por la API:

1. `POST /api/fiscal/ventas/{id}/factura` (venta confirmada; cuerpo opcional
   `{"cheque": {"numero", "banco"}}` si se pagó con cheque) o `POST /api/fiscal/facturas-grupales/{id}/factura`.
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

En la ficha del cliente (sección **Factura electrónica**, sólo con el módulo `fe`) se cargan el tipo de
contribuyente y de operación (si no, se deducen: RUC de 8 dígitos que empieza con 80 = jurídica; con RUC
= B2B) y el domicilio con los catálogos de SIFEN (departamento, distrito, ciudad, número de casa). Con
dirección y domicilio completo, la factura lleva el domicilio; si falta algo, sale sin él (SIFEN rechaza
una dirección sin departamento, distrito y ciudad). Los catálogos están en `backend/fiscal/catalogos.json`.

Cada producto tiene su **unidad de medida** de SIFEN (77 = unidad por defecto; kg, litro, metro...).

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

- 2.3: cancelación, inutilización y nota de crédito al anular una venta facturada.
- 2.4: homologación con un cliente piloto (certificado, timbrado y CSC de prueba).
