# Esquema de base de datos

Implementa el modelo entidad-relación de la **Fase 3, §3** con las
decisiones registradas en [`docs/adr/`](../docs/adr/).

## Aplicación

En el editor SQL de Supabase, **en este orden**:

| Archivo | Contenido |
|---|---|
| [`001_esquema.sql`](001_esquema.sql) | Extensión `pgvector`, las 8 tablas, índices y disparadores |
| [`002_catalogo_barrios.sql`](002_catalogo_barrios.sql) | Siembra de los 7 barrios de la UPZ 84 más `otro` |
| [`003_rls.sql`](003_rls.sql) | Activación de RLS y retirada de privilegios públicos |
| [`004_idempotencia.sql`](004_idempotencia.sql) | Tabla de idempotencia del webhook ([ADR-0005](../docs/adr/0005-procesamiento-asincrono-e-idempotencia.md)) |
| [`005_registro_pendiente.sql`](005_registro_pendiente.sql) | Borrador del CU3 a la espera de confirmación ([ADR-0008](../docs/adr/0008-borrador-de-registro-y-una-huerta-por-usuaria.md)) |

Los cinco son idempotentes: reejecutarlos no duplica nada.

## Modelo

Diez tablas: las siete entidades de la Fase 3, el catálogo `barrio` del
[ADR-0002](../docs/adr/0002-catalogo-de-barrios.md), la idempotencia del
[ADR-0005](../docs/adr/0005-procesamiento-asincrono-e-idempotencia.md) y el
borrador del [ADR-0008](../docs/adr/0008-borrador-de-registro-y-una-huerta-por-usuaria.md).

```
barrio ──1:N──> huerta <──N:1── usuario ──1:N──> mensaje
                  │
                  ├──1:N──> cultivo
                  └──1:1──> fragmento_comunitario

fuente ──1:N──> fragmento_oficial
```

Decisiones que el esquema materializa:

- **Dos colecciones vectoriales separadas**, no una con discriminador
  (Fase 3, §3).
- **Un fragmento comunitario por huerta**, impuesto con `UNIQUE` sobre
  `huerta_id` ([ADR-0004](../docs/adr/0004-cultivo-y-fragmento-comunitario.md)).
- **El barrio no se indexa para la recuperación**: no filtra la búsqueda,
  solo atribuye ([ADR-0001](../docs/adr/0001-barrio-no-filtra-recuperacion.md)).
- **Idempotencia con dos estados y sin dueño.** `idempotencia_webhook` se
  escribe **antes** de la compuerta del CU1, así que no puede contener dato
  personal alguno: guarda el HMAC del `wamid` —que en claro lleva dentro el
  teléfono del remitente— y no tiene `usuario_id`. Junto con `barrio`, es la
  única tabla sin dueño, y es deliberado
  ([ADR-0005](../docs/adr/0005-procesamiento-asincrono-e-idempotencia.md)).
- **La existencia de una fila en `usuario` ES el consentimiento**. No hay
  columna booleana: el CU1 prohíbe persistir nada antes de autorizar, y
  el [ADR-0003](../docs/adr/0003-consentimiento-sin-insistencia.md)
  prohíbe guardar el rechazo.

## Datos personales

Solo dos columnas contienen datos personales, y ninguna en claro:

| Columna | Protección |
|---|---|
| `usuario.telefono_hash` | HMAC-SHA256 + pepper, desde la aplicación |
| `usuario.nombre_usuario_cifrado` | AES-GCM, desde la aplicación |

Toda la información agronómica queda **sin cifrar a propósito**: alimenta
la búsqueda vectorial y cifrarla rompería la recuperación (Fase 3, §5.2).

## Sobre el RLS

Está activo en las diez tablas y **sin políticas permisivas**, lo que en
PostgreSQL equivale a denegar todo. No es un olvido.

El backend usa la clave de *service role*, que omite el RLS por diseño.
La barrera real es la **capa 1**: el filtrado por `usuario_id` en cada
consulta del repositorio de datos. El RLS protege únicamente frente al
uso de la clave anónima. Así lo declara la Fase 3, §5.1, y así debe
describirse en el documento de grado.

## Puntos a verificar al implementar

1. **Dimensión del embedding.** ~~Confirmar el parámetro.~~ **Verificado.**
   Las columnas son `vector(768)` y `output_dimensionality=768` funciona con
   `gemini-embedding-001`. No mezclar embeddings de modelos distintos:
   habría que re-vectorizar todo, y por eso el modelo no es configurable
   ([ADR-0007](../docs/adr/0007-modelo-de-embeddings-fijo-en-codigo.md)).
2. **Normalización del vector truncado.** ~~Verificarlo.~~ **Verificado:
   llega sin normalizar**, con norma medida 0.594, y
   `app/services/embeddings.py` lo normaliza en L2. Matiz importante para
   la redacción: **no afecta a la similitud coseno**, porque el operador
   `<=>` divide por la norma. Importa para poder usar `<#>` y para no
   mezclar vectores de normas distintas en la misma columna.
3. **Distancia contra similitud.** El operador `<=>` de pgvector devuelve
   **distancia** coseno. El umbral de 0.7 de la Fase 4, §7, es de
   *similitud*, así que se escribe `embedding <=> consulta <= 0.3`.
   Confundirlo invierte el filtro.
4. **Esquema `extensions`.** `001` instala pgvector ahí, siguiendo la
   convención de Supabase, que lo incluye en el `search_path`. En un
   PostgreSQL corriente habría que crear el esquema o instalar la
   extensión en `public`.
