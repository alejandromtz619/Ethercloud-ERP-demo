"""
Facturación electrónica (SIFEN) con un proveedor: SIFEN SIS (Guaratec). Módulo "fe" de MODULOS.

Qué hace el proveedor y qué hace el ERP
- El proveedor arma el XML, lo firma con el certificado del cliente, calcula el CDC, lo envía a
  SIFEN y genera el KuDE (PDF). Los datos del emisor (RUC, timbrado, establecimientos, certificado,
  CSC) se cargan en su portal y no se mandan en cada documento.
- El ERP arma el contenido del documento desde la venta (constructor.py), lleva la numeración
  (numerador.py) y guarda cada documento con su estado (models.DocumentoFiscal).

Piezas
- puerto.py     interfaz EmisorFiscal y errores; el resto del ERP sólo conoce esto.
- sifensis.py   adaptador de SIFEN SIS (httpx, reintentos con Retry-After).
- falso.py      emisor en memoria para las pruebas.
- servicio.py   emitir (validar → numerar → enviar), reintentar, reemitir y seguir estados.
- rutas.py      /api/fiscal (estado de la conexión, emitir la factura de una venta, KuDE).

Por qué se valida antes de numerar: el proveedor tiene /de/validar, que no consume números. Así
un dato mal cargado (un RUC equivocado) no deja huecos en la numeración.
"""
