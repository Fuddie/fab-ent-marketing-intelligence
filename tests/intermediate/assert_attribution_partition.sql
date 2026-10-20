select 'partition_or_count' as failure
from {{ ref('int_marketing__orders_attributed') }}
having count(*) <> (select count(*) from {{ ref('stg_marketing__orders') }})
    or count(*) <> count(*) filter (where attribution_status = 'attributed')
        + count(*) filter (where attribution_status = 'unattributed')
{% for amount in ['gross_order_amount_gbp', 'refund_amount_gbp', 'net_order_amount_gbp'] %}
    or sum({{ amount }}) is distinct from (select sum({{ amount }}) from {{ ref('stg_marketing__orders') }})
    or sum({{ amount }}) is distinct from
        coalesce(sum({{ amount }}) filter (where attribution_status = 'attributed'), 0)
        + coalesce(sum({{ amount }}) filter (where attribution_status = 'unattributed'), 0)
{% endfor %}
