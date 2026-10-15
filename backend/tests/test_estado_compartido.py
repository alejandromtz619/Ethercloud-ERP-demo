"""
Estado que antes vivía en la memoria de un proceso y ahora está en la base, para que lo vean
todos los procesos de la API (WEB_CONCURRENCY > 1) y sobreviva a reinicios.

    pytest backend/tests/test_estado_compartido.py
"""
from datetime import datetime, timedelta, timezone

import server
from models import AjusteSistema, IntentoLoginFallido


def _en_la_base(client, fn):
    async def correr():
        async with server.async_session_maker() as db:
            return await fn(db)
    return client.portal.call(correr)


def test_cotizacion_manual_queda_en_la_base(client, admin):
    r = client.post("/api/cotizacion/manual", headers=admin, json={"usd_pyg": 7310.5, "brl_pyg": 1355, "manual": True})
    assert r.status_code == 200, r.text
    cot = client.get("/api/cotizacion", headers=admin).json()
    assert (float(cot["usd_pyg"]), float(cot["brl_pyg"]), cot["manual"]) == (7310.5, 1355.0, True)

    async def leer(db):
        return (await db.get(AjusteSistema, server.CLAVE_COTIZACION_MANUAL)).valor
    assert _en_la_base(client, leer)["usd_pyg"] == 7310.5

    assert client.post("/api/cotizacion/auto", headers=admin).status_code == 200
    guardada = _en_la_base(client, leer)
    assert guardada["manual"] is False and guardada["usd_pyg"] == 7310.5  # conserva los valores


def test_login_cuenta_solo_fallos_recientes(client):
    email = "nadie-reciente@test.com"
    viejo = datetime.now(timezone.utc) - timedelta(minutes=16)

    async def fallos_viejos(db):
        db.add_all([IntentoLoginFallido(clave=email, creado_en=viejo) for _ in range(5)])
        await db.commit()
    _en_la_base(client, fallos_viejos)
    # Cinco fallos de hace más de 15 minutos no bloquean
    assert client.post("/api/auth/login", json={"email": email, "password": "x"}).status_code == 401

    async def cuantos(db):
        return len((await db.execute(server.select(IntentoLoginFallido).where(
            IntentoLoginFallido.clave == email))).scalars().all())
    assert _en_la_base(client, cuantos) == 1  # los vencidos se borraron al registrar el nuevo
