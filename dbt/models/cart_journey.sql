{{ config(materialized='incremental', unique_key='visit_id', incremental_strategy='delete+insert',
 pre_hook="{% if is_incremental() %}DELETE FROM {{ this }} WHERE day BETWEEN '{{ var('start') }}'::date AND '{{ var('end') }}'::date{% endif %}") }}
with selected_visits as (
 select * from {{ source('raw','visits') }}
 {% if is_incremental() %}
 where day between '{{ var("start") }}'::date and '{{ var("end") }}'::date
 {% endif %}
), carts as (
 select h.visit_id,
  (array_agg(h.referrer order by h.seq,h.hit_id))[1] as first_cart_source,
  (array_agg(h.referrer order by h.seq desc,h.hit_id desc))[1] as last_cart_source,
  count(*) as cart_entries
 from {{ source('raw','hits') }} h join selected_visits v using(visit_id)
 where h.event='cart_entry' group by h.visit_id
), orders as (
 select h.visit_id,count(*) as orders
 from {{ source('raw','hits') }} h join selected_visits v using(visit_id)
 where h.event='order' group by h.visit_id
)
select v.*,c.first_cart_source,c.last_cart_source,coalesce(c.cart_entries,0) as cart_entries,
 coalesce(o.orders,0) as orders
from selected_visits v left join carts c using(visit_id) left join orders o using(visit_id)
