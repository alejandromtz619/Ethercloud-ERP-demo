# Migraciones

Archivos `NNNN_nombre.sql` que el backend aplica solos al arrancar, en orden, y registra en
`migraciones_aplicadas`. Variantes por base: `NNNN_nombre.postgresql.sql` / `NNNN_nombre.sqlite.sql`.
Una migración aplicada no se edita: los cambios van en una nueva. Detalle en `../migraciones.py`.
