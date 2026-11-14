"""Validated CSV spending hierarchy and cent-exact personal allocations."""
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tax_model import allocate_tax_dollars

CSV_PATH = Path(__file__).resolve().parent / "data" / "tax-explorer" / "tax_explorer_prototype_v3_reconciled.csv"
LEVEL_POOLS = {
    "Federal": "federal_positive_programs",
    "State": "state_all_sources_proxy",
    "County": "county_all_funds_proxy",
    "City": "city_general_fund",
}
SHARE_TOLERANCE = Decimal("0.000000001")


def load_spending_data(path=CSV_PATH):
    """Validate each selected pool before exposing it to the interface."""
    required = {"node_id", "parent_id", "government_level", "entity", "fiscal_year", "depth",
                "plain_english_name", "citizen_category", "normalized_share", "share_of_parent",
                "attributed_spending_usd", "official_amount_usd", "allocation_status",
                "tax_allocation_pool", "source_url", "notes", "metric_value", "metric_unit"}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("The allocation CSV is missing required columns.")
        rows = list(reader)
    ids = [row["node_id"] for row in rows]
    if not rows or any(not key for key in ids) or len(ids) != len(set(ids)):
        raise ValueError("Allocation IDs must be present and unique.")
    all_nodes = {row["node_id"]: row for row in rows}
    pools = {}
    for level, pool_id in LEVEL_POOLS.items():
        nodes = {key: dict(row) for key, row in all_nodes.items() if row["tax_allocation_pool"] == pool_id}
        if not nodes:
            raise ValueError("A required government pool is missing.")
        children = defaultdict(list)
        roots = []
        for key, row in nodes.items():
            row["depth"] = int(row["depth"])
            if row["government_level"] != level.lower() or row["depth"] < 0 or not row["plain_english_name"]:
                raise ValueError("Invalid level, depth or category name.")
            if row["parent_id"]:
                parent = nodes.get(row["parent_id"])
                if parent is None or int(parent["depth"]) != row["depth"] - 1:
                    raise ValueError("Invalid allocation hierarchy.")
                children[row["parent_id"]].append(key)
            else:
                roots.append(key)
                if row["depth"] != 0:
                    raise ValueError("An allocation root must have depth zero.")
            if row["allocation_status"] == "spending":
                share = Decimal(row["normalized_share"])
                attributed = Decimal(row["attributed_spending_usd"])
                if not share.is_finite() or not 0 <= share <= 1 or not attributed.is_finite() or attributed < 0:
                    raise ValueError("Invalid spending amount or share.")
                row["share"] = share
                # Preserve 12 decimal places; do not truncate fractional shares to zero.
                row["weight"] = int(share * 10**12)
            elif row["allocation_status"] == "metric":
                value = Decimal(row["metric_value"])
                if row["normalized_share"] or not value.is_finite() or value < 0:
                    raise ValueError("Metrics must not carry spending shares.")
            else:
                raise ValueError("Unknown allocation status.")
        if len(roots) != 1 or nodes[roots[0]]["allocation_status"] != "spending":
            raise ValueError("Each pool needs exactly one spending root.")
        root = nodes[roots[0]]
        if abs(root["share"] - 1) > SHARE_TOLERANCE:
            raise ValueError("A pool root must represent the full pool.")
        for key, row in nodes.items():
            money_children = [nodes[child] for child in children[key] if nodes[child]["allocation_status"] == "spending"]
            if not money_children:
                continue
            if row["allocation_status"] != "spending":
                raise ValueError("A metric cannot contain spending children.")
            if (abs(sum(child["share"] for child in money_children) - row["share"]) > SHARE_TOLERANCE
                    or abs(sum(Decimal(child["share_of_parent"]) for child in money_children) - 1) > SHARE_TOLERANCE
                    or abs(sum(Decimal(child["attributed_spending_usd"]) for child in money_children)
                           - Decimal(row["attributed_spending_usd"])) > Decimal("0.05")):
                raise ValueError("Child allocations do not reconcile to their parent.")
        top = [nodes[key] for key in children[root["node_id"]] if nodes[key]["allocation_status"] == "spending"]
        if not top or any(not row["citizen_category"] for row in top):
            raise ValueError("Broad spending categories are missing.")
        pools[level] = {"root": root, "nodes": nodes, "children": dict(children), "top": top}
    return pools


def _split_amount(items, amount):
    """Apportion rounded parent cents among siblings exactly once."""
    weights = [{"category": item["key"], "weight": item["weight"]} for item in items]
    return {row["Category"]: row["Your allocation (USD)"] for row in allocate_tax_dollars(weights, amount)}


def build_allocations(pool, amount):
    """Group broad purposes, then allocate to departments and available descendants."""
    groups = defaultdict(list)
    for row in pool["top"]:
        groups[row["citizen_category"]].append(row)
    items = [{"key": name, "weight": sum(row["weight"] for row in members)} for name, members in groups.items()]
    group_amounts = _split_amount(items, amount)
    amounts = {}

    def assign_siblings(rows, parent_amount):
        parts = _split_amount([{"key": row["node_id"], "weight": row["weight"]} for row in rows], parent_amount)
        for row in rows:
            key = row["node_id"]
            amounts[key] = parts[key]
            children = [pool["nodes"][child] for child in pool["children"].get(key, [])
                        if pool["nodes"][child]["allocation_status"] == "spending"]
            if children:
                assign_siblings(children, parts[key])

    total_weight = sum(item["weight"] for item in items)
    broad = []
    for item in items:
        name = item["key"]
        assign_siblings(groups[name], group_amounts[name])
        broad.append({"Category": name, "Your allocation (USD)": group_amounts[name],
                      "Share (%)": item["weight"] / total_weight * 100})
    broad.sort(key=lambda row: (row["Your allocation (USD)"], row["Share (%)"]), reverse=True)
    return broad, amounts, dict(groups)
