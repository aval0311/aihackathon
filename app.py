"""Two-input individual tax story using a married, single-earner demo profile."""
import json
import re
from pathlib import Path
import streamlit as st
from tax_model import estimate_taxes, allocate_tax_dollars

st.set_page_config(page_title="Your Tax Dollar", page_icon="??", layout="centered")
DATA_DIR = Path(__file__).resolve().parent / "data"
PILOT_ZIPS = {"84101", "84102", "84103", "84104", "84105", "84106", "84108", "84111", "84112", "84116"}
LEVEL_STYLE = {
    "Federal": {"icon": "???", "color": "#087F8C", "place": "United States"},
    "State": {"icon": "???", "color": "#6554A4", "place": "Utah"},
    "County": {"icon": "??", "color": "#33744A", "place": "Salt Lake County"},
    "City": {"icon": "???", "color": "#A76512", "place": "Salt Lake City"},
}

# Scope decorative CSS to our own cards; native controls use the theme above.
st.markdown("""
<style>
.tax-eyebrow {color:#087F8C;font-size:.8rem;font-weight:750;letter-spacing:.12em;text-transform:uppercase;margin:0 0 .35rem;}
.tax-tagline {font-size:1.4rem;font-weight:650;line-height:1.4;margin:0 0 .5rem;}
.tax-profile {background:#EDF5F0;color:#172B4D;border-radius:16px;padding:1rem 1.2rem;border-left:5px solid #D5A73C;margin:.5rem 0;}
.tax-profile strong {display:block;margin-bottom:.3rem;}
.tax-summary {background:#FFFFFF;color:#172B4D;border:1px solid #DCE5E4;border-top:4px solid var(--accent);border-radius:16px;padding:1rem 1.2rem;margin-bottom:1rem;}
.tax-summary-label {font-size:1rem;font-weight:700;}
.tax-summary-amount {font-size:clamp(1.5rem,4vw,2rem);font-weight:750;line-height:1.6;font-variant-numeric:tabular-nums;}
.tax-summary-note {font-size:.8rem;color:#526078;}
</style>
""", unsafe_allow_html=True)


def allocation_chart_spec(allocations, color):
    """Keep category order explicit and leave room for dollar labels at bar ends."""
    largest = max(row["Your allocation (USD)"] for row in allocations)
    return {
        "description": "Your annual tax allocations ranked from largest to smallest, with dollar labels.",
        "encoding": {
            "y": {"field": "Category", "type": "nominal", "title": None,
                  "sort": [row["Category"] for row in allocations],
                  "axis": {"labelLimit": 180, "labelFontSize": 12, "ticks": False, "domain": False}},
            "x": {"field": "Your allocation (USD)", "type": "quantitative",
                  "title": "Your annual allocation (USD)", "scale": {"domain": [0, max(1, largest * 1.4)]},
                  "axis": {"format": "$,.0f", "tickCount": 4, "gridColor": "#E7ECEB", "domain": False}},
            "tooltip": [{"field": "Category", "type": "nominal"},
                        {"field": "Your allocation (USD)", "type": "quantitative", "format": "$,.2f"},
                        {"field": "Share (%)", "type": "quantitative", "format": ".2f"}],
        },
        "layer": [
            {"mark": {"type": "bar", "color": color, "cornerRadiusEnd": 5, "height": 20}},
            {"mark": {"type": "text", "align": "left", "dx": 7, "color": "#172B4D", "fontSize": 12},
             "encoding": {"text": {"field": "Your allocation (USD)", "type": "quantitative", "format": "$,.2f"}}},
        ],
        "config": {"view": {"stroke": None}, "background": "#FFFCF5"},
    }


def parse_salary_entry(value):
    """Accept plain digits or correctly grouped commas, with optional cents."""
    text = value.strip().removeprefix("$").strip()
    if not text:
        return None
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?", text):
        raise ValueError("Enter a salary such as 100,000.")
    amount = float(text.replace(",", ""))
    if not 0 <= amount <= 10000000:
        raise ValueError("Enter a salary between 0 and 10,000,000.")
    return amount


def format_salary_entry():
    """Add thousands separators after the user finishes editing the field."""
    try:
        amount = parse_salary_entry(st.session_state.get("salary_entry", ""))
    except ValueError:
        return  # Show validation feedback when the user submits.
    if amount is not None:
        st.session_state["salary_entry"] = (
            f"{amount:,.0f}" if amount.is_integer() else f"{amount:,.2f}"
        )


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
    style = LEVEL_STYLE[level]
    label = "Your illustrative property-tax allocation" if local else "Your estimated income-tax allocation"
    st.subheader(f"{style['icon']} {snapshot['jurisdiction']}")
    st.caption(f"{label} | {snapshot['period']}")
    allocations = allocate_tax_dollars(snapshot["rows"], amount)
    with st.container(border=True):
        if amount > 0:
            top = allocations[0]
            st.caption(f"YOUR LARGEST {level.upper()} ALLOCATION")
            st.subheader(top["Category"])
            st.write(f"About **${top['Your allocation (USD)']:,.2f} per year** of your estimated {level.lower()} taxes supports this category - **{top['Share (%)']:.1f}%** of this breakdown.")
        else:
            st.write("Your estimated tax is $0 at this level. Each allocation below is $0.")
    st.markdown("#### Follow your dollars")
    st.caption("Largest to smallest � Hover over a bar for more detail.")
    st.vega_lite_chart(
        allocations,
        allocation_chart_spec(allocations, style["color"]),
        height=max(240, len(allocations) * 38),
        use_container_width=True,
        theme=None,
    )
    with st.expander("See every allocation in a table"):
        st.dataframe(
            allocations, hide_index=True, use_container_width=True,
            column_config={"Your allocation (USD)": st.column_config.NumberColumn(format="$%.2f"), "Share (%)": st.column_config.NumberColumn(format="%.2f%%")},
        )
        st.caption("Allocations add up to your displayed tax amount, including rounding.")
    with st.expander("Budget source and how this breakdown works"):
        st.markdown(f"[Official spending source]({snapshot['source_url']}) - {snapshot['source_location']}.")
        st.write("Allocation = tax amount multiplied by each category's share of this spending snapshot. These are proportional illustrations, not a trace of your individual payments.")
        st.write(snapshot["scope"])
        st.write(snapshot["notes"])
        st.caption(f"Underlying source weights are in {snapshot['weight_unit']}.")
        st.dataframe(snapshot["rows"], hide_index=True, use_container_width=True)


def submit_profile():
    """Validate both entries before opening the separate results view."""
    error = None
    try:
        salary = parse_salary_entry(st.session_state.get("salary_entry", ""))
    except ValueError as exc:
        salary = None
        error = str(exc)
    zip_code = st.session_state.get("zip_entry", "").strip()
    if not error:
        if salary is None:
            error = "Please enter your annual gross salary."
        elif not re.fullmatch(r"[0-9]{5}", zip_code):
            error = "Please enter a five-digit ZIP code."
        elif zip_code not in PILOT_ZIPS:
            error = "This pilot uses selected Salt Lake City ZIPs, such as 84101, 84103 or 84111. Other locations are not implemented."
    if error:
        st.session_state.pop("profile", None)
        st.session_state["input_error"] = error
        st.session_state["view"] = "inputs"
        return
    format_salary_entry()
    st.session_state["profile"] = {"salary": salary, "zip_code": zip_code}
    st.session_state.pop("input_error", None)
    st.session_state["view"] = "results"


def edit_profile():
    """Restore submitted values when returning from results to the landing page."""
    profile = st.session_state.get("profile", {})
    salary = profile.get("salary")
    if salary is not None:
        st.session_state["salary_entry"] = f"{salary:,.0f}" if float(salary).is_integer() else f"{salary:,.2f}"
    st.session_state["zip_entry"] = profile.get("zip_code", "")
    st.session_state.pop("input_error", None)
    st.session_state["view"] = "inputs"


def show_assumptions():
    """Keep detailed methodology and privacy text on the results view."""
    with st.expander("Tax rules, assumptions, and sources"):
        st.write("Selected ZIP codes choose the Salt Lake City demo. They do not verify a property's city boundary. Assumes wage income with no pre-tax deductions.")
        st.write("Profile: you are married filing jointly, both adults are under 65, with one qualifying child under 17 and required Social Security numbers. You are the sole earner and pay the modeled local property taxes. Your spouse has no additional income. These are demo assumptions, not measured facts about the person using the app. The entered salary is used directly for income-tax calculations; it is not multiplied to add assumed spouse earnings.")
        st.write("Federal: 2026 married-filing-jointly progressive brackets and a $32,200 standard deduction. Includes one nonrefundable child tax credit of up to $2,200, reduced by $50 per $1,000 (or part) of household income above $400,000. Tax is floored at zero. Refundable ACTC, EITC, other credits, payroll taxes and AMT are not modeled.")
        st.markdown("[IRS 2026 brackets and standard deduction](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers)")
        st.markdown("[IRS 2026 child and dependent credit calculation](https://www.irs.gov/pub/irs-prior/f1040s8--2026.pdf)")
        st.write("Utah: assumes your entered wages equal state taxable income; 4.45% rate, less the nonrefundable taxpayer tax credit: 6% times ($32,200 joint standard deduction + $2,167 for one dependent), reduced by 1.3% of income above $37,392. Other credits and exemptions are excluded.")
        st.markdown("[Utah income-tax rate](https://le.utah.gov/xcode/Title59/Chapter10/C59-10-S104_2026050620260506.html) | [Utah taxpayer credit, 2026 review](https://le.utah.gov/interim/2026/pdf/00003360.pdf)")
        st.write("Home-value scenario uses 2020-2024 ACS figures: median owner-occupied home value $539,500 divided by median full-time worker earnings $62,180 = 8.67642. We multiply your individual salary by this ratio only to create a hypothetical home value. A ratio of citywide medians does not predict an individual's home value. The previously discussed 2.06 household-income multiplier is not applied to your income or taxes.")
        st.markdown("[Census home-value data](https://www.census.gov/quickfacts/fact/table/saltlakecitycityutah/EDU635224) | [ACS full-time worker earnings reported by Neilsberg](https://www.neilsberg.com/insights/topic/salt-lake-city-ut/)")
        st.write("Taxable home value is 55% of the scenario home value. City scenario uses the approved 2026 Salt Lake City general operations rate of 0.002374 only. County scenario uses the sum of approved countywide rates, 0.001349, excluding the separate library levy. Neither represents the complete property-tax bill.")
        st.markdown("[Utah Tax Commission approved 2026 levy rates](https://tax.utah.gov/propertytax/rates/approved-rates/)")
        st.write("Tax rules are for 2026. Federal spending uses FY2025 actual outlays; state uses FY2026-27 appropriations; city uses a verified FY2025-26 adopted snapshot; county uses a 2026 budget snapshot. Years and scopes are labeled in each panel. Transfers are not reallocated twice. This is not a comprehensive tax bill or a tax-return calculation.")

    st.caption("Educational prototype. Inputs stay in this app session; this code does not store them in a database or send them to an AI service.")


# A submitted profile opens a separate view; the landing page contains no results.
profile = st.session_state.get("profile")
if profile and profile["zip_code"] not in PILOT_ZIPS:
    st.session_state.pop("profile", None)
    st.session_state["view"] = "inputs"
    profile = None

if st.session_state.get("view", "inputs") == "results" and profile:
    st.markdown('<p class="tax-eyebrow">Your Tax Dollar � Your personal tax receipt</p>', unsafe_allow_html=True)
    st.title("Where your tax dollars go")
    st.button("Change salary or ZIP", on_click=edit_profile)
    taxes = estimate_taxes(profile["salary"])
    st.write(f"Your salary: **${profile['salary']:,.0f}** � ZIP: **{profile['zip_code']}** � Tax year **2026**")
    st.caption("An estimate based on your demo profile and published spending shares.")
    # Two columns keep amounts readable on a projected screen and stack on phones.
    columns = st.columns(2)
    for index, level in enumerate(["Federal", "State", "County", "City"]):
        style = LEVEL_STYLE[level]
        note = "Property-tax scenario / year" if level in ("County", "City") else "Estimated income tax / year"
        columns[index % 2].markdown(
            f'<div class="tax-summary" style="--accent:{style["color"]}">'
            f'<div class="tax-summary-label">{style["icon"]} {level} � {style["place"]}</div>'
            f'<div class="tax-summary-amount">${taxes[level]:,.2f}</div>'
            f'<div class="tax-summary-note">{note}</div></div>', unsafe_allow_html=True,
        )
    st.caption(f"City and county examples assume you pay the modeled taxes on a home worth ${taxes['assumed_home_value']:,.0f}. They do not calculate your actual property taxes.")
    st.markdown("### Explore your impact")
    st.write("Choose a government level to follow your dollars.")
    try:
        snapshots = load_snapshots()
    except (OSError, ValueError, KeyError, TypeError):
        st.error("A reviewed spending snapshot could not be loaded or verified.")
    else:
        levels = ["Federal", "State", "County", "City"]
        for level, tab in zip(levels, st.tabs(levels)):
            with tab:
                show_breakdown(level, snapshots[level], taxes[level])
    show_assumptions()
else:
    st.markdown('<p class="tax-eyebrow">?? A little clarity. A closer community.</p>', unsafe_allow_html=True)
    st.title("Your Tax Dollar")
    st.markdown('<p class="tax-tagline">Your money. Your community.<br>See the connection.</p>', unsafe_allow_html=True)
    st.write("Discover the services your tax dollars help support - from your neighborhood to the nation.")
    st.caption("Salt Lake City, Utah � Tax year 2026")
    st.markdown('<div class="tax-profile"><strong>?? Your demo profile</strong>You are married, own a home in Salt Lake City, and have one child under 17.</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Start with two simple details")
        st.caption("Your individual salary + ZIP  your estimated tax story")
        st.text_input("Your annual gross salary ($)", key="salary_entry", placeholder="Enter your salary", max_chars=20, on_change=format_salary_entry, help="Enter your individual salary before taxes, for example 100,000. For this demo, your spouse has no additional income.")
        st.text_input("Residential ZIP code", key="zip_entry", max_chars=5, placeholder="Enter your ZIP code")
        st.caption("Salt Lake City pilot � Try ZIP 84103. Estimates and sources appear with your results.")
        st.button("Show where my tax dollars go", on_click=submit_profile, type="primary", use_container_width=True)
    if st.session_state.get("input_error"):
        st.error(st.session_state["input_error"])
