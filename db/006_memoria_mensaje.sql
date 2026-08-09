-- =====================================================================
-- 006 — El `wamid` sale de `mensaje` (ADR-0012)
--
-- `mensaje` se declaró en 001 con `wamid text unique`, en claro. Era
-- anterior al hallazgo del 30/07/2026: el wamid lleva dentro el número de
-- teléfono del remitente en ASCII, recuperable con un `base64 -d`. Una
-- columna de wamid en claro es una columna de teléfonos, y aquí sería
-- peor que en la bitácora, porque sería permanente y una fila por
-- mensaje.
--
-- Hasta hoy era inocuo: nada escribía en `mensaje`. Deja de serlo ahora,
-- porque `mensaje` es la memoria del agente y empieza a llenarse.
--
-- Se sustituye por la huella, exactamente igual que en
-- `idempotencia_webhook.wamid_huella` (004): mismo HMAC-SHA256 con el
-- pepper, misma etiqueta de dominio, misma forma. La comparación exacta
-- que hace falta —descartar una fila repetida— funciona igual sobre la
-- huella.
--
-- POR QUÉ NULABLE Y POR QUÉ ÍNDICE ÚNICO
--
-- Nulable porque no todo mensaje tiene wamid: si el envío a WhatsApp
-- falla, el cliente no devuelve ninguno y la respuesta se registra igual.
-- En PostgreSQL varios nulos no chocan entre sí bajo un índice único, así
-- que la restricción sigue valiendo para las filas que sí lo tienen.
--
-- Índice único y no `constraint ... unique` para poder escribir
-- `if not exists` y que la migración se pueda reejecutar.
--
-- CUIDADO al escribir en esta tabla: el insert tiene que llevar
-- `on conflict do nothing`. La garantía del ADR-0005 es *al menos una
-- vez*; si el proceso muere entre el final del trabajo y el marcado, Meta
-- reintenta y el mensaje se reprocesa. Sin esa cláusula el segundo insert
-- chocaría con este índice y tumbaría el reintento, que es justo la rama
-- que el ADR-0005 existe para proteger.
--
-- El RLS ya lo activó 003 sobre esta tabla; no hay que repetirlo.
--
-- Idempotente: puede reejecutarse sin duplicar nada.
-- =====================================================================

alter table public.mensaje drop column if exists wamid;

alter table public.mensaje
    add column if not exists huella_wamid text
        check (huella_wamid ~ '^[0-9a-f]{64}$');

create unique index if not exists ux_mensaje_huella_wamid
    on public.mensaje (huella_wamid);


-- ---------------------------------------------------------------------
-- Comentarios
--
-- Los de 001 decían además que la idempotencia del webhook "sigue en
-- memoria por ahora". Dejó de ser cierto el 30/07/2026: vive en
-- `idempotencia_webhook` (004). Se corrigen aquí.
-- ---------------------------------------------------------------------
comment on table public.mensaje is
    'Memoria de conversación del agente: los últimos N mensajes de cada '
    'usuaria (CLAUDE.md §8). Solo se escribe después de la compuerta de '
    'consentimiento, así que toda fila pertenece a alguien que autorizó. '
    'ADR-0012.';

comment on column public.mensaje.contenido is
    'Texto de la conversación, SIN CIFRAR (Fase 3, §5.2 solo obliga a '
    'cifrar el nombre). Es texto libre: puede contener lo personal que la '
    'usuaria decida contar. Límite declarado en el ADR-0012.';

comment on column public.mensaje.tipo is
    'Tipo de la entrada ANTES de normalizar. Para el análisis de la Fase '
    '7 —cuánta voz se usa—, no para el prompt del agente.';

comment on column public.mensaje.huella_wamid is
    'HMAC-SHA256 hex del wamid, nunca el wamid. Del mensaje entrante en '
    'las filas de la usuaria y del saliente en las del asistente; nulo si '
    'el envío falló. Evita duplicar la memoria cuando Meta reintenta.';


-- ---------------------------------------------------------------------
-- Verificación
--
-- No debe quedar ninguna columna `wamid` en el esquema.
-- ---------------------------------------------------------------------
-- select table_name, column_name
--   from information_schema.columns
--  where table_schema = 'public'
--    and column_name like '%wamid%'
--  order by table_name;
