-- =====================================================================
-- 001 — Esquema base
-- Chatbot de huertas urbanas, UPZ 84 Bosa Occidental
--
-- Implementa el modelo entidad-relación de la Fase 3, §3, con las
-- decisiones registradas en docs/adr/.
--
-- Se ejecuta una sola vez, en orden: 001 -> 002 -> 003.
-- =====================================================================

-- pgvector. En Supabase las extensiones viven en el esquema `extensions`,
-- que ya forma parte del search_path por defecto; por eso más abajo el
-- tipo se escribe simplemente como `vector(768)`.
create extension if not exists vector with schema extensions;

-- gen_random_uuid() es parte del núcleo desde PostgreSQL 13, no requiere
-- pgcrypto.


-- ---------------------------------------------------------------------
-- Marca de tiempo de actualización
-- ---------------------------------------------------------------------
create or replace function public.fn_actualizar_marca_tiempo()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    new.actualizado_en = now();
    return new;
end;
$$;


-- ---------------------------------------------------------------------
-- barrio — catálogo (ADR-0002)
--
-- Tabla y no tipo ENUM: añadir un barrio debe ser un INSERT, no una
-- migración de esquema. Los valores siguen siendo controlados porque
-- quien puebla el campo no es la usuaria escribiendo, sino el modelo
-- extrayendo entidades de audio transcrito.
--
-- El prompt de extracción se genera leyendo esta tabla; no lleva la
-- lista escrita a mano.
-- ---------------------------------------------------------------------
create table if not exists public.barrio (
    id      smallint generated always as identity primary key,
    codigo  text not null unique,
    nombre  text not null unique,
    -- Permite retirar un barrio del enum de extracción sin romper las
    -- huertas que ya lo referencian.
    activo  boolean not null default true
);

comment on table  public.barrio is
    'Catálogo de barrios de la UPZ 84 Bosa Occidental. ADR-0002.';
comment on column public.barrio.codigo is
    'Valor que consume el enum de la salida estructurada de Gemini.';
comment on column public.barrio.nombre is
    'Nombre para mostrar; se usa en la atribución del dato comunitario.';


-- ---------------------------------------------------------------------
-- usuario — identidad y consentimiento (Fase 3, Tabla 1)
--
-- La fila existe únicamente si la usuaria autorizó el tratamiento: el
-- CU1 prohíbe persistir cualquier dato antes de la autorización, y el
-- ADR-0003 prohíbe además guardar el hecho del rechazo. Por eso no hay
-- columna booleana de consentimiento: la existencia de la fila ES el
-- consentimiento, y `consentimiento_en` es su constancia legal
-- (Ley 1581 de 2012).
--
-- Minimización (Fase 3, capa 6): sin cédula, sin dirección, sin el
-- número en claro.
-- ---------------------------------------------------------------------
create table if not exists public.usuario (
    id                     uuid primary key default gen_random_uuid(),

    -- HMAC-SHA256 del número + pepper, en hexadecimal (64 caracteres).
    -- Determinista a propósito: es la llave de búsqueda en cada mensaje
    -- entrante. El número en claro solo existe en memoria durante la
    -- petición (Fase 3, §5.2).
    telefono_hash          text not null unique
                           check (telefono_hash ~ '^[0-9a-f]{64}$'),

    -- AES-GCM del lado de la aplicación: nonce || texto cifrado || tag.
    -- Nulo mientras la usuaria no dé su nombre.
    nombre_usuario_cifrado bytea,

    consentimiento_en      timestamptz not null default now(),
    creado_en              timestamptz not null default now()
);

comment on table  public.usuario is
    'Identidad y consentimiento del líder de huerta. La existencia de la '
    'fila implica autorización otorgada (CU1, ADR-0003).';
comment on column public.usuario.telefono_hash is
    'HMAC-SHA256 hex del celular con pepper. Si el pepper cambia, las '
    'usuarias registradas dejan de ser reconocidas.';


-- ---------------------------------------------------------------------
-- huerta — datos de la parcela (compartibles)
--
-- Toda esta información queda EN CLARO a propósito: alimenta la
-- búsqueda vectorial y cifrarla rompería la recuperación
-- (Fase 3, §5.2).
-- ---------------------------------------------------------------------
create table if not exists public.huerta (
    id             uuid primary key default gen_random_uuid(),
    usuario_id     uuid not null references public.usuario(id) on delete cascade,
    barrio_id      smallint not null references public.barrio(id),

    -- Nulo si la usuaria no lo menciona; el extractor no debe inventarlo
    -- (Fase 4, Tabla 3).
    nombre_huerta  text,
    comentarios    text,

    creado_en      timestamptz not null default now(),
    actualizado_en timestamptz not null default now()
);

-- Capa 1 del modelo de seguridad: todas las consultas a datos de una
-- usuaria se acotan por usuario_id. Es la barrera real (Fase 3, §5.1).
create index if not exists ix_huerta_usuario on public.huerta (usuario_id);

create trigger tg_huerta_actualizado
    before update on public.huerta
    for each row execute function public.fn_actualizar_marca_tiempo();

comment on table public.huerta is
    'Datos compartibles de la parcela. Sin cifrar: alimentan el RAG.';


-- ---------------------------------------------------------------------
-- cultivo — fuente de verdad del dato agronómico (ADR-0004)
-- ---------------------------------------------------------------------
create table if not exists public.cultivo (
    id                  uuid primary key default gen_random_uuid(),
    huerta_id           uuid not null references public.huerta(id) on delete cascade,
    especie             text not null,

    -- La Fase 4 normaliza a mes/año: se guarda el día 1 del mes.
    fecha_siembra_aprox date,

    -- "Marca de imprecisión" de la Fase 4, Tabla 3: distingue "sembré en
    -- marzo" de "sembré hace meses", que el extractor aproximó. Se afina
    -- en la confirmación del CU3.
    fecha_imprecisa     boolean not null default false,

    creado_en           timestamptz not null default now()
);

create index if not exists ix_cultivo_huerta on public.cultivo (huerta_id);


-- ---------------------------------------------------------------------
-- mensaje — memoria del agente (Fase 3, Tabla 1; Fase 4, §6)
--
-- Registro mínimo de la conversación. El agente lee los últimos 10 en
-- cada turno.
-- ---------------------------------------------------------------------
create table if not exists public.mensaje (
    id         uuid primary key default gen_random_uuid(),
    usuario_id uuid not null references public.usuario(id) on delete cascade,

    rol        text not null check (rol in ('usuaria', 'asistente')),

    -- Tipo de la entrada ANTES de normalizar, para poder analizar cuánto
    -- se usa la voz durante las pruebas de la Fase 7.
    tipo       text not null default 'text'
               check (tipo in ('text', 'audio', 'interactive')),

    -- Contenido ya normalizado (el audio, transcrito una sola vez).
    contenido  text not null,

    -- Identificador del mensaje en Meta. Sirve de trazabilidad y evita
    -- filas duplicadas si un reintento llegara a procesarse dos veces.
    -- No es el control de idempotencia del webhook, que sigue en memoria
    -- por ahora (ADR-0005).
    wamid      text unique,

    creado_en  timestamptz not null default now()
);

-- Ventana de memoria: los últimos N mensajes de una usuaria.
create index if not exists ix_mensaje_usuario_fecha
    on public.mensaje (usuario_id, creado_en desc);


-- ---------------------------------------------------------------------
-- fuente — metadatos de los documentos oficiales (Fase 4, §5.1)
-- ---------------------------------------------------------------------
create table if not exists public.fuente (
    id           uuid primary key default gen_random_uuid(),
    entidad      text not null,   -- p. ej. 'Jardín Botánico de Bogotá'
    titulo       text not null,
    url          text,
    ingestado_en timestamptz not null default now()
);

comment on table public.fuente is
    'Documentos oficiales curados. Sus metadatos se citan en la respuesta '
    'del CU2 (Fase 2, §5.3).';


-- ---------------------------------------------------------------------
-- Colecciones vectoriales
--
-- Dos tablas separadas y no una con discriminador (Fase 3, §3): cada
-- una mantiene su esquema y su índice, sin columnas nulas según el tipo,
-- y refuerza el trato distinto entre la fuente oficial (autoridad de la
-- recomendación) y el dato comunitario (contexto atribuido).
--
-- Dimensión 768: gemini-embedding-001 con output_dimensionality=768.
-- El modelo devuelve 3072 por defecto y pgvector solo indexa hasta 2000
-- con el tipo `vector`. No mezclar embeddings de modelos distintos: los
-- espacios vectoriales son incompatibles.
-- ---------------------------------------------------------------------
create table if not exists public.fragmento_oficial (
    id         uuid primary key default gen_random_uuid(),
    fuente_id  uuid not null references public.fuente(id) on delete cascade,

    -- Posición dentro del documento, para depurar la fragmentación.
    orden      integer not null default 0,

    contenido  text not null,
    embedding  vector(768) not null,

    creado_en  timestamptz not null default now()
);

create index if not exists ix_fragmento_oficial_fuente
    on public.fragmento_oficial (fuente_id);


create table if not exists public.fragmento_comunitario (
    id             uuid primary key default gen_random_uuid(),

    -- UNIQUE, no solo FK: un fragmento por huerta, no uno por cultivo
    -- (ADR-0004). El texto se regenera entero desde `cultivo` cada vez
    -- que la huerta cambia.
    huerta_id      uuid not null unique
                   references public.huerta(id) on delete cascade,

    contenido      text not null,
    embedding      vector(768) not null,

    creado_en      timestamptz not null default now(),
    actualizado_en timestamptz not null default now()
);

create trigger tg_fragmento_comunitario_actualizado
    before update on public.fragmento_comunitario
    for each row execute function public.fn_actualizar_marca_tiempo();

comment on table public.fragmento_comunitario is
    'Un fragmento por huerta, derivado de cultivo (ADR-0004). Solo campos '
    'compartibles: nombre_huerta, barrio y cultivos. Nunca datos personales.';


-- ---------------------------------------------------------------------
-- Índices vectoriales
--
-- HNSW y no IVFFlat: IVFFlat necesita datos para construir sus listas y
-- aquí las tablas arrancan vacías. Se indexa por distancia coseno, que
-- es la métrica del umbral de 0.7 de la Fase 4, §7.
--
-- CUIDADO al consultar: el operador <=> de pgvector devuelve DISTANCIA
-- coseno, no similitud. Similitud >= 0.7 se escribe como
-- `embedding <=> consulta <= 0.3`. Confundirlo invierte el filtro.
--
-- Con el volumen del prototipo el planificador probablemente prefiera un
-- recorrido secuencial e ignore estos índices. Es lo esperado y correcto;
-- están para cuando la colección oficial crezca con la ingesta.
--
-- NOTA sobre `barrio`: no se indexa para la recuperación. El barrio no
-- filtra la búsqueda, solo atribuye el dato (ADR-0001).
-- ---------------------------------------------------------------------
create index if not exists ix_fragmento_oficial_embedding
    on public.fragmento_oficial
    using hnsw (embedding vector_cosine_ops);

create index if not exists ix_fragmento_comunitario_embedding
    on public.fragmento_comunitario
    using hnsw (embedding vector_cosine_ops);
