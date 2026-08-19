Extraiga los cultivos que la usuaria diga tener sembrados en su huerta.

Es español de Colombia. El mensaje puede venir de una nota de voz
transcrita, así que puede traer titubeos, repeticiones y frases sin
terminar.

## Qué extraer

- **cultivos**: cada planta que menciona tener sembrada.

Nada más. Ni la fecha de siembra, ni el nombre de la huerta, ni el barrio.
Los dos últimos se le preguntaron al principio, una por una, y ya están
guardados. Si el mensaje menciona cualquiera de las tres cosas, ignórelas:
la usuaria puede decir "sembré cilantro en marzo" y de ahí solo sale
"cilantro".

## Lo que no debe hacer

- **No invente.** Si no menciona cultivos, devuelva la lista vacía. Un dato
  inventado se le mostrará a la usuaria como si lo hubiera dicho ella.
- **No complete lo que falta con lo que suele acompañarlo.** Que alguien
  siembre tomate no significa que también tenga cilantro.
- **No traduzca ni cambie los nombres de las plantas.** Si dice "cebolla
  larga", la especie es "cebolla larga", no "cebolla". Si usa un nombre
  local, consérvelo.
- **No trate una pregunta como un registro.** "¿Cuándo se siembra el
  tomate?" no dice que tenga tomate sembrado: no hay cultivo que extraer.
- **No junte dos plantas en una.** "tomate y cilantro" son dos cultivos,
  no uno llamado "tomate y cilantro".

## Ejemplos

Mensaje: "buenas, mi huerta se llama El Porvenir, queda en Holanda y
sembré tomate y cilantro en marzo"
→ dos cultivos: "tomate" y "cilantro". El nombre de la huerta, el barrio y
la fecha se ignoran.

Mensaje: "tengo unas maticas de cebolla larga desde hace rato"
→ un cultivo: "cebolla larga".

Mensaje: "y al tomate qué le echo para los bichos"
→ cultivos vacío. Es una consulta, no un registro.

## Mensaje de la usuaria

{mensaje}
