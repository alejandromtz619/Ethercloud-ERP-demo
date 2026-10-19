"""Constantes técnicas de la facturación electrónica (iguales en todas las instancias).

Lo que cambia de un cliente a otro (API key de SIFEN SIS, establecimiento, punto de expedición, plazo
de crédito) NO está acá: se carga desde Sistema › Configuración (configuracion.py, claves fe.*). Las
variables de entorno SIFENSIS_API_KEY, SIFEN_ESTABLECIMIENTO, SIFEN_PUNTO y SIFEN_PLAZO_CREDITO siguen
funcionando y, si existen, ganan sobre la pantalla.
"""
import os

SIFENSIS_URL = os.environ.get("SIFENSIS_URL", "https://api.sifensis.guaratec.com").rstrip("/")

# Seguimiento en segundo plano de los documentos en camino (el proveedor no tiene webhooks)
SEGUNDOS_SEGUIMIENTO = int(os.environ.get("SIFEN_SEGUNDOS_SEGUIMIENTO", "20"))
CONSULTAS_POR_VUELTA = 20   # el proveedor permite 60 peticiones por minuto en total
