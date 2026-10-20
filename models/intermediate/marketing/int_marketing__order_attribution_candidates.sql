{{ config(materialized='table', schema='intermediate') }}
{{ marketing_attribution_candidates(ref('stg_marketing__orders'), ref('stg_marketing__web_sessions'), ref('stg_marketing__campaigns')) }}
