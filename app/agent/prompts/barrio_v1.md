La usuaria escribió el nombre de su barrio. Encuentre en el catálogo de
abajo los que más se parezcan a lo que ella dijo.

Es español de Colombia, barrios de la localidad de Bosa en Bogotá. El texto
puede venir de una nota de voz transcrita, así que puede traer el nombre mal
escrito, partido o con palabras de más ("yo vivo en el barrio Holanda desde
hace años").

## Qué devolver

Hasta **{maximo}** códigos del catálogo, **ordenados del más parecido al
menos parecido**. Solo códigos que estén en la lista; ninguno inventado.

Si no se parece a ninguno, devuelva la lista vacía.

## Cómo elegir

- **Fíjese en el nombre del barrio, no en el relleno.** "queda en el
  Porvenir" es "EL PORVENIR"; el "queda en" no cuenta.
- **Una respuesta escueta apunta al barrio base, no a sus variantes.** El
  catálogo trae nombres que empiezan igual y siguen distinto —el mismo
  nombre a secas, y luego "… I SECTOR", "… II SECTOR", "… SECTOR" con un
  añadido—. Si ella dice solo el nombre, el más parecido es **el que no
  lleva añadido**, y las variantes van después.
- **Tolere la ortografía y el dictado.** Sin tildes, con la letra cambiada
  o pegado son el mismo barrio.
- **No convierta una cosa en otra.** Si dice un nombre que no está en el
  catálogo, no lo fuerce al que más letras comparta: es preferible la
  lista vacía o pocos candidatos a mandarle un barrio que no es el suyo.
- **No use el orden de la lista como pista.** El catálogo va alfabético y
  eso no dice nada de qué es más parecido.

## Catálogo de barrios

Devuelva el código, nunca el nombre.

{barrios}

## Lo que ella escribió

{mensaje}
