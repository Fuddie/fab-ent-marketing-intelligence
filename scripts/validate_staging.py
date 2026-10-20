"""Read-only Phase 2 count and monetary reconciliation using dbt's manifest."""
import json
from decimal import Decimal
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    manifest = json.loads((ROOT / 'target/manifest.json').read_text(encoding='utf-8'))
    nodes = {node['name']: node for node in manifest['nodes'].values()
             if node['resource_type'] in ('seed', 'model')}
    counts = {'campaigns': 24, 'ad_performance': 2985, 'web_sessions': 15000,
              'customers': 1500, 'orders': 2500, 'order_items': 6129, 'products': 30}
    with duckdb.connect(str(ROOT / 'data/generated/fab_ent.duckdb'), read_only=True) as con:
        con.execute("SET TimeZone = 'UTC'")
        for name, expected in counts.items():
            seed = nodes[name]['relation_name']
            staged = nodes['stg_marketing__' + name]['relation_name']
            raw_count = con.execute(f'SELECT count(*) FROM {seed}').fetchone()[0]
            staged_count = con.execute(f'SELECT count(*) FROM {staged}').fetchone()[0]
            check(raw_count == staged_count == expected, f'{name}: count mismatch')
            print(f'{name}: seed={raw_count:,}; staging={staged_count:,}')

        for name, columns, baseline in [
            ('ad_performance', ['spend_gbp'], ['189198.54']),
            ('orders', ['gross_order_amount_gbp', 'refund_amount_gbp', 'net_order_amount_gbp'],
             ['416314.00', '62956.50', '353357.50']),
            ('order_items', ['gross_line_amount_gbp', 'refund_amount_gbp', 'net_line_amount_gbp'],
             ['416314.00', '62956.50', '353357.50']),
        ]:
            sums = ', '.join(f'sum({column})' for column in columns)
            expected = tuple(Decimal(value) for value in baseline)
            for relation in (name, 'stg_marketing__' + name):
                totals = con.execute(f"SELECT {sums} FROM {nodes[relation]['relation_name']}").fetchone()
                check(totals == expected, f'{relation}: monetary reconciliation failed')
                if relation.startswith('stg_'):
                    print(f'{relation}: ' + ', '.join(
                        f'{column}=GBP {amount:,.2f}' for column, amount in zip(columns, totals)))
    print('PASS: all seven row counts and seed/staging spend, gross, refunds/reversals and net totals')


if __name__ == '__main__':
    validate()
