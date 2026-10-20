"""Generate the fixed Fab ENT synthetic source snapshot (standard library only)."""
import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'raw'
SEED = 20250101
START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 1, 1, tzinfo=timezone.utc)
PAID = ['Meta Paid Social', 'Google Paid Search', 'TikTok Paid Social']
SOURCES = dict(zip(PAID + ['Direct', 'Organic'], ['facebook / paid_social', 'google / cpc', 'tiktok / paid_social', '(direct) / (none)', 'google / organic']))
FIELDS = {
    'campaigns': 'campaign_id,campaign_name,channel,objective,start_date,end_date,budget_gbp',
    'ad_performance': 'date,campaign_id,channel,spend_gbp,impressions,clicks',
    'web_sessions': 'session_id,session_timestamp,customer_id,campaign_id,channel,source_medium,device',
    'customers': 'customer_id,created_at',
    'orders': 'order_id,order_timestamp,customer_id,status,gross_order_amount_gbp,refund_amount_gbp,net_order_amount_gbp',
    'order_items': 'order_item_id,order_id,product_id,quantity,unit_price_gbp,gross_line_amount_gbp,refund_amount_gbp,net_line_amount_gbp',
    'products': 'product_id,product_name,category,unit_price_gbp,currency',
}


def money(pence):
    return f'{pence // 100}.{pence % 100:02d}'


def stamp(value):
    return value.isoformat(timespec='seconds').replace('+00:00', 'Z')


def london_date(value):
    # Fixed 2025 Europe/London DST rules, avoiding a third-party tzdata dependency.
    bst = datetime(2025, 3, 30, 1, tzinfo=timezone.utc) <= value < datetime(2025, 10, 26, 1, tzinfo=timezone.utc)
    return (value + timedelta(hours=int(bst))).date()


def generate():
    rng = random.Random(SEED)
    tables = {name: [] for name in FIELDS}
    def add(name, *values):
        tables[name].append(dict(zip(FIELDS[name].split(','), values)))
    campaigns = []
    for i in range(1, 25):
        channel = PAID[(i - 1) % 3]
        begin = date(2025, 1, 1) if i <= 3 else date(2025, 1 + ((i - 4) % 4) * 3, 1)
        finish = date(2025, 12, 31) if i <= 3 else min(begin + timedelta(days=89), date(2025, 12, 31))
        budget = rng.randint(4000, 14000) * 100
        campaigns.append((f'CAM-{i:04d}', channel, begin, finish, budget))
        add('campaigns', campaigns[-1][0], f'2025 Fashion Campaign {i:02d}', channel, ['Sales', 'Traffic', 'Awareness'][(i - 1) % 3], begin, finish, money(budget))
    for i, (cid, channel, begin, finish, budget) in enumerate(campaigns):
        days = (finish - begin).days + 1
        target = budget * [75, 98, 112, 65][i % 4] // 100
        weights = [rng.randint(50, 150) for _ in range(days)]
        spends = [target * weight // sum(weights) for weight in weights]
        spends[-1] += target - sum(spends)
        for d, spend in enumerate(spends):
            impressions = rng.randint(3000, 15000)
            clicks = int(impressions * rng.uniform(.008, .035))
            if d == 0:
                clicks = 0  # exercise safe zero-click metrics
            add('ad_performance', begin + timedelta(days=d), cid, channel, money(spend), impressions, clicks)
    categories = ['Tops', 'Dresses', 'Denim', 'Outerwear', 'Accessories']
    prices = []
    for i in range(1, 31):
        price = rng.choice([1800, 2500, 3500, 4500, 5900, 7900, 9900, 12900])
        prices.append(price)
        add('products', f'PRD-{i:04d}', f'{categories[(i - 1) % 5]} Style {i:02d}', categories[(i - 1) % 5], money(price), 'GBP')
    for i in range(1, 1501):
        add('customers', f'CUS-{i:06d}', stamp(START))
    def session(when, customer, campaign=None, channel='Direct'):
        if campaign:
            channel = campaigns[campaign - 1][1]
        add('web_sessions', f'SES-{len(tables["web_sessions"]) + 1:06d}', stamp(when), customer, f'CAM-{campaign:04d}' if campaign else '', channel, SOURCES[channel], rng.choice(['mobile', 'desktop', 'tablet']))
    # Dedicated customers isolate adversarial cases from all random activity.
    fixture_time = datetime(2025, 6, 15, 12, tzinfo=timezone.utc)
    for case in range(1, 13):
        customer = f'CUS-{case:06d}'
        t = fixture_time
        if case == 1:  # last non-direct wins despite later direct
            session(t - timedelta(days=3), customer, 1)
            session(t - timedelta(days=1), customer, 2)
            session(t - timedelta(hours=1), customer)
        elif case == 2:
            session(t - timedelta(days=7), customer, 1)
        elif case == 3:
            session(t - timedelta(days=7, seconds=1), customer, 1)
        elif case == 4:
            session(t, customer, 1)
            session(t + timedelta(seconds=1), customer, 2)
        elif case == 5:
            session(t - timedelta(hours=1), customer, 1)
            session(t - timedelta(hours=1), customer, 2)
        elif case == 6:
            session(t - timedelta(hours=1), customer, channel='Organic')
            session(t - timedelta(minutes=30), customer)
        elif case == 7:
            session(t - timedelta(days=1), '', 1)  # anonymous cannot match
        elif case == 8:
            t = datetime(2025, 2, 1, 0, 30, tzinfo=timezone.utc)
            session(t - timedelta(hours=2), customer, 1)
        elif case == 9:
            session(t - timedelta(days=2), customer, 1)
            session(t - timedelta(hours=1), customer, channel='Organic')
        elif case in (10, 11):
            session(t - timedelta(hours=1), customer, 2)
        # case 12 has no sessions
        add('orders', f'ORD-{case:06d}', stamp(t), customer, '', '', '', '')
    for i in range(13, 2501):
        customer = f'CUS-{rng.randint(31, 1500):06d}'
        t = START + timedelta(seconds=rng.randrange(10 * 86400, 365 * 86400))
        add('orders', f'ORD-{i:06d}', stamp(t), customer, '', '', '', '')
        for _ in range(rng.randint(1, 3)):
            when = t - timedelta(seconds=rng.randint(1, 12 * 86400))
            if when < START:
                continue
            active = [i for i, c in enumerate(campaigns, 1) if i < 23 and c[2] <= london_date(when) <= c[3]]
            choice = rng.random()
            session(when, customer, rng.choice(active) if choice < .7 else None, 'Organic' if choice >= .85 else 'Direct')
    while len(tables['web_sessions']) < 15000:
        t = START + timedelta(seconds=rng.randrange(365 * 86400))
        active = [i for i, c in enumerate(campaigns, 1) if i < 23 and c[2] <= london_date(t) <= c[3]]
        choice = rng.random()
        session(t, f'CUS-{rng.randint(31, 1500):06d}' if rng.random() < .65 else '', rng.choice(active) if choice < .65 else None, 'Organic' if choice >= .85 else 'Direct')
    for i, order in enumerate(tables['orders'], 1):
        status = 'cancelled' if i == 10 else 'refunded' if i == 11 else rng.choices(['completed', 'cancelled', 'partially_refunded', 'refunded'], [82, 5, 8, 5])[0]
        gross = refund = 0
        for line in range(rng.randint(1, 4)):
            product = rng.randint(1, 30)
            qty = rng.choices([1, 2, 3], [85, 12, 3])[0]
            amount = prices[product - 1] * qty
            returned = amount if status in ('cancelled', 'refunded') else amount // 2 if status == 'partially_refunded' else 0
            add('order_items', f'ITM-{len(tables["order_items"]) + 1:06d}', order['order_id'], f'PRD-{product:04d}', qty, money(prices[product - 1]), money(amount), money(returned), money(amount - returned))
            gross += amount
            refund += returned
        order.update(status=status, gross_order_amount_gbp=money(gross), refund_amount_gbp=money(refund), net_order_amount_gbp=money(gross - refund))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        with (OUT / f'{name}.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS[name].split(','), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        print(f'{name}: {len(rows):,} rows')


if __name__ == '__main__':
    generate()
