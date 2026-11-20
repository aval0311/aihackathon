"""Two-input individual tax story using a married, single-earner demo profile."""
import re
from html import escape
from decimal import DecimalException
import streamlit as st
from tax_model import estimate_taxes
from spending_data import load_spending_data, build_allocations

st.set_page_config(page_title="Your Tax Dollar", page_icon="🪙", layout="centered")
PILOT_ZIPS = {"84101", "84102", "84103", "84104", "84105", "84106", "84108", "84111", "84112", "84116"}
LEVEL_STYLE = {
    "Federal": {"icon": "🏛️", "place": "United States"},
    "State": {"icon": "🏔️", "place": "Utah"},
    "County": {"icon": "🌳", "place": "Salt Lake County"},
    "City": {"icon": "🏙️", "place": "Salt Lake City"},
}

# Scope decorative CSS to our own cards; native controls use .streamlit/config.toml.
st.markdown("""
<style>
:root {
    --tax-lake: #165C82;
    --tax-navy: #17324D;
    --tax-ice: #E8F3F8;
    --tax-white: #FFFFFF;
    --tax-muted: #455D70;
    --tax-border: #C9DCE6;
}
.tax-eyebrow {color:var(--tax-lake);font-size:.95rem;font-weight:750;letter-spacing:.12em;text-transform:uppercase;margin:0 0 .35rem;}
.tax-tagline {font-size:1.5rem !important;font-weight:650;line-height:1.4;margin:0 0 .5rem;}
.tax-profile {font-size:1.05rem;background:var(--tax-ice);color:var(--tax-navy);border-radius:16px;padding:1rem 1.2rem;border-left:5px solid var(--tax-lake);margin:.5rem 0;}
.tax-profile strong {display:block;margin-bottom:.3rem;}
.tax-summary {background:var(--tax-white);color:var(--tax-navy);border:1px solid var(--tax-border);border-top:4px solid var(--tax-lake);border-radius:16px;padding:1rem 1.2rem;margin-bottom:1rem;}
.tax-summary-label {font-size:1.1rem;font-weight:700;}
.tax-summary-amount {font-size:clamp(1.8rem,4vw,2.2rem);font-weight:750;line-height:1.6;font-variant-numeric:tabular-nums;}
.tax-summary-note {font-size:1rem;color:var(--tax-muted);}
.tax-tree {margin:1rem 0;}
.tax-node {border:1px solid var(--tax-border);border-radius:12px;margin:.6rem 0;background:var(--tax-white);color:var(--tax-navy);}
.tax-node summary {font-size:1.05rem;display:flex;gap:.65rem;align-items:center;cursor:pointer;padding:1rem;font-weight:650;list-style:none;}
.tax-node summary::-webkit-details-marker {display:none;}
.tax-node summary::before {content:'+';font-size:1.3rem;font-weight:750;color:var(--tax-lake);flex-shrink:0;}
.tax-node[open]>summary::before {content:'-';}
.tax-node summary:focus-visible {outline:3px solid var(--tax-lake);outline-offset:2px;border-radius:10px;}
.tax-node-amount {margin-left:auto;white-space:nowrap;font-size:1.05rem;font-weight:700;font-variant-numeric:tabular-nums;}
.tax-node-content {padding:0 1rem 1rem;}
.tax-leaf {display:flex;gap:.75rem;padding:.75rem .25rem;border-bottom:1px solid var(--tax-border);}
.tax-leaf>span:first-child {overflow-wrap:anywhere;}
.tax-node-context,.tax-metric-context {font-size:1rem;color:var(--tax-muted);margin:.5rem 0;}
@media(max-width:480px) {.tax-node summary,.tax-leaf {flex-wrap:wrap;}.tax-node-amount {margin-left:1.3rem;}}
.tax-bar-row {margin:1rem 0 1.25rem;}
.tax-bar-label {display:flex;align-items:baseline;justify-content:space-between;gap:1rem;font-size:1.1rem;color:var(--tax-navy);}
.tax-bar-label span {min-width:0;overflow-wrap:anywhere;}
.tax-bar-label strong {flex-shrink:0;font-variant-numeric:tabular-nums;}
.tax-bar-track {height:14px;background:var(--tax-ice);border-radius:7px;margin-top:.45rem;overflow:hidden;}
.tax-bar-fill {background:var(--tax-lake);height:100%;border-radius:7px;}
@media(max-width:480px) {.tax-node summary>span:first-child {min-width:0;overflow-wrap:anywhere;}.tax-node-content {padding-left:.6rem;padding-right:.6rem;}.tax-bar-label {gap:.65rem;}}
/* Keep native labels, tabs and explanatory text legible when projected. */
[data-testid="stWidgetLabel"] p,
[data-testid="stCaptionContainer"] p,
[data-testid="stButton"] p,
[data-baseweb="tab"] p {font-size:1rem !important;line-height:1.5;}
.tax-leaf {font-size:1.05rem;}
@media(max-width:640px) {
    .tax-bar-label {flex-wrap:wrap;}
    .tax-bar-label span {flex-basis:100%;}
    .tax-bar-label strong {margin-left:auto;}
    .tax-summary-label {overflow-wrap:anywhere;}
    .tax-summary-amount {font-size:1.65rem;overflow-wrap:anywhere;}
}
</style>
""", unsafe_allow_html=True)


def render_allocation_chart(allocations):
    """Responsive bars keep full category names and exact dollars above each bar."""
    largest = max(row["Your allocation (USD)"] for row in allocations)
    html = '<div class="tax-bars" role="list" aria-label="Annual allocations, largest to smallest">'
    for row in allocations:
        name = escape(row["Category"])
        amount = row["Your allocation (USD)"]
        width = amount / largest * 100 if largest else 0
        html += (f'<div class="tax-bar-row" role="listitem"><div class="tax-bar-label">'
                 f'<span>{name}</span><strong>${amount:,.2f}</strong></div>'
                 f'<div class="tax-bar-track" aria-hidden="true"><div class="tax-bar-fill" '
                 f'style="width:{width:.6f}%"></div></div></div>')
    return html + '</div>'

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


def render_allocation_details(pool, broad, amounts, groups):
    """Native HTML disclosures allow accessible nested '+' drilldowns."""
    nodes = pool["nodes"]

    def money_label(value):
        return f'<span class="tax-node-amount">${value:,.2f} / year</span>'

    def render_node(row):
        key = row["node_id"]
        children = [nodes[child] for child in pool["children"].get(key, [])]
        spending = sorted((child for child in children if child["allocation_status"] == "spending"),
                          key=lambda child: (amounts[child["node_id"]], child["share"]), reverse=True)
        metrics = [child for child in children if child["allocation_status"] == "metric"]
        label = escape(row["plain_english_name"])
        value = money_label(amounts[key])
        description = row.get("plain_english_description", "")
        context = f'<p class="tax-node-context">{escape(description)}</p>' if description else ""
        if not spending and not metrics:
            return f'<div class="tax-leaf"><span>{label}</span>{value}</div>' + context
        content = context + "".join(render_node(child) for child in spending)
        if metrics:
            content += '<p class="tax-node-context">Service context (not additional spending)</p>'
            for metric in metrics:
                number = float(metric["metric_value"])
                formatted = f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"
                content += (f'<div class="tax-metric-context">{escape(metric["plain_english_name"])}: '
                            f'<strong>{formatted} {escape(metric["metric_unit"])}</strong></div>')
        return (f'<details class="tax-node"><summary><span>{label}</span>{value}</summary>'
                f'<div class="tax-node-content">{content}</div></details>')

    html = '<div class="tax-tree">'
    for category in broad:
        name = category["Category"]
        members = sorted(groups[name], key=lambda row: (amounts[row["node_id"]], row["share"]), reverse=True)
        html += (f'<details class="tax-node tax-broad"><summary><span>{escape(name)}</span>'
                 f'{money_label(category["Your allocation (USD)"])}</summary><div class="tax-node-content">'
                 + "".join(render_node(row) for row in members) + '</div></details>')
    return html + '</div>'


def show_breakdown(level, pool, amount):
    """Show broad purposes first; '+' disclosures reveal named CSV sublevels."""
    style = LEVEL_STYLE[level]
    root = pool["root"]
    st.subheader(f"{style['icon']} {root['entity']}")
    period = "FY2025 actual spending" if level == "Federal" else "FY2026 spending data"
    label = "Property-tax scenario" if level in ("County", "City") else "Estimated income-tax allocation"
    st.caption(f"{label} | {period}")
    if level == "County":
        st.warning("Broad county spending illustration: this CSV redistributes shared costs and does not separately identify public safety. It also includes library and fee-funded services outside our modeled county levy. These shares do not trace your property-tax payments.")
    elif level == "State":
        st.caption("Uses Utah's all-source spending mix, including federal funding, as an illustration of your estimated state taxes.")
    elif level == "Federal":
        st.caption("The CSV spreads interest and general government costs across services; those costs are included in the program shares below.")
    else:
        st.caption("The CSV distributes shared and non-departmental costs across city departments. These are modeled service allocations.")
    allocations, amounts, groups = build_allocations(pool, amount)
    with st.container(border=True):
        if amount > 0:
            top = allocations[0]
            st.caption(f"YOUR LARGEST {level.upper()} ALLOCATION")
            st.subheader(top["Category"])
            st.write(f"About **${top['Your allocation (USD)']:,.2f} per year** of your estimated {level.lower()} taxes is allocated here in this illustration (**{top['Share (%)']:.1f}%**).")
        else:
            st.write("Your estimated tax is $0 at this level. Each allocation below is $0.")
    st.markdown("#### Follow your dollars")
    st.caption("Largest to smallest. Dollar amounts are annual estimates.")
    st.markdown(render_allocation_chart(allocations), unsafe_allow_html=True)
    st.markdown("#### Explore the categories")
    st.caption("Select + to see named subcategories. Select + again where more detail is available. Subcategories are parts of their parent amount, not additional taxes.")
    st.markdown(render_allocation_details(pool, allocations, amounts, groups), unsafe_allow_html=True)
    with st.expander("See every broad allocation in a table"):
        st.dataframe(allocations, hide_index=True, use_container_width=True,
                     column_config={"Your allocation (USD)": st.column_config.NumberColumn(format="$%.2f"),
                                    "Share (%)": st.column_config.NumberColumn(format="%.2f%%")})
        st.caption("Broad categories add up to your displayed tax estimate. Each expanded spending branch adds up to its parent, including rounding.")
    with st.expander("Dataset, sources and allocation assumptions"):
        st.markdown("[View the allocation CSV](https://github.com/aval0311/your-tax-dollar/blob/main/data/tax-explorer/tax_explorer_prototype_v3_reconciled.csv)")
        st.write("Your individual tax estimate is distributed using this CSV's normalized spending shares. Broad purposes group the first-level records by citizen category. Shared costs and interest retain the CSV's attribution method. These figures illustrate spending patterns; they do not track actual payments or personal benefits.")
        st.write(root["notes"])
        if level == "County":
            st.caption("The county source URL supplied in the CSV could not be verified during review. It is preserved in the source table below.")
        st.caption("Official amounts are published spending figures. Attributed amounts include the dataset's modeled redistribution; they are not official department budgets. Staffing and service metrics never enter money totals.")
        details = [{"Category": row["plain_english_name"], "Level": row["depth"],
                    "Official spending (USD)": float(row["official_amount_usd"] or 0),
                    "Modeled attributed spending (USD)": float(row["attributed_spending_usd"]),
                    "Method": row["allocation_method"], "Source": row["source_url"],
                    "Page": row.get("source_page", ""), "Notes": row["notes"]}
                   for row in pool["nodes"].values() if row["allocation_status"] == "spending"]
        st.dataframe(details, hide_index=True, use_container_width=True)


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
        st.write("Tax rules are for 2026. The canonical allocation CSV uses FY2025 federal spending and FY2026 state and local data. State and county shares are all-source approximations, including grants, fees and potentially internal transfers. Federal interest and shared costs are redistributed as documented in the CSV. The county library spending scope differs from our levy estimate, and county public safety is not separately identified. We do not add government spending totals together. School-district data is not used. These are proportional illustrations, not a comprehensive tax bill or a tax-return calculation.")

    st.caption("Educational prototype. Inputs stay in this app session; this code does not store them in a database or send them to an AI service.")


# A submitted profile opens a separate view; the landing page contains no results.
profile = st.session_state.get("profile")
if profile and profile["zip_code"] not in PILOT_ZIPS:
    st.session_state.pop("profile", None)
    st.session_state["view"] = "inputs"
    profile = None

if st.session_state.get("view", "inputs") == "results" and profile:
    st.markdown('<p class="tax-eyebrow">Your Tax Dollar · Your personal tax receipt</p>', unsafe_allow_html=True)
    st.title("Where your tax dollars go")
    st.button("Change salary or ZIP", on_click=edit_profile)
    taxes = estimate_taxes(profile["salary"])
    st.write(f"Your salary: **${profile['salary']:,.0f}** · ZIP: **{profile['zip_code']}** · Tax year **2026**")
    st.caption("An estimate based on your demo profile and published spending shares.")
    # Separate rows preserve Federal, State, County, City order when columns stack.
    for index, level in enumerate(["Federal", "State", "County", "City"]):
        if index % 2 == 0:
            columns = st.columns(2)
        style = LEVEL_STYLE[level]
        note = "Property-tax scenario / year" if level in ("County", "City") else "Estimated income tax / year"
        columns[index % 2].markdown(
            '<div class="tax-summary">'
            f'<div class="tax-summary-label">{style["icon"]} {level} · {style["place"]}</div>'
            f'<div class="tax-summary-amount">${taxes[level]:,.2f}</div>'
            f'<div class="tax-summary-note">{note}</div></div>', unsafe_allow_html=True,
        )
    st.caption(f"City and county examples assume you pay the modeled taxes on a home worth ${taxes['assumed_home_value']:,.0f}. They do not calculate your actual property taxes.")
    st.markdown("### Explore your impact")
    st.write("Choose a government level to follow your dollars.")
    try:
        pools = load_spending_data()
    except (OSError, ValueError, KeyError, TypeError, DecimalException):
        st.error("The allocation CSV could not be loaded or verified. Please check its columns and spending totals.")
    else:
        levels = ["Federal", "State", "County", "City"]
        for level, tab in zip(levels, st.tabs(levels)):
            with tab:
                show_breakdown(level, pools[level], taxes[level])
    show_assumptions()
else:
    st.markdown('<p class="tax-eyebrow">🪙 A little clarity. A closer community.</p>', unsafe_allow_html=True)
    st.title("Your Tax Dollar")
    st.markdown('<p class="tax-tagline">Your money. Your community.<br>See the connection.</p>', unsafe_allow_html=True)
    st.write("Discover the services your tax dollars help support — from your neighborhood to the nation.")
    st.caption("Salt Lake City, Utah · Tax year 2026")
    st.markdown('<div class="tax-profile"><strong>🏡 Your demo profile</strong>You are married, own a home in Salt Lake City, and have one child under 17.</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Start with two simple details")
        st.caption("Your individual salary + ZIP → your estimated tax story")
        st.text_input("Your annual gross salary ($)", key="salary_entry", placeholder="Enter your salary", max_chars=20, on_change=format_salary_entry, help="Enter your individual salary before taxes, for example 100,000. For this demo, your spouse has no additional income.")
        st.text_input("Residential ZIP code", key="zip_entry", max_chars=5, placeholder="Enter your ZIP code")
        st.caption("Salt Lake City pilot · Try ZIP 84103. Estimates and sources appear with your results.")
        st.button("Show where my tax dollars go", on_click=submit_profile, type="primary", use_container_width=True)
    if st.session_state.get("input_error"):
        st.error(st.session_state["input_error"])
