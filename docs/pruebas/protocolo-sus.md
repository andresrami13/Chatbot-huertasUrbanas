# Protocolo del SUS y prompt para ejecutarlo

| | |
|---|---|
| **Identificador** | `SUS-CHU-001`, versión 1.0 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Estado** | Listo para aplicar |
| **Fecha** | 02/10/2026 |
| **Depende de** | [`docs/prueba_formativa.md`](../prueba_formativa.md) (`EVF-CHU-001` v1.1) |

Este documento es dos cosas a la vez: el **protocolo** con el que se aplica
el cuestionario SUS, y el **prompt** que se le pasa a una conversación nueva
para procesar los resultados. La sección 7 es el prompt; todo lo anterior es
lo que hay que hacer antes, con las personas.

**No contiene el nombre de nadie.** Las participantes se nombran por su
seudónimo; la correspondencia con nombres de pila está en la base y se
reconstruye como dice el §7.2.

---

# 1. Qué es esto y qué no

El SUS (System Usability Scale, Brooke 1996) mide **satisfacción percibida**:
diez frases que la persona puntúa de 1 a 5. Da un número de 0 a 100.

**No es el criterio de éxito del trabajo de grado.** Eso cambió el
28/09/2026: la hipótesis pide ahora completar sin asistencia el 80 % de las
tareas, y eso ya está medido en `EVF-CHU-001` —dio 0,80, justo en el
umbral—. El SUS entra como la **tercera pata** que el cuarto objetivo
específico nombra: eficacia, eficiencia y **satisfacción**.

**El 68 sigue sirviendo, pero como referencia y no como prueba.** Es el
promedio de la literatura y permite decir «por encima o por debajo de lo
corriente». Ya no es la hipótesis, y presentarlo como tal sería falso.

**Hay una sola ronda.** No existe una evaluación sumativa posterior.

---

# 2. A quién se le aplica

**Las siete participantes que completaron las tres tareas**, listadas por
seudónimo en `analisis/salidas/candidatas_sus.csv`:

| Seudónimo | Por qué está en la lista |
|---|---|
| P-02 | Única con actividad en tres días distintos |
| P-07 | 15 cultivos en dos intentos de registro |
| P-08 | 14 cultivos |
| P-09 | La que más consultas hizo: cuatro |
| P-10 | Tres consultas, y la que más insistió con un tema que el corpus no cubre |
| P-14 | — |
| P-15 | — |

**El sistema no guarda el teléfono de nadie** y no puede darlo: desde el
ADR-0023 la identidad es el BSUID que manda Meta, y el número no se
persiste ni hasheado. El nombre de pila sí está en claro en `mensaje`
(INC-026) y permite cruzar cada seudónimo con los contactos propios.

**Si alguna no contesta, se reporta como pérdida y no se sustituye.** Siete
es el universo, no una muestra: cambiarlo por conveniencia rompería la
correspondencia con `EVF-CHU-001`.

---

# 3. Cómo se aplica

**Por llamada telefónica.** Quien aplica lee las diez frases y la persona
contesta el número. No por WhatsApp, no por formulario.

**Nunca lo pide el propio bot.** Preguntar dentro de la herramienta que se
evalúa sesga la respuesta, y es regla del proyecto (`docs/pruebas/plan-de-pruebas.md` §4).

## 3.1 Lo que se dice al empezar

> Buenas, le habla Andrés, el de la Universidad Distrital, el que hizo el
> asistente de huertas de WhatsApp. ¿Tiene cinco minuticos?
>
> Le quiero hacer diez preguntas cortitas sobre cómo le pareció el
> asistente. No hay respuestas buenas ni malas, y lo que diga no me ofende:
> si estuvo malo, necesito saberlo para arreglarlo.
>
> Yo le leo una frase y usted me dice un número del 1 al 5. **El 1 es que no
> está nada de acuerdo y el 5 es que está totalmente de acuerdo.** El 3 es
> que ni lo uno ni lo otro. ¿Le parece?

Si la persona duda del número, se repite la escala; **no se le sugiere uno**
ni se interpreta por ella.

## 3.2 Reglas que no se pueden saltar

1. **Las diez frases se leen tal cual.** Parafrasearlas o explicarlas
   convierte el SUS en otra cosa y el número deja de ser comparable con la
   literatura.
2. **Se conserva la polaridad original**: las impares son positivas y las
   pares negativas, a propósito. No se convierten todas a positivo.
3. **Se aplican las diez, siempre y en orden.** Un SUS incompleto no se
   puntúa.
4. **Si la persona no entiende una frase**, se repite igual, más despacio.
   Si sigue sin entender, se anota `NS` y se sigue; se reporta, no se
   rellena.
5. **No se comenta la respuesta** ni se dice «ah, qué bien». Se agradece al
   final.

## 3.3 Lo que hay que anotar además del número

- Si pidió que se le repitiera la frase, y cuál.
- Si contestó algo que contradice el número (por ejemplo, «sí, facilito»
  y luego dice 2).
- La fecha y la duración de la llamada.

**Esto importa por un riesgo documentado.** Con personas adultas mayores,
los ítems negativos se contestan mal con más frecuencia e inflan el puntaje:
alguien que está de acuerdo con todo responde 5 a «es fácil» y 5 a «es
engorroso». El §5 explica cómo detectarlo.

---

# 4. Las diez frases

Traducción al español colombiano, trato de usted, conservando el orden y la
polaridad del instrumento original. «El asistente» es el chatbot de
WhatsApp.

| # | Frase | Polaridad |
|---|---|---|
| 1 | Creo que me gustaría usar este asistente a menudo. | + |
| 2 | Me pareció que el asistente era más complicado de lo necesario. | − |
| 3 | Me pareció fácil de usar. | + |
| 4 | Creo que necesitaría la ayuda de alguien que sepa de tecnología para poder usarlo. | − |
| 5 | Me pareció que las cosas que hace el asistente encajan bien unas con otras. | + |
| 6 | Me pareció que el asistente tenía muchas cosas que no cuadraban entre sí. | − |
| 7 | Me imagino que la mayoría de la gente aprendería a usarlo muy rápido. | + |
| 8 | Me pareció muy enredado de usar. | − |
| 9 | Me sentí con confianza usándolo. | + |
| 10 | Tuve que aprender muchas cosas antes de poder usarlo. | − |

Escala para todas: **1 = nada de acuerdo · 2 · 3 = ni lo uno ni lo otro ·
4 · 5 = totalmente de acuerdo.**

## 4.1 Preguntas abiertas, opcionales

Después de las diez, y **solo si la persona tiene tiempo**. No se puntúan;
sirven para el diagnóstico, que es lo que el SUS no da.

1. ¿Qué fue lo que más le sirvió?
2. ¿Hubo algo que no entendió o que le pareció enredado?
3. ¿Le faltó algo que usted esperaba que hiciera?
4. ¿Se lo recomendaría a otra persona de la huerta?

Se transcriben literalmente, sin resumir, y **no se versionan**: son texto
libre de una persona identificable.

---

# 5. Cómo se calcula

Para cada persona, con las diez respuestas de 1 a 5:

- **Ítems impares (1, 3, 5, 7, 9):** se resta 1 al número. Un 5 vale 4.
- **Ítems pares (2, 4, 6, 8, 10):** se resta el número a 5. Un 5 vale 0.
- Se suman los diez resultados y **se multiplica por 2,5**.

El resultado va de 0 a 100. **No es un porcentaje** y no se puede decir
«sacó 72 %».

## 5.1 Señales de que la respuesta no es válida

Hay que mirarlas antes de promediar nada:

| Señal | Qué puede significar |
|---|---|
| Las diez respuestas iguales | Aquiescencia: contestó por cortesía, no por criterio |
| Contradicción entre el 3 y el 8, o entre el 2 y el 3 | No entendió la polaridad de los ítems negativos |
| Todos los impares altos **y** todos los pares altos | Lo mismo, y es el riesgo documentado con adultas mayores |
| Más de dos `NS` | El cuestionario no se puede puntuar |

**Se reportan, no se corrigen.** Si aparecen en varias personas, el hallazgo
es sobre el instrumento y hay que escribirlo así.

## 5.2 Cómo se reporta

Con **siete personas**, cada número va con su conteo al lado y **no se dan
porcentajes**. Se reporta:

- El puntaje de cada participante, por seudónimo.
- La **mediana**, el mínimo y el máximo. La media solo si no hay valores
  extremos que la desvirtúen.
- Cuántas quedaron por encima y por debajo de 68, **en conteo**: «5 de 7»,
  nunca «el 71 %».
- Las señales del §5.1 que hayan aparecido.

---

# 6. Qué no se puede concluir

Tres límites que van escritos en el informe, no en una nota al pie:

1. **Siete personas no dan para estadística.** La mediana describe a estas
   siete y nada más.
2. **Quien aplica el cuestionario es quien construyó la herramienta.** Es el
   riesgo J-01 del plan de pruebas y no queda mitigado: la gente es amable
   con quien le hizo un favor. Si alguien más puede hacer las llamadas,
   mejor, y hay que decir quién las hizo.
3. **Las siete son las que completaron las tres tareas**, es decir, a
   quienes mejor les fue. **No representan a las dieciséis**: seis de las
   dieciséis se registraron y nunca usaron la herramienta, y a esas no se
   les pregunta nada. El SUS va a salir mejor de lo que sería con todas, y
   eso hay que declararlo.

---

# 7. Prompt para la conversación nueva

Lo que sigue se le pasa a una conversación nueva, con las respuestas ya
recogidas.

---

## 7.1 Contexto

Eres asistente de análisis de datos de un trabajo de grado de la
Especialización en Ingeniería de Software de la Universidad Distrital. El
proyecto es un chatbot de WhatsApp con IA para líderes de huertas urbanas de
Bosa, Bogotá.

**Lee primero, en este orden:** `CLAUDE.md`, `docs/ESTADO.md`,
`docs/prueba_formativa.md` (`EVF-CHU-001` v1.1) y este mismo documento
completo.

La evaluación formativa de usabilidad ya está medida y cerrada: eficacia y
eficiencia, con Ef-1-G global de 40/50 = 0,80. **Falta la tercera pata, la
satisfacción**, que es el cuestionario SUS aplicado por llamada a las siete
participantes que completaron las tres tareas. Tu trabajo es procesar esas
respuestas e integrarlas en el informe, produciendo la **versión 1.2**.

## 7.2 Reglas obligatorias

1. **Solo lectura sobre la base.** Ni `INSERT`, ni `UPDATE`, ni `DELETE`, ni
   migraciones.
2. **No descifres nada** ni leas las claves del entorno. El nombre de pila
   está en claro en `mensaje.contenido` (INC-026) y de ahí se cruza el
   seudónimo si hace falta; la columna `nombre_usuario_cifrado` no se toca.
3. **El teléfono no existe en la base** (ADR-0023). No lo busques.
4. **Privacidad de las salidas.** Este repositorio es público. Lo que lleve
   texto libre de una persona o permita identificarla va al `.gitignore`;
   lo que solo lleve seudónimos y conteos se versiona. Ante la duda, fuera.
5. **No inventes un puntaje.** Un cuestionario incompleto o con más de dos
   `NS` no se puntúa: se reporta como pérdida.
6. **Reporta las anomalías** del §5.1 en vez de corregirlas en silencio.
7. **Todo número con su conteo al lado** y sin porcentajes: son siete
   personas.
8. **Un solo script reproducible**, en español, que regenere las salidas
   desde cero, siguiendo la convención del proyecto:
   `python -m scripts.<nombre>`.

## 7.3 Entrada

El autor entrega las respuestas de las siete llamadas. Si no te las ha dado,
**pídelas antes de calcular nada**, en esta forma:

```
P-02: 4 2 5 2 4 1 5 1 5 2
P-07: ...
```

Diez números del 1 al 5 por persona, en el orden de las frases del §4, o
`NS` donde no haya respuesta. Junto a ellas, lo que el §3.3 manda anotar.

## 7.4 Qué hacer

1. **Calcula el puntaje SUS de cada participante** con la fórmula del §5, y
   comprueba a mano el primero para verificar que el script hace lo que
   dice.
2. **Aplica las comprobaciones del §5.1** antes de agregar nada, y reporta
   lo que encuentres.
3. **Calcula la mediana, el mínimo y el máximo**, y cuántas quedan por
   encima de 68 en conteo.
4. **Cruza el puntaje con lo que ya se midió** de cada participante en
   `analisis/salidas/intentos_tareas.csv`: cuántos cultivos registró,
   cuántas consultas hizo, si volvió otro día. No para correlacionar —son
   siete— sino para ver si alguien que lo usó mucho lo puntuó mal, o al
   revés. Si aparece, es un hallazgo.
5. **Escribe la versión 1.2 de `docs/prueba_formativa.md`**: añade la fila
   al historial de cambios, una ficha de la medida de satisfacción en el §6
   con el mismo formato de las demás, una sección de resultados, y actualiza
   las limitaciones y los pendientes. **No toques los números de eficacia y
   eficiencia**, que ya están cerrados.
6. **Regenera el Word** a partir del Markdown.
7. **Actualiza `README.md`, `CLAUDE.md`, `AGENTS.md` y `docs/ESTADO.md`**
   con el resultado, igual que se hizo con la v1.1.

## 7.5 Qué NO hacer

- **No conviertas el SUS en el criterio de éxito.** Ya no lo es.
- **No digas que el proyecto «pasó» o «no pasó» por el 68.** Es una
  referencia de la literatura, no un umbral de este trabajo.
- **No promedies sin mirar las señales del §5.1** ni presentes una media
  sobre siete valores sin dar también la mediana y el rango.
- **No extiendas la conclusión a las dieciséis participantes.** Las siete
  son a quienes mejor les fue, y el §6.3 explica por qué eso sesga al alza.
- **No propongas una segunda ronda.** El diseño es de una sola.

## 7.6 Salidas esperadas

| Archivo | Contenido | Versionado |
|---|---|---|
| `analisis/salidas/sus_respuestas.csv` | Las diez respuestas y el puntaje, por seudónimo | **No** |
| `analisis/salidas/sus_abiertas.md` | Las respuestas a las preguntas abiertas, literales | **No** |
| `scripts/calcular_sus.py` | El cálculo, reproducible | Sí |
| `docs/prueba_formativa.md` y su `.docx` | Versión 1.2, con la satisfacción integrada | Sí |
