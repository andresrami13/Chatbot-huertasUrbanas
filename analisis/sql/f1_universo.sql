-- Fase 1 — universo y conteos de control.
--
-- Fija el tamaño del universo contra la base, no contra la documentación:
-- `docs/ESTADO.md` decía 12 usuarias al 25/09/2026 y el prompt de la
-- evaluación esperaba 16 elegibles. Ninguno de los dos acertaba.
--
-- Sustituya :fecha_extraccion por el valor de `analisis/salidas/parametros.json`.
-- SOLO LECTURA.

-- 1. Conteos de control.
select (select count(*) from usuario)                                            as usuarias,
       (select count(*) from huerta)                                             as huertas,
       (select count(*) from cultivo)                                            as cultivos,
       (select count(*) from mensaje where creado_en <= :fecha_extraccion)        as mensajes,
       (select count(*) from mensaje
         where rol = 'usuaria'     and creado_en <= :fecha_extraccion)            as mensajes_de_ella,
       (select count(*) from mensaje
         where rol = 'asistente'   and creado_en <= :fecha_extraccion)            as mensajes_del_asistente,
       (select count(*) from mensaje
         where tipo = 'audio'      and creado_en <= :fecha_extraccion)            as notas_de_voz,
       (select count(*) from mensaje
         where tipo = 'interactive' and creado_en <= :fecha_extraccion)           as pulsaciones_de_boton,
       (select count(*) from fragmento_comunitario)                              as fragmentos_comunitarios,
       (select count(*) from idempotencia_webhook)                               as filas_idempotencia,
       (select count(*) from idempotencia_webhook where estado <> 'procesado')    as idempotencia_sin_procesar,
       (select count(*) from onboarding_pendiente)                               as onboardings_en_curso,
       (select count(*) from registro_pendiente)                                 as borradores_de_registro;

-- 2. Ventana temporal de los datos analizados.
select min(creado_en) as primer_mensaje,
       max(creado_en) as ultimo_mensaje
  from mensaje
 where creado_en <= :fecha_extraccion;

select min(consentimiento_en) as primer_consentimiento,
       max(consentimiento_en) as ultimo_consentimiento
  from usuario;

-- 3. Una fila por usuaria, con las banderas que se pueden leer de las
--    tablas. `nombre_usuario_cifrado` NO prueba que el onboarding se
--    completara: se persiste en la primera de las tres preguntas
--    (`onboarding._atender_nombre`). Lo que lo prueba es la fila de huerta.
select u.id,
       left(u.identidad_hash, 8)                       as hash8,
       u.consentimiento_en,
       (u.nombre_usuario_cifrado is not null)          as dio_su_nombre,
       (h.id is not null)                              as completo_onboarding,
       (h.barrio_id is not null)                       as tiene_barrio,
       (h.nombre_huerta is not null)                   as tiene_nombre_huerta,
       coalesce(c.n, 0)                                as cultivos,
       coalesce(m.entrantes, 0)                        as mensajes_de_ella,
       coalesce(m.salientes, 0)                        as mensajes_del_asistente,
       coalesce(m.dias, 0)                             as dias_con_actividad
  from usuario u
  left join huerta h on h.usuario_id = u.id
  left join (select h.usuario_id, count(c.id) as n
               from huerta h
               join cultivo c on c.huerta_id = h.id
              group by h.usuario_id) c on c.usuario_id = u.id
  left join (select usuario_id,
                    count(*) filter (where rol = 'usuaria')   as entrantes,
                    count(*) filter (where rol = 'asistente') as salientes,
                    count(distinct (creado_en at time zone 'America/Bogota')::date) as dias
               from mensaje
              where creado_en <= :fecha_extraccion
              group by usuario_id) m on m.usuario_id = u.id
 order by u.consentimiento_en;
