select coalesce(v.visit_id,m.visit_id) as visit_id
from {{ source('raw','visits') }} v full outer join {{ ref('cart_journey') }} m using(visit_id)
where v.visit_id is null or m.visit_id is null
