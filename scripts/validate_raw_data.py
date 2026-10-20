"""Validate the synthetic source snapshot; exit nonzero on a failed invariant."""
import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    'campaigns': 'campaign_id,campaign_name,channel,objective,start_date,end_date,budget_gbp',
    'ad_performance': 'date,campaign_id,channel,spend_gbp,impressions,clicks',
    'web_sessions': 'session_id,session_timestamp,customer_id,campaign_id,channel,source_medium,device',
    'customers': 'customer_id,created_at',
    'orders': 'order_id,order_timestamp,customer_id,status,gross_order_amount_gbp,refund_amount_gbp,net_order_amount_gbp',
    'order_items': 'order_item_id,order_id,product_id,quantity,unit_price_gbp,gross_line_amount_gbp,refund_amount_gbp,net_line_amount_gbp',
    'products': 'product_id,product_name,category,unit_price_gbp,currency',
}
PAID = {'Meta Paid Social', 'Google Paid Search', 'TikTok Paid Social'}
SOURCES = {'Meta Paid Social': 'facebook / paid_social', 'Google Paid Search': 'google / cpc', 'TikTok Paid Social': 'tiktok / paid_social', 'Direct': '(direct) / (none)', 'Organic': 'google / organic'}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    check(value.endswith('Z'), f'UTC timestamp required: {value}')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    check('2025-01-01' <= parsed.date().isoformat() <= '2025-12-31', f'Timestamp out of range: {value}')
    return parsed


def london_date(value):
    # Europe/London's 2025 BST interval, expressed in UTC; no external tzdata needed.
    return (value + timedelta(hours=int(datetime(2025, 3, 30, 1, tzinfo=timezone.utc) <= value < datetime(2025, 10, 26, 1, tzinfo=timezone.utc)))).date().isoformat()


def amount(value):
    parsed = Decimal(value)
    check(parsed.is_finite() and parsed >= 0 and parsed.as_tuple().exponent == -2, f'Invalid GBP amount: {value}')
    return parsed


def validate():
    tables = {}
    for name, columns in REQUIRED.items():
        path = ROOT / 'data' / 'raw' / f'{name}.csv'
        check(path.is_file(), f'Missing {path}')
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            check(set(columns.split(',')) <= set(reader.fieldnames or []), f'Missing columns: {name}')
            tables[name] = list(reader)
        check(tables[name], f'Empty table: {name}')
        keys = columns.split(',')[:1] if name != 'ad_performance' else ['date', 'campaign_id', 'channel']
        identities = [tuple(row[k] for k in keys) for row in tables[name]]
        check(all(all(key) for key in identities) and len(identities) == len(set(identities)), f'Invalid primary key: {name}')
    campaigns = {r['campaign_id']: r for r in tables['campaigns']}
    customers = {r['customer_id']: timestamp(r['created_at']) for r in tables['customers']}
    products = {r['product_id']: r for r in tables['products']}
    orders = {r['order_id']: r for r in tables['orders']}
    for row in products.values():
        amount(row['unit_price_gbp'])
        check(row['currency'] == 'GBP', 'Product currency')
    for row in campaigns.values():
        check(date(2025, 1, 1) <= date.fromisoformat(row['start_date']) <= date.fromisoformat(row['end_date']) <= date(2025, 12, 31), 'Campaign dates')
        check(row['channel'] in PAID and row['objective'] in {'Sales', 'Traffic', 'Awareness'}, 'Campaign classification')
        check(amount(row['budget_gbp']) > 0, 'Campaign budget')
    def campaign_link(row, day):
        check(row['campaign_id'] in campaigns, 'Campaign foreign key')
        campaign = campaigns[row['campaign_id']]
        check(row['channel'] == campaign['channel'], 'Campaign channel mismatch')
        check(campaign['start_date'] <= day <= campaign['end_date'], 'Activity outside campaign dates')
    spend = defaultdict(Decimal)
    for row in tables['ad_performance']:
        check(date(2025, 1, 1) <= date.fromisoformat(row['date']) <= date(2025, 12, 31), 'Ad date range')
        campaign_link(row, row['date'])
        spend[row['campaign_id']] += amount(row['spend_gbp'])
        check(int(row['impressions']) >= 0 and int(row['clicks']) >= 0, 'Negative impressions/clicks')
    expected_ad_keys = set()
    for campaign in campaigns.values():
        day = date.fromisoformat(campaign['start_date'])
        end = date.fromisoformat(campaign['end_date'])
        while day <= end:
            expected_ad_keys.add((day.isoformat(), campaign['campaign_id'], campaign['channel']))
            day += timedelta(days=1)
    check(expected_ad_keys == {(r['date'], r['campaign_id'], r['channel']) for r in tables['ad_performance']}, 'Incomplete daily campaign coverage')
    sessions = defaultdict(list)
    anonymous = False
    for row in tables['web_sessions']:
        t = timestamp(row['session_timestamp'])
        check(row['customer_id'] == '' or row['customer_id'] in customers, 'Session customer foreign key')
        check(row['channel'] in SOURCES and row['source_medium'] == SOURCES[row['channel']], 'Session channel/source')
        check(row['device'] in {'mobile', 'desktop', 'tablet'}, 'Session device')
        if row['customer_id']:
            check(customers[row['customer_id']] <= t, 'Session predates customer')
        else:
            anonymous = True
        if row['campaign_id']:
            campaign_link(row, london_date(t))
            if row['customer_id']:
                sessions[row['customer_id']].append((t, row['session_id'], row['campaign_id']))
        else:
            check(row['channel'] in {'Direct', 'Organic'}, 'Paid session missing campaign')
    totals = defaultdict(lambda: [Decimal(0), Decimal(0), Decimal(0)])
    multi_product = defaultdict(set)
    for row in tables['order_items']:
        check(row['order_id'] in orders and row['product_id'] in products, 'Order-item foreign key')
        qty = int(row['quantity'])
        check(qty > 0, 'Nonpositive quantity')
        unit, gross, refund, net = [amount(row[k]) for k in ['unit_price_gbp', 'gross_line_amount_gbp', 'refund_amount_gbp', 'net_line_amount_gbp']]
        check(unit == amount(products[row['product_id']]['unit_price_gbp']), 'Product price mismatch')
        check(gross == qty * unit and refund <= gross and net == gross - refund, 'Line amount reconciliation')
        for i, value in enumerate([gross, refund, net]):
            totals[row['order_id']][i] += value
        multi_product[row['order_id']].add(row['product_id'])
    assignments = {}
    statuses = Counter()
    for row in orders.values():
        t = timestamp(row['order_timestamp'])
        check(row['customer_id'] in customers, 'Order customer foreign key')
        check(customers[row['customer_id']] <= t, 'Order predates customer')
        values = [amount(row[k]) for k in ['gross_order_amount_gbp', 'refund_amount_gbp', 'net_order_amount_gbp']]
        gross, refund, net = values
        check(row['order_id'] in totals and totals[row['order_id']] == values, 'Order-item totals mismatch')
        check(refund <= gross and net == gross - refund, 'Order net/refund mismatch')
        status = row['status']
        check(status in {'completed', 'cancelled', 'refunded', 'partially_refunded'}, 'Unknown order status')
        check((status == 'completed' and refund == 0) or (status in {'cancelled', 'refunded'} and refund == gross) or (status == 'partially_refunded' and 0 < refund < gross), 'Status/refund inconsistency')
        statuses[status] += 1
        candidates = [s for s in sessions[row['customer_id']] if t - timedelta(days=7) <= s[0] < t]
        assignments[row['order_id']] = max(candidates)[2] if candidates else None
    # These independent expected assignments protect the deliberately isolated fixtures.
    expected = [2, 1, None, None, 2, None, None, 1, 1, 2, 2, None]
    for i, campaign in enumerate(expected, 1):
        check(assignments[f'ORD-{i:06d}'] == (f'CAM-{campaign:04d}' if campaign else None), f'Attribution fixture {i} failed')
    # Check fixture input shapes too, so deleting an excluded touch cannot pass unnoticed.
    all_sessions = tables['web_sessions']
    def touches(i):
        return [r for r in all_sessions if r['customer_id'] == f'CUS-{i:06d}']
    for i, count in {1: 3, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 0, 8: 1, 9: 2, 10: 1, 11: 1, 12: 0}.items():
        check(len(touches(i)) == count, f'Fixture {i} session coverage')
    def delta(i, touch=0):
        return timestamp(orders[f'ORD-{i:06d}']['order_timestamp']) - timestamp(touches(i)[touch]['session_timestamp'])
    check(delta(2) == timedelta(days=7) and delta(3) == timedelta(days=7, seconds=1), 'Seven-day boundary cases')
    check(delta(4, 0) == timedelta(0) and delta(4, 1) < timedelta(0), 'At/after purchase cases')
    check(delta(5, 0) == delta(5, 1), 'Timestamp tie case')
    check([r['channel'] for r in touches(1)] == ['Meta Paid Social', 'Google Paid Search', 'Direct'], 'Direct override case')
    check([r['channel'] for r in touches(6)] == ['Organic', 'Direct'] and touches(9)[1]['channel'] == 'Organic', 'Organic cases')
    check(any(r['customer_id'] == '' and r['campaign_id'] for r in all_sessions) and anonymous, 'Anonymous paid case')
    check(touches(8)[0]['session_timestamp'][:7] != orders['ORD-000008']['order_timestamp'][:7], 'Cross-month case')
    check(orders['ORD-000010']['status'] == 'cancelled' and orders['ORD-000011']['status'] == 'refunded', 'Status fixtures')
    attributed = Counter(c for c in assignments.values() if c)
    check(all(spend[c] > 0 and not attributed[c] for c in ['CAM-0023', 'CAM-0024']), 'Spend without attributed orders')
    utilisation = [spend[c] / amount(row['budget_gbp']) for c, row in campaigns.items()]
    check(any(Decimal('.95') <= u <= 1 for u in utilisation) and any(u > 1 for u in utilisation), 'Near/over-budget cases')
    check(max(Counter(r['customer_id'] for r in orders.values()).values()) > 1, 'Repeat customers')
    check(any(len(p) > 1 for p in multi_product.values()), 'Multi-product orders')
    check(20 <= len(campaigns) <= 25 and 25 <= len(products) <= 35 and len(customers) == 1500 and 12000 <= len(all_sessions) <= 18000 and 2000 <= len(orders) <= 3000, 'Expected volumes')
    print('PASS: files/columns, keys, foreign keys, dates, amounts, campaign consistency, reconciliation and attribution edge cases')
    print('\nDATA PROFILE (synthetic; GBP; raw timestamps UTC)')
    for name, rows in tables.items():
        print(f'{name}: {len(rows):,} rows')
        field = {'campaigns': 'start_date', 'ad_performance': 'date', 'web_sessions': 'session_timestamp', 'customers': 'created_at', 'orders': 'order_timestamp'}.get(name)
        if field:
            print(f'  {field}: {min(r[field] for r in rows)} .. {max(r[field] for r in rows)}')
        if name == 'campaigns':
            print(f'  end_date: {min(r["end_date"] for r in rows)} .. {max(r["end_date"] for r in rows)}')
    print('Statuses:', dict(sorted(statuses.items())))
    print('Channels:', ', '.join(sorted({r['channel'] for r in all_sessions})))
    print(f'Total spend: {sum(spend.values()):,.2f}')
    for label, field in [('Gross revenue', 'gross_order_amount_gbp'), ('Refunds/cancellation reversals', 'refund_amount_gbp'), ('Net revenue', 'net_order_amount_gbp')]:
        print(f'{label}: {sum(amount(r[field]) for r in orders.values()):,.2f}')
    print(f'Attribution diagnostic (all statuses): {sum(attributed.values())} attributed; {sum(c is None for c in assignments.values())} unattributed')


if __name__ == '__main__':
    try:
        validate()
    except (ValueError, KeyError, TypeError, ArithmeticError) as error:
        raise SystemExit(f'VALIDATION FAILED: {error}')
