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


# ADR-0003: una sola respuesta, sin volver a insistir. La puerta queda
# abierta por si cambia de opinión, pero la iniciativa es suya.
CONSENTIMIENTO_RECHAZADO = """Entiendo, no hay problema.

Sin su autorización no puedo guardar ni consultar información, así que no le voy a insistir.

Si cambia de parecer, escríbame cuando quiera. Mientras tanto puede escribir "ayuda" para ver qué hago."""
