-- =====================================================================
-- 009 — Por dónde va el listado del CU4 (ADR-0021)
--
-- El CU4 ya no cuenta las otras huertas en un párrafo redactado por el
-- modelo, sino en un listado que compone el código y que sale de tres en
-- tres. Entre una tanda y la siguiente hay dos mensajes de WhatsApp
-- distintos, así que hace falta recordar por dónde iba: mismo problema
-- que el borrador del CU3 (ADR-0008) y el onboarding (ADR-0016), y misma
-- solución.
--
-- POR QUÉ EN LA BASE Y NO EN MEMORIA: un redeploy de Railway le daría
-- otra vez las tres primeras huertas a quien acababa de pedir las
-- siguientes. Es el argumento del ADR-0008, y aquí cuesta todavía menos
-- discutirlo porque la tabla es de dos columnas.
--
-- POR QUÉ NO SE GUARDAN LOS IDENTIFICADORES DE LAS HUERTAS YA MOSTRADAS:
-- se guarda un desplazamiento, no una foto. Si entre una tanda y la
-- siguiente alguien registra o actualiza una huerta, el orden cambia y
-- ella podría ver repetida una que ya vio, o saltarse una. Se acepta a
-- propósito: con las 5 a 7 huertas de la evaluación el riesgo es
-- pequeño, y guardar la lista de identificadores para evitar un repetido
-- es más maquinaria de la que el problema merece. Queda declarado en el
-- ADR-0021.
--
-- CADUCIDAD DE UNA HORA, no las 24 del borrador y el onboarding. Aquello
-- son tareas a medio terminar y conviene que sobrevivan a que ella deje
-- el teléfono; esto es la posición de una conversación en curso. Pasadas
-- dos días, "cuénteme de las otras huertas" quiere decir empezar de
-- nuevo, no seguir donde lo dejó hace dos días.
--
-- Idempotente: puede reejecutarse sin duplicar nada.
-- =====================================================================

create table if not exists public.listado_comunitario_pendiente (
    -- Clave primaria y no solo foránea: un recorrido a la vez por usuaria.
    usuario_id     uuid primary key
                   references public.usuario(id) on delete cascade,

    -- Cuántas huertas ya se le mostraron. Es el `offset` de la siguiente
    -- consulta, no un número de página: así el tamaño de la tanda se
    -- puede calibrar en la Fase 7 sin que un cursor viejo apunte a otro
    -- sitio del que apuntaba al escribirse.
    desplazamiento integer not null default 0
                   check (desplazamiento >= 0),

    actualizado_en timestamptz not null default now()
);

-- Para el descarte por antigüedad de los recorridos abandonados.
create index if not exists ix_listado_comunitario_actualizado
    on public.listado_comunitario_pendiente (actualizado_en);

comment on table public.listado_comunitario_pendiente is
    'Por dónde va el listado de otras huertas del CU4 (ADR-0021). Caduca '
    'a la hora: pasada esa ventana se vuelve a empezar por las últimas.';
comment on column public.listado_comunitario_pendiente.desplazamiento is
    'Cuántas huertas ya se mostraron. Sin datos personales ni agronómicos: '
    'es un contador.';


-- ---------------------------------------------------------------------
-- RLS con el mismo criterio de 003, 005 y 007: activo y sin políticas
-- permisivas. Defensa en profundidad, no la barrera principal, porque el
-- backend usa service role y la omite (Fase 3, §5.1).
-- ---------------------------------------------------------------------
alter table public.listado_comunitario_pendiente enable row level security;

revoke all on public.listado_comunitario_pendiente from anon, authenticated;
