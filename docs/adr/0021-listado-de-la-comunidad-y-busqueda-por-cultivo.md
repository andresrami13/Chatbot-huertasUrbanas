# ADR-0021. El listado de la comunidad lo compone el código, y la búsqueda por cultivo se separa como CU7

- **Estado:** Aceptada
- **Fecha:** 2026-09-08
- **Fase:** 7
- **Origen:** Fase 2 (CU4) / ADR-0011

## Contexto

El CU4 respondía hablando de **una sola huerta** teniendo varias que
enseñar. El autor lo detectó probando con datos reales, y al mirarlo de
cerca no había un defecto sino tres cosas distintas, solo una de las
cuales era un error.

**Primera, y no es un defecto:** el CU4 excluye a propósito la huerta de
quien pregunta (`buscar_fragmentos_comunitarios`, ADR-0011), y desde el
vaciado del 18/08/2026 apenas había huertas registradas. Con dos huertas
en la base, una es el máximo que puede salir.

**Segunda: `RAG_TOP_K` era el techo de las dos vías**, y es la misma
variable que gobierna cuántos fragmentos oficiales entran al prompt del
CU2. Subirla para enseñar más huertas le habría cambiado al CU2 el tamaño
de su contexto en mitad de una calibración que sigue abierta (CLAUDE.md
§8). Una perilla estaba haciendo dos trabajos con necesidades distintas.

**Tercera, y esta sí es el defecto: el prompt le pedía al modelo no pasar
de 70 palabras.** Con cuatro huertas y sus cultivos, un listado fiel son
50–70 palabras solo de datos. El modelo, obligado a caber, escogía. Nadie
se lo mandó: es lo único que podía hacer.

## El hallazgo, que solo aparece al separar las dos preguntas

El ADR-0011 ya había medido que aquí llegan **dos clases de pregunta que
no se resuelven igual**:

| Pregunta | Qué es | Cómo se resolvía |
|---|---|---|
| «¿qué están sembrando las otras huertas?» | un **listado** | mal por similitud: se queda en 0.63 |
| «¿alguien más siembra tomate?» | una **búsqueda** | bien por similitud: la huerta con fresas a 0.819, las demás bajo 0.653 |

Aquel ADR las atendió con un respaldo: buscar por similitud y, si nada
superaba el umbral, listar lo más reciente. Funciona mientras las dos
compartan camino, y **esconde un fallo que solo se ve al separarlas**:

> Si ella pregunta por un cultivo que **nadie** tiene, la búsqueda no
> devuelve nada, el respaldo se dispara y recibe un listado de huertas que
> no tienen lo que preguntó.

Ese fallo ya existía. Con el listado bien formateado quedaría peor, no
mejor, porque una página ordenada de huertas ajenas parece una respuesta
mucho más que un párrafo vago.

De ahí sale lo demás: **la vía hay que elegirla antes de recuperar**, no
después mirando si la recuperación encontró algo. Y esa información solo
la tiene el modelo.

## Decisión

### 1. La búsqueda por cultivo se separa como CU7

Deja de ser un curso alternativo del CU4 y pasa a ser un caso de uso
propio: **CU7, buscar un cultivo concreto en otras huertas**. El número
sigue al CU6 (Onboarding), que el documento de grado ya tiene especificado
en su §3.6.

No es orden documental. Los dos casos tienen **cursos de excepción
distintos**, y hasta hoy se respondían con el mismo texto vago porque el
código no podía distinguirlos:

| Situación | Antes | Ahora |
|---|---|---|
| No hay otras huertas | «Todavía no tengo qué contarle de otras huertas por esa pregunta» | igual, y es cierto (`COMUNIDAD_SIN_HUERTAS`) |
| Ninguna tiene tomate | el mismo texto, o un listado que no viene a cuento | «De las huertas que conozco, ninguna tiene tomate anotado» |

### 2. Una sola herramienta, con `especie` de bandera

El agente sigue teniendo **cuatro herramientas** (ADR-0013).
`consultar_comunidad` gana un parámetro opcional `especie`: si viene, es
el CU7; si no, el CU4. El modelo decide *cuándo*, el backend decide *qué*
(CLAUDE.md §5).

Se descartó una quinta herramienta: pondría una decisión no determinista
más a 0.7 donde ya hay una, y la simetría caso de uso ↔ herramienta el
ADR-0013 ya la había roto en el otro sentido (cuatro herramientas para
cinco casos de uso, con `mostrar_ayuda` sirviendo al CU5).

**`especie` es una bandera, no la consulta.** La búsqueda por similitud
sigue corriendo sobre la pregunta completa. Dos motivos, los dos ya
medidos aquí: el umbral comunitario está calibrado sobre la forma en que
ella escribe (ADR-0011), y el ADR-0013 dejó dicho lo que pasa cuando el
dato lo pone el modelo —«cebolla larga» vuelve como «cebolla»—. Así el
parámetro no puede degradar el ranking aunque el modelo lo recorte.

### 3. El listado lo compone el código, no el modelo

Mismo criterio que el resumen del CU3 (ADR-0008): un listado es un reporte
de datos, y lo que el modelo puede hacer con él es restarle.

Lo que se gana no es estilo, son tres garantías que pasan de pedidas a
imposibles de incumplir:

- **No se cae ninguna huerta.** Era el defecto original.
- **La atribución de huerta y barrio siempre está.** Es obligatoria porque
  el barrio no filtra (ADR-0001), y estaba encomendada a una regla de
  prompt. Ya está medido que a 0.4 esas reglas se incumplen de forma
  intermitente: `limpiar_etiquetas` existe exactamente por eso.
- **No hay cómo convertir el reporte en recomendación**, que es lo que
  media hoja del prompt del CU4 trataba de impedir.

Y se gana tiempo de reloj: el listado no llama a Gemini, y la medición del
19/08/2026 dejó claro que el modelo era prácticamente todo el tiempo de
respuesta.

La búsqueda del CU7 **sí** pasa por el modelo (`redaccion_comunidad_v2.md`):
ahí no hay un formato fijo que componer, hay que contestar lo que ella
preguntó.

### 4. El listado sale de tres en tres, y el recorrido espera en la base

Tres huertas por mensaje dejan siete renglones contando encabezado y cola,
dentro de los 6–8 que manda el CLAUDE.md §11. Cinco cultivos por huerta
evitan que una con quince especies se lleve el mensaje entero; lo que se
recorta se dice —«y 3 más»— en lugar de desaparecer.

`CU4_HUERTAS_POR_TANDA` y `CU4_CULTIVOS_POR_HUERTA` son variables de
entorno **propias, no `RAG_TOP_K`**: son decisiones de presentación, no de
recuperación, y mezclarlas era el segundo problema del contexto.

El recorrido vive en `listado_comunitario_pendiente` (migración `009`),
hermana de `registro_pendiente` (ADR-0008) y `onboarding_pendiente`
(ADR-0016), y por el mismo motivo: **un redeploy de Railway le daría otra
vez las tres primeras a quien acababa de pedir las siguientes.**

**Cada vez que se toma la vía del listado, el recorrido avanza.** Eso evita
tener que detectar «más» en lenguaje natural: el agente ya decidió que esto
es una consulta a la comunidad, y con eso basta. Al llegar al final se
vuelve a empezar **avisando**, porque recibir otra vez las tres primeras
sin explicación parecería que el bot se trabó.

Caduca **a la hora**, no a las 24 del borrador y el onboarding. Aquellos
son tareas a medio terminar que conviene que sobrevivan a que ella suelte
el teléfono; esto es la posición de una conversación en curso, y dos días
después «cuénteme de las otras huertas» quiere decir empezar de nuevo.

### 5. El CU7 comprueba la especie después de recuperar

La similitud trae candidatas; el código comprueba que la especie esté de
verdad en la lista de la huerta antes de nombrarla.

Hace falta porque **el umbral no basta, y está medido en el propio
ADR-0011**: con 5 a 7 huertas y top-k=4, casi cualquier consulta recupera
medio corpus. Sin la comprobación se le atribuirían cultivos a quien no
los sembró, que es el peor fallo posible en el dato comunitario.

Se puede hacer sin modelo y sin margen de error porque el fragmento
comunitario es literalmente la lista de especies separadas por comas
(ADR-0011). Se compara por palabras completas y sin tildes: «papa» no da
por buena una huerta que sembró «papaya», y «cebolla» sí encuentra
«cebolla larga», que es la dirección útil —quien pregunta nombra la
especie más corta de lo que está registrada—.

**Medido contra las cuatro huertas reales el 08/09/2026, y no era una
precaución teórica:** «alguien siembra maracuyá?» recuperó **dos
fragmentos con la mejor similitud en 0.6601**, por encima del umbral de
0.65. Ninguna de esas dos huertas tiene maracuyá. Sin la comprobación, esa
consulta habría terminado atribuyéndole a dos vecinas un cultivo que no
sembraron, y con el formato de respuesta arreglado habría parecido más
fiable que antes. Con ella, la respuesta es «ninguna tiene maracuya
anotado».

Es la misma lección del proyecto una vez más: **el umbral no separa lo que
parece que separa.** Ya se había visto en el CU2 con la intención
(ADR-0013) y en el propio ADR-0011 con la sobre-recuperación; aquí se ve
con la especie.

## Consecuencias

**El respaldo por listado del ADR-0011 desaparece.** No se sustituye por
otra cosa: el listado dejó de ser un respaldo de la búsqueda para ser un
caso de uso con su propio camino, que no consulta la colección vectorial.
`buscar_en_comunidad` devuelve hoy la lista vacía cuando no encuentra, y
eso es una respuesta, no un fallo.

**El listado ya no lee `fragmento_comunitario`, lee `cultivo`**, que es la
fuente de verdad del dato agronómico (ADR-0004). Listar desde el derivado
obligaba a deshacer con un `split` el texto que `componer_texto` acababa de
armar. La colección vectorial se queda para lo que sí es una búsqueda.

**`RAG_UMBRAL_COMUNITARIO` gobierna hoy solo el CU7.** La remedición
pendiente desde el 04/08 —con 5 a 7 huertas de verdad— sigue haciendo
falta, pero ya no afecta a la pregunta más frecuente del CU4, que no pasa
por ningún umbral.

**La paginación puede repetir o saltarse una huerta.** Se guarda un
desplazamiento, no una foto: si entre una tanda y la siguiente alguien
registra o actualiza una huerta, el orden cambia. Se acepta a propósito —
con las 5 a 7 huertas de la evaluación el riesgo es pequeño, y guardar la
lista de identificadores para evitar un repetido es más maquinaria de la
que el problema merece.

**Aparece una tercera tabla efímera**, y con ella una tercera limpieza al
arrancar. Es el precio de sostener estado entre dos mensajes de WhatsApp, y
ya se pagó dos veces por lo mismo.

**Los documentos de fase quedan con un caso de uso de menos.** La Fase 2
especifica cinco; el sistema tiene siete contando el CU6 del documento de
grado. Anotado en `docs/correcciones-a-los-documentos.md`.

## Lo que este ADR no resuelve

**Si el modelo rellena `especie` cuando toca.** Corre a 0.7 y el
enrutamiento no es determinista (CLAUDE.md §12). Un fallo en cualquiera de
las dos direcciones degrada de forma recuperable —una búsqueda tratada
como listado le enseña huertas de más; un listado tratado como búsqueda
acaba en «ninguna tiene eso»—, pero **cuántas veces pasa está sin medir**.
La bitácora ya lo cuenta: cada llamada registra `via=CU4` o `via=CU7`.

**Si tres huertas por tanda es el número.** Lo fijó el autor por el límite
de renglones del CLAUDE.md §11, no midiendo con usuarias. Es calibrable
desde Railway sin desplegar.

**Si la cola invita de verdad a pedir más.** «Si quiere le cuento de
ellas, dígame» supone que ella entiende que puede pedirlo. Es exactamente
el tipo de suposición que la evaluación con 5 a 7 usuarias tiene que
desmentir o confirmar.

**Nada de esto está probado desde un celular.** Sí está probado contra la
base real con las cuatro huertas: la paginación recorre 3 + 1 y da la
vuelta avisando, el CU7 encuentra la fresa y descarta la maracuyá, y las
26 comprobaciones de `spike_despachador` pasan. Lo que falta es lo de
siempre: una persona escribiendo, que es lo único que dice si la cola
«si quiere le cuento de ellas, dígame» se entiende como una invitación.
