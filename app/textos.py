"""Textos fijos que el backend envía sin pasar por el modelo.

La bienvenida y la ayuda son contenido estático (Fase 4, §1): no son
prompts y no deben ir a `app/agent/prompts/`. Pasarlas por el modelo
costaría dinero y latencia, e introduciría variabilidad en el único
mensaje que conviene que sea siempre idéntico.

Criterios de redacción (CLAUDE.md §11 y Fase 4, bloque 2 del prompt):
español colombiano, trato de usted, frases cortas, sin tecnicismos, un
máximo de 6 a 8 líneas por mensaje, y presentarse siempre como asistente
virtual y nunca como persona (CONPES 4144).

Redacción neutra en género a propósito: la comunidad es mayoritariamente
de mujeres, pero no exclusivamente.

Estos textos son los que más van a cambiar tras la primera ronda SUS de
la Fase 8. Están juntos aquí para que ajustarlos no obligue a tocar la
lógica.
"""

# Identificadores de los botones. Vuelven en el webhook cuando la usuaria
# pulsa, así que cambiarlos rompe los mensajes ya enviados.
BOTON_ACEPTO = "consentimiento_acepto"
BOTON_NO_ACEPTO = "consentimiento_no_acepto"

# CU3. El segundo y último momento binario del diseño (Fase 2, §1): no hay
# más botones que estos cuatro en todo el sistema.
BOTON_REGISTRO_CONFIRMO = "registro_confirmo"
BOTON_REGISTRO_DESCARTO = "registro_descarto"


# CU5. Sirve de bienvenida y de ayuda: la Fase 2 define un solo texto para
# ambos casos. Los ejemplos están en lenguaje natural, para enseñar cómo
# se pide sin convertir el bot en un menú.
BIENVENIDA = """Buenas. Soy el asistente virtual de huertas urbanas de Bosa Occidental.

Le puedo ayudar a:
- Cuidar su huerta: "mi tomate tiene bichos"
- Guardar los datos de su huerta: "sembré cilantro en marzo"
- Saber qué siembran cerca: "qué siembran por mi barrio"

Escríbame con sus propias palabras, o mándeme una nota de voz."""


# CU1. Cuerpo del mensaje con los botones [Acepto] / [No acepto].
SOLICITUD_CONSENTIMIENTO = """Antes de empezar necesito su permiso.

Para poder ayudarle guardo el nombre de su huerta, el barrio y lo que tiene sembrado. Eso se comparte con las demás huertas, para que aprendan unas de otras.

Su número de celular y su nombre no se le muestran a nadie.

¿Me da su autorización?"""


CONSENTIMIENTO_ACEPTADO = """Gracias. Ya puede usar el asistente.

Cuénteme de su huerta: cómo se llama, en qué barrio queda y qué tiene sembrado. Puede escribirlo o mandarme una nota de voz."""


# La nota de voz llegó pero no se pudo convertir en texto: fallo de la
# descarga, del modelo, o audio sin voz. Se ofrece escribir como salida,
# nunca como reproche: buena parte de las usuarias manda voz precisamente
# porque escribir le cuesta.
AUDIO_NO_ENTENDIDO = """Perdone, no logré entender la nota de voz.

¿Me la puede repetir? Ayuda hablar cerquita del celular y sin ruido alrededor.

Si prefiere, también me lo puede escribir."""


# --- CU3, registro de la huerta ---------------------------------------
# El resumen que va antes de los botones lo compone `registro.py` con los
# datos extraídos, no un modelo: tiene que decir exactamente lo que se va a
# guardar. Aquí están solo las partes fijas.

# El barrio es obligatorio en la base y sin él no se puede crear la huerta.
# Se pregunta en lenguaje natural, sin lista de opciones: un menú de ocho
# barrios es justo la barrera que el diseño evita (Fase 2, §1).
REGISTRO_FALTA_BARRIO = """Anoté lo que me contó de su huerta.

Para guardarlo me falta el barrio. ¿En qué barrio queda su huerta?"""


REGISTRO_GUARDADO = """Listo, ya quedó guardado.

Cuando siembre algo nuevo me cuenta y lo agrego."""


# No se le pide explicación ni se repregunta: es su decisión.
REGISTRO_DESCARTADO = """Listo, no guardé nada.

Si quiere lo intentamos otra vez, cuénteme de nuevo."""


# El borrador caducó o se perdió: la usuaria pulsó un botón de un mensaje
# viejo. Se le dice sin tecnicismos y se le ofrece la salida.
REGISTRO_SIN_BORRADOR = """Perdone, ya no tengo a la mano lo que iba a guardar.

¿Me cuenta otra vez qué tiene sembrado?"""


# Fallo al escribir en la base. Importa que quede claro que NO se guardó,
# para que no crea que sus datos están cuando no lo están.
REGISTRO_FALLO = """Perdone, no pude guardar la información en este momento.

No se guardó nada. ¿Lo intentamos de nuevo en un rato?"""


# --- CU2, orientación agroecológica -----------------------------------

# No se recuperó ninguna fuente por encima del umbral. Se responde con este
# texto fijo y NO se le pregunta al modelo de todos modos: sin respaldo
# oficial, su conocimiento solo podría ofrecerse advirtiendo que no está
# verificado (CLAUDE.md §6), y aquí vale más reconocer que no se sabe.
#
# Se evita decir "no encontré información", que suena a base de datos. Y se
# le ofrece reformular, porque muchas veces la pregunta era buena y lo que
# falló fue el vocabulario.
ORIENTACION_SIN_RESPALDO = """De eso no le puedo responder con seguridad, y prefiero no decirle algo que no me consta.

¿Me lo cuenta con otras palabras? A veces con más detalle sí le encuentro la respuesta.

También me puede preguntar por riego, abonos, plagas o cuándo cosechar."""


# Falló la llamada al modelo. Se distingue del caso anterior a propósito:
# ahí no había respaldo, aquí el sistema no pudo trabajar, y mezclarlos le
# haría creer que su pregunta está fuera de alcance cuando no lo está.
ORIENTACION_NO_DISPONIBLE = """Perdone, en este momento no pude consultar la información.

¿Me vuelve a preguntar en un ratico?"""


# ADR-0003: una sola respuesta, sin volver a insistir. La puerta queda
# abierta por si cambia de opinión, pero la iniciativa es suya.
CONSENTIMIENTO_RECHAZADO = """Entiendo, no hay problema.

Sin su autorización no puedo guardar ni consultar información, así que no le voy a insistir.

Si cambia de parecer, escríbame cuando quiera. Mientras tanto puede escribir "ayuda" para ver qué hago."""
