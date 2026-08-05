# ADR-0009. La ingesta de fuentes oficiales es un script local y repetible

- **Estado:** Aceptada
- **Fecha:** 2026-08-04
- **Fase:** 6 (implementa la mitad de ingesta del CU2)

## Contexto

La Fase 4 define el troceo —fragmentos de 300–500 tokens con solape de 50—
y la Fase 3 define las tablas `fuente` y `fragmento_oficial`, pero ningún
documento dice **quién ejecuta la ingesta, cuándo, ni qué se hace con el
documento antes de trocearlo**. Se daba por supuesto que un PDF entra al
RAG tal cual sale del extractor.

No es así. El documento del Jardín Botánico está maquetado en InDesign y lo
que `extract_text` devuelve son renglones de página, no frases. Sin
tratarlo, los fragmentos quedarían cortados por la maquetación y no por el
sentido.

## Decisión 1. Script local, fuera del servicio

La ingesta vive en [`scripts/ingesta_fuente.py`](../../scripts/ingesta_fuente.py)
y se ejecuta a mano desde el equipo de desarrollo. **No forma parte del
backend desplegado.**

Así `pypdf` se queda en `requirements-scripts.txt` y no entra en el
`requirements.txt` que instala Railway. El servicio no abre un PDF jamás:
solo consulta lo que la ingesta dejó escrito.

El acceso a la base sí lo hace `app/services/repositorio.py`, que sigue
siendo el punto único de acceso a Supabase (Fase 3, Tabla 2). Lo que se
queda en el script es únicamente lo propio del documento: extraer, limpiar,
trocear.

## Decisión 2. La limpieza es parte de la ingesta, no un detalle

Cinco tratamientos, todos derivados de medir el documento y no de suponer:

1. **Se descartan la cabecera y la cola.** Se ingiere de la página 12 a la
   121. Antes van portada, créditos y tabla de contenido (1–7) y la
   presentación institucional y los agradecimientos (8–10). Después van las
   referencias bibliográficas (122–126), el colofón de imprenta (127) y la
   contracubierta (128). ESTADO.md solo advertía de la cabecera; la cola
   importa igual, porque una lista de URL y el gramaje del papel entrarían
   al nivel más alto de la jerarquía de fuentes (CLAUDE.md §6). **Sí se
   conserva el glosario** de las páginas 120–121.
2. **El folio se quita en sus tres formas.** En renglón propio (39
   páginas), pegado a la palabra —`"13medicinal"`— (30) y seguido de
   espacio —`"48 Nombre común"`— (37). La tercera es la fácil de pasar por
   alto y la que más daño hace: deja el número incrustado a mitad del texto
   y acaba dentro de un fragmento vectorizado. Solo se quita si el número
   coincide con el folio esperado, para no mutilar un texto que empiece
   legítimamente por una cifra.
3. **Se recomponen las palabras cortadas y los párrafos.** El corte de
   palabra viene en dos variantes: `"enten-"` (325 veces) y `"inte -"`, con
   espacio antes del guión (55). Y no hay renglones en blanco entre
   párrafos, así que el corte hay que deducirlo de la puntuación y de la
   mayúscula siguiente. Las páginas se procesan **encadenadas**, porque hay
   párrafos que cruzan el salto de página.
4. **Se descartan los pies de figura.** Remiten a una imagen que la usuaria
   no va a ver por WhatsApp.
5. **Se sanean las tablas de especies.** Ver la decisión 3.

## Decisión 3. De las tablas se retira lo que la extracción destruyó

El documento trae cuatro tablas de especies aptas para el clima de Bogotá,
con columnas de nombre común, nombre científico, familia, exótica y nativa.
Al extraer, las columnas se colapsan y las dos últimas quedan en una `x`
suelta de la que ya no se sabe a cuál pertenece:

```
Nombre común  Nombre científico            Familia      Exótica  Nativa
Tomate        Solanum lycopersicum L.      Solanaceae            x
```

El problema no es que falte el dato: es que el fragmento **invita a
inventarlo**, y entra como fuente oficial, el nivel de la jerarquía donde
la respuesta se da por verificada.

Se retiran las marcas y su encabezado, y se conserva lo que sobrevivió
intacto —nombre común, nombre científico y familia—. La lista de unas 80
especies sigue sirviendo para responder qué se puede sembrar, y ya no se
puede afirmar de ninguna que sea nativa o introducida.

La regla distingue la marca de celda de la `x` de los híbridos botánicos
(`Fragaria x ananassa`): solo se elimina cuando le sigue mayúscula o fin de
texto.

**Alternativas descartadas:** dejar las tablas tal cual, que conserva la
fidelidad al original pero admite la atribución errónea; y descartarlas
enteras, que pierde la lista de especies sin necesidad.

## Decisión 4. El tamaño del fragmento se calibra midiendo tokens, no estimándolos

El troceo corta por caracteres —contar tokens en cada corte serían ~80
llamadas de red para gobernar un punto de corte—, pero **la ratio se midió
con `count_tokens` del propio `gemini-embedding-001`**, no se supuso.

El recorrido interesa porque desmiente la aproximación habitual:

| Ratio usada | Origen | Tokens reales | Dentro de 300–500 |
|---|---|---|---|
| 4.0 | aproximación estándar para español | 208–445 | — |
| 4.78 | medida sobre 10 fragmentos | 333–625, mediana 482 | 62 % |
| **3.9** | **extremo denso del corpus** | **229–516, mediana 392** | **90 %** |

Dos lecciones:

- **Muestrear diez fragmentos no basta.** Daba ratios entre 4.54 y 4.78
  según cuáles tocaran, oscilación del mismo orden que la corrección que se
  quería comprobar. `--medir-tokens` cuenta ahora todos.
- **Hay que dimensionar por el extremo denso, no por la media.** La media
  del corpus es 4.49 car./token, pero la ratio varía mucho entre
  fragmentos: los que cargan nomenclatura botánica tokenizan más denso. Con
  la media, la mitad del corpus se salía del intervalo.

La constante queda calibrada **contra este documento**. Con otra fuente hay
que volver a medir.

## Decisión 5. La ingesta es repetible: reemplaza, no añade

Si la fuente ya está registrada, el script se niega y lo dice; con
`--reingerir` borra sus fragmentos y los rehace, **borrado e inserción en
una sola transacción**.

Repetir una ingesta que añadiera duplicaría el corpus, y los duplicados
coparían el top-k con el mismo texto. El fallo no daría ningún error: se
manifestaría como respuestas peores.

Se añade `--simular`, que trocea e informa sin vectorizar ni escribir, por
el mismo criterio que los spikes de la Fase 5: mirar el troceo antes de
gastar embeddings y escribir en la base.

## Decisión 6. El fragmento no lleva plantilla de atribución

El texto vectorizado es contenido del documento y nada más. La entidad y el
título salen de la tabla `fuente` por la clave foránea en el momento de
responder.

Es consecuencia directa del hallazgo del spike de la Fase 5: un texto fijo
repetido en todos los fragmentos infla por igual la similitud de todos, que
es lo que le pasa a la colección comunitaria. La colección oficial se libra
—se comprobó que este documento no tiene encabezado ni pie repetido— y no
tiene sentido introducirle el defecto a mano.

## Consecuencias

- Primera fuente oficial ingerida: **81 fragmentos**, `fuente_id`
  `5afa2267-bcc6-4773-b5a2-c87593fa32cf`, 768 dimensiones, sin duplicados.
- Los PDF no se versionan: `fuentes/` está en el `.gitignore`. Son
  publicaciones de terceros y el repositorio es público. El script los
  descarga de la URL que queda registrada en la fila de `fuente`, que es lo
  que hace reproducible la ingesta.
- `requirements-scripts.txt` es un archivo nuevo, deliberadamente separado.

## Hallazgo que condiciona el paso siguiente

**El umbral de 0.7 deja fuera la consulta insignia del CU2.** Medido contra
el corpus ya ingerido:

| Consulta | Mejor similitud | Con umbral 0.7 |
|---|---|---|
| "a mi mata de tomate le salieron unos bichitos verdes, qué le echo" | 0.6911 | **no recupera nada** |
| "cada cuánto tengo que regar la huerta" | 0.7320 | recupera 4 |
| "cómo hago compost con lo que sobra de la cocina" | 0.7167 | recupera 1 |
| "cuándo cambio el aceite del carro" | 0.5538 | descarta, correcto |

Los fragmentos que la primera consulta deja fuera **sí tratan del manejo de
plagas**: quedan a centésimas.

La causa es que la evidencia que respaldaba el umbral (ESTADO.md, spike del
29/07) se obtuvo contra un documento **escrito a mano para la prueba**, casi
con las palabras de la consulta, que puntuó 0.797. Contra prosa real de un
documento real, el mismo tipo de acierto puntúa entre 0.66 y 0.73.

La separación sigue existiendo —lo ajeno al dominio se queda en 0.55—, pero
desplazada unas siete centésimas hacia abajo. **No se cambia aquí**: el
umbral es parámetro documentado de la Fase 4 y su calibración corresponde a
la recuperación, que es el paso siguiente. Queda registrado con la medida
que lo respalda.

Es, además, una advertencia metodológica citable en el documento de grado:
un spike validado contra material sintético sobreestima la similitud, y la
cifra solo vale cuando se remide contra el corpus real.
