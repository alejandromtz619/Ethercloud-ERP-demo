"""Configuración de la facturación electrónica, por variables de entorno (una instancia por cliente)."""
import os

# API key del cliente en SIFEN SIS. Es un secreto: va en las variables de Coolify, nunca en la base.
# El ambiente (SANDBOX, HOMOLOGACION, PRODUCCION) lo define la key.
SIFENSIS_API_KEY = os.environ.get("SIFENSIS_API_KEY", "").strip()
SIFENSIS_URL = os.environ.get("SIFENSIS_URL", "https://api.sifensis.guaratec.com").rstrip("/")

# Desde dónde emite esta instancia. Establecimiento vacío = el primero configurado en el proveedor.
# El punto de expedición lo elige el ERP: uno distinto por sistema que emita con el mismo RUC.
SIFEN_ESTABLECIMIENTO = os.environ.get("SIFEN_ESTABLECIMIENTO", "").strip()
SIFEN_PUNTO = os.environ.get("SIFEN_PUNTO", "001").strip().zfill(3)

# Plazo que se informa en las facturas a crédito
SIFEN_PLAZO_CREDITO = os.environ.get("SIFEN_PLAZO_CREDITO", "30 días").strip()

# Seguimiento en segundo plano de los documentos en camino (el proveedor no tiene webhooks)
SEGUNDOS_SEGUIMIENTO = int(os.environ.get("SIFEN_SEGUNDOS_SEGUIMIENTO", "20"))
CONSULTAS_POR_VUELTA = 20   # el proveedor permite 60 peticiones por minuto en total
