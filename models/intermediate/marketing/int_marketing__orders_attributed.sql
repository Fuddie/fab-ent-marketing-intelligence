{{ config(materialized='table', schema='intermediate') }}
{{ marketing_orders_attributed(ref('stg_marketing__orders'), ref('int_marketing__order_attribution_candidates')) }}
