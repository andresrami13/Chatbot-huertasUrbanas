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

## Decisión 6. La normalización pasa de NFC a NFKC, y es igual para todos

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
- **El solape entre fuentes.** La cartilla de 2022 comparte el 22 % de su
  texto, palabra por palabra, con el documento ya ingerido, medido sobre
  secuencias de ocho palabras. No son dos ediciones de la misma obra —el
  78 % es material nuevo—, pero en las consultas que caigan sobre un pasaje
  compartido el top-k puede llenarse con el mismo párrafo firmado por dos
  fuentes. La decisión 5 del ADR-0009 previó los duplicados **dentro** de
  una fuente, no entre fuentes distintas. Falta una comprobación previa a
  la escritura.
- **La advertencia sobre contenido medicinal**, acordada el 15/08/2026 y
  pendiente de implementar: se marcará el fragmento en la ingesta y el
  backend añadirá un texto fijo, en lugar de confiarlo a una regla del
  prompt. Tendrá su propio ADR.
- **La revalidación del umbral.** Los dos umbrales están medidos contra el
  corpus real y no sobreviven a un cambio de corpus (CLAUDE.md §8). Pasar
  de 81 fragmentos a varios cientos obliga a rehacer la medición del
  ADR-0010.
