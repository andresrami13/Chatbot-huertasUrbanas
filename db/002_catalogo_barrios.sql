-- =====================================================================
-- 002 — Catálogo de barrios (ADR-0002)
--
-- Los siete barrios que conforman la UPZ 84 Bosa Occidental según el
-- anteproyecto §5.3.1, más el valor `otro`.
--
-- El §7.1 del anteproyecto lista solo seis y omite Los 3 Sectores; se
-- siembran los siete y queda anotado como corrección pendiente del
-- documento (ADR-0002).
--
-- `otro` absorbe el caso de una huerta cuyo barrio no esté previsto, de
-- modo que ningún registro se pierde. Si aparece con frecuencia durante
-- la Fase 8, es señal de que al catálogo le falta un barrio.
--
-- Idempotente: puede reejecutarse sin duplicar filas.
-- =====================================================================

insert into public.barrio (codigo, nombre) values
    ('holanda',        'Holanda'),
    ('los_3_sectores', 'Los 3 Sectores'),
    ('el_regalo',      'El Regalo'),
    ('el_anhelo',      'El Anhelo'),
    ('la_cabana',      'La Cabaña'),
    ('el_bosque',      'El Bosque'),
    ('santa_fe',       'Santa Fe'),
    ('otro',           'Otro')
on conflict (codigo) do nothing;
