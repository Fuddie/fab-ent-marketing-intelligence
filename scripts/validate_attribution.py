"""Read-only Phase 3 validation; independent raw-CSV Python attribution oracle."""
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def raw(name):
    with (ROOT / f"data/raw/{name}.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def validate():
    manifest = json.loads((ROOT / "target/manifest.json").read_text(encoding="utf-8"))
    nodes = {n["name"]: n for n in manifest["nodes"].values() if n["resource_type"] == "model"}
    relation = nodes["int_marketing__orders_attributed"]["relation_name"]
    campaigns = {c["campaign_id"] for c in raw("campaigns")}
    sessions = defaultdict(list)
    for s in raw("web_sessions"):
        if s["customer_id"]:
            sessions[s["customer_id"]].append(s)
    with duckdb.connect(str(ROOT / "data/generated/fab_ent.duckdb"), read_only=True) as con:
        con.execute("SET TimeZone = 'UTC'")
        cursor = con.execute(f"select * from {relation}")
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        staged = con.execute(f"select count(*) from {nodes['stg_marketing__orders']['relation_name']}").fetchone()[0]
    orders = raw("orders")
    actual = {r["order_id"]: r for r in rows}
    require(len(actual) == len(rows) == len(orders) == staged, "Order count/key conservation")
    amounts = ["gross_order_amount_gbp", "refund_amount_gbp", "net_order_amount_gbp"]
    for o in orders:
        a = actual[o["order_id"]]
        time = datetime.fromisoformat(o["order_timestamp"])
        eligible = [s for s in sessions[o["customer_id"]]
                    if s["campaign_id"] in campaigns
                    and s["channel"] in ("Meta Paid Social", "Google Paid Search", "TikTok Paid Social")
                    and time - timedelta(days=7) <= datetime.fromisoformat(s["session_timestamp"]) < time]
        winner = max(eligible, key=lambda s: (datetime.fromisoformat(s["session_timestamp"]), s["session_id"]), default=None)
        require(a["session_id"] == (winner["session_id"] if winner else None), f"Independent winner: {o['order_id']}")
        require(a["customer_id"] == o["customer_id"] and a["order_timestamp"] == time and a["status"] == o["status"], "Source order fields")
        require(all(a[c] == Decimal(o[c]) for c in amounts), "Per-order money preservation")
        require(a["attribution_status"] == ("attributed" if winner else "unattributed"), "Assignment status")
        require((a["unattributed_reason"] is None) == bool(winner), "Reason partition")
        if winner:
            require(a["campaign_id"] == winner["campaign_id"] and a["interaction_timestamp"] == datetime.fromisoformat(winner["session_timestamp"]), "Selected interaction fields")
    counts = Counter(r["attribution_status"] for r in rows)
    print(f"Orders: total={len(rows)}, attributed={counts['attributed']}, unattributed={counts['unattributed']}, attribution_rate={counts['attributed']/len(rows):.2%}")
    print("Unattributed reasons:", dict(sorted(Counter(r["unattributed_reason"] for r in rows if r["attribution_status"] == "unattributed").items())))
    print("Attributed channels:", dict(sorted(Counter(r["channel"] for r in rows if r["attribution_status"] == "attributed").items())))
    for state in ("all", "attributed", "unattributed"):
        subset = rows if state == "all" else [r for r in rows if r["attribution_status"] == state]
        totals = [sum((r[c] for r in subset), Decimal(0)) for c in amounts]
        require(totals[0] - totals[1] == totals[2], "Gross minus reversal equals net")
        print(state + " GBP: " + ", ".join(f"{c}={v:,.2f}" for c, v in zip(amounts, totals)))
    for i, expected in enumerate(['CAM-0002','CAM-0001',None,None,'CAM-0002',None,None,'CAM-0001','CAM-0001','CAM-0002','CAM-0002',None], 1):
        row = actual[f"ORD-{i:06}"]
        require(row["campaign_id"] == expected, f"Fixture {i}")
        print(f"Fixture ORD-{i:06}: PASS campaign={row['campaign_id']} session={row['session_id']}")
    print("PASS: independent raw-CSV oracle matches every order; counts, statuses and exact amounts conserved")

if __name__ == "__main__":
    validate()
