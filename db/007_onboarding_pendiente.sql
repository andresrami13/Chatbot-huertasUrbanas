-- =====================================================================
-- 007 — Onboarding en curso (ADR-0016)
--
-- El registro empieza con tres preguntas cerradas, una por mensaje:
-- nombre de pila, barrio y nombre de la huerta. Entre pregunta y
-- respuesta hay dos mensajes de WhatsApp distintos, así que el estado
-- tiene que esperar en alguna parte, por el mismo motivo que el borrador
-- del CU3 (ADR-0008).
--
-- Tabla propia y no `registro_pendiente`: aquel guarda una extracción a
-- confirmar y este guarda el punto de una conversación guiada. Mezclarlos
-- obligaría a distinguir por el contenido del jsonb cuál de los dos
-- flujos está en curso.
--
-- POR QUÉ EN LA BASE Y NO EN MEMORIA: un redeploy de Railway dejaría a la
-- usuaria contestando preguntas que el servicio ya no recuerda haber
-- hecho. Mismo razonamiento que el ADR-0008.
--
-- QUÉ NO ENTRA AQUÍ: el nombre de pila. Se persiste cifrado en
-- `usuario.nombre_usuario_cifrado` en cuanto ella lo escribe, porque la
-- fila de `usuario` ya existe desde el consentimiento. Guardarlo además
-- aquí, en claro, anularía ese cifrado. Lo que sí espera es el barrio y
-- el nombre de la huerta, que son información agronómica y van sin
-- cifrar como el resto (Fase 3, §5.2).
--
-- Idempotente: puede reejecutarse sin duplicar nada.
-- =====================================================================

create table if not exists public.onboarding_pendiente (
    -- Clave primaria y no solo foránea: un onboarding a la vez.
    usuario_id     uuid primary key
                   references public.usuario(id) on delete cascade,

    -- En qué pregunta va. Valores: 'nombre', 'barrio', 'barrio_opciones',
    -- 'huerta', 'confirmacion'.
    --
    -- Texto y no un tipo ENUM, por el mismo motivo del ADR-0002: añadir o
    -- renombrar un paso durante la calibración de la Fase 7 exigiría un
    -- ALTER TYPE y una migración.
    paso           text not null,

    -- Lo contestado que aún no se ha confirmado: barrio_codigo,
    -- nombre_huerta, los candidatos de barrio que se le ofrecieron y
    -- cuántas veces respondió "Ninguno de estos".
    --
    -- El mapa de candidatos hace falta porque la respuesta es un número:
    -- un "3" no significa nada sin saber qué tres opciones vio (ADR-0016,
    -- decisión 5).
    --
    -- jsonb y no columnas: la forma cambiará durante la calibración.
    datos          jsonb not null default '{}'::jsonb,

    creado_en      timestamptz not null default now(),
    actualizado_en timestamptz not null default now()
);

-- Para el descarte por antigüedad de los onboarding abandonados.
create index if not exists ix_onboarding_pendiente_actualizado
    on public.onboarding_pendiente (actualizado_en);

comment on table public.onboarding_pendiente is
    'Estado del onboarding de tres preguntas (ADR-0016). Caduca a las 24 '
    'horas: al volver se repiten las tres y sobrescriben lo que hubiera.';
comment on column public.onboarding_pendiente.datos is
    'Barrio y nombre de huerta pendientes, candidatos ofrecidos y conteo '
    'de "Ninguno". Sin datos personales: el nombre va cifrado en usuario.';


-- ---------------------------------------------------------------------
-- RLS con el mismo criterio de 003 y 005: activo y sin políticas
-- permisivas. Es defensa en profundidad, no la barrera principal, porque
-- el backend usa service role y la omite (Fase 3, §5.1).
-- ---------------------------------------------------------------------
alter table public.onboarding_pendiente enable row level security;

revoke all on public.onboarding_pendiente from anon, authenticated;
