# ADR-0020. Los renglones de índice salen del corpus, y el umbral baja a 0.66

- **Estado:** Aceptada. **La calibración no está cerrada** — ver «Lo que
  este ADR no resuelve»
- **Fecha:** 2026-08-19 (escrito el 08/09/2026)
- **Fase:** 7
- **Origen:** Fase 4 (§7) / ADR-0010

> Este ADR se escribió tres semanas después de la decisión. Hasta el
> 08/09/2026 vivía solo en los mensajes de commit `00133ef` y `9102b50` y
> en un comentario de `app/config.py`, que es exactamente lo que la
> trazabilidad del CLAUDE.md §12 existe para evitar. El número quedó
> reservado en `docs/adr/README.md` mientras tanto.

## Contexto

La prueba con celular del 15/08/2026 dejó un modo de fallo que la usuaria
nombró ella misma, y conviene citarlo literal porque es la mejor
descripción del problema que hay en todo el proyecto:

> «sino me estas respondiendo nada, porque citas información?»

El bot respondía «no tengo esa información sobre eso» y firmaba con
`Fuente: Jardín Botánico`. Una cita al pie de una frase vacía es peor que
no responder: el sello de fuente verificada es lo que sostiene la jerarquía
del CLAUDE.md §6, y ahí estaba avalando la nada.

El ADR-0010 había atribuido ese fallo al umbral —se probó bajarlo a 0.65 y
apareció; se dejó en 0.68 y no—. **Era el corpus.**

## La medición

Midiendo las **81 consultas reales** de las dos pruebas con celular contra
los 774 fragmentos de entonces, los renglones de índice —
`«Cilantro ........... 51»` — salían así:

| | de 81 consultas |
|---|---|
| con un índice entre los 4 mejores | 20 (25 %) |
| con un índice como **el mejor** | 8 (10 %) |

Eran **10 fragmentos de 774**, el 1.3 % del corpus.

La causa es estructural y no un accidente de extracción: **un índice es una
lista de nombres de plantas.** Puntúa altísimo contra cualquier pregunta
sobre plantas y no responde nada. Es el fragmento con mejor relación
similitud/utilidad que puede existir, en el peor sentido.

**Ningún umbral lo arregla.** Un fragmento inútil que puntúa 0.7185 pasa
cualquier umbral razonable. Por eso la limpieza va **antes** de recalibrar
y no después: recalibrar sobre un corpus con índices habría medido el
ruido.

## Decisión

### 1. La ingesta descarta los renglones de índice

El filtro va en `_reconstruir_parrafos`, donde ya se descartaban la
plantilla y los pies de figura. Reingeridas las dos fuentes afectadas:
catálogo de plantas 125 → 120 y cartilla de fertilización 34 → 30.
**El corpus queda en 765 fragmentos.** Tras la limpieza, la polución de
índices en esas mismas 81 consultas es **0 %**.

### 2. El umbral del CU2 baja de 0.68 a 0.66

Y baja **por consecuencia de lo anterior**, que es lo que no se veía venir:
quitar los índices **bajó** las similitudes de las consultas que los
recuperaban, porque lo que puntuaba era el índice.

    Cuánto se demora en dar cosecha la papa    0.6883 -> 0.6865
    pero que plantas me sirven para interior   0.6755 -> 0.6643
    Que recomendaciones das para sembrar papa  0.7282 -> 0.7044

Varias consultas legítimas quedaron rozando el 0.68 o por debajo, así que
mantenerlo habría dejado sin citar cosas que el corpus **sí** responde. Con
0.66 pasan a citar cuatro consultas legítimas más: las plantas que no dan
frutos, cómo medir si el suelo está ácido, la cascarilla de huevo y las
plantas de interior.

**Bajar es menos arriesgado que antes**, y esto es lo que cierra el círculo
con el ADR-0010: el motivo por el que aquel ADR descartó el 0.65 era el
«no tengo esa información» firmado con la fuente, y su causa principal eran
justo los índices. Con ellos fuera, el riesgo de bajar es otro.

## Tres mediciones que contradicen al ADR-0010

Están en el comentario de `RAG_UMBRAL_SIMILITUD` para que no se pierdan, y
valen para el documento de grado más que el número:

- **La frontera que aquel ADR midió no existe.** Con 81 consultas reales,
  los rangos de legítimas y ajenas **se solapan y ningún umbral los
  separa**: «Que conocimiento en agricultura sabes» (no es CU2) puntúa
  **0.6779** y «Qué puedo hacer si mis plantas no dan frutos» (sí lo es)
  puntúa **0.6775**. Quien filtra la intención hoy es el agente (ADR-0013),
  no el umbral.
- **Los mensajes del CU3 y del CU4 puntúan entre los mejores.** «Y que
  están sembrando las otras huertas» da **0.7194**. Subir el umbral no
  protegería de ellos; solo el enrutamiento lo hace.
- **Lo verdaderamente ajeno se separa solo:** «Que carro está barato hoy en
  día» **0.5782**, los barrios entre 0.587 y 0.612.

De ahí que **el umbral ya no signifique lo mismo**. Hasta el ADR-0010
decidía responder o callar; con `CU2_RESPALDO_MODELO` activo decide **citar
o no citar**. Por encima se responde con la guía oficial y su atribución;
por debajo responde el modelo, sin fuente ninguna.

## La lección de método, que es la parte que más viaja al documento

**El primer resultado se anunció mal, y el error estaba en el
denominador.** La limpieza se presentó como «el 25 % de las consultas
mejoran». Ese 25 % contaba consultas cuya **recuperación** cambió, no
respuestas que la usuaria fuera a notar mejores.

Al desglosarlo, la mayoría eran barrios, saludos y mensajes del CU3 y del
CU4, **que nunca llegan al CU2**. Filtrando a consultas reales del CU2 con
un índice como mejor fragmento quedaban **dos**, más unas siete con el
índice en tercera o cuarta posición.

La mejora es real pero modesta. Lo que sí desaparece por completo es la
causa principal del modo de fallo de la cita vacía, que era el objetivo.

**Antes de dar un porcentaje, comprueba que el denominador sea lo que le
importa a la usuaria.** Recogido en el CLAUDE.md §12.

## Consecuencias

**La calibración del ADR-0010 queda obsoleta entera**, no solo su número:
aquella se hizo con 12 consultas positivas y 6 negativas escritas por el
autor, y estas son 81 de dos usuarias reales.
`scripts/calibrar_umbral.py`, que la produjo, se borró el 08/09/2026 y vive
en el historial de git.

**Las etiquetas de `scripts/calibrar_umbral_real.py` quedaron viejas.**
Varias consultas marcadas `DESCUBIERTA` dejaron de serlo cuando el corpus
pasó a nueve fuentes (ADR-0014). Ese script mide 21 consultas escritas a
mano contra las 81 reales que ya existen, así que conviene rehacerlo
leyendo de `mensaje`, que es lo que hizo la medición del 19/08.

**El corpus volvió a cambiar**, y con él cualquier medición anterior. Es la
cuarta vez en el proyecto y ya está anotado como tal en el CLAUDE.md §12.

## Lo que este ADR no resuelve

**`jbb_practicas_2022` no se puede reproducir**, y no lo causó esta
limpieza: la base tiene **62 fragmentos** de esa fuente y el código produce
**83**, comprobado revirtiendo el árbol a `b159cd2`. No se reingirió porque
no estaba autorizado y habría cambiado el corpus más de lo pedido. Mientras
siga así, **el corpus entero no es reproducible y toda calibración hereda
esa debilidad**, incluida esta.

**Falta etiquetar leyendo el fragmento recuperado de cada consulta.** La
frontera que importa no es «del dominio o no», es «el fragmento responde de
verdad o no». Eso exige leer los 81 textos uno por uno, es criterio del
autor y no es automatizable. Sin ello, **el 0.66 es un número razonable
pero no demostrado**.

**El modelo generativo quedó desalineado el mismo día, y es otra decisión.**
Railway pasó a `gemini-3.5-flash-lite` —los de la familia flash completa
daban 503 por sobrecarga, con tiempos de 10 a 138 s— mientras
`app/config.py` sigue declarando `gemini-3.6-flash`. El propio comentario de
ese archivo dice que el valor por defecto existe para dejar constancia de
con qué se probó, así que hoy se contradice, y el autor observó además que
el *lite* redacta peor. **Sigue sin decidirse y no lo decide este ADR**; la
tabla de los siete modelos medidos está en `docs/ESTADO.md`.

**Y un resto que no es de aquí:** los commits de ese día arrastraron dos
menciones a la fecha de siembra que el ADR-0018 no había alcanzado, porque
hablaban de ella en prosa y no con los nombres de código que se rastrearon
—`REGISTRO_NADA_QUE_ANOTAR` y la descripción de `registrar_huerta` en el
prompt del agente—. La segunda era la seria: el prompt decide el
enrutamiento, y describir una herramienta con campos muertos invita a
llamarla cuando no toca.
