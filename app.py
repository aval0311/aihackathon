# Create the Streamlit application file.
import csv
import json
import re
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


def show_city_budget():
    """Display city spending without inferring personal taxes from salary."""
    try:
        spending, metadata = load_city_budget()
    except (OSError, ValueError, KeyError, TypeError):
        st.error("City budget data could not be loaded or verified.")
        return

    st.subheader("Draper General Fund")
    st.caption(
        f"FY {metadata['fiscal_year']} | August 2026 adoption snapshot | "
        "Budgeted amounts, including transfers"
    )
    st.metric("General Fund budget", f"${metadata['published_total_usd']:,.0f}")
    st.bar_chart(
        spending,
        x="Category",
        y="Budget (USD)",
        horizontal=True,
        height=480,
    )
    st.dataframe(
        spending,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Budget (USD)": st.column_config.NumberColumn(format="$%d"),
            "Share (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )
    st.markdown(
        f"[Official budget presentation]({metadata['source_url']}) "
        f"- PDF page {metadata['source_pdf_page']}, FY2027 column."
    )
    st.info(
        "These percentages show how Draper's General Fund budget is allocated. "
        "They do not estimate your personal city taxes and do not change "
        "with your salary or ZIP code."
    )
    with st.expander("About this city dataset"):
        for limitation in metadata["limitations"]:
            st.write(f"- {limitation}")

# Display the app introduction and development status.
st.title("Your Tax Dollar")
st.write(
    "Understand your estimated taxes and the public services "
    "government budgets support."
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
    federal.metric("Estimated federal income tax", "Pending")
    state.metric("Estimated state income tax", "Pending")

    # Create one spending tab for each government level.
    st.subheader("Explore public spending")
    levels = ["Federal", "State", "County", "City"]
    tabs = st.tabs(levels)

    for level, tab in zip(levels, tabs):
        with tab:
            st.write(f"**{level} spending breakdown**")
            if level == "City":
                show_city_budget()
            else:
                st.info(
                    "Awaiting reviewed budget data. Categories, charts, "
                    "fiscal year, and source links will appear here."
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
        "are pending. No personal tax estimate is calculated yet."
    )
    st.write(
        "Spending allocations will be illustrative estimates, "
        "not a trace of individual tax payments."
    )

# Explain how this initial shell handles submitted inputs.
st.caption(
    "Educational prototype. Salary and ZIP are held in this app "
    "session; this shell does not save them to a database or send "
    "them to an AI service."
)
