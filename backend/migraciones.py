"""
Migraciones de la base: archivos SQL numerados en backend/migraciones/ que el backend aplica solos al
arrancar, en orden, y registra en la tabla migraciones_aplicadas. Reemplaza correr SQL a mano en
pgAdmin en cada instancia (decisión D10 del plan).

    migraciones/0001_campos_fiscales.sql             PostgreSQL y SQLite
    migraciones/0002_algo.postgresql.sql             sólo PostgreSQL ...
    migraciones/0002_algo.sqlite.sql                 ... y su versión para SQLite (pruebas, desarrollo)

Reglas:
- Una migración aplicada no se edita: los cambios van en una migración nueva. Si el archivo cambia,
  se avisa en el log y no se vuelve a correr.
- Cada migración corre en su propia transacción. Si falla, el backend no arranca (el código nuevo
  necesitaría esos cambios) y en Coolify queda andando el contenedor anterior.
- create_all() sigue creando las tablas que falten en una instalación nueva; las migraciones
  agregan columnas, índices y datos, y conviene escribirlas idempotentes (IF NOT EXISTS).
- server.py las corre dentro del candado de arranque: con varios procesos de API, una sola vez.
"""
import hashlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

DIRECTORIO = Path(os.environ.get("MIGRACIONES_DIR", Path(__file__).parent / "migraciones"))
_NOMBRE = re.compile(r"^(\d{4})_([\w-]+?)(?:\.(postgresql|sqlite))?\.sql$")


class ErrorDeMigracion(RuntimeError):
    pass


@dataclass(frozen=True)
class Migracion:
    version: int
    nombre: str
    ruta: Path

    @property
    def sql(self) -> str:
        return self.ruta.read_text(encoding="utf-8")

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def pendientes_en_disco(dialecto: str, directorio: Path = None) -> list:
    """Migraciones para este dialecto, ordenadas. Un archivo .postgresql/.sqlite reemplaza al genérico."""
    directorio = directorio or DIRECTORIO
    candidatas = {}  # versión -> {"generica": [...], "dialecto": [...]}
    for ruta in sorted(directorio.glob("*.sql")) if directorio.is_dir() else []:
        m = _NOMBRE.match(ruta.name)
        if not m:
            raise ErrorDeMigracion(f"Nombre de migración inválido: {ruta.name} (se espera 0001_nombre.sql)")
        version, nombre, solo_para = int(m.group(1)), m.group(2), m.group(3)
        if solo_para and solo_para != dialecto:
            continue
        tipo = "dialecto" if solo_para else "generica"
        candidatas.setdefault(version, {"generica": [], "dialecto": []})[tipo].append(Migracion(version, nombre, ruta))
    elegidas = []
    for version, tipos in sorted(candidatas.items()):
        if len(tipos["generica"]) > 1 or len(tipos["dialecto"]) > 1:
            nombres = [m.ruta.name for m in tipos["generica"] + tipos["dialecto"]]
            raise ErrorDeMigracion(f"Más de una migración con la versión {version:04d}: {nombres}")
        elegidas.append((tipos["dialecto"] or tipos["generica"])[0])  # la del dialecto gana
    return elegidas


async def aplicar_migraciones(engine: AsyncEngine, directorio: Path = None) -> list:
    """Aplica las migraciones pendientes. Devuelve las versiones aplicadas."""
    dialecto = engine.dialect.name
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS migraciones_aplicadas ("
            " version INTEGER PRIMARY KEY, nombre VARCHAR(200) NOT NULL,"
            " checksum VARCHAR(64) NOT NULL, aplicada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        aplicadas = {v: c for v, c in (await conn.execute(
            text("SELECT version, checksum FROM migraciones_aplicadas"))).all()}

    nuevas = []
    for mig in pendientes_en_disco(dialecto, directorio):
        if mig.version in aplicadas:
            if aplicadas[mig.version] != mig.checksum:
                logger.error(f"La migración {mig.ruta.name} cambió después de aplicada; no se vuelve a "
                             f"correr. Los cambios van en una migración nueva.")
            continue
        logger.info(f"Aplicando migración {mig.ruta.name}")
        try:
            await _ejecutar(engine, mig)
        except Exception as e:
            raise ErrorDeMigracion(f"Falló la migración {mig.ruta.name}: {e}") from e
        nuevas.append(mig.version)
    return nuevas


async def _ejecutar(engine: AsyncEngine, mig: Migracion) -> None:
    """Corre el archivo entero (varias sentencias) y lo registra, en una transacción."""
    registro = ("INSERT INTO migraciones_aplicadas (version, nombre, checksum) VALUES ", (mig.version, mig.nombre, mig.checksum))
    async with engine.connect() as conn:
        crudo = (await conn.get_raw_connection()).driver_connection
        if engine.dialect.name == "postgresql":  # asyncpg
            async with crudo.transaction():
                await crudo.execute(mig.sql)
                await crudo.execute(registro[0] + "($1, $2, $3)", *registro[1])
        else:  # aiosqlite: executescript no admite transacción externa; se envuelve a mano
            try:
                await crudo.executescript(f"BEGIN;\n{mig.sql}\n;\n" + registro[0] +
                                          f"({mig.version}, '{mig.nombre}', '{mig.checksum}');\nCOMMIT;")
            except Exception:
                await crudo.rollback()
                raise
