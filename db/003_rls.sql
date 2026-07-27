-- =====================================================================
-- 003 — Seguridad a nivel de fila (RLS)
--
-- Capa 2 del modelo de seguridad de la Fase 3, Tabla 3. DEFENSA EN
-- PROFUNDIDAD, NO BARRERA PRIMARIA.
--
-- Conviene ser explícito sobre lo que esto hace y lo que no, porque el
-- documento de grado lo declara así (Fase 3, §5.1):
--
--   El backend se conecta a Supabase con la clave de service role, que
--   por diseño OMITE el RLS. El sistema no abre una sesión de Supabase
--   Auth por cada líder de huerta, así que ninguna política escrita aquí
--   protege al sistema de un fallo en el código del backend.
--
--   La barrera real es la capa 1: el filtrado por usuario_id en cada
--   consulta del repositorio de datos.
--
-- Lo que sí aporta esta capa: si la clave anónima (pública) se filtrara
-- —va incrustada en cualquier cliente que la use— nadie podría leer ni
-- escribir nada a través de la API de Supabase.
--
-- Estrategia: activar RLS SIN definir políticas permisivas. En
-- PostgreSQL eso equivale a denegar todo a cualquier rol que no omita
-- el RLS. No es un olvido; es la postura deliberada.
-- =====================================================================

alter table public.usuario               enable row level security;
alter table public.huerta                enable row level security;
alter table public.cultivo               enable row level security;
alter table public.mensaje               enable row level security;
alter table public.fuente                enable row level security;
alter table public.fragmento_oficial     enable row level security;
alter table public.fragmento_comunitario enable row level security;
alter table public.barrio                enable row level security;


-- ---------------------------------------------------------------------
-- Retirada de privilegios a los roles públicos
--
-- Supabase concede privilegios a `anon` y `authenticated` por defecto en
-- el esquema public. Con RLS activo y sin políticas ya quedarían
-- bloqueados, pero retirarlos explícitamente evita que una política
-- añadida por descuido más adelante abra el acceso sin querer.
--
-- `service_role` conserva los suyos: es el rol con el que trabaja el
-- backend.
-- ---------------------------------------------------------------------
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from anon, authenticated;

-- Mismo criterio para las tablas que se creen en adelante.
alter default privileges in schema public
    revoke all on tables    from anon, authenticated;
alter default privileges in schema public
    revoke all on sequences from anon, authenticated;


-- ---------------------------------------------------------------------
-- Verificación
--
-- Debe devolver las ocho tablas con rowsecurity = true y sin políticas.
-- ---------------------------------------------------------------------
-- select c.relname                    as tabla,
--        c.relrowsecurity             as rls_activo,
--        count(p.polname)             as politicas
--   from pg_class c
--   join pg_namespace n on n.oid = c.relnamespace
--   left join pg_policy p on p.polrelid = c.oid
--  where n.nspname = 'public' and c.relkind = 'r'
--  group by c.relname, c.relrowsecurity
--  order by c.relname;
