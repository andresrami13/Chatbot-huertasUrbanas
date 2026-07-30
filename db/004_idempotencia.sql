-- =====================================================================
-- 004 — Idempotencia del webhook (ADR-0005, puntos abiertos 2, 3 y 4)
--
-- Sustituye al conjunto en memoria del despachador, que tenía tres
-- defectos: se perdía en cada reinicio, se vaciaba entero al llegar al
-- límite —olvidando también los mensajes vistos hace segundos— y marcaba
-- el mensaje como visto ANTES de procesarlo, así que un fallo a mitad
-- hacía que el reintento de Meta se descartara como duplicado y el
-- mensaje se perdiera en silencio.
--
-- Dos estados, que es lo que el ADR exige:
--
--   recibido  — se tomó el mensaje y se está procesando.
--   procesado — terminó correctamente. Solo entonces es un duplicado.
--
-- POR QUÉ ESTA TABLA NO ROMPE LA COMPUERTA DE CONSENTIMIENTO
--
-- La fila se crea al recibir el mensaje, antes de saber si quien escribe
-- autorizó el tratamiento, así que el CU1 obliga a que no contenga dato
-- personal alguno. Se cumple de dos formas:
--
--   1. Se guarda el HMAC-SHA256 del wamid, no el wamid. El wamid lleva
--      dentro el número de teléfono del remitente en ASCII, recuperable
--      con un base64 -d, así que una tabla de wamid en claro sería una
--      tabla de teléfonos. La huella no es reversible.
--   2. No hay usuario_id ni ninguna columna que relacione la fila con una
--      persona. Es la única tabla del sistema, junto con `barrio`, sin
--      dueño, y es deliberado.
--
-- Idempotente: puede reejecutarse sin duplicar nada.
-- =====================================================================

create table if not exists public.idempotencia_webhook (
    -- HMAC-SHA256 hex del wamid (`huella_wamid`). Misma forma que
    -- usuario.telefono_hash y mismo pepper, con etiqueta de dominio
    -- distinta para que los dos espacios no se solapen.
    wamid_huella text primary key
                 check (wamid_huella ~ '^[0-9a-f]{64}$'),

    estado       text not null default 'recibido'
                 check (estado in ('recibido', 'procesado')),

    -- Marca el comienzo del plazo: si sigue en 'recibido' pasado el plazo,
    -- el intento anterior murió y el mensaje se puede volver a tomar.
    recibido_en  timestamptz not null default now(),
    procesado_en timestamptz
);

-- Para el descarte por antigüedad. Sin este índice la limpieza recorrería
-- la tabla entera.
create index if not exists ix_idempotencia_recibido
    on public.idempotencia_webhook (recibido_en);

comment on table public.idempotencia_webhook is
    'Control de duplicados del webhook por huella del wamid. Sin relación '
    'con ninguna usuaria: se escribe antes de la compuerta del CU1.';
comment on column public.idempotencia_webhook.estado is
    'recibido = en proceso o intento fallido; procesado = terminado bien. '
    'Solo procesado hace que un reintento sea un duplicado.';


-- ---------------------------------------------------------------------
-- RLS, con el mismo criterio de 003: activo y sin políticas permisivas.
--
-- Aquí importa menos que en el resto —la tabla no tiene datos
-- personales— pero dejarla fuera crearía la única tabla sin RLS del
-- esquema, y eso parecería un olvido en la auditoría de la Fase 7.
-- ---------------------------------------------------------------------
alter table public.idempotencia_webhook enable row level security;

revoke all on public.idempotencia_webhook from anon, authenticated;


-- ---------------------------------------------------------------------
-- Diagnóstico: mensajes que se tomaron y nunca terminaron.
--
-- Es lo que el ADR-0005 no tenía. Antes, un mensaje perdido por un
-- redeploy a mitad de procesamiento no dejaba rastro; ahora queda una
-- fila en 'recibido' que esta consulta encuentra.
-- ---------------------------------------------------------------------
-- select wamid_huella, recibido_en, now() - recibido_en as antiguedad
--   from public.idempotencia_webhook
--  where estado = 'recibido'
--    and recibido_en < now() - interval '10 minutes'
--  order by recibido_en;
