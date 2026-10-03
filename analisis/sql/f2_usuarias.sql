-- Fase 2 — una fila por usuaria, con las banderas que salen de las tablas.
--
-- Es la primera de las dos consultas de `scripts/evaluacion_formativa.py`.
-- De aquí salen: el universo (17), `completo_T1` (decisión D-2: la fila de
-- `huerta`), `completo_T2` (al menos un cultivo) y el arranque del tiempo de
-- T1 (decisión D-5: `consentimiento_en`).
--
-- Alimenta: Ef-1-G, el embudo del onboarding y `intentos_tareas.csv`.
-- SOLO LECTURA.

select u.id,
       left(u.identidad_hash, 8)              as hash8,
       u.consentimiento_en,
       (u.nombre_usuario_cifrado is not null) as dio_su_nombre,
       (h.id is not null)                     as tiene_huerta,
       (h.barrio_id is not null)              as tiene_barrio,
       (h.nombre_huerta is not null)          as tiene_nombre_huerta,
       coalesce(c.n, 0)                       as cultivos
  from usuario u
  left join huerta h on h.usuario_id = u.id
  left join (select h.usuario_id, count(c.id) as n
               from huerta h
               join cultivo c on c.huerta_id = h.id
              group by h.usuario_id) c on c.usuario_id = u.id
 order by u.consentimiento_en;
