"""Read-only Phase 4 oracle: rebuild expected results from CSVs, not mart SQL.

Uses the dictionary's fixed 2025 BST interval independently of DuckDB timezone
functions. Do not reuse that interval for other years. No dbt imports or writes.
"""
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
ZERO = Decimal(0)
PAID = {"Meta Paid Social", "Google Paid Search", "TikTok Paid Social"}
COUNTS = [
    "impressions", "clicks", "valid_sessions", "placed_orders",
    "attributed_placed_orders", "unattributed_placed_orders", "eligible_conversions",
    "attributed_orders", "unattributed_eligible_orders", "first_observed_acquisitions",
    "attributed_first_observed_acquisitions", "unattributed_first_observed_acquisitions",
    "negative_input_count",
]
MONEY = [
    "spend_gbp", "raw_gross_order_amount_gbp", "cancellation_gross_amount_gbp",
    "gross_merchandise_revenue_gbp", "sales_refunds_gbp", "cancellation_reversals_gbp",
    "net_revenue_gbp", "raw_net_order_amount_gbp", "allocated_budget_gbp",
] + [p + "_" + m for p in ("attributed", "unattributed") for m in (
    "gross_merchandise_revenue_gbp", "sales_refunds_gbp",
    "cancellation_reversals_gbp", "net_revenue_gbp",
)]
MEASURES = COUNTS + MONEY


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(name):
    with (ROOT / "data/raw" / (name + ".csv")).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def london_day(value):
    time = instant(value)
    require(time.year == 2025, "Independent London oracle supports only 2025 UTC input")
    bst = instant("2025-03-30T01:00:00Z") <= time < instant("2025-10-26T01:00:00Z")
    return (time + timedelta(hours=int(bst))).date()


def empty():
    return {name: ZERO for name in MEASURES}


def equal(actual, expected, label, tolerance=ZERO):
    if expected is None:
        require(actual is None, f"{label}: expected NULL, got {actual}")
    else:
        require(actual is not None and abs(Decimal(str(actual)) - Decimal(expected)) <= tolerance,
                f"{label}: expected {expected}, got {actual}")


def ratio(numerator, denominator, percent=False):
    return numerator / denominator * (100 if percent else 1) if denominator else None


def validate():
    campaigns = {c["campaign_id"]: c for c in raw("campaigns")}
    orders = raw("orders")
    sessions = raw("web_sessions")
    items = raw("order_items")
    media = raw("ad_performance")
    daily = defaultdict(empty)
    customer_sessions = defaultdict(list)
    negative_line_orders = set()
    for item in items:
        if any(Decimal(item[k]) < 0 for k in (
                "quantity", "unit_price_gbp", "gross_line_amount_gbp",
                "refund_amount_gbp", "net_line_amount_gbp")):
            negative_line_orders.add(item["order_id"])
    for s in sessions:
        daily[london_day(s["session_timestamp"]), s["campaign_id"] or None, s["channel"]]["valid_sessions"] += 1
        if s["customer_id"] and s["campaign_id"] in campaigns and s["channel"] in PAID:
            customer_sessions[s["customer_id"]].append(s)
    for a in media:
        bucket = daily[date.fromisoformat(a["date"]), a["campaign_id"], a["channel"]]
        for key in ("spend_gbp", "impressions", "clicks"):
            bucket[key] += Decimal(a[key])
        bucket["negative_input_count"] += any(Decimal(a[k]) < 0 for k in ("spend_gbp", "impressions", "clicks"))
    for cid, c in campaigns.items():
        start, end = (date.fromisoformat(c[k]) for k in ("start_date", "end_date"))
        for i in range((end - start).days + 1):
            bucket = daily[start + timedelta(days=i), cid, c["channel"]]
            bucket["allocated_budget_gbp"] += Decimal(c["budget_gbp"]) / ((end - start).days + 1)
            bucket["negative_input_count"] += Decimal(c["budget_gbp"]) < 0
    order_expected = {}
    first = {}
    for o in orders:
        time = instant(o["order_timestamp"])
        candidates = [s for s in customer_sessions[o["customer_id"]]
                      if time - timedelta(days=7) <= instant(s["session_timestamp"]) < time]
        winner = max(candidates, key=lambda s: (instant(s["session_timestamp"]), s["session_id"]), default=None)
        cid = winner["campaign_id"] if winner else None
        channel = winner["channel"] if winner else "Unattributed"
        day = london_day(o["order_timestamp"])
        bucket = daily[day, cid, channel]
        gross, refund, net = (Decimal(o[k]) for k in (
            "gross_order_amount_gbp", "refund_amount_gbp", "net_order_amount_gbp"))
        eligible = o["status"] in ("completed", "partially_refunded") and net > 0
        attributed = winner is not None
        prefix = "attributed" if attributed else "unattributed"
        bucket["placed_orders"] += 1
        bucket[prefix + "_placed_orders"] += 1
        bucket["eligible_conversions"] += eligible
        bucket["attributed_orders" if attributed else "unattributed_eligible_orders"] += eligible
        bucket["raw_gross_order_amount_gbp"] += gross
        bucket["raw_net_order_amount_gbp"] += net
        if o["status"] == "cancelled":
            bucket["cancellation_gross_amount_gbp"] += gross
            bucket["cancellation_reversals_gbp"] += refund
            bucket[prefix + "_cancellation_reversals_gbp"] += refund
        else:
            for name, amount in (("gross_merchandise_revenue_gbp", gross),
                                 ("sales_refunds_gbp", refund), ("net_revenue_gbp", net)):
                bucket[name] += amount
                bucket[prefix + "_" + name] += amount
        negative = min(gross, refund, net) < 0 or o["order_id"] in negative_line_orders
        bucket["negative_input_count"] += negative
        order_expected[o["order_id"]] = {
            "reporting_date": day, "commercially_eligible": eligible,
            "revenue_scope": o["status"] != "cancelled", "is_attributed": attributed,
            "campaign_id": cid, "marketing_channel": channel,
            "negative_input_count": int(negative),
        }
        if eligible:
            candidate = (time, o["order_id"], day, cid, channel, attributed)
            current = first.get(o["customer_id"])
            if current is None or candidate[:2] < current[:2]:
                first[o["customer_id"]] = candidate
    for _, _, day, cid, channel, attributed in first.values():
        bucket = daily[day, cid, channel]
        bucket["first_observed_acquisitions"] += 1
        bucket[("attributed" if attributed else "unattributed") + "_first_observed_acquisitions"] += 1

    manifest = json.loads((ROOT / "target/manifest.json").read_text(encoding="utf-8"))
    nodes = {n["name"]: n for n in manifest["nodes"].values() if n["resource_type"] == "model"}
    with duckdb.connect(str(ROOT / "data/generated/fab_ent.duckdb"), read_only=True) as con:
        con.execute("SET TimeZone = 'UTC'")

        def rows(name):
            cursor = con.execute("select * from " + nodes[name]["relation_name"])
            return [dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()]

        actual_orders = rows("int_marketing__governed_orders")
        require(len(actual_orders) == len(order_expected) == 2500, "Governed order conservation")
        for o in actual_orders:
            for key, value in order_expected[o["order_id"]].items():
                require(o[key] == value, f"Governed order {o['order_id']}: {key}")
        acquisitions = rows("int_marketing__first_observed_acquisitions")
        require(len(acquisitions) == len(first), "Acquisition conservation")
        require(len({a["customer_id"] for a in acquisitions}) == len(first), "Unique acquisitions")
        for a in acquisitions:
            time, oid, day, cid, channel, attributed = first[a["customer_id"]]
            require((a["acquisition_timestamp"], a["acquisition_order_id"], a["reporting_date"],
                     a["campaign_id"], a["marketing_channel"], a["is_attributed"])
                    == (time, oid, day, cid, channel, attributed), "First eligible order and attribution")
            require(a["acquisition_basis"] == "first_observed_2025_snapshot", "Acquisition label")
        print(f"int_marketing__governed_orders: {len(actual_orders):,} rows")
        print(f"int_marketing__first_observed_acquisitions: {len(acquisitions):,} rows")

        layouts = {
            "int_marketing__daily_facts": ("reporting_date", "campaign_id", "marketing_channel"),
            "mart_marketing__campaign_daily": ("reporting_date", "campaign_id"),
            "mart_marketing__campaign_summary": ("campaign_id",),
            "mart_marketing__channel_monthly": ("reporting_month", "marketing_channel"),
            "mart_marketing__monthly_overview": ("reporting_month",),
        }
        for name, keys in layouts.items():
            expected = defaultdict(empty)
            for (day, cid, channel), values in daily.items():
                if "campaign_" in name and cid is None:
                    continue
                dims = {"reporting_date": day, "reporting_month": day.replace(day=1),
                        "campaign_id": cid, "marketing_channel": channel}
                bucket = expected[tuple(dims[k] for k in keys)]
                for key in MEASURES:
                    bucket[key] += values[key]
            if name.endswith("campaign_summary"):
                for cid in campaigns:
                    expected[cid,]  # Retain a campaign even without any fact rows.
            actual = rows(name)
            require(len(actual) == len(expected), f"{name}: grain/key count")
            require(len({tuple(r[k] for k in keys) for r in actual}) == len(actual), f"{name}: unique grain")
            for r in actual:
                rowkey = tuple(r[k] for k in keys)
                require(rowkey in expected, f"{name}: extra key {rowkey}")
                e = expected[rowkey]
                for key in MEASURES:
                    equal(r[key], e[key], f"{name} {rowkey}: {key}",
                          Decimal("0.000001") if key == "allocated_budget_gbp" else ZERO)
                if not name.startswith("mart_"):
                    continue
                overall = name.endswith("monthly_overview")
                paid = overall or r["marketing_channel"] in PAID
                require(r["cost_coverage"] == ("platform_media_only" if paid else "not_available"), "Cost coverage")
                require(r["acquisition_basis"] == "first_observed_2025_snapshot", "Snapshot labelling")
                if "campaign_" in name:
                    c = campaigns[r["campaign_id"]]
                    for key in ("campaign_name", "objective"):
                        require(r[key] == c[key], f"Campaign dimension: {key}")
                    require(r["marketing_channel"] == c["channel"], "Campaign channel relationship")
                    for key in ("start_date", "end_date"):
                        require(r[key] == date.fromisoformat(c[key]), f"Campaign bound: {key}")
                    budget = Decimal(c["budget_gbp"])
                    equal(r["lifetime_budget_gbp"], budget, "Lifetime budget once")
                    if name.endswith("campaign_daily"):
                        day = r["reporting_date"]
                        cumulative = sum(v["spend_gbp"] for (d, cid, _), v in daily.items()
                                         if cid == r["campaign_id"] and d <= day)
                        start, end = (date.fromisoformat(c[k]) for k in ("start_date", "end_date"))
                        elapsed = min(max((day - start).days + 1, 0), (end - start).days + 1)
                        planned = budget * elapsed / ((end - start).days + 1)
                        equal(r["cumulative_spend_gbp"], cumulative, "Cumulative media spend")
                        equal(r["expected_cumulative_spend_gbp"], planned, "Straight-line cumulative budget", Decimal("0.000001"))
                        utilisation = ratio(cumulative, budget, True)
                        pacing = ratio(cumulative, planned, True)
                    else:
                        utilisation = pacing = ratio(e["spend_gbp"], budget, True)
                else:
                    utilisation = pacing = ratio(e["spend_gbp"], e["allocated_budget_gbp"], True)
                ratios = {
                    "ctr_pct": ratio(e["clicks"], e["impressions"], True),
                    "cpc_gbp": ratio(e["spend_gbp"], e["clicks"]),
                    "conversion_rate_pct": ratio(e["eligible_conversions"] if overall else e["attributed_orders"], e["valid_sessions"], True) if paid else None,
                    "gross_roas": ratio(e["attributed_gross_merchandise_revenue_gbp"], e["spend_gbp"]) if paid else None,
                    "net_roas": ratio(e["attributed_net_revenue_gbp"], e["spend_gbp"]) if paid else None,
                    "media_only_cac_gbp": ratio(e["spend_gbp"], e["attributed_first_observed_acquisitions"]) if paid else None,
                    "attribution_rate_pct": ratio(e["attributed_orders"], e["eligible_conversions"], True),
                    "budget_utilisation_pct": utilisation, "budget_pacing_pct": pacing,
                }
                for key, value in ratios.items():
                    equal(r[key], value, f"{name} {rowkey}: {key}", Decimal("0.0000001"))
                flags = {
                    "flag_spend_without_eligible_attributed_orders": e["spend_gbp"] > 0 and e["attributed_orders"] == 0,
                    "flag_budget_overspend": utilisation is not None and utilisation > 100,
                    "flag_ahead_of_budget_pacing": pacing is not None and pacing > 100,
                    "flag_approaching_budget": utilisation is not None and 90 <= utilisation <= 100,
                    "flag_unexpected_negative_inputs": e["negative_input_count"] > 0,
                    "flag_incomplete_attribution": e["unattributed_placed_orders"] > 0,
                }
                for key, value in flags.items():
                    require(r[key] == value, f"{name} {rowkey}: {key}")
            print(f"{name}: {len(actual):,} rows; all keys, additive measures, ratios and flags match CSV oracle")

        summaries = {r["campaign_id"]: r for r in rows("mart_marketing__campaign_summary")}
        for cid in ("CAM-0023", "CAM-0024"):
            require(summaries[cid]["spend_gbp"] > 0 and summaries[cid]["attributed_orders"] == 0
                    and summaries[cid]["flag_spend_without_eligible_attributed_orders"], f"Spend-only {cid}")

    totals = empty()
    for values in daily.values():
        for key in MEASURES:
            totals[key] += values[key]
    baselines = {"spend_gbp": "189198.54", "raw_gross_order_amount_gbp": "416314.00",
                 "gross_merchandise_revenue_gbp": "396434.00", "sales_refunds_gbp": "43076.50",
                 "cancellation_reversals_gbp": "19880.00", "net_revenue_gbp": "353357.50",
                 "placed_orders": "2500", "eligible_conversions": "2228", "attributed_orders": "1439",
                 "unattributed_eligible_orders": "789", "valid_sessions": "15000"}
    for key, value in baselines.items():
        equal(totals[key], Decimal(value), f"Fixed-snapshot baseline: {key}")
        print(f"{key}: {totals[key]:,.2f}")
    equal(sum(Decimal(i["gross_line_amount_gbp"]) for i in items), totals["raw_gross_order_amount_gbp"], "Raw line gross")
    for key in ("impressions", "clicks", "first_observed_acquisitions", "attributed_first_observed_acquisitions",
                "unattributed_first_observed_acquisitions", "attributed_gross_merchandise_revenue_gbp", "attributed_net_revenue_gbp"):
        print(f"{key}: {totals[key]:,.2f}")
    print(f"Overall website conversion: {ratio(totals['eligible_conversions'], totals['valid_sessions'], True):.4f}%")
    print(f"Eligible attribution rate: {ratio(totals['attributed_orders'], totals['eligible_conversions'], True):.4f}%")
    print(f"Media-only CAC: GBP {ratio(totals['spend_gbp'], totals['attributed_first_observed_acquisitions']):.4f}")
    print(f"Gross ROAS: {ratio(totals['attributed_gross_merchandise_revenue_gbp'], totals['spend_gbp']):.4f}")
    print(f"Net ROAS: {ratio(totals['attributed_net_revenue_gbp'], totals['spend_gbp']):.4f}")
    print("PASS: raw-CSV attribution, London dates, first acquisitions, all mart grains/metrics/flags, budgets, spend-only campaigns and fixed monetary reconciliations")


if __name__ == "__main__":
    validate()
