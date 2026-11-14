# Create the Streamlit application file.
import csv
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import streamlit as st

# Configure the page; use the default icon to avoid encoding issues.
st.set_page_config(
    page_title="Your Tax Dollar",
    layout="centered",
)

# Resolve data relative to this script, including on Streamlit Cloud.
CITY = "Draper"
COUNTY = "Salt Lake and Utah counties"
STATE = "Utah"
DATA_DIR = Path(__file__).resolve().parent / "data"


def load_city_budget():
    """Load the reviewed snapshot and check it against its source total."""
    metadata = json.loads(
        (DATA_DIR / "draper_general_fund_fy2027_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    with (DATA_DIR / metadata["dataset_file"]).open(
        encoding="utf-8", newline=""
    ) as source_file:
        rows = list(csv.DictReader(source_file))
    amounts = [int(row["amount_usd"]) for row in rows]
    total = sum(amounts)
    if (
        not rows
        or any(amount < 0 for amount in amounts)
        or total <= 0
        or total != metadata["published_total_usd"]
        or len({row["category"] for row in rows}) != len(rows)
    ):
        raise ValueError("Budget data does not match its published total.")
    spending = [
        {
            "Category": row["category"],
            "Budget (USD)": amount,
            "Share (%)": amount / total * 100,
        }
        for row, amount in zip(rows, amounts)
    ]
    return sorted(spending, key=lambda row: row["Budget (USD)"], reverse=True), metadata


def allocate_tax_dollars(spending, annual_tax):
    """Allocate a tax amount using spending shares and reconcile every cent."""
    amount = Decimal(str(annual_tax))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Tax contribution must be a nonnegative amount.")
    cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total = sum(row["Budget (USD)"] for row in spending)
    # Allocate whole cents first, then distribute leftover cents fairly.
    parts = [divmod(cents * row["Budget (USD)"], total) for row in spending]
    allocated = [part[0] for part in parts]
    remainder_order = sorted(
        range(len(parts)), key=lambda index: parts[index][1], reverse=True
    )
    for index in remainder_order[:cents - sum(allocated)]:
        allocated[index] += 1
    rows = [
        {
            "Category": row["Category"],
            "Your tax allocation (USD)": value / 100,
            "Share (%)": row["Share (%)"],
        }
        for row, value in zip(spending, allocated)
    ]
    return sorted(
        rows,
        key=lambda row: (row["Your tax allocation (USD)"], row["Share (%)"]),
        reverse=True,
    )


def show_city_budget(annual_city_tax):
    """Tell the citizen's tax story using the city's reviewed spending shares."""
    try:
        spending, metadata = load_city_budget()
    except (OSError, ValueError, KeyError, TypeError):
        st.error("City budget data could not be loaded or verified.")
        return

    st.subheader("Where your Draper city tax dollars could go")
    st.caption(
        f"FY {metadata['fiscal_year']} | August 2026 adoption snapshot | "
        "Budgeted amounts, including transfers"
    )
    if annual_city_tax is None:
        st.info(
            "Enter your annual Draper city property tax amount in the form "
            "above and submit again to see your dollar breakdown. Use only "
            "the Draper City portion, not your entire property tax bill."
        )
    else:
        allocations = allocate_tax_dollars(spending, annual_city_tax)
        st.metric("City tax amount you entered", f"${annual_city_tax:,.2f}")
        if annual_city_tax > 0:
            top = allocations[0]
            st.write(
                f"Your largest illustrative allocation is **{top['Category']}**: "
                f"**${top['Your tax allocation (USD)']:,.2f} per year** "
                f"({top['Share (%)']:.2f}% of the amount you entered)."
            )
        else:
            st.write("You entered zero city tax, so every allocation is zero.")
        st.caption("Illustrative annual allocations, ordered largest to smallest.")
        # Set the chart's category order explicitly so it matches the table.
        st.vega_lite_chart(
            allocations,
            {
                "mark": "bar",
                "encoding": {
                    "y": {
                        "field": "Category", "type": "nominal",
                        "sort": [row["Category"] for row in allocations],
                        "axis": {"labelLimit": 220},
                    },
                    "x": {
                        "field": "Your tax allocation (USD)",
                        "type": "quantitative",
                        "title": "Your illustrative allocation per year (USD)",
                        "axis": {"format": "$,.2f"},
                    },
                    "tooltip": [
                        {"field": "Category", "type": "nominal"},
                        {"field": "Your tax allocation (USD)",
                         "type": "quantitative", "format": "$,.2f"},
                    ],
                },
            },
            height=480,
            use_container_width=True,
        )
        st.dataframe(
            allocations,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Your tax allocation (USD)": st.column_config.NumberColumn(
                    format="$%.2f"
                ),
                "Share (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        st.caption(
            "Allocations add up to the city tax amount you entered. "
            "Rounding is reconciled to the nearest cent."
        )
    st.markdown(
        f"[Official budget presentation]({metadata['source_url']}) "
        f"- PDF page {metadata['source_pdf_page']}, FY2027 column."
    )
    st.info(
        "Illustrative allocation = your entered city tax amount multiplied by "
        "each category's share of the General Fund budget. This assumes those "
        "tax dollars follow the fund's overall spending mix; it is not an "
        "exact trace of your payments. Other revenues also support this fund."
    )
    with st.expander("View the underlying city budget"):
        st.metric("General Fund budget", f"${metadata['published_total_usd']:,.0f}")
        st.dataframe(spending, hide_index=True, use_container_width=True)
    with st.expander("About this city dataset"):
        for limitation in metadata["limitations"]:
            st.write(f"- {limitation}")

# Display the app introduction and development status.
st.title("Your Tax Dollar")
st.write(
    "See an illustrative dollar-by-dollar breakdown of the public services "
    "your taxes support, from the largest allocation to the smallest."
)
st.info(
    "Draper's official city budget is connected. Tax calculations, "
    "other government budgets, and Gemini explanations are still in development."
)

# Use plain-text separators to avoid corrupted display characters.
st.caption(f"Pilot location: {CITY} | {COUNTY} | {STATE}")
st.caption(
    "This pilot shows Draper's budget for every ZIP entered. "
    "ZIP codes are not yet matched to city or county boundaries."
)

# Collect inputs together; process them only when the user submits.
with st.form("tax_inputs"):
    salary = st.number_input(
        "Annual gross salary ($)",
        min_value=0,
        value=60000,
        step=1000,
        help="Your annual wages before taxes and deductions.",
    )

    # Keep ZIP codes as text to preserve any leading zeros.
    zip_code = st.text_input(
        "Residential ZIP code",
        max_chars=5,
        placeholder="Enter five digits",
    )

    st.caption(
        "Planned estimate: single filer, standard deduction, "
        "wage income only, no dependents or additional credits."
    )

    # Local property taxes cannot be derived from annual salary.
    annual_city_tax = st.number_input(
        "Annual property tax paid to Draper City ($), optional",
        min_value=0.0,
        value=None,
        step=50.0,
        format="%.2f",
        help=(
            "Enter only the Draper City general operating tax line from your "
            "property tax bill. Exclude county, school, and special district "
            "amounts. Leave blank if unknown."
        ),
    )
    st.caption(
        "City dollar allocations use this entered amount, not salary. "
        "For a demonstration, you may enter 1000 as an example contribution."
    )

    submitted = st.form_submit_button("Explore my tax picture")

# Validate ZIP format before storing the submitted inputs.
if submitted:
    if not re.fullmatch(r"[0-9]{5}", zip_code.strip()):
        # Clear old results so they do not appear under a new error.
        st.session_state.pop("profile", None)
        st.error("Please enter a five-digit ZIP code.")
    else:
        st.session_state["profile"] = {
            "salary": salary,
            "zip_code": zip_code.strip(),
            "annual_city_tax": annual_city_tax,
        }

# Keep valid results available during Streamlit page reruns.
profile = st.session_state.get("profile")

if profile:
    # Show the submitted inputs used for the displayed results.
    st.subheader("Your tax picture")
    st.write(
        f"Annual salary: **${profile['salary']:,.0f}** | "
        f"ZIP code: **{profile['zip_code']}**"
    )
    st.caption(
        "ZIP format checked only. The City tab shows the Draper pilot budget; "
        "your ZIP has not been verified as a Draper address."
    )

    # Reserve space for calculated taxes without inventing estimates.
    federal, state = st.columns(2)
    federal.metric("Estimated federal income tax", "Not calculated")
    state.metric("Estimated state income tax", "Not calculated")
    st.caption("Federal and state calculators are not implemented; these are not loading indicators.")

    # Create one spending tab for each government level.
    st.subheader("Where your tax dollars could go")
    levels = ["Federal", "State", "County", "City"]
    tabs = st.tabs(levels)

    for level, tab in zip(levels, tabs):
        with tab:
            st.write(f"**{level} tax dollar breakdown**")
            if level == "City":
                show_city_budget(profile.get("annual_city_tax"))
            else:
                st.info(
                    "This breakdown is not implemented yet. Once the tax "
                    "amount and reviewed spending data are connected, "
                    "your dollar allocations will appear largest to smallest."
                )

            if level in ["County", "City"]:
                st.caption(
                    "Salary alone does not determine property "
                    "or sales taxes."
                )

    # Enable this after verified data and Gemini are connected.
    st.button(
        "Explain these budgets with Gemini",
        disabled=True,
        help="Available after verified budget data is connected.",
    )

# Keep source information and methodology accessible.
with st.expander("Sources and assumptions"):
    st.markdown(
        "City: [Draper FY2027 Final Budget Adoption]"
        "(https://www.utah.gov/pmn/files/1477201.pdf), PDF page 12. "
        "General Fund, August 18, 2026 snapshot; later amendments not included."
    )
    st.write(
        "Federal, state, and county sources and tax calculation rules "
        "are pending. The City tab allocates only the city tax amount "
        "you enter, using General Fund spending shares."
    )
    st.write(
        "Spending allocations will be illustrative estimates, "
        "not a trace of individual tax payments."
    )

# Explain how this initial shell handles submitted inputs.
st.caption(
    "Educational prototype. Inputs are held in this app "
    "session; this shell does not save them to a database or send "
    "them to an AI service."
)
