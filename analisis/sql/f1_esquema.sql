-- Fase 1 — reconocimiento del esquema.
--
-- Comprueba contra `information_schema` qué columnas existen de verdad, en
-- vez de fiarse de `db/001_esquema.sql`: las migraciones 006, 008 y 010
-- quitaron y renombraron columnas, y el prompt de la evaluación nombraba
-- `usuario.telefono_hash`, que ya no existe.
--
-- SOLO LECTURA.

select table_name,
       column_name,
       data_type,
       is_nullable
  from information_schema.columns
 where table_schema = 'public'
   and table_name in ('usuario', 'huerta', 'cultivo', 'mensaje',
                      'barrio', 'idempotencia_webhook',
                      'registro_pendiente', 'onboarding_pendiente',
                      'listado_comunitario_pendiente')
 order by table_name, ordinal_position;
