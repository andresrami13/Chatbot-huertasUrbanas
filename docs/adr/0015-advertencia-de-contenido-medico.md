# ADR-0015. Toda respuesta del CU2 que hable de salud lleva advertencia, puesta por el backend

- **Estado:** Aceptada
- **Fecha:** 2026-08-15
- **Fase:** 7
- **Origen:** la ampliación del corpus del [ADR-0014](0014-catalogo-de-fuentes-oficiales.md)

## Contexto

Las fuentes oficiales del Jardín Botánico no hablan solo de cultivar.
*Sembrando Biodiversidad* trae, por cada especie, secciones de **usos
medicinales y de toxicidad**, y el catálogo de plantas —todavía sin
ingerir— atribuye a la papayuela un uso «como tratamiento de diabetes,
enfermedades hepáticas».

Al ingerirlo, esto dejó de ser una hipótesis. Medido contra el corpus real
el 15/08/2026, ya en producción:

| Consulta | Lo que recupera |
|---|---|
| «para qué sirve la limonaria» | 0.7570 — «ser **anticonceptiva** (Cáceres 1996). Se ha empleado como estomáquico, carminativo, **antiulceroso** y antiespasmódico» |
| «qué mata es buena para el dolor de estómago» | 0.6939 — «usos tradicionales: calmante y para problemas estomacales, para **dolores de cabeza y fiebre**» |

Y la respuesta que el CU2 componía con eso terminaba en `Fuente: Jardín
Botánico de Bogotá José Celestino Mutis`: el sello del nivel más alto de la
jerarquía del CLAUDE.md §6, donde la respuesta se da por verificada.

**El documento oficial avala la botánica, no un consejo de salud para una
persona concreta.** Y el perfil de usuaria agrava la distancia entre las dos
cosas: mayoritariamente adultas mayores, muchas medicadas. Una planta «buena
para el estómago» no es inocua junto a un tratamiento formulado.

Ninguna fase documentada previó este caso. Las fases 2 y 4 dan por supuesto
que una fuente oficial de agricultura urbana solo dice cosas de agricultura
urbana.

## Decisión 1. La advertencia la pone el backend, no el prompt

Texto fijo en `app/textos.py`, añadido por el código al final de la
respuesta. Es el mismo criterio del [ADR-0006](0006-saludo-y-ayuda-sin-modelo.md)
para el saludo y la ayuda, y del [ADR-0013](0013-agente-orquestador.md) para
las herramientas del agente: **el modelo decide cuándo, el backend decide
qué y manda el texto literal.**

Una regla de prompt era la alternativa obvia y se descartó con evidencia
propia: a temperatura 0.4 las reglas de prompt se incumplen de forma
intermitente, y está medido en este mismo proyecto —la prohibición de copiar
la etiqueta `[OFICIAL – ...]` está escrita en los dos prompts de redacción y
aun así se cuela, por eso existe la red de `recuperacion.limpiar_etiquetas`.

Una advertencia que falte una vez de cada diez es peor que no tenerla,
porque falta justo en el mensaje en que hacía falta. Va aparte, además, para
que no consuma el presupuesto de 80 palabras del prompt del CU2.

## Decisión 2. Se mira el texto que sale, no el fragmento que entra

La otra opción era marcar el fragmento en la ingesta, con una columna nueva
en `fragmento_oficial`. Cubre menos, y por una razón que no es de
comodidad: **no alcanza al camino sin respaldo**.

Desde que el CU2 responde con el conocimiento del modelo cuando nada supera
el umbral, hay un camino en el que no existe ningún fragmento que marcar. Y
es el más expuesto de los dos, porque ahí la respuesta ni siquiera está
atada a un documento.

Mirando el texto que se va a enviar quedan cubiertos los dos caminos, y
cualquiera que se añada después. No hace falta migración.

El vocabulario que dispara la advertencia **tira a ancho a propósito**:
advertir de más cuesta dos renglones; advertir de menos falla en el único
mensaje que importaba.

## Comprobación

Siete consultas contra el corpus real y el CU2 corriendo entero, 7 de 7:

- **Advierte** en «para qué sirve la limonaria», «qué mata es buena para el
  dolor de estómago» y «la manzanilla para qué es buena». Las tres
  respuestas hablaban de fiebre, migraña, cólicos o dolores menstruales.
- **No advierte** en «cada cuánto regar», «bichitos verdes en la mata de
  tomate», «cómo hago compost» ni «cuándo cosecho la acelga».

## Consecuencias

- El CU2 puede pasar de 8 a 10 renglones cuando la advertencia entra. Es
  más de lo que fija el CLAUDE.md §11, y se acepta: el mensaje que se pasa
  de largo es exactamente aquel en el que la usuaria necesita leer que eso
  no es un consejo médico.
- **Lo que este ADR no hace es filtrar el contenido.** El bot sigue
  contando lo que dice la guía, incluida la palabra «anticonceptiva». Se
  decidió así el 15/08/2026: ese contenido interesa a las usuarias, y
  recortarlo sería decidir por ellas qué parte de una publicación pública
  pueden leer. Lo que se corrige es el **sello de verificado** que la
  atribución le ponía encima.
- Queda por calibrar en la Fase 7 si el vocabulario acierta con consultas
  reales. Los aciertos se cuentan en la bitácora, sin el contenido de la
  respuesta (CLAUDE.md §11).