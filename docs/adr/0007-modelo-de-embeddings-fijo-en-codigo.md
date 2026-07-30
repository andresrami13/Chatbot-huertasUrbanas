# ADR-0007. Se mantiene `gemini-embedding-001`, y el modelo de embeddings no se configura por entorno

- **Estado:** Aceptada
- **Fecha:** 2026-07-29
- **Fase:** 5

## Contexto

Las Fases 3 y 4 citan `text-embedding-004`, que Google retiró el 14 de enero
de 2026. La corrección vigente (CLAUDE.md §9.1) fija
`gemini-embedding-001` con `output_dimensionality=768`, truncado porque
pgvector solo indexa hasta 2000 dimensiones con el tipo `vector`.

Al implementar el cliente aparecieron dos cuestiones que esa corrección no
resuelve, porque cuando se escribió no existía el escenario:

1. **Google publicó `gemini-embedding-2`** (estable desde el 22 de abril de
   2026) y lo señala como el reemplazo recomendado de `gemini-embedding-001`.
   Hay que decidir si se migra.
2. **¿Debe el modelo de embeddings ser una variable de entorno?** El modelo
   generativo sí lo es, para poder cambiarlo en Railway sin desplegar. La
   simetría invita a hacer lo mismo con el de embeddings.

## Decisión

### 1. Se mantiene `gemini-embedding-001`

No se migra a `gemini-embedding-2`, por dos motivos verificados en la
documentación oficial:

- **No admite `task_type`.** `gemini-embedding-001` permite vectorizar con
  `RETRIEVAL_DOCUMENT` en la ingesta y `RETRIEVAL_QUERY` en la consulta. Esa
  asimetría es una palanca de calidad de la recuperación; `gemini-embedding-2`
  la sustituye por instrucciones dentro del propio texto, menos determinista.
- **Devuelve un solo embedding agregado** cuando recibe varias entradas, en
  lugar de uno por entrada. La ingesta por lotes de fragmentos exigiría una
  llamada por fragmento.

No hay urgencia: el retiro de `gemini-embedding-001` está previsto para el
**14 de mayo de 2028**, muy por detrás de la Fase 8.

### 2. El modelo de embeddings queda como constante en código

`MODELO_EMBEDDING` y `DIMENSIONES_EMBEDDING` viven en
[`app/core/gemini.py`](../../app/core/gemini.py). **No hay variable de
entorno para ellos**, a diferencia de `GEMINI_GENERATIVE_MODEL`.

## Justificación de la asimetría

No es una inconsistencia: los dos modelos tienen consecuencias distintas al
cambiarlos.

- Cambiar el **generativo** no invalida nada almacenado. Es calibración
  normal, prevista para la Fase 7, y los modelos de Gemini se retiran con
  calendario, así que poder cambiarlo sin desplegar es una ventaja
  operativa real.
- Cambiar el **de embeddings** invalida todos los vectores guardados. Los
  espacios vectoriales de dos modelos distintos son incompatibles: las
  consultas nuevas se compararían contra vectores viejos y la recuperación
  se degradaría **sin producir ningún error**. El fallo no se manifiesta
  como una excepción, sino como respuestas peores, que es la forma más
  difícil de diagnosticar.

Un cambio así obliga a re-vectorizar el corpus completo. Es una operación de
código y de datos, no un ajuste de configuración, y exigir un commit es lo
que garantiza que no ocurra por accidente al tocar el panel de Railway. Es
el mismo razonamiento que protege a `PHONE_HASH_PEPPER` (CLAUDE.md §7): lo
que rompe datos ya guardados no debe ser fácil de cambiar.

## Consecuencias

- El repositorio deja constancia de con qué modelo se vectorizó, sin
  depender de la configuración de un entorno. Importa para la
  reproducibilidad del trabajo de grado.
- Migrar de modelo de embeddings es, por diseño, un cambio con commit,
  re-vectorización y un ADR nuevo.
- `GEMINI_GENERATIVE_MODEL` lleva **valor por defecto en el código**
  (`gemini-3.6-flash`), no solo en Railway, para que el repositorio registre
  con qué se probó aunque el entorno no defina nada.
- La configuración **rechaza al arrancar** un `GEMINI_GENERATIVE_MODEL` que
  contenga `embedding`. Sin esa comprobación el error no aparecería en el
  arranque sino en la primera conversación, ya en producción.
- El truncado a 768 dimensiones de `gemini-embedding-001` llega **sin
  normalizar** y `app/services/embeddings.py` lo normaliza en L2. Matiz que
  conviene no exagerar en el documento de grado: para el operador de
  distancia coseno de pgvector (`<=>`) la norma es indiferente, porque el
  operador divide por ella. Normalizar sirve para poder usar el producto
  interno (`<#>`) como equivalente más barato y para no mezclar vectores de
  normas distintas en una misma columna.

## Hallazgo relacionado

**`gemini-2.5-flash` se retira el 16 de octubre de 2026**, fecha que puede
caer antes de la evaluación sumativa de la Fase 8. El modelo generativo debe
ser de la serie 3; la estable más reciente es `gemini-3.6-flash` (21 de julio
de 2026). Es precisamente el tipo de cambio que justifica que esa sí sea una
variable de entorno.

## Alternativas descartadas

- **Migrar a `gemini-embedding-2`.** Descartada por la pérdida de
  `task_type` y por el embedding agregado en las llamadas por lotes. Se
  revisará si `001` recibe fecha de retiro más cercana.
- **Hacer configurable el modelo de embeddings.** Descartada: convierte una
  operación que requiere re-vectorizar en un cambio de un minuto sin aviso
  ni error visible.
- **Hacerlo configurable y guardar el modelo junto a cada vector para
  detectar mezclas.** Resolvería la detección, pero añade una columna y una
  comprobación en cada consulta para habilitar algo que no hace falta: en el
  prototipo el modelo de embeddings no va a cambiar. Si algún día cambia,
  esta es la vía a considerar.
