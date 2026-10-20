with expected(order_id, campaign_id) as (values
('ORD-000001','CAM-0002'), ('ORD-000002','CAM-0001'), ('ORD-000003',null),
('ORD-000004',null), ('ORD-000005','CAM-0002'), ('ORD-000006',null),
('ORD-000007',null), ('ORD-000008','CAM-0001'), ('ORD-000009','CAM-0001'),
('ORD-000010','CAM-0002'), ('ORD-000011','CAM-0002'), ('ORD-000012',null))
select e.order_id from expected e
left join {{ ref('int_marketing__orders_attributed') }} a using (order_id)
where a.order_id is null or a.campaign_id is distinct from e.campaign_id
