"""Two-input tax story for a married Salt Lake City household with one child."""
import json
import re
from pathlib import Path
import streamlit as st
from tax_model import estimate_taxes, allocate_tax_dollars

st.set_page_config(page_title="Your Tax Dollar", layout="centered")
DATA_DIR = Path(__file__).resolve().parent / "data"
PILOT_ZIPS = {"84101", "84102", "84103", "84104", "84105", "84106", "84108", "84111", "84112", "84116"}


def load_snapshots():
    """Use reviewed local snapshots so the demo does not depend on live scraping."""
    snapshots = json.loads((DATA_DIR / "spending_snapshots.json").read_text(encoding="utf-8"))
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
    st.metric("Annual household scenario tax" if local else "Estimated annual household income tax", f"${amount:,.2f}")
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
st.write("Enter your personal salary and ZIP to explore the services your household's tax dollars could support, ranked from largest to smallest.")
st.caption("Salt Lake City, Utah | Tax year 2026")
st.info("Demo profile: Married homeowners in Salt Lake City with one child under 17.")
st.caption("Your salary and local averages help illustrate this household's taxes. See assumptions and sources below.")

with st.form("tax_inputs"):
    salary = st.number_input("Your annual gross salary ($)", min_value=0, max_value=10000000, value=None, placeholder="Enter your salary", step=1000, help="Enter your individual salary, not combined household income. The prototype applies its disclosed household-income assumption automatically.")
    zip_code = st.text_input("Residential ZIP code", max_chars=5, placeholder="Enter your ZIP code")
    st.caption("Enter just your salary and ZIP. Results use the demo household and show estimated allocations.")
    submitted = st.form_submit_button("Show where my tax dollars could go")

if submitted:
    error = None
    if salary is None:
        error = "Please enter your annual gross salary."
    elif not re.fullmatch(r"[0-9]{5}", zip_code.strip()):
        error = "Please enter a five-digit ZIP code."
    elif zip_code.strip() not in PILOT_ZIPS:
        error = "This pilot uses selected Salt Lake City ZIPs, such as 84101, 84103 or 84111. Other locations are not implemented."
    if error:
        st.session_state.pop("profile", None)
        st.error(error)
    else:
        st.session_state["profile"] = {"salary": salary, "zip_code": zip_code.strip()}

profile = st.session_state.get("profile")
# Clear a submission from the previous pilot after the deployment changes.
if profile and profile["zip_code"] not in PILOT_ZIPS:
    st.session_state.pop("profile", None)
    profile = None
if profile:
    taxes = estimate_taxes(profile["salary"])
    st.subheader("Your household's annual tax story")
    st.write(f"Your salary: **${profile['salary']:,.0f}** | ZIP: **{profile['zip_code']}**")
    st.write(f"Assumed household income: **${taxes['household_income']:,.2f}** (about 2.06 times your salary).")
    columns = st.columns(2)
    for index, level in enumerate(["Federal", "State", "County", "City"]):
        columns[index % 2].metric(f"{level} household homeowner scenario" if level in ("County", "City") else f"{level} household income tax estimate", f"${taxes[level]:,.2f}")
    st.caption(f"City and county examples assume a home worth ${taxes['assumed_home_value']:,.0f}. They do not calculate your actual property taxes.")
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
    st.write("Selected ZIP codes choose the Salt Lake City demo. They do not verify a property's city boundary. Assumes wage income with no pre-tax deductions.")
    st.write("Profile: married filing jointly, both adults under 65, with one qualifying child under 17 and required Social Security numbers. The child assumption is a demo choice, not a measured city average. Household income is modeled from the citizen's personal salary; it is not an estimate of actual spouse earnings.")
    st.write("Federal: 2026 married-filing-jointly progressive brackets and a $32,200 standard deduction. Includes one nonrefundable child tax credit of up to $2,200, reduced by $50 per $1,000 (or part) of household income above $400,000. Tax is floored at zero. Refundable ACTC, EITC, other credits, payroll taxes and AMT are not modeled.")
    st.markdown("[IRS 2026 brackets and standard deduction](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers)")
    st.markdown("[IRS 2026 child and dependent credit calculation](https://www.irs.gov/pub/irs-prior/f1040s8--2026.pdf)")
    st.write("Utah: assumes modeled household wages equal state taxable income; 4.45% rate, less the nonrefundable taxpayer tax credit: 6% times ($32,200 joint standard deduction + $2,167 for one dependent), reduced by 1.3% of household income above $37,392. Other credits and exemptions are excluded.")
    st.markdown("[Utah income-tax rate](https://le.utah.gov/xcode/Title59/Chapter10/C59-10-S104_2026050620260506.html) | [Utah taxpayer credit, 2026 review](https://le.utah.gov/interim/2026/pdf/00003360.pdf)")
    st.write("Scenario multipliers use 2020-2024 ACS figures: median owner-occupied home value $539,500; median full-time worker earnings $62,180; median married-couple family income $127,972. Household-income multiplier = 127,972 / 62,180 = 2.05809. Home/household-income multiplier = 539,500 / 127,972 = 4.21577. Combined home/personal-salary multiplier = 8.67642. The ratios are not independent multipliers to apply twice to salary, nor are they a count of earners.")
    st.markdown("[Census home-value data](https://www.census.gov/quickfacts/fact/table/saltlakecitycityutah/EDU635224) | [ACS earnings and married-family income figures reported by Neilsberg](https://www.neilsberg.com/insights/topic/salt-lake-city-ut/)")
    st.write("Taxable home value is 55% of the scenario home value. City scenario uses the approved 2026 Salt Lake City general operations rate of 0.002374 only. County scenario uses the sum of approved countywide rates, 0.001349, excluding the separate library levy. Neither represents the complete property-tax bill.")
    st.markdown("[Utah Tax Commission approved 2026 levy rates](https://tax.utah.gov/propertytax/rates/approved-rates/)")
    st.write("Tax rules are for 2026. Federal spending uses FY2025 actual outlays; state uses FY2026-27 appropriations; city uses a verified FY2025-26 adopted snapshot; county uses a 2026 budget snapshot. Years and scopes are labeled in each panel. Transfers are not reallocated twice. This is not a comprehensive tax bill or a tax-return calculation.")

st.caption("Educational prototype. Inputs stay in this app session; this code does not store them in a database or send them to an AI service.")
