-- Fase 2 — la conversación completa hasta la instantánea.
--
-- Es la segunda de las dos consultas de `scripts/evaluacion_formativa.py`.
-- $1 es `FECHA_EXTRACCION` de `analisis/salidas/parametros.json`: congela los
-- datos, no filtra usuarias.
--
-- Todo lo demás se deriva de estas filas en Python, porque depende de las
-- **marcas de los textos que compone el backend** y `mensaje` no guarda qué
-- herramienta respondió. El catálogo de marcas está en el propio script y la
-- justificación en `analisis/salidas/mapeo_esquema.md` §6.
--
-- Alimenta: Ef-3-G, Ey-1-G, Ey-5-S, PTb-1-G, el embudo, `consultas_T3.csv` y
-- `tiempos_respuesta_sistema.csv`.
-- SOLO LECTURA.

select usuario_id, rol, tipo, contenido, creado_en
  from mensaje
 where creado_en <= $1
 order by usuario_id, creado_en;
