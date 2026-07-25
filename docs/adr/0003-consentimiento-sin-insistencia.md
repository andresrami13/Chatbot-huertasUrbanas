# ADR-0003. Consentimiento sin insistencia ante el rechazo

- **Estado:** Aceptada
- **Fecha:** 2026-07-25
- **Fase:** 5 (corrige el CU1 de la Fase 2)

## Contexto

El flujo alternativo 3a del CU1 (Fase 2) establece que, si la usuaria no
autoriza el tratamiento de datos, "el bot le indica que no es posible
continuar sin autorización y vuelve a presentar la solicitud; **el ciclo se
repite hasta que el usuario acepte**".

Ese bucle presenta dos problemas:

- **Legal.** La Ley Estatutaria 1581 de 2012 exige que el consentimiento
  sea libre. Repreguntar de forma indefinida tras una negativa es una forma
  de presión y tensiona ese principio.
- **De usabilidad.** El hallazgo de la Fase 1 es que 8 de 11 encuestadas
  desconfían de que se guarden sus datos personales. Insistir ante quien ya
  dijo que no actúa justo sobre esa desconfianza, y el criterio de éxito del
  proyecto es una puntuación SUS ≥ 68.

## Decisión

**El bot no insiste.** Ante un rechazo:

1. Responde **una sola vez** explicando que sin autorización solo puede
   ofrecer la ayuda (CU5), y qué implicaría autorizar.
2. No vuelve a presentar la solicitud de consentimiento por iniciativa
   propia.
3. La usuaria puede autorizar cuando quiera. Si más adelante lo pide o
   escribe algo que requiera consentimiento, el flujo se retoma desde la
   solicitud.

## Consecuencias

- Se mantiene intacta la compuerta: sin autorización, cualquier consulta o
  registro sigue bloqueado y solo se atienden el saludo y la ayuda.
- **No se persiste nada del rechazo**, conforme al CU1. El sistema no
  guarda que dijo que no; sencillamente no tiene registro de ella. Por
  tanto no hay estado que consultar, y la reaparición de la solicitud ante
  un mensaje posterior que requiera consentimiento no es un olvido del bot:
  es la consecuencia correcta de no haber persistido nada.
- La diferencia con el bucle original es que **no se repite dentro de la
  misma conversación tras la negativa**, y que la solicitud vuelve solo
  cuando la usuaria intenta algo que la necesita.

## Pendiente de corrección documental

Fase 2, CU1, flujo alternativo 3a: sustituir el ciclo por este
comportamiento.

## Alternativas descartadas

- **Mantener el bucle.** Descartada por los motivos de arriba.
- **Recordar el rechazo para no volver a preguntar nunca.** Requeriría
  persistir el hecho del rechazo, que es exactamente lo que el CU1 prohíbe.
