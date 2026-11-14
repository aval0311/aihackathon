"""Two-input, four-level tax story for the Draper hackathon pilot."""
import csv
import json
import re
from pathlib import Path
import streamlit as st
from tax_model import estimate_taxes, allocate_tax_dollars

st.set_page_config(page_title="Your Tax Dollar", layout="centered")
DATA_DIR = Path(__file__).resolve().parent / "data"


def load_snapshots():
    """Use reviewed local snapshots so the demo does not depend on live scraping."""
    snapshots = json.loads((DATA_DIR / "spending_snapshots.json").read_text(encoding="utf-8"))
    city_meta = json.loads((DATA_DIR / "draper_general_fund_fy2027_metadata.json").read_text(encoding="utf-8"))
    with (DATA_DIR / city_meta["dataset_file"]).open(encoding="utf-8", newline="") as handle:
        city_rows = [{"category": row["category"], "weight": int(row["amount_usd"])} for row in csv.DictReader(handle)]
    snapshots["City"] = {
        "jurisdiction": "Draper City",
        "period": "FY2026-27, August 2026 adoption snapshot",
        "scope": "General Fund expenditure and transfers",
        "source_url": city_meta["source_url"],
        "source_location": "PDF page 12, FY2027 column",
        "weight_unit": "USD",
        "published_weight_total": city_meta["published_total_usd"],
        "rounding_tolerance": 0,
        "notes": "General Fund only, not all city funds. Later amendments are not incorporated. Transfers are counted once. Tax payments are illustrated using the overall fund spending mix, including spending supported by other revenues.",
        "rows": city_rows,
    }
    for snapshot in snapshots.values():
        rows = snapshot["rows"]
        total = sum(row["weight"] for row in rows)
        if (not rows or total <= 0 or any(row["weight"] < 0 for row in rows)
                or len({row["category"] for row in rows}) != len(rows)
                or abs(total - snapshot["published_weight_total"]) > snapshot["rounding_tolerance"]):
            raise ValueError("Source totals could not be verified.")
    return snapshots


def show_breakdown(level, snapshot, amount):
    """Lead with personal dollar allocations, then provide source context."""
    local = level in ("County", "City")
    label = "Hypothetical homeowner allocation" if local else "Illustrative income-tax allocation"
    st.subheader(f"{snapshot['jurisdiction']}: where the dollars could go")
    st.caption(f"{label} | {snapshot['period']}")
    st.metric("Annual scenario tax" if local else "Estimated annual income tax", f"${amount:,.2f}")
    allocations = allocate_tax_dollars(snapshot["rows"], amount)
    if amount > 0:
        top = allocations[0]
        st.write(f"The largest share supports **{top['Category']}**: **${top['Your allocation (USD)']:,.2f} per year** ({top['Share (%)']:.2f}%).")
    else:
        st.write("This model returns zero tax for this level, so all allocations are zero.")
    st.vega_lite_chart(
        allocations,
        {
            "mark": "bar",
            "encoding": {
                "y": {"field": "Category", "type": "nominal", "sort": [row["Category"] for row in allocations], "axis": {"labelLimit": 200}},
                "x": {"field": "Your allocation (USD)", "type": "quantitative", "title": "Illustrative annual dollars (USD)", "axis": {"format": "$,.2f"}},
                "tooltip": [{"field": "Category", "type": "nominal"}, {"field": "Your allocation (USD)", "type": "quantitative", "format": "$,.2f"}],
            },
        },
        height=max(240, len(allocations) * 32),
        use_container_width=True,
    )
    st.dataframe(
        allocations, hide_index=True, use_container_width=True,
        column_config={"Your allocation (USD)": st.column_config.NumberColumn(format="$%.2f"), "Share (%)": st.column_config.NumberColumn(format="%.2f%%")},
    )
    st.caption("Largest to smallest. Allocations reconcile to the displayed tax amount, including rounding.")
    st.markdown(f"[Official spending source]({snapshot['source_url']}) - {snapshot['source_location']}.")
    with st.expander("How this breakdown works"):
        st.write("Allocation = tax amount multiplied by each category's share of this spending snapshot. These are proportional illustrations, not a trace of your individual payments.")
        st.write(snapshot["scope"])
        st.write(snapshot["notes"])
        st.caption(f"Underlying source weights are in {snapshot['weight_unit']}.")
        st.dataframe(snapshot["rows"], hide_index=True, use_container_width=True)


st.title("Your Tax Dollar")
st.write("Enter your salary and ZIP to explore the public services your tax dollars could support, ranked from largest to smallest.")
st.caption("Draper / Salt Lake County pilot | ZIP 84020 | Tax year 2026")
st.info("Federal and state panels estimate income tax. City and county panels are hypothetical homeowner scenarios: a home worth 3 times salary, taxed at published local rates. They are not estimates of your actual property taxes.")

with st.form("tax_inputs"):
    salary = st.number_input("Annual gross salary ($)", min_value=0, max_value=10000000, value=None, placeholder="Enter your salary", step=1000)
    zip_code = st.text_input("Residential ZIP code", max_chars=5, placeholder="Enter your ZIP code")
    st.caption("Assumes a single adult under 65, wage income only, standard deduction, no dependents or pre-tax deductions. Federal payroll taxes and most credits are excluded. This pilot uses a Salt Lake County scenario, not a precise ZIP-to-boundary lookup.")
    submitted = st.form_submit_button("Show where my tax dollars could go")

if submitted:
    error = None
    if salary is None:
        error = "Please enter your annual gross salary."
    elif not re.fullmatch(r"[0-9]{5}", zip_code.strip()):
        error = "Please enter a five-digit ZIP code."
    elif zip_code.strip() != "84020":
        error = "This hackathon pilot supports Draper ZIP 84020 only. Other locations are not implemented."
    if error:
        st.session_state.pop("profile", None)
        st.error(error)
    else:
        st.session_state["profile"] = {"salary": salary, "zip_code": zip_code.strip()}

profile = st.session_state.get("profile")
if profile:
    taxes = estimate_taxes(profile["salary"])
    st.subheader("Your annual tax story")
    st.write(f"Salary: **${profile['salary']:,.0f}** | ZIP: **{profile['zip_code']}**")
    columns = st.columns(2)
    for index, level in enumerate(["Federal", "State", "County", "City"]):
        columns[index % 2].metric(f"{level} homeowner scenario" if level in ("County", "City") else f"{level} income tax estimate", f"${taxes[level]:,.2f}")
    st.warning(f"Local scenario only: assumes a primary residence worth ${taxes['assumed_home_value']:,.0f} (3 times salary), with 55% taxable value. This is a project assumption, not an inferred home value. Excludes library, school and special district levies, sales taxes, exemptions beyond the standard primary-residence exemption, and renter circumstances.")
    try:
        snapshots = load_snapshots()
    except (OSError, ValueError, KeyError, TypeError):
        st.error("A reviewed spending snapshot could not be loaded or verified.")
    else:
        levels = ["Federal", "State", "County", "City"]
        for level, tab in zip(levels, st.tabs(levels)):
            with tab:
                show_breakdown(level, snapshots[level], taxes[level])

with st.expander("Tax rules, assumptions, and sources"):
    st.write("Federal: 2026 single-filer progressive brackets and a $16,100 standard deduction. No additional credits, adjustments, other income, payroll taxes, or alternative minimum tax are modeled.")
    st.markdown("[IRS 2026 brackets and standard deduction](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers)")
    st.write("Utah: assumes wages equal state taxable income; 4.45% rate, less the nonrefundable taxpayer tax credit: 6% of the $16,100 standard deduction, reduced by 1.3% of income above $18,696. Other state credits and exemptions are excluded.")
    st.markdown("[Utah income-tax rate](https://le.utah.gov/xcode/Title59/Chapter10/C59-10-S104_2026050620260506.html) | [Utah taxpayer credit, 2026 review](https://le.utah.gov/interim/2026/pdf/00003360.pdf)")
    st.write("Local: hypothetical home value = 3 times salary (a project assumption). Taxable home value = 55% of that value. City scenario = taxable value times 0.001128; countywide scenario = taxable value times 0.001509. The ZIP selects the fixed pilot; it does not establish parcel location or home ownership.")
    st.markdown("[Draper adopted-budget presentation, page 4](https://www.utah.gov/pmn/files/1477201.pdf) | [Salt Lake County budget and tax example, printed pages 10-11](https://www.saltlakecounty.gov/globalassets/1-site-files/mayor-finance/budget/budget-documents/2026/supplemental/4.5---2026-adopted-budget-in-brief-12-9-2025.pdf?v=2)")
    st.write("Tax rules are for 2026; spending snapshots span FY2025 federal actual outlays and FY2026/27 local/state budgets. Years and scopes are labeled in each panel. Transfers are not reallocated a second time. This is not a comprehensive tax bill or a tax-return calculation.")

st.caption("Educational prototype. Inputs stay in this app session; this code does not store them in a database or send them to an AI service.")