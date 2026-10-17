"""
Runner de migraciones SQL (migraciones.py) sobre una base SQLite aparte.

    pytest backend/tests/test_migraciones.py
"""
import asyncio
import logging

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from migraciones import ErrorDeMigracion, aplicar_migraciones, pendientes_en_disco


@pytest.fixture
def base(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'm.db').as_posix()}")
    carpeta = tmp_path / "migraciones"
    carpeta.mkdir()
    yield engine, carpeta
    asyncio.run(engine.dispose())


def _correr(coro):
    return asyncio.run(coro)


async def _filas(engine, sql):
    async with engine.connect() as conn:
        return (await conn.execute(text(sql))).all()


def test_aplica_en_orden_una_sola_vez(base):
    engine, carpeta = base
    (carpeta / "0001_tabla.sql").write_text("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT);\n"
                                            "INSERT INTO cosas (nombre) VALUES ('a');", encoding="utf-8")
    (carpeta / "0002_columna.postgresql.sql").write_text("ALTER TABLE cosas ADD COLUMN IF NOT EXISTS x INT;", encoding="utf-8")
    (carpeta / "0002_columna.sqlite.sql").write_text("ALTER TABLE cosas ADD COLUMN x INT;", encoding="utf-8")

    async def todo():
        primera = await aplicar_migraciones(engine, carpeta)
        segunda = await aplicar_migraciones(engine, carpeta)
        return primera, segunda, await _filas(engine, "SELECT version, nombre FROM migraciones_aplicadas ORDER BY version"), \
            await _filas(engine, "SELECT nombre, x FROM cosas")
    primera, segunda, registradas, cosas = _correr(todo())
    assert (primera, segunda) == ([1, 2], [])
    assert registradas == [(1, "tabla"), (2, "columna")]
    assert cosas == [("a", None)]


def test_si_falla_no_queda_nada_a_medias_y_corta(base):
    engine, carpeta = base
    (carpeta / "0001_ok.sql").write_text("CREATE TABLE a (id INTEGER);", encoding="utf-8")
    (carpeta / "0002_rota.sql").write_text("CREATE TABLE b (id INTEGER);\nINSERT INTO no_existe VALUES (1);", encoding="utf-8")
    (carpeta / "0003_despues.sql").write_text("CREATE TABLE c (id INTEGER);", encoding="utf-8")

    async def todo():
        with pytest.raises(ErrorDeMigracion, match="0002_rota"):
            await aplicar_migraciones(engine, carpeta)
        return await _filas(engine, "SELECT version FROM migraciones_aplicadas"), \
            await _filas(engine, "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('a','b','c')")
    registradas, tablas = _correr(todo())
    assert registradas == [(1,)]
    assert tablas == [("a",)]  # b se deshizo y c no se intentó


def test_archivo_cambiado_despues_de_aplicado_no_se_reaplica(base, caplog):
    engine, carpeta = base
    archivo = carpeta / "0001_tabla.sql"
    archivo.write_text("CREATE TABLE a (id INTEGER);", encoding="utf-8")
    _correr(aplicar_migraciones(engine, carpeta))
    archivo.write_text("CREATE TABLE a (id INTEGER, otra TEXT);", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        assert _correr(aplicar_migraciones(engine, carpeta)) == []
    assert "cambió después de aplicada" in caplog.text


def test_versiones_repetidas_o_nombres_invalidos(tmp_path):
    (tmp_path / "0001_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "0001_b.sql").write_text("", encoding="utf-8")
    with pytest.raises(ErrorDeMigracion, match="0001"):
        pendientes_en_disco("sqlite", tmp_path)
    (tmp_path / "0001_b.sql").unlink()
    (tmp_path / "1_mal.sql").write_text("", encoding="utf-8")
    with pytest.raises(ErrorDeMigracion, match="inválido"):
        pendientes_en_disco("sqlite", tmp_path)


def test_la_del_dialecto_reemplaza_a_la_generica(tmp_path):
    for nombre in ("0001_x.sql", "0001_x.sqlite.sql", "0002_y.postgresql.sql"):
        (tmp_path / nombre).write_text("", encoding="utf-8")
    assert [m.ruta.name for m in pendientes_en_disco("sqlite", tmp_path)] == ["0001_x.sqlite.sql"]
    assert [m.ruta.name for m in pendientes_en_disco("postgresql", tmp_path)] == ["0001_x.sql", "0002_y.postgresql.sql"]
