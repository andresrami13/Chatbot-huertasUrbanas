# ADR-0013. El agente enruta y no relata, y el mensaje completo conserva su oportunidad

- **Estado:** Aceptada
- **Fecha:** 2026-08-08
- **Fase:** 6 (implementa el agente orquestador, Fase 2 §4)
- **Depende de:** [ADR-0006](0006-saludo-y-ayuda-sin-modelo.md),
  [ADR-0008](0008-borrador-de-registro-y-una-huerta-por-usuaria.md),
  [ADR-0010](0010-umbral-de-similitud-recalibrado.md),
  [ADR-0011](0011-fragmento-comunitario-solo-especies.md),
  [ADR-0012](0012-memoria-de-conversacion.md)

## Contexto

La Fase 2 §4 fija que las intenciones se resuelven con function calling y
enumera tres herramientas. Lo que ningún documento resuelve es **qué hace
el agente con lo que devuelven**, y esa pregunta resultó ser la que decide
la arquitectura entera.

Cuando el agente llega, el CU2 y el CU4 ya existen y están probados, y cada
uno **redacta su propia respuesta** con su prompt y su temperatura de 0.4.
El CU3 va más lejos: `proponer_registro` **envía él mismo** el resumen con
botones. Las tres piezas producen texto listo para la usuaria antes de que
el agente vuelva a intervenir.

## Decisión 1. El agente enruta; el texto de la herramienta se envía tal cual

La salida de cada herramienta llega a la usuaria **sin volver a pasar por
el modelo**.

La alternativa —realimentar el resultado para que el agente redacte la
respuesta definitiva— es la forma habitual de usar function calling, y aquí
es justamente la que rompe el sistema. La respuesta del CU2 está atada a la
guía del Jardín Botánico por su propio prompt: cita la entidad, no añade
conocimiento propio, no completa lo que el fragmento dejó cortado y no pasa
de 80 palabras. Una segunda pasada a temperatura 0.7 puede reescribirla,
perder la cita o rellenar el hueco, y **nada en el resultado delataría que
ocurrió**. Lo mismo con la etiqueta `[COMUNITARIO – huerta, barrio]` del
CU4, sin la cual la usuaria creería que todo se siembra en su barrio
(ADR-0001).

Dicho de otro modo: la jerarquía de fuentes de CLAUDE.md §6 no vive en el
agente, vive en los prompts de las herramientas. Pasar su salida por el
agente la anularía.

### Consecuencia: no hace falta bucle de llamadas

El plan de trabajo daba por necesario un bucle de llamadas a mano. Con esta
forma no lo es: **una sola pasada por el modelo**, se ejecuta lo que pidió
y se manda lo que devuelve. No hay nada que realimentar cuando el resultado
ya está listo para enviarse.

Queda señalado en el código como punto de extensión por si la Fase 7
encuentra un caso donde el agente sí deba comentar un resultado.

## Decisión 2. AFC desactivado

`types.AutomaticFunctionCallingConfig(disable=True)`, verificado en
`google-genai 2.14.0` el 08/08/2026.

Sin esto el SDK ejecuta las funciones por su cuenta en un bucle interno, y
el modelo daría el registro por hecho sin pasar por los botones, que es
exactamente lo que CLAUDE.md §4.7 prohíbe. El aviso estaba en la bitácora
desde la Fase 5 (`AFC is enabled with max remote calls: 10`) y era inocuo
solo mientras no hubiera herramientas declaradas.

## Decisión 3. `registrar_huerta` no lleva parámetros

El modelo decide **que** hay un registro; no extrae los datos.

La extracción se queda donde estaba: temperatura 0.1 fija, salida
estructurada y enum generado desde la tabla `barrio` (CLAUDE.md §8,
ADR-0002). Y trabaja sobre el **mensaje literal**, no sobre nada que haya
escrito el modelo. Si los datos vinieran del agente, "cebolla larga"
volvería como "cebolla" y "papa criolla" como "papa" —los dos casos que la
extracción tiene probados desde el 30/07/2026— y el enum del catálogo
dejaría de aplicarse.

## Decisión 4. Una cuarta herramienta, `mostrar_ayuda`

CLAUDE.md §5 enumera tres herramientas. Se añade una cuarta porque el
saludo posterior al consentimiento no cabe en ninguna de las tres y las dos
reglas que lo gobiernan se contradicen si no existe:

- La Fase 2 §4 exige que la bienvenida sea **texto fijo enviado por el
  backend, sin pasar por el modelo**.
- El [ADR-0006](0006-saludo-y-ayuda-sin-modelo.md) declara que, una vez hay
  consentimiento, **la intención la decide el function calling**, y que el
  atajo por palabras clave posterior a la compuerta es provisional.

`mostrar_ayuda` las cumple las dos: el modelo decide **cuándo**, el backend
decide **qué** y devuelve `textos.BIENVENIDA` palabra por palabra.

El atajo `es_saludo_o_ayuda` **sigue vigente antes de la compuerta**, que es
donde el ADR-0006 lo declara camino permanente. Lo que desaparece es solo
su uso posterior.

## Decisión 5. El mensaje completo conserva siempre su oportunidad

Es el hallazgo del paso, y solo pudo aparecer con el agente delante.

El prompt le pide al modelo que pase la duda **con las palabras de la
usuaria**, quitando el saludo. Ante un mensaje de doble intención —"a mi
tomate le salieron bichos y de paso sembré lechuga el mes pasado"— el
modelo hace lo correcto: separa la duda del dato y pasa solo la duda. Y la
recuperación falla. Medido contra el corpus real el 08/08/2026:

| Formulación | Mejor similitud | ¿Pasa 0.68? |
|---|---|---|
| "a mi mata de tomate le salieron unos bichitos verdes, que le echo" | 0.6911 | sí |
| mensaje mixto completo | 0.6840 | sí |
| **"a mi tomate le salieron bichos"** (el recorte del agente) | **0.6796** | **no** |
| "a mi tomate le salieron bichos, que le echo" | 0.6990 | sí |
| "mi tomate tiene bichos" | 0.6872 | sí |

**Cuatro diezmilésimas.** El umbral de 0.68 se calibró sobre doce mensajes
completos (ADR-0010) y su margen es de una centésima; ese margen no
sobrevive a que el agente recorte la consulta. Un recorte más corto pierde
señal: "que le echo" al final vale casi dos centésimas.

Por eso `consultar_orientacion` acepta un `respaldo` y, si el recorte no
recupera nada, **reintenta con el mensaje tal como lo escribió la usuaria**.
El recorte se intenta primero porque suele ser mejor, pero no puede
quitarle a la usuaria una respuesta que el sistema medido sí le daba. El
coste es una vectorización más, y solo cuando la primera falla.

Es la lección metodológica del proyecto aplicada al revés. Antes fue "medir
reproduciendo las condiciones de producción" (ADR-0010, ADR-0011); aquí es
**hacer que producción conserve las condiciones sobre las que existe la
medición**.

### Lo que este respaldo no arregla

Hay que decirlo con precisión: en la prueba, el reintento recuperó **un
fragmento a 0.6840**, y la respuesta resultante empieza reconociendo que no
tiene información específica sobre el tomate. Es honesta y cita la fuente,
pero no es la respuesta del caso simple, que recupera tres fragmentos. **El
respaldo evita el silencio; no mejora el corpus.**

## Decisión 6. El orden de ejecución lo impone el código

Cuando el modelo pide varias funciones:

- **Sin repetidas.** Dos llamadas iguales darían dos veces la misma
  respuesta.
- **La ayuda cede** ante cualquier otra: existe para cuando no hay nada que
  hacer.
- **El registro va siempre el último.** Es el que lleva botones, y los
  botones tienen que quedar en el último mensaje de la pantalla o la
  usuaria los pulsaría con otra respuesta encima. Coincide con la regla de
  orquestación de CLAUDE.md §5 —primero la necesidad urgente— pero no se
  confía al modelo: se ordena en el código.
- **Tope de tres**, para que un modelo desbocado no produzca una ráfaga de
  mensajes en el celular de la usuaria.

## Consecuencias

- **El CU4 queda enrutado sin clasificador aparte** (CLAUDE.md §4.9), que
  era la razón por la que estaba construido y sin conectar.
- **La prueba deja de ser determinista.** El agente corre a 0.7, así que el
  mismo mensaje puede tomar caminos distintos en dos ejecuciones. Un fallo
  aislado en `scripts/spike_agente.py` no es una medida; hay que repetir.
- **La bitácora registra si el modelo respetó las palabras de la usuaria**
  (`literal=True/False`) y si el CU2 tuvo que reintentar. Es el dato que la
  Fase 7 necesita para saber cuántas veces el recorte se queda corto.
- Una herramienta que falle no impide que se ejecute la otra: en un mensaje
  de doble intención, que falle la consulta no es motivo para perder
  también el registro.

## Hallazgo del cableado: la etiqueta se cuela en la respuesta

Al conectar el CU4 al despachador apareció un defecto que los spikes
anteriores no habían destapado. El modelo copió el rótulo de atribución en
el texto que lee la usuaria:

> "En la huerta **COMUNITARIO –** La Esperanza, del barrio El Regalo,
> reportaron que tienen sembrado fresa y uchuva."

La etiqueta `[COMUNITARIO – huerta, barrio]` es andamiaje del prompt: le
dice al modelo de quién es cada dato. Para la usuaria no significa nada.

Es **intermitente** —en la ejecución anterior del mismo caso salió bien—,
que es lo que lo hacía fácil de no ver. Se corrige por dos vías, y las dos
hacen falta:

1. **En los prompts**, que ahora dicen explícitamente que la marca es
   interna y no parte del nombre. Es la defensa principal.
2. **En el código**, con `recuperacion.limpiar_etiquetas`, que retira el
   rótulo conservando la atribución. Vive en `recuperacion.py` porque es el
   módulo que crea las etiquetas y el único que sabe qué forma tienen.

La red del código no sobra: una regla de prompt a temperatura 0.4 no es una
garantía, y lo que está en juego es la atribución, que el
[ADR-0011](0011-fragmento-comunitario-solo-especies.md) declara
imprescindible. Cuando la limpieza actúa lo deja en la bitácora, así que la
Fase 7 puede contar cuántas veces la regla del prompt no bastó.

Los dos spikes llevan ya una comprobación que lo habría atrapado.

## Lo que el agente NO resolvió, contra lo previsto

El [ADR-0008](0008-borrador-de-registro-y-una-huerta-por-usuaria.md) dejó
dicho que una consulta que mencione cultivos —"a mi tomate le salieron
bichos"— podía ofrecer guardar el tomate, y que **la mezcla era cosa del
agente**. No lo es.

Comprobado en el spike: el agente enruta las dos intenciones correctamente,
pero la extracción sigue corriendo sobre el mensaje literal completo, así
que saca `tomate` de la parte que era pregunta y el resumen ofrece
guardarlo sin fecha.

No se corrige aquí, y el motivo es el de siempre: la alternativa —que el
agente le pase a la extracción qué trozo es el registro— reintroduce la
paráfrasis del modelo sobre los nombres de especie, que es un problema
medido, a cambio de uno que la confirmación ya contiene. Ella ve "tomate,
sin fecha" en el resumen y puede descartar. **Queda como punto de
calibración de la Fase 7**, con datos reales de cómo mezclan las usuarias.

## Alternativas descartadas

- **Realimentar el resultado al modelo.** Descartada en la decisión 1:
  anula la jerarquía de fuentes sin dejar rastro.
- **Que el agente extraiga los datos del registro.** Duplica `extraccion.py`
  a temperatura 0.7, pierde el enum del catálogo y recorta los nombres
  compuestos de especie.
- **Que el agente redacte el saludo.** Incumple la Fase 2 §4 y vuelve
  variable el único mensaje que conviene que sea siempre idéntico.
- **Mantener `es_saludo_o_ayuda` después de la compuerta.** Ahorra una
  llamada al modelo en el mensaje más frecuente, pero contradice la
  consecuencia declarada del ADR-0006 y deja dos mecanismos de intención
  conviviendo.
- **Bajar el umbral para que el recorte pasara.** Reabre el ADR-0010 y deja
  entrar la consulta de trámite que se quedó a una centésima. El respaldo
  consigue lo mismo sin tocar la calibración.
