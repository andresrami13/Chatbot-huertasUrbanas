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

Los tres son idempotentes: reejecutarlos no duplica nada.

## Modelo

Ocho tablas: las siete entidades de la Fase 3 más el catálogo `barrio`
que introduce el [ADR-0002](../docs/adr/0002-catalogo-de-barrios.md).

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
- **Sin tabla de idempotencia**: sigue en memoria en el despachador
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

Está activo en las ocho tablas y **sin políticas permisivas**, lo que en
PostgreSQL equivale a denegar todo. No es un olvido.

El backend usa la clave de *service role*, que omite el RLS por diseño.
La barrera real es la **capa 1**: el filtrado por `usuario_id` en cada
consulta del repositorio de datos. El RLS protege únicamente frente al
uso de la clave anónima. Así lo declara la Fase 3, §5.1, y así debe
describirse en el documento de grado.

## Puntos a verificar al implementar

1. **Dimensión del embedding.** Las columnas son `vector(768)`, para
   `gemini-embedding-001` con `output_dimensionality=768`. Confirmar el
   parámetro contra la documentación vigente antes de la ingesta. No
   mezclar embeddings de modelos distintos: habría que re-vectorizar todo.
2. **Normalización del vector truncado.** Al pedir menos de las 3072
   dimensiones nativas, el vector puede venir sin normalizar, lo que
   afecta a la similitud coseno. Verificarlo en la documentación oficial
   durante la Fase 6 y normalizar en la aplicación si hace falta.
3. **Distancia contra similitud.** El operador `<=>` de pgvector devuelve
   **distancia** coseno. El umbral de 0.7 de la Fase 4, §7, es de
   *similitud*, así que se escribe `embedding <=> consulta <= 0.3`.
   Confundirlo invierte el filtro.
4. **Esquema `extensions`.** `001` instala pgvector ahí, siguiendo la
   convención de Supabase, que lo incluye en el `search_path`. En un
   PostgreSQL corriente habría que crear el esquema o instalar la
   extensión en `public`.
