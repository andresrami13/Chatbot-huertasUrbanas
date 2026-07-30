Extraiga los datos de la huerta que aparezcan en el mensaje de la usuaria.

Es español de Colombia. El mensaje puede venir de una nota de voz
transcrita, así que puede traer titubeos, repeticiones y frases sin
terminar.

## Qué extraer

- **nombre_huerta**: como llama la usuaria a su huerta. Solo si lo dice.
- **barrio**: uno de los valores de la lista de abajo, y ninguno más.
- **cultivos**: cada planta que menciona tener sembrada, con su fecha
  aproximada de siembra.

## Lo que no debe hacer

- **No invente.** Si el mensaje no dice el nombre de la huerta, devuelva
  `null`. Si no dice el barrio, `null`. Si no menciona cultivos, la lista
  vacía. Un dato inventado se le mostrará a la usuaria como si lo hubiera
  dicho ella.
- **No complete lo que falta con lo que suele acompañarlo.** Que alguien
  siembre tomate no significa que también tenga cilantro.
- **No traduzca ni cambie los nombres de las plantas.** Si dice "cebolla
  larga", la especie es "cebolla larga", no "cebolla". Si usa un nombre
  local, consérvelo.
- **No trate una pregunta como un registro.** "¿Cuándo se siembra el
  tomate?" no dice que tenga tomate sembrado: no hay cultivo que extraer.

## Barrios admitidos

Devuelva el código, no el nombre. Si menciona un barrio que no está en esta
lista, use `otro`. Si no menciona ninguno, `null`.

{barrios}

## Fechas

Hoy es **{hoy}**. Resuelva las fechas con respecto a esa referencia.

- Devuelva `anio` y `mes` (1 a 12). El día no se pide: no se guarda.
- Si nombra un mes sin año ("sembré en marzo"), tome el más reciente ya
  pasado. Si ese mes aún no ha llegado este año, es del año anterior.
- Si la fecha es relativa ("hace dos meses", "hace rato"), calcúlela desde
  hoy.
- Si no dice nada de cuándo sembró, deje `anio` y `mes` en `null`.

**fecha_imprecisa** distingue lo que la usuaria precisó de lo que usted
aproximó:

- `false` cuando nombra un mes o una fecha concreta: "en marzo", "el mes
  pasado", "en abril del año pasado".
- `true` cuando la expresión es vaga y usted tuvo que estimar: "hace
  rato", "hace unos meses", "a principios de año", "cuando empezó a
  llover".
- `true` también si no hay fecha alguna.

Esa marca sirve para preguntarle después, en la confirmación, así que
márquela con honestidad: es mejor admitir que se aproximó.

## Ejemplos

Mensaje: "buenas, mi huerta se llama El Porvenir, queda en Holanda y
sembré tomate y cilantro en marzo"
→ nombre_huerta "El Porvenir", barrio `holanda`, dos cultivos —tomate y
cilantro— ambos en marzo del año correspondiente, `fecha_imprecisa` false.

Mensaje: "tengo unas maticas de cebolla larga desde hace rato"
→ nombre_huerta `null`, barrio `null`, un cultivo "cebolla larga" con la
fecha estimada y `fecha_imprecisa` true.

Mensaje: "y al tomate qué le echo para los bichos"
→ nombre_huerta `null`, barrio `null`, cultivos vacío. Es una consulta, no
un registro.

## Mensaje de la usuaria

{mensaje}
