# Registro de la prueba de aceptación

| | |
|---|---|
| **Identificador** | `RAC-CHU-001`, versión 1.0 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9) |
| **Estado** | Vigente. Se regenera al cerrar la Fase 8 |
| **Fecha** | 25/09/2026 |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 25/09/2026 | 1.0 | Reconstrucción desde `mensaje`, actividad A-14 | A. Ramírez |

## Introducción

Son los **resultados reales, el resultado por caso de uso y la bitácora de
ejecución** de la prueba de aceptación, que ISO/IEC/IEEE 29119-3 pide en sus
§8.9 y §8.10 y que la conformidad declarada en la
[política](politica-y-practicas-de-prueba.md) obliga a producir. Corresponde
al procedimiento PR-04 de la [especificación](especificacion-de-pruebas.md).

La aceptación no se planificó como sesión: la ejecutaron **personas reales
escribiéndole al número de producción desde sus celulares**, entre el 09 y
el 25/09/2026. Lo único que queda de ella es la conversación guardada en la
tabla `mensaje`, y este documento la reconstruye.

## Alcance

Los ocho casos de uso, en producción. No mide usabilidad —eso es la
evaluación SUS de la Fase 8— ni si el CU2 acierta —eso es el
[banco de preguntas](banco-de-preguntas.md)—. Mide **si cada caso de uso se
ejerció de verdad y con qué resultado**.

## Cómo se obtuvo, y por qué puede vivir aquí

    python -m scripts.registro_aceptacion

El script **no imprime una sola palabra de lo que escribió nadie**: solo
fechas, conteos y seudónimos —`P-01`, `P-02`…, por orden de
consentimiento—, que no se cruzan con nada fuera de la base. Ni barrio, ni
nombre de huerta, ni cultivos. Por eso su salida puede ir a este
repositorio, que es público, y la de `revisar_prueba_real`, que imprime la
conversación en claro, no.

`mensaje` no guarda qué herramienta respondió, así que el caso de uso se
deduce de las **marcas de los textos que compone el código**. Lo que
redacta el modelo sin marca fija no se le atribuye a ningún caso de uso: se
prefiere contar de menos a contar lo que no se puede demostrar.

Dos casos de uso no dejan rastro en `mensaje` **por diseño**. El CU1 se
atiende antes de la compuerta y no se recuerda (ADR-0012): su evidencia es
la fila de `usuario`, que **es** el consentimiento. El CU6 se da por
completado cuando existe la fila de `huerta`.

**Lo que este registro no puede distinguir**: si alguna de las filas es del
propio autor probando. No hay marca que lo diga. P-12, que consintió el
25/09, coincide con la verificación del ADR-0025 que se le propuso al
autor ese mismo día.

---

# 1. Bitácora por participante

Del 09 al 25/09/2026. 12 participantes, 273 mensajes: 130 de ellas y 143
del asistente.

| Participante | Consintió | Onboarding | Días con actividad | Mensajes de ella | De ellos, voz | CU2 con cita | CU2 sin respaldo | CU3 guardados | Cultivos | Sin respuesta registrada |
|---|---|---|---|---|---|---|---|---|---|---|
| P-01 | 09/09 | completo | 1 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| P-02 | 09/09 | completo | 3 | 13 | 0 | 3 | 0 | 1 | 1 | 1 |
| P-03 | 09/09 | completo | 1 | 19 | 3 | 1 | 0 | 2 | 26 | 0 |
| P-04 | 09/09 | completo | 1 | 11 | 0 | 0 | 0 | 0 | 0 | 0 |
| P-05 | 10/09 | sin completar | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| P-06 | 15/09 | sin completar | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| P-07 | 15/09 | completo | 1 | 24 | 6 | 2 | 1 | 2 | 15 | 0 |
| P-08 | 15/09 | completo | 1 | 9 | 0 | 2 | 0 | 1 | 14 | 0 |
| P-09 | 17/09 | completo | 1 | 11 | 0 | 2 | 2 | 1 | 1 | 0 |
| P-10 | 18/09 | completo | 1 | 17 | 0 | 6 | 1 | 1 | 4 | 0 |
| P-11 | 23/09 | completo | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| P-12 | 25/09 | completo | 1 | 7 | 0 | 0 | 1 | 0 | 0 | 0 |

**Once de doce volvieron un solo día.** Solo P-02 escribió en tres días
distintos. Es el dato que el ESTADO §3 señalaba como más revelador que el
SUS para medir adopción, y aquí dice que **la adopción sostenida no está
demostrada**: la gente probó, no se quedó.

---

# 2. Resultado por caso de uso

| CU | Evidencia en la base | Participantes | Respuestas | Periodo | Resultado |
|---|---|---|---|---|---|
| CU1 Consentimiento | Filas de `usuario` | 12 | — | 09/09 a 25/09 | **Pasa** |
| CU2 Orientación | «Fuente:» o texto del camino sin respaldo | 7 | 21 | 09/09 a 25/09 | **Pasa**, con los defectos de calidad del banco |
| CU3 Registro | Propuesta y «ya quedó guardado» | 6 | 19 | 09/09 a 18/09 | **Pasa**: 61 cultivos persistidos, todos confirmados |
| CU4 Comunidad | Listado del código | **0** | 0 | — | **Sin evidencia** |
| CU5 Ayuda | Texto de bienvenida | 1 | 2 | 10/09 a 15/09 | **Pasa**, con evidencia mínima |
| CU6 Onboarding | Filas de `huerta` | 10 de 12 | — | — | **Pasa**; 2 lo abandonaron |
| CU7 Búsqueda por cultivo | «ninguna tiene…» o redacción comunitaria | **0** | 0 | — | **Sin evidencia** |
| CU8 Mi huerta | Texto compuesto de «su huerta» | **0** | 0 | — | **Sin evidencia** |

## 2.1 Tres casos de uso sin aceptación en la base

**Ninguna de las doce participantes preguntó nunca por otras huertas ni por
la suya.** Se buscaron también sus mensajes con esa intención —«otras
huertas», «qué siembran», «qué tengo sembrado», «mi huerta»— y no hay
ninguno. No es que el CU4, el CU7 y el CU8 fallaran: **nadie los usó**.

Esto corrige lo que los documentos decían hasta hoy —«los ocho casos de
uso han pasado por aceptación»—, que se apoyaba en la declaración del autor
y no en la base. Puede que el autor los probara desde una fila que después
borró para repetir el onboarding —borrar `usuario` se lleva la
conversación por cascada—; si es así, **la evidencia se perdió**, y este
registro no puede darla por buena.

Lo único que los ejerce de punta a punta es `spike_despachador` —CU4 en la
comprobación 6, CU8 en la 7—, que es sistema y no aceptación. **El CU7 no
lo ejerce ni eso**: solo tiene casos de componente (MP-18).

## 2.2 La voz

9 de los 130 mensajes de ellas fueron **notas de voz**, de 2 participantes
—P-03 y P-07—. Ninguna quedó sin transcribir: el texto de «no logré
entender la nota de voz» no se recuerda, pero tampoco hay un mensaje de voz
suelto sin respuesta.

---

# 3. Anomalías observadas

Contrastadas con el [registro de incidencias](incidencias.md).

| Observación | Cantidad | Lectura |
|---|---|---|
| Reintentos del onboarding —barrio no encontrado o número no entendido— | 9 | Fricción conocida: el catálogo de barrios está incompleto (ADR-0024) |
| Onboarding descartado y vuelto a empezar | 1 | Ella pulsó «No» en el resumen y lo repitió |
| Onboarding sin completar | 2 (P-05, P-06) | P-06 coincide **en fecha** con la usuaria que, según el ADR-0024, abandonó el 15/09 porque su barrio no estaba en la lista. No se comprobó que sea ella |
| Registro del CU3 descartado | 1 | Funcionamiento correcto: confirmar antes de guardar (`CLAUDE.md` §4.7) |
| Confirmación del CU3 sin borrador que confirmar | 1 | «Ya no tengo a la mano lo que iba a guardar»: el borrador caducó o ya se había usado |
| El agente prometió reportar la pregunta a un equipo | 2, **ambas el 18/09** | Anteriores al ADR-0024 del 19/09, que lo prohíbe. **Después no hay ninguna**, aunque solo dos participantes escribieron después |
| Mensaje de ella sin respuesta registrada | 1 (P-02) | Puede ser un envío que no se recuerda a propósito; no es prueba de silencio |
| **Su nombre de pila queda en claro en `mensaje`** | todas las que completaron el onboarding | Ver INC-026 |

Fuera de `mensaje`, y por eso no aparecen arriba: **los ocho mensajes del
15/09 que no recibieron respuesta** por la identidad (INC-015, corregido
con el ADR-0023). Se descartaron antes de la compuerta y nunca llegaron a
guardarse.

## 3.1 El nombre de pila, en claro en la conversación

Reconstruir este registro destapó un defecto de datos personales. El
despachador guarda cada mensaje de ella **antes** de pasarlo al
onboarding (`recordar_usuaria`, ADR-0012), así que su respuesta a «¿cómo se
llama usted?» queda en `mensaje.contenido` **en claro**, mientras en
`usuario` va **cifrada** con AES-GCM (Fase 3 §5, capa 3). El agente la lee
de la ventana de memoria y la repite en respuestas que también se guardan.

El ADR-0016 dejó el saludo personalizado fuera de la memoria precisamente
porque «lleva el nombre, que va cifrado en `usuario` mientras
`mensaje.contenido` va en claro». La premisa no se cumple: el nombre ya
estaba en `mensaje` por la respuesta de ella. Queda registrado como
**INC-026** y la corrección es decisión del autor.

---

# 4. Resultado frente al criterio de salida

El criterio de salida de la aceptación (política §4.1) es «la conversación
completa desde un celular real, sin incidencia de severidad 1 o 2».

- **Cinco de los ocho casos de uso** tienen aceptación con evidencia:
  CU1, CU2, CU3, CU5 y CU6.
- **Tres no la tienen**: CU4, CU7 y CU8 (INC-027).
- Hay **incidencias de severidad 2 abiertas** que tocan la aceptación:
  INC-021 y INC-024 en el CU2, e INC-026 en los datos personales.

**La aceptación no se supera.** Lo que falta es barato de conseguir y no
necesita código: que alguien le pregunte al bot qué siembran las otras
huertas, si alguien más tiene un cultivo concreto, y qué tiene sembrado
ella. Tres mensajes, y regenerar este registro.
