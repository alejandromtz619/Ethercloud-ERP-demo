"""
Preparación compartida para las pruebas que corren la app en memoria (sin red):
SQLite temporal, secreto JWT efímero y endpoints de desarrollo apagados.
Las pruebas viejas que llaman a la API desplegada no usan estos fixtures.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="ethercloud-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_TMP, 'test.db').as_posix()}"
os.environ.pop("JWT_SECRET", None)
os.environ.pop("PERMITIR_ENDPOINTS_DESARROLLO", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def client():
    """App en memoria con la base sembrada (empresa 1, admin@ether.com / admin123)."""
    from fastapi.testclient import TestClient
    import server

    with TestClient(server.app) as c:
        server.PERMITIR_ENDPOINTS_DESARROLLO = True
        assert c.post("/api/seed").status_code == 200
        server.PERMITIR_ENDPOINTS_DESARROLLO = False
        yield c


@pytest.fixture(scope="session")
def admin(client):
    r = client.post("/api/auth/login", json={"email": "admin@ether.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
