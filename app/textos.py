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

# Los rótulos de esos dos botones están aquí, y no escritos en el sitio que
# los envía, porque se usan dos veces: al mostrarlos y al anotar en la
# memoria qué pulsó la usuaria (ADR-0012). Lo que se guarda es lo que ella
# leyó en el botón, no su identificador interno.
ROTULOS_BOTONES_REGISTRO = {
    BOTON_REGISTRO_CONFIRMO: "Sí, guardar",
    BOTON_REGISTRO_DESCARTO: "No",
}


# CU5. Sirve de bienvenida y de ayuda: la Fase 2 define un solo texto para
# ambos casos. Los ejemplos están en lenguaje natural, para enseñar cómo
# se pide sin convertir el bot en un menú.
BIENVENIDA = """👋 Buenas. Soy el asistente virtual de huertas urbanas de Bosa Occidental.

Le puedo ayudar a:
🌱 Cuidar su huerta: "mi tomate tiene bichos"
📝 Guardar los datos de su huerta: "tengo sembrado cilantro"
🏘️ Saber qué siembran cerca: "qué siembran por mi barrio"

Escríbame con sus propias palabras, o mándeme una nota de voz 🎤."""


# CU1. Cuerpo del mensaje con los botones [Acepto] / [No acepto].
SOLICITUD_CONSENTIMIENTO = """Antes de empezar necesito su permiso.

Para poder ayudarle guardo el nombre de su huerta, el barrio y lo que tiene sembrado. Eso se comparte con las demás huertas, para que aprendan unas de otras.

Su número de celular y su nombre no se le muestran a nadie.

¿Me da su autorización?"""


# Solo el acuse. Las preguntas las hace el onboarding, una por mensaje
# (ADR-0016). Hasta el 17/08/2026 este texto pedía las tres cosas a la vez
# —nombre de huerta, barrio y sembrado— y de ahí salía una extracción
# pobre: era la causa raíz del CU3 que el ADR-0016 corrige.
CONSENTIMIENTO_ACEPTADO = """Gracias, ya quedó autorizado.

Le voy a hacer tres preguntas cortas para conocer su huerta."""


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

# No tiene huerta, es decir, no completó el onboarding (ADR-0016). No
# debería llegar aquí: el despachador atiende el onboarding antes que el
# agente. Se responde de todos modos porque un envío que no ocurre deja en
# la memoria un hueco que el agente no puede detectar (ADR-0012).
REGISTRO_SIN_HUERTA = """Antes de anotar lo que sembró necesito unos datos de su huerta.

Empecemos por ahí y ya seguimos."""


# El agente vio que contaba algo de su huerta, pero la extracción no sacó
# ningún dato aprovechable ("sembré algo el otro día"). Se le pregunta en
# vez de proponerle guardar un borrador vacío.
#
# **Solo se le pregunta la planta.** Pedirle además la fecha sería pedirle
# un dato que el sistema ya no guarda (ADR-0018), y encima en el mensaje
# que existe precisamente porque no se le entendió: cuantas menos cosas se
# le pidan a la vez, más probable es que la segunda vez salga bien. Es el
# mismo criterio del onboarding (ADR-0016).
REGISTRO_NADA_QUE_ANOTAR = """Me quedé con las ganas de anotarlo, pero no le entendí bien qué sembró.

¿Me cuenta qué planta es? Con el nombre me basta."""


# Cierre del CU3, después del botón [Sí, guardar]. Además de acusar el
# guardado, **encadena con el CU2**: hasta el 05/09/2026 terminaba en
# "cuando siembre algo nuevo me cuenta" y ahí se acababa la conversación,
# sin decirle qué más podía hacer.
#
# Los tres ejemplos son preguntas, nunca afirmaciones, y es deliberado: uno
# del tipo "tengo tomate" lo enrutaría el agente al CU3 y le ofrecería
# guardar un cultivo que ella no tiene.
#
# Y están escogidos entre lo que el corpus sí responde —siembra mide 0.7044
# en las consultas reales, y el riego y el abono los cubre el manual de
# compostaje de la FAO con sus 68 fragmentos—: invitar a preguntar algo que
# termine en "no tengo esa información" es peor que no invitar.
#
# No repiten el ejemplo de plagas de BIENVENIDA, que ella ya vio.
#
# Pendiente de medir en la Fase 7: esto sale en CADA registro confirmado,
# no solo en el primero. A la quinta planta que anote, la invitación puede
# sobrar. Condicionarla a la primera confirmación es cambio de código.
REGISTRO_GUARDADO = """✅ Listo, ya quedó guardado.

Cuando siembre algo nuevo me cuenta y lo agrego.

Por ahora cuénteme, ¿tiene alguna duda de su huerta? Pregúnteme sin pena:
🌱 "cómo se siembra la cebolla larga"
💧 "cada cuánto riego el cilantro"
♻️ "cómo hago abono con las cáscaras\""""


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

# Dejó de ser la respuesta habitual cuando no hay fuente oficial: con
# `CU2_RESPALDO_MODELO` activo, ese caso lo atiende ahora el modelo sin
# citar nada. Este texto queda para los tres casos en los que ese camino
# tampoco puede responder:
#
# - el modelo dio la pregunta por ajena a las huertas,
# - devolvió una respuesta atribuida a una fuente y hubo que descartarla,
# - el respaldo está apagado, que es el comportamiento del ADR-0010.
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


# Se añade al final de cualquier respuesta del CU2 que hable de salud.
#
# Hace falta porque las fuentes oficiales del corpus traen usos medicinales
# y toxicidad. Comprobado el 15/08/2026 contra el corpus real: «para qué
# sirve la limonaria» recupera un fragmento que la describe como
# «anticonceptiva» y «antiulceroso», y «qué mata es buena para el dolor de
# estómago» recupera usos tradicionales para fiebre y dolor de cabeza. Todo
# eso se responde citando al Jardín Botánico, es decir, con el sello de
# fuente verificada (CLAUDE.md §6).
#
# Que el documento sea oficial avala la botánica, no un consejo de salud
# para una persona concreta. La usuaria es mayoritariamente adulta mayor y
# puede estar medicada; una planta «buena para el estómago» no es inocua
# junto a un tratamiento.
#
# Va como texto fijo del backend y no como regla de prompt por lo mismo que
# el saludo y la ayuda (ADR-0006): a temperatura 0.4 una regla de prompt no
# es una garantía, y ya está medido que se incumplen —la prohibición de
# copiar la etiqueta `[OFICIAL – ...]` está en los dos prompts y aun así se
# cuela—. Una advertencia que falte una vez de cada diez es peor que no
# tenerla, porque falta justo cuando hace falta.
ADVERTENCIA_MEDICA = """⚠️ Eso que le conté es lo que dice la guía sobre la planta, no es un consejo médico.

Antes de tomar cualquier planta como remedio, consúltelo con su médico o en el centro de salud, sobre todo si usted toma alguna droga formulada."""


# --- CU4, qué siembran otras huertas -----------------------------------

# No hay otras huertas registradas todavía, o ninguna viene a cuento. No se
# distinguen los dos casos: a la usuaria le da igual el motivo, y en la
# Fase 8 el primero será el habitual durante las primeras sesiones.
#
# Se aprovecha para invitarla a registrar la suya, que es lo que hace
# crecer el dato comunitario. Sin presionar: se le cuenta para qué sirve.
COMUNIDAD_SIN_DATOS = """🌱 Todavía no tengo qué contarle de otras huertas por esa pregunta.

Esto se va llenando a medida que cada quien cuenta lo suyo. Si me cuenta qué tiene sembrado, las demás también pueden verlo.

Mientras tanto, pregúnteme por su huerta y le ayudo con lo que necesite."""


COMUNIDAD_NO_DISPONIBLE = """Perdone, en este momento no pude consultar lo de las otras huertas.

¿Me vuelve a preguntar en un ratico?"""


# --- Agente orquestador -----------------------------------------------

# Falló la llamada al modelo que decide qué hacer con el mensaje. No se
# puede saber siquiera qué quería, así que no se promete nada concreto.
# Se distingue de los fallos del CU2 y el CU4 porque allí sí se sabía qué
# preguntaba y solo falló la redacción.
AGENTE_NO_DISPONIBLE = """Perdone, en este momento no le puedo responder.

¿Me escribe otra vez en un ratico? Ahí le ayudo con lo que necesite."""


# ADR-0003: una sola respuesta, sin volver a insistir. La puerta queda
# abierta por si cambia de opinión, pero la iniciativa es suya.
CONSENTIMIENTO_RECHAZADO = """Entiendo, no hay problema.

Sin su autorización no puedo guardar ni consultar información, así que no le voy a insistir.

Si cambia de parecer, escríbame cuando quiera. Mientras tanto puede escribir "ayuda" para ver qué hago."""


# --- Onboarding de tres preguntas (CU3, ADR-0016) ---------------------
# Tres preguntas cerradas, una por mensaje: nombre de pila, barrio y
# nombre de la huerta. Antes se pedían las tres a la vez en un solo
# mensaje libre, y de ahí salía la extracción pobre que este onboarding
# corrige.
#
# El eco de lo contestado va DENTRO de la pregunta siguiente, sin pedir un
# "sí" aparte: tres confirmaciones seguidas convertirían tres preguntas en
# seis mensajes. La única confirmación explícita es la del final, con los
# botones que ya existen del CU3.

# "guardé" y "anoté" NO son sinónimos aquí. El nombre se persiste en el
# acto —la fila de `usuario` existe desde el consentimiento—, así que
# "guardé" es verdad. El barrio y el nombre de la huerta esperan en el
# borrador hasta el botón final, y decirle "guardé" sería falso en ese
# instante. "Guardado" queda reservado para después del botón.
ONBOARDING_ECO_NOMBRE = "✅ Entendido, guardé {nombre}."
ONBOARDING_ECO_BARRIO = "✅ Entendido, anoté el barrio {barrio}."


# Solo el nombre de pila: el apellido no se usa en ninguna parte del
# sistema, y pedirlo sería recoger un dato personal sin finalidad
# (Ley 1581 de 2012; Fase 3, §5).
ONBOARDING_PREGUNTA_NOMBRE = """👤 Para empezar, ¿cómo se llama usted?

Con el nombre me basta, no necesito el apellido."""


# Segundo intento: se le ofrece una salida. No es un reproche, es una
# puerta para quien no quiera dar su nombre.
ONBOARDING_NOMBRE_REINTENTO = """Perdone, no le entendí el nombre.

¿Cómo la llaman? Si prefiere no decirlo, escriba vecina."""


ONBOARDING_PREGUNTA_BARRIO = "🏡 ¿En qué barrio de Bosa queda su huerta?"


ONBOARDING_BARRIO_REINTENTO = """Perdone, no le entendí el barrio.

¿En qué barrio de Bosa queda su huerta? Escriba solo el nombre del barrio."""


# El modelo no encontró ningún barrio parecido en el catálogo.
ONBOARDING_BARRIO_SIN_CANDIDATOS = """No encontré ese barrio en mi lista.

¿Me lo escribe otra vez, por favor?"""


# Encabezado de la lista numerada de candidatos. El cuerpo con los nombres
# lo compone `onboarding.py`, porque es dinámico.
ONBOARDING_BARRIO_ENCABEZADO = "🏡 ¿Cuál de estos es su barrio? Escriba solo el número."


# Rótulos de las opciones fijas de esa lista. Se redactan por lo que
# HACEN y no por lo que significan: "Ninguno" y "Otro" son casi sinónimos
# en español y la usuaria no sabría cuál escoger.
ONBOARDING_OPCION_NINGUNO = "Ninguno de estos"
ONBOARDING_OPCION_OTRO = "Mi barrio no está en la lista"


# Ella respondió algo que no es un número. Acepta el dígito y la palabra
# (uno, dos, tres...), porque una nota de voz se transcribe literalmente y
# diría "tres" en letras, nunca un dígito: con un lector de solo dígitos,
# quien responde por voz no podría terminar nunca el onboarding.
ONBOARDING_NUMERO_NO_ENTENDIDO = """No entendí.

Por favor escriba solo el número de su opción, por ejemplo: 2"""


ONBOARDING_PREGUNTA_HUERTA = "🌱 ¿Cómo se llama su huerta?"


# Segundo intento: la salida para quien no le haya puesto nombre.
ONBOARDING_HUERTA_REINTENTO = """Perdone, no le entendí el nombre de la huerta.

¿Cómo la llama? Si no tiene nombre, escriba Mi huerta."""


# Cierre del onboarding, después del botón. Aquí sí se dice "guardado",
# porque aquí sí lo está.
#
# El ejemplo va entre comillas y dentro de una frase, no como lista de
# especies: una lista se lee como un menú del que escoger y parte de las
# usuarias la copiaría, mete un dato falso en `cultivo`, que es lo que
# alimenta el CU4. Así se lee como "así se dice", que es lo que hace falta:
# es el primer texto libre que ella escribe tras tres preguntas cerradas.
ONBOARDING_GUARDADO = """✅ Listo, ya quedó guardada su huerta.

Ahora cuénteme qué tiene sembrado. Puede decirlo sencillo, por ejemplo: "tengo tomate, cilantro y una mata de sábila".

Si ahora no se acuerda de todo, me va contando cuando quiera. También puede mandarme una nota de voz 🎤, si le queda más fácil."""


# Pulsó [No]. Se repiten las tres preguntas desde el principio: es lo que
# ella pidió al descartar.
ONBOARDING_DESCARTADO = """Listo, no guardé nada.

Volvamos a empezar."""


# Fallo al escribir en la base. Importa que quede claro que NO se guardó.
ONBOARDING_FALLO = """Perdone, no pude guardar la información en este momento.

No se guardó nada. ¿Lo intentamos de nuevo en un ratico?"""


# --- Saludo personalizado (ADR-0016) ----------------------------------
# Se antepone a la respuesta una vez cada 24 horas. Lo pone `memoria.py`
# al ENVIAR y **no entra en la memoria**: el nombre va cifrado en
# `usuario.nombre_usuario_cifrado` y `mensaje.contenido` va en claro
# (ADR-0012), así que guardarlo ahí anularía el cifrado.
SALUDO_PERSONALIZADO = "Hola, {nombre}."


# --- Acuse de la nota de voz (Fase 7) ---------------------------------
# Se manda en cuanto llega un audio, y **no entra en la memoria**: es la
# excepción declarada a "enviar y recordar van juntos" (CLAUDE.md §11).
# El motivo de esa regla —que un envío sin registrar deja un hueco que el
# agente no puede detectar— no aplica aquí, porque el acuse no dice nada
# que el agente vaya a necesitar. Recordarlo sí haría daño: gastaría uno
# de los diez huecos de la ventana en cada nota de voz.
#
# Son varias y se reparten barajadas para que no suene a máquina.
#
# **Hubo diez frases más, para el camino con RAG, y se retiraron el
# 18/08/2026** (ADR-0017, revisión): en la prueba con celular la
# conversación se sintió más lenta con el aviso que sin él.

# Llevan 🎤 a propósito: lo que más tranquiliza no es "espere", es saber
# que la nota de voz sí llegó.
ESPERA_AUDIO = (
    "🎤 Ya le estoy oyendo la nota de voz. Deme un momentico.",
    "🎤 Estoy escuchando lo que me mandó. Permítame tantico.",
    "🎤 Deme un momentico que estoy oyendo su mensaje.",
    "🎤 Ya mismo le oigo la razón que me dejó. Espéreme tantico.",
    "🎤 Permítame un momentico, que estoy oyendo su nota de voz.",
    "🎤 Estoy oyendo lo que me contó. Deme un segundito.",
)


# --- La base de datos no responde (ADR-0019) --------------------------
# Se manda cuando el mensaje ni siquiera se pudo reclamar, es decir cuando
# Supabase no contesta y el turno no llega a empezar. Hasta el 08/09/2026
# ese caso era **silencio absoluto**: el webhook ya le había devuelto 200 a
# Meta, así que no había reintento, y la usuaria se quedaba sin respuesta y
# sin señal de ninguna clase.
#
# Se envía con `whatsapp.enviar_texto` y **no entra en la memoria**, que es
# la segunda excepción declarada al CLAUDE.md §11 después del acuse de voz.
# Aquí ni siquiera es una excepción incómoda: con la base caída no hay dónde
# escribir, y como el fallo ocurre antes de `recordar_usuaria`, tampoco se
# guardó el mensaje de ella. La ventana se salta el turno entero y queda
# coherente, que es justo lo que el ADR-0012 quiere proteger.
#
# Sin tecnicismos (CLAUDE.md §11): "base de datos" no le dice nada a la
# usuaria. Lo que necesita saber son tres cosas y están las tres: que no fue
# culpa suya, que no se guardó nada, y que vuelva a escribir.
SERVICIO_NO_DISPONIBLE = """Perdone, en este momento no la puedo atender.

No es culpa suya y no se perdió nada de lo que tenía guardado, pero este mensaje no lo alcancé a recibir.

¿Me lo vuelve a escribir en una hora?"""
