# ADR-0026. El top-k sube de 4 a 5

- **Estado:** Aceptada
- **Fecha:** 2026-09-25
- **Fase:** 7
- **Origen:** decisión del autor, tras la actividad A-17 del plan de pruebas

## Contexto

`RAG_TOP_K` decide cuántos fragmentos oficiales entran al contexto con el
que el modelo redacta la respuesta del CU2, y cuántas huertas candidatas
recupera el CU7 antes de comprobar la especie. La Fase 4 §7 lo fija en 4.

El banco de veinte preguntas destapó un caso que parecía de top-k: la
consulta real «Cual es la dirección de enlace al JBB para obtener el
formulario» tiene la respuesta en el corpus —los enlaces `forms.office.com`
del Protocolo de espacio público—, con similitud por encima del umbral
(0.6811), **en el puesto 5**. Con top-k 4 no entraría al contexto.

## Decisión

**`RAG_TOP_K` pasa a 5**, por decisión del autor. Es variable de entorno con
defecto en `app/config.py`, así que **el valor que manda es el de Railway**
si está definido allí: hay que comprobarlo, porque `/health` no lo informa.

## Lo que se midió antes de cambiarlo

Tres repeticiones de cada pregunta, con 4 y con 5, por el camino real
—`procesar_evento`, el agente y la redacción—, más el banco completo con 5.

| Pregunta | top-k 4 | top-k 5 |
|---|---|---|
| Enlace del formulario del JBB | 0 de 3 dan el enlace | 0 de 3 dan el enlace |
| D-06, hojas verdaderas para trasplantar | «2 a 4» en 2 de 3 | «2 a 4» en 3 de 3 |
| D-03, para qué sirve el romero | advertencia médica 3 de 3 | advertencia médica 3 de 3 |
| Banco: declina y cita (INC-020) | 0 de 20 | 0 de 20 |

**No se encontró beneficio ni daño apreciable.** Y la razón de que no haya
beneficio es instructiva: **la pregunta del formulario nunca llega a la
recuperación**. El agente la contesta por su cuenta, sin llamar al CU2
—comprobado envolviendo `agente.consultar_orientacion`: no se invoca—, así
que el top-k no entra en juego. Es un problema de enrutamiento (ADR-0013),
no de recuperación, y medir la recuperación con la consulta suelta —fuera
del agente— daba por hecho un camino que producción no toma. Es la lección
del `CLAUDE.md` §12, «mide reproduciendo las condiciones de producción»,
otra vez.

La otra pregunta que el banco señalaba, D-10 —tapar un desagüe está
prohibido—, tiene su fragmento en el puesto 32 y por debajo del umbral:
ningún top-k razonable la alcanza.

## Consecuencias

- **Es una decisión, no una calibración**, y así se declara en el documento
  de grado: el cambio no está respaldado por una mejora medida.
- **Afecta también al CU7**, que comparte la perilla: recupera hasta cinco
  huertas candidatas en vez de cuatro, antes de filtrar por la especie. Con
  diez huertas en la base, eso puede sumar una huerta a la respuesta.
- **El contexto del CU2 crece un 25 %.** Más texto para redactar, algo más
  de latencia y de coste por consulta; no se midió el efecto en tiempo.
- Revertir cuesta cambiar una variable en Railway, sin desplegar.
