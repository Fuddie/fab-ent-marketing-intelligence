"""Read-only verification of the default Phase 1 DuckDB seed load."""
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COUNTS = {
    'ad_performance': 2985, 'campaigns': 24, 'customers': 1500,
    'order_items': 6129, 'orders': 2500, 'products': 30, 'web_sessions': 15000,
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    metadata = yaml.safe_load((ROOT / 'data/raw/seeds.yml').read_text(encoding='utf-8'))
    with duckdb.connect(str(ROOT / 'data/generated/fab_ent.duckdb'), read_only=True) as con:
        con.execute("SET TimeZone = 'UTC'")
        tables = {r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
        ).fetchall()}
        check(tables == set(EXPECTED_COUNTS), 'Expected exactly seven raw tables')
        for seed in metadata['seeds']:
            name = seed['name']
            types = seed['config']['column_types']
            columns = ', '.join(f'"{c}"' for c in types)
            # Cast the independent CSV read to the declared seed types, including
            # blank nullable identities -> NULL and UTC-aware timestamps.
            projection = ', '.join(
                f'CAST(NULLIF("{c}", \'\') AS {t}) AS "{c}"' for c, t in types.items()
            )
            source = f'SELECT {projection} FROM read_csv(?, header=true, all_varchar=true)'
            loaded = f'SELECT {columns} FROM raw."{name}"'
            path = str(ROOT / 'data/raw' / f'{name}.csv')
            for left, right in [(loaded, source), (source, loaded)]:
                differences = con.execute(
                    f'SELECT count(*) FROM (({left}) EXCEPT ALL ({right}))', [path]
                ).fetchone()[0]
                check(differences == 0, f'{name}: database/CSV row mismatch')
            count = con.execute(f'SELECT count(*) FROM raw."{name}"').fetchone()[0]
            check(count == EXPECTED_COUNTS[name], f'{name}: unexpected snapshot count')
            print(f'{name}: {count:,} rows; exact typed CSV match')

        for table, expressions, expected in [
            ('ad_performance', 'sum(spend_gbp)', ('189198.54',)),
            ('orders', 'sum(gross_order_amount_gbp), sum(refund_amount_gbp), sum(net_order_amount_gbp)',
             ('416314.00', '62956.50', '353357.50')),
            ('order_items', 'sum(gross_line_amount_gbp), sum(refund_amount_gbp), sum(net_line_amount_gbp)',
             ('416314.00', '62956.50', '353357.50')),
        ]:
            totals = con.execute(f'SELECT {expressions} FROM raw.{table}').fetchone()
            check(totals == tuple(Decimal(v) for v in expected), f'{table}: total mismatch')
            print(f'{table} GBP totals: {", ".join(str(t) for t in totals)}')
        mismatches = con.execute('''
            SELECT count(*) FROM raw.orders o
            FULL OUTER JOIN (
                SELECT order_id, sum(gross_line_amount_gbp) gross,
                       sum(refund_amount_gbp) refund, sum(net_line_amount_gbp) net
                FROM raw.order_items GROUP BY order_id
            ) i USING (order_id)
            WHERE o.order_id IS NULL OR i.order_id IS NULL
               OR o.gross_order_amount_gbp IS DISTINCT FROM i.gross
               OR o.refund_amount_gbp IS DISTINCT FROM i.refund
               OR o.net_order_amount_gbp IS DISTINCT FROM i.net
        ''').fetchone()[0]
        check(mismatches == 0, 'Order/line reconciliation failed')
    print('PASS: seven seed tables, CSV equality, fixed snapshot totals and per-order line reconciliation')


if __name__ == '__main__':
    validate()
