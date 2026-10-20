-- Exact multiset equality preserves duplicates, NULLs, signed amounts and UTC instants.
select 'ad_performance' as source_name from ((select "date", "campaign_id", "channel", "spend_gbp", "impressions", "clicks" from {{ ref('ad_performance') }}) except all (select performance_date, campaign_id, channel, spend_gbp, impressions, clicks from {{ ref('stg_marketing__ad_performance') }})) as differences
union all
select 'ad_performance' as source_name from ((select performance_date, campaign_id, channel, spend_gbp, impressions, clicks from {{ ref('stg_marketing__ad_performance') }}) except all (select "date", "campaign_id", "channel", "spend_gbp", "impressions", "clicks" from {{ ref('ad_performance') }})) as differences
union all
select 'campaigns' as source_name from ((select "campaign_id", "campaign_name", "channel", "objective", "start_date", "end_date", "budget_gbp" from {{ ref('campaigns') }}) except all (select campaign_id, campaign_name, channel, objective, start_date, end_date, budget_gbp from {{ ref('stg_marketing__campaigns') }})) as differences
union all
select 'campaigns' as source_name from ((select campaign_id, campaign_name, channel, objective, start_date, end_date, budget_gbp from {{ ref('stg_marketing__campaigns') }}) except all (select "campaign_id", "campaign_name", "channel", "objective", "start_date", "end_date", "budget_gbp" from {{ ref('campaigns') }})) as differences
union all
select 'customers' as source_name from ((select "customer_id", "created_at" from {{ ref('customers') }}) except all (select customer_id, created_at from {{ ref('stg_marketing__customers') }})) as differences
union all
select 'customers' as source_name from ((select customer_id, created_at from {{ ref('stg_marketing__customers') }}) except all (select "customer_id", "created_at" from {{ ref('customers') }})) as differences
union all
select 'order_items' as source_name from ((select "order_item_id", "order_id", "product_id", "quantity", "unit_price_gbp", "gross_line_amount_gbp", "refund_amount_gbp", "net_line_amount_gbp" from {{ ref('order_items') }}) except all (select order_item_id, order_id, product_id, quantity, unit_price_gbp, gross_line_amount_gbp, refund_amount_gbp, net_line_amount_gbp from {{ ref('stg_marketing__order_items') }})) as differences
union all
select 'order_items' as source_name from ((select order_item_id, order_id, product_id, quantity, unit_price_gbp, gross_line_amount_gbp, refund_amount_gbp, net_line_amount_gbp from {{ ref('stg_marketing__order_items') }}) except all (select "order_item_id", "order_id", "product_id", "quantity", "unit_price_gbp", "gross_line_amount_gbp", "refund_amount_gbp", "net_line_amount_gbp" from {{ ref('order_items') }})) as differences
union all
select 'orders' as source_name from ((select "order_id", "order_timestamp", "customer_id", "status", "gross_order_amount_gbp", "refund_amount_gbp", "net_order_amount_gbp" from {{ ref('orders') }}) except all (select order_id, order_timestamp, customer_id, status, gross_order_amount_gbp, refund_amount_gbp, net_order_amount_gbp from {{ ref('stg_marketing__orders') }})) as differences
union all
select 'orders' as source_name from ((select order_id, order_timestamp, customer_id, status, gross_order_amount_gbp, refund_amount_gbp, net_order_amount_gbp from {{ ref('stg_marketing__orders') }}) except all (select "order_id", "order_timestamp", "customer_id", "status", "gross_order_amount_gbp", "refund_amount_gbp", "net_order_amount_gbp" from {{ ref('orders') }})) as differences
union all
select 'products' as source_name from ((select "product_id", "product_name", "category", "unit_price_gbp", "currency" from {{ ref('products') }}) except all (select product_id, product_name, category, unit_price_gbp, currency from {{ ref('stg_marketing__products') }})) as differences
union all
select 'products' as source_name from ((select product_id, product_name, category, unit_price_gbp, currency from {{ ref('stg_marketing__products') }}) except all (select "product_id", "product_name", "category", "unit_price_gbp", "currency" from {{ ref('products') }})) as differences
union all
select 'web_sessions' as source_name from ((select "session_id", "session_timestamp", "customer_id", "campaign_id", "channel", "source_medium", "device" from {{ ref('web_sessions') }}) except all (select session_id, session_timestamp, customer_id, campaign_id, channel, source_medium, device from {{ ref('stg_marketing__web_sessions') }})) as differences
union all
select 'web_sessions' as source_name from ((select session_id, session_timestamp, customer_id, campaign_id, channel, source_medium, device from {{ ref('stg_marketing__web_sessions') }}) except all (select "session_id", "session_timestamp", "customer_id", "campaign_id", "channel", "source_medium", "device" from {{ ref('web_sessions') }})) as differences
