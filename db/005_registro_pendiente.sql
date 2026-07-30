-- =====================================================================
-- 005 — Borrador de registro pendiente de confirmación (CU3, ADR-0008)
--
-- El CU3 obliga a mostrar lo extraído y persistir solo tras la
-- confirmación de la usuaria (CLAUDE.md §4.7). Entre el resumen y el
-- botón hay DOS mensajes de WhatsApp distintos, y la respuesta de un
-- botón solo trae su identificador: no hay forma de que traiga los datos.
-- Así que lo extraído tiene que esperar en alguna parte.
--
-- Por qué en la base y no en memoria: un redeploy de Railway borraría el
-- borrador y la usuaria pulsaría [Sí, guardar] para que no pasara nada.
-- Es el mismo defecto que el ADR-0005 acaba de quitar de la idempotencia,
-- y aquí sería peor, porque el fallo lo ve ella.
--
-- ESTO NO CONTRADICE "confirmar antes de guardar" (ADR-0008). El borrador
-- no es el registro: no aparece en el CU4, no entra al RAG, no se
-- comparte con nadie y caduca. Lo que la usuaria autoriza al confirmar es
-- la creación de su fila en `huerta`, y eso sigue ocurriendo solo
-- entonces.
--
-- Idempotente: puede reejecutarse sin duplicar nada.
-- =====================================================================

create table if not exists public.registro_pendiente (
    -- Clave primaria y no solo foránea: una usuaria tiene como máximo un
    -- borrador a la vez. Si cuenta algo nuevo antes de confirmar, el
    -- borrador se actualiza; no se acumulan registros a medias que luego
    -- no se sabría cuál confirma.
    usuario_id uuid primary key
               references public.usuario(id) on delete cascade,

    -- La extracción serializada: nombre_huerta, barrio y cultivos. Solo
    -- información agronómica, que es compartible y va sin cifrar como el
    -- resto (Fase 3, §5.2). Ningún dato personal entra aquí.
    --
    -- jsonb y no columnas: la forma de lo extraído la fija el prompt y
    -- cambiará durante la calibración de la Fase 7. Una migración por cada
    -- ajuste del extractor no se sostiene, y este dato es efímero.
    datos      jsonb not null,

    creado_en  timestamptz not null default now()
);

-- Para el descarte por antigüedad de los borradores abandonados.
create index if not exists ix_registro_pendiente_creado
    on public.registro_pendiente (creado_en);

comment on table public.registro_pendiente is
    'Extracción a la espera de confirmación (CU3). No es un registro: '
    'caduca, no se comparte y no entra al RAG. ADR-0008.';


-- ---------------------------------------------------------------------
-- RLS con el mismo criterio de 003: activo y sin políticas permisivas.
-- ---------------------------------------------------------------------
alter table public.registro_pendiente enable row level security;

revoke all on public.registro_pendiente from anon, authenticated;
