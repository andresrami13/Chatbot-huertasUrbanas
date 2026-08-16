# ADR-0014. Las fuentes oficiales se declaran en un catálogo, y sus parámetros son mediciones

- **Estado:** Aceptada
- **Fecha:** 2026-08-15
- **Fase:** 7 (amplía la base de conocimiento del CU2)
- **Amplía:** [ADR-0009](0009-ingesta-de-fuentes-oficiales.md)

## Contexto

El ADR-0009 dejó la ingesta resuelta **para un documento**. La entidad, el
título, la URL, el rango de páginas y la ratio de caracteres por token eran
constantes de módulo de `scripts/ingesta_fuente.py`.

Con cinco documentos nuevos eso se rompe por dos sitios. El práctico: para
ingerir otro hay que editar el script, y una ingesta que exige editar el
programa no se repite igual seis meses después, que es justo lo que el
ADR-0009 quería garantizar. El de fondo: **esos números no son
configuración, son mediciones**, y estaban mezclados con la lógica que los
usa.

## Decisión 1. Un catálogo versionado, separado del script

`scripts/catalogo_fuentes.py` declara cada documento con lo que le es
propio y `scripts/ingesta_fuente.py` lo recibe como parámetro. El script se
invoca con `--fuente <clave>` y `--listar` enseña las declaradas.

Como los PDF no se versionan —`fuentes/` está en el `.gitignore` porque son
publicaciones de terceros y el repositorio es público—, **lo único que
permite rehacer el mismo corpus en la Fase 8 es la URL más estos
parámetros**. El catálogo es, por tanto, parte del registro experimental
del trabajo, no un archivo de configuración.

## Decisión 2. La ratio de caracteres por token se comprueba, no se hereda

Cada fuente lleva `ratio_medida`. Mientras esté en `False`, la ingesta real
**se niega a correr** y solo se permite `--simular` y `--medir-tokens`.

La decisión 4 del ADR-0009 ya advertía por escrito de que la constante
estaba calibrada contra un documento concreto y que con otra fuente había
que volver a medir. Esto convierte esa advertencia en algo que el programa
comprueba. La diferencia importa porque el fallo es silencioso: con una
ratio heredada los fragmentos salen del intervalo de 300–500 tokens de la
Fase 4 sin que nada dé error.

`--medir-tokens` informa ahora también del **percentil 10** de la ratio, que
es el valor que hay que llevar al catálogo. La media no sirve: dimensionar
por ella dejó fuera de intervalo a la mitad del corpus en el ADR-0009.

## Decisión 3. Tres parámetros nuevos, cada uno por un defecto medido

**Desfase del folio.** El folio impreso no siempre coincide con el índice
de la página dentro del PDF. La cartilla de 2011 lleva un 16 impreso en su
página 20, y el catálogo de plantas un 10 en la suya. Con el desfase mal
puesto el folio no se retira y acaba incrustado a mitad de un fragmento
vectorizado, que es el defecto que describe la decisión 2 del ADR-0009. Se
añade `--detectar-folio`, que cuenta en cuántas páginas encaja cada desfase
posible en vez de deducirlo de una muestra: en la cartilla de 2022 hay
páginas sueltas con cifras que parecen folios y no lo son, y mirar dos o
tres habría fijado un desfase equivocado para todo el documento.

**Umbral de plantilla por documento.** El valor de 10 páginas vale para
prosa corrida. En un documento organizado en fichas borra contenido: en el
catálogo de plantas, `Compositae` aparece en 12 páginas y `Lamiaceae` en
11, y son nombres de familia botánica, no maquetación.

**Modo de extracción por documento.** `pypdf` devuelve por defecto los
renglones en el orden del flujo interno del PDF. En prosa corrida eso
coincide con el orden de lectura; en un documento maquetado por cajas, no.
En *Sembrando Biodiversidad* el nombre de la especie y los rótulos de
sección salían **detrás del contenido que encabezan**, y los rótulos de las
cajas aparecían amontonados al principio, separados de lo que rotulan. Con
`extraction_mode="layout"` el orden se corrige.

Este hallazgo merece figurar en el documento de grado por lo que enseña
sobre la medición: con la extracción desordenada, el troceo daba **232
fragmentos y un 99 % dentro del intervalo objetivo**. La distribución de
tamaños era mejor que la de cualquier otro documento mientras el contenido
estaba revuelto. Un indicador de calidad puede estar midiendo algo que no
es la calidad.

## Decisión 4. Las páginas de dos columnas se leen por columnas, y por bloques

Corregido el orden de lectura, quedaba un defecto mayor que los dos que se
habían anotado: **82 de las 260 páginas de *Sembrando Biodiversidad* son de
dos columnas**, y leerlas renglón a renglón entreteje dos textos ajenos
frase a frase.

> «Condiciones o requerimientos especiales: **Semillas** la especie requiere
> suelos con un pH entre **Reportadas: se usa una dosis de semilla** los 6.0
> y 6.5 aproximadamente…»

La calle entre columnas se detecta por lo que es: una franja vertical en
blanco en casi todos los renglones **que tienen texto a ambos lados**. Solo
cuentan esos, porque un título corto o un pie centrado no dicen nada sobre
si la página tiene columnas.

La detección se hace **en dos pasadas, y la segunda no es un adorno**:
primero sobre la página entera y, si no hay calle que la cruce de arriba
abajo, bloque a bloque, separando por los renglones en blanco que la
maquetación ya deja entre secciones. Hacen falta las dos porque las páginas
mixtas son las que más daño hacían: cada ficha trae prosa de una columna y,
debajo, la lista de plagas y enfermedades en dos. Solo con la detección por
página, esa lista se quedaba entretejida —«Trips (Thrips tabaci Lind.):
generan Trozador (Agriotes lineatus L.): manchas plateadas en las hojas
conocido como gusano del alambre»—, que es justo el contenido que responde
la consulta insignia del CU2. Con la segunda pasada, las páginas tratadas
subieron de 67 a **95**.

## Decisión 5. Hay material que se recorta por el medio, no por los extremos

*Sembrando Biodiversidad* no lleva una bibliografía al final: **cada ficha
de especie lleva la suya**, dieciocho en total, cada una en su página. El
recorte de cabecera y cola del ADR-0009 da por supuesto un libro lineal y
no las alcanza.

Se añade `saltar_pagina_si_empieza_por`, una regla y no una lista de
números de página: si el documento se vuelve a extraer, la regla sigue
valiendo. Una lista de autores y URLs no responde nada y ocuparía puestos
del top-k, que es el mismo motivo por el que se recortan las referencias
del final en los otros documentos.

La misma regla resuelve un segundo caso, y por un motivo distinto: las
**15 páginas de preparación del recetario** se maquetan en *tres* columnas
y la extracción las deja inservibles.

> «1. Cocinar el haba al 2. Una vez cocinada 3. Pasar por un vapor o con
> poca agua, dejar enfriar y colar. procesador o licuadora»

La separación de columnas no las salva, porque parte por una sola calle y
ahí hay dos. Y aquí no se descarta por irrelevante sino por **ilegible**:
una receta revuelta que entra como fuente oficial invita al modelo a
componer una preparación que el documento no dice. Es el mismo criterio con
el que la decisión 3 del ADR-0009 retiró las columnas que la extracción
había destruido en las tablas de especies. Se conservan las páginas de
valor nutricional y las de cultivo del recetario, que van a una columna y
salen bien.

## Decisión 7. Antes de escribir se comprueban los casi duplicados

La decisión 5 del ADR-0009 previó los duplicados **dentro** de una fuente.
Con seis fuentes aparece el caso que no contemplaba: pasajes repetidos
**entre** documentos distintos.

`--comprobar-duplicados` compara los fragmentos nuevos contra el corpus ya
ingerido, y **se ejecuta sola antes de toda ingesta real**, por el mismo
criterio por el que existe `--simular`: mirar antes de escribir.

La comprobación es **textual y no vectorial**, a propósito. Lo que interesa
es si el pasaje está literalmente repetido, y para eso la coincidencia de
secuencias de ocho palabras es más precisa que la similitud coseno: dos
fragmentos distintos sobre el mismo tema pueden puntuar muy alto en coseno
sin ser el mismo texto, y confundirlos llevaría a descartar material
legítimo. Además no gasta embeddings.

Medido el 15/08/2026:

| Fuente | Solape medio | Fragmentos con más del 50 % repetido |
|---|---|---|
| `jbb_practicas_2022` | 27,9 % | **21 de 83** |
| `jbb_sembrando_2023` | 0,4 % | **0 de 211** |

*Sembrando Biodiversidad* es material enteramente nuevo. La cartilla de
2022, no: uno de cada cuatro de sus fragmentos ya está en el corpus, y el
peor repite el 85 %.

**El script mide y enseña; descartar es decisión de quien ingiere.** Se
resolvió el 15/08/2026 **descartar los 21** de la cartilla de 2022, que
entra con 62 de sus 83 fragmentos.

La exclusión se declara como **regla** (`descartar_repetidos`) y no como
lista de números de fragmento, para que la ingesta se vuelva a derivar
sola. Tiene un límite que conviene declarar en el documento de grado: **el
conjunto descartado depende del corpus que hubiera en la base en ese
momento**. Es reproducible dado el mismo estado de la base, no en
abstracto. Por eso se ingirió primero la cartilla de 2022, contra los
mismos 81 fragmentos con los que se midió.

## Consecuencia medida: el corpus era el límite, no el umbral

Ingeridas las dos fuentes, el corpus oficial pasa de 81 a **354
fragmentos**. Medido contra las consultas del ADR-0010, con el umbral de
0.68 y top-k=4 sin tocar:

| Consulta | Antes (81 fragmentos) | Después (354) |
|---|---|---|
| «a mi mata de tomate le salieron unos bichitos verdes» | 0.6911, recupera 1 | **0.7133, recupera 4** |
| «cada cuánto tengo que regar la huerta» | 0.7320, recupera 4 | 0.7358, recupera 4 |
| «cómo hago compost con lo que sobra de la cocina» | 0.7167, recupera 1 | **0.7311, recupera 4** |
| «cuándo cambio el aceite del carro» | descarta | descarta |

La consulta insignia del CU2 era la que motivó bajar el umbral de 0.70 a
0.68 en el ADR-0010, porque se quedaba a centésimas. Con el corpus ampliado
puntúa **0.7133 y superaría incluso el umbral original**. La separación
frente a lo ajeno al dominio se mantiene: la pregunta del aceite sigue sin
recuperar nada.

Es una corrección al diagnóstico del ADR-0010, que vale la pena registrar:
lo que fallaba no era el umbral sino la cobertura del corpus. Bajarlo fue lo
correcto con un solo documento; queda por ver, en la revalidación, si con
354 fragmentos sigue haciendo falta.

## Decisión 8. La normalización pasa de NFC a NFKC, y es igual para todos

Las ligaduras tipográficas —`ﬁ` en U+FB01— sobreviven a NFC porque son
equivalencia de compatibilidad y no canónica. La cartilla de 2022 trae
**293**, dentro de palabras corrientes: «beneﬁcios», «especíﬁcas»,
«ﬂoración». Vectorizadas así no son la misma palabra que escribe una
usuaria en WhatsApp, y el fragmento que las contiene se recupera peor sin
que nada lo delate.

A diferencia de los tres parámetros anteriores, **este no se declara por
documento y es deliberado**: el modo de extracción responde a cómo está
maquetado cada PDF, pero la normalización determina cómo se escribe una
palabra, y que la misma palabra se escriba distinto según el documento del
que venga es precisamente el defecto que se quiere evitar.

Se comprobó el coste sobre lo ya ingerido antes de cambiarlo: el documento
del Jardín Botánico no tiene ni una ligadura y NFKC solo le altera 9
caracteres de 130 719, sin mover ningún límite de fragmento.

## Consecuencias

- **La ingesta ya existente se reproduce exacta.** `jbb_pasos_basicos`
  sigue dando 81 fragmentos con la misma distribución de tamaños tras el
  refactor, el cambio de normalización y los parámetros nuevos. Era la
  condición para dar el cambio por bueno: el corpus de esos 81 fragmentos
  es el que sostiene la calibración del umbral de 0.68 (ADR-0010).
- Quedan declaradas tres fuentes: la ingerida y las dos primeras de la
  ampliación. Las tres restantes de `fuentes/` figuran como pendientes, con
  lo que le falta a cada una. **No se declaran a medias a propósito:** una
  entrada del catálogo es ejecutable, y media entrada invita a ingerir con
  parámetros que nadie midió.
- `Cartilla_agricultura_urbana_final.pdf` no puede entrar todavía: **falta
  su URL**, que es la clave por la que la ingesta reconoce lo ya ingerido.
  La candidata `cartilla_tecnica_agricultura_urbana.pdf` se descargó y se
  descartó: es otro documento, de 62 páginas y de otra administración.
- `Anexo_9_del_Protocolo_Listado_de_Especies.pdf` queda **fuera de
  alcance**: son 63 páginas de lista de nombre común y nombre científico,
  sin orientación. Competiría en el top-k contra los fragmentos que sí
  explican algo.

## Lo que este ADR no resuelve

- **Los rótulos al margen de *Sembrando Biodiversidad*.** En las páginas de
  descripción botánica, las etiquetas del margen izquierdo se siguen
  inyectando dentro de la frase: «el tallo presenta un diámetro de entre 13
  mm y **TALLO** 13,95 mm». No lo resuelve la separación por columnas
  porque ahí no hay dos columnas de texto, sino una etiqueta al margen de
  un solo renglón, y con un renglón no se puede afirmar que haya calle. Son
  unas 17 páginas y el ruido es de una palabra suelta por caja. Cinco
  páginas avisan además de texto rotado que `pypdf` no extrae.
- **Los rótulos al margen** y las cinco páginas de texto rotado de
  *Sembrando Biodiversidad*, descritos arriba.
- **La advertencia sobre contenido medicinal**, acordada el 15/08/2026 y
  pendiente de implementar: se marcará el fragmento en la ingesta y el
  backend añadirá un texto fijo, en lugar de confiarlo a una regla del
  prompt. Tendrá su propio ADR.
- **La revalidación del umbral.** Los dos umbrales están medidos contra el
  corpus real y no sobreviven a un cambio de corpus (CLAUDE.md §8). Pasar
  de 81 fragmentos a varios cientos obliga a rehacer la medición del
  ADR-0010.
