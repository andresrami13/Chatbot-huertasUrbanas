-- =====================================================================
-- 008 — La fecha de siembra sale de `cultivo`
--
-- El CU3 dejó de pedir cuándo sembró. Se quitan las dos columnas que
-- sostenían ese dato: `fecha_siembra_aprox` y la "marca de imprecisión"
-- `fecha_imprecisa` de la Fase 4, Tabla 3.
--
-- ## Por qué
--
-- Era un dato de solo escritura. Lo insertaban `agregar_cultivos` y
-- `guardar_huerta`, y no lo leía ningún caso de uso: el CU2 no toca
-- `cultivo`, el agente tampoco, y el CU4 lo excluye a propósito. El único
-- lector era `scripts/revisar_prueba_real.py`, que lo imprimía para
-- diagnosticar.
--
-- Y que estorbaba ya estaba medido, aunque para otra cosa. Al calibrar el
-- fragmento comunitario (ADR-0011) se compararon cuatro formatos contra
-- consultas reales del CU4, y la separación media fue:
--
--     solo cultivos con fecha    0.0735
--     solo especies              0.1166   <- el que quedó
--
-- La fecha empeoraba la recuperación. Esta migración extiende al CU3 lo
-- que el CU4 ya había concluido.
--
-- ## Qué se pierde
--
-- La posibilidad de responder "¿cuándo sembré esto?" y cualquier
-- recordatorio de cosecha. Ninguna de las dos está en el alcance: la
-- Fase 2 no define un caso de uso que las pida. Si la Fase 8 las quisiera,
-- vuelven con otra migración.
--
-- Se ejecuta con `cultivo` en cero filas, así que no se pierde ningún
-- dato de ninguna usuaria.
--
-- Idempotente: puede reejecutarse sin fallar.
-- =====================================================================

alter table public.cultivo drop column if exists fecha_siembra_aprox;
alter table public.cultivo drop column if exists fecha_imprecisa;

comment on table public.cultivo is
    'Fuente de verdad del dato agronómico: qué especies tiene sembradas. '
    'Sin fecha de siembra desde la migración 008.';
