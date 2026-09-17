-- =====================================================================
-- 010 — La identidad de la usuaria es el BSUID, no el teléfono
--
-- `usuario.telefono_hash` pasa a llamarse `usuario.identidad_hash`. La
-- columna guarda lo mismo —un HMAC-SHA256 hexadecimal con pepper— pero
-- ya no siempre de un número: desde el ADR-0023 lo normal es que sea la
-- huella del **Business-Scoped User ID** que Meta manda en cada mensaje.
--
-- ## Por qué
--
-- Meta dejó de mandar el teléfono de quien activa su nombre de usuario
-- de WhatsApp. El 16/09/2026 se vio en la bitácora: ocho mensajes de
-- unos setenta se descartaban con `Mensaje sin remitente`, todos del
-- 15/09 en adelante y sin que hubiera cambiado una línea de código.
-- Esas personas escribían y no recibían **nada**.
--
-- El BSUID llega siempre, con nombre de usuario o sin él, así que sirve
-- de identidad para todas. Y como el sistema ya no necesita el número
-- para nada —ni para responder, que eso ahora va por `recipient`—, deja
-- de guardarse en cualquier forma, también hasheado. Es una mejora de la
-- minimización de la Fase 3, §5, y la corrección del «identidad por
-- número de celular» de las fases previas.
--
-- El nombre viejo mentiría, y esa es toda la razón de esta migración:
-- una columna que dice `telefono_hash` y guarda la huella de otra cosa
-- es una trampa para quien lea el esquema dentro de seis meses.
--
-- ## Qué NO hace
--
-- **No borra ni una fila.** Las usuarias que se registraron cuando la
-- identidad era el teléfono conservan su huella vieja, y el despachador
-- les cambia la llave sola la primera vez que escriban, mientras Meta
-- siga mandando las dos cosas (`repositorio.rellavear_identidad`). Nadie
-- tiene que volver a autorizar ni a repetir el onboarding, y no se
-- pierde ninguna huerta, ningún cultivo ni ninguna conversación — que al
-- 17/09/2026 son 9 usuarias, 7 huertas, 56 cultivos y 204 mensajes, el
-- material de la Fase 7.
--
-- El pepper **no se toca**, aunque `PHONE_HASH_PEPPER` se quede con un
-- nombre impreciso: cambiarlo es irreversible y no aporta nada.
--
-- ## Orden de aplicación, y esta vez es al revés que la 008
--
-- El código desplegado lee `telefono_hash` y el nuevo lee
-- `identidad_hash`, así que **el cambio de columna y el despliegue van
-- juntos**: entre uno y otro, cada mensaje que llegue falla y la usuaria
-- se queda sin respuesta. Es cosa de un minuto y no se pierde nada —la
-- fila de idempotencia queda en 'recibido'—, pero conviene hacerlo a una
-- hora tranquila y comprobar con `/health` que Railway ya está corriendo
-- el commit nuevo.
--
-- Idempotente: puede reejecutarse sin fallar.
-- =====================================================================

do $$
begin
    if exists (
        select 1
          from information_schema.columns
         where table_schema = 'public'
           and table_name   = 'usuario'
           and column_name  = 'telefono_hash'
    ) then
        alter table public.usuario
            rename column telefono_hash to identidad_hash;
    end if;

    -- Las dos restricciones llevan el nombre que Postgres les puso al
    -- crear la tabla, con la columna dentro. Renombrar la columna no las
    -- renombra, y el índice único viaja con su restricción.
    if exists (
        select 1 from pg_constraint
         where conrelid = 'public.usuario'::regclass
           and conname  = 'usuario_telefono_hash_key'
    ) then
        alter table public.usuario
            rename constraint usuario_telefono_hash_key
                           to usuario_identidad_hash_key;
    end if;

    if exists (
        select 1 from pg_constraint
         where conrelid = 'public.usuario'::regclass
           and conname  = 'usuario_telefono_hash_check'
    ) then
        alter table public.usuario
            rename constraint usuario_telefono_hash_check
                           to usuario_identidad_hash_check;
    end if;
end
$$;

comment on column public.usuario.identidad_hash is
    'HMAC-SHA256 hex de la identidad que manda Meta —el BSUID desde el '
    'ADR-0023— con pepper y etiqueta de dominio. Si el pepper cambia, las '
    'usuarias registradas dejan de ser reconocidas.';

comment on table public.usuario is
    'Identidad y consentimiento del líder de huerta. La existencia de la '
    'fila implica autorización otorgada (CU1, ADR-0003). Identificada por '
    'BSUID, nunca por teléfono (ADR-0023).';
