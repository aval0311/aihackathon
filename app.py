# Create the Streamlit application file.
import re
import streamlit as st

# Configure the page; use the default icon to avoid encoding issues.
st.set_page_config(
    page_title="Your Tax Dollar",
    layout="centered",
)

# Update these values when the pilot location is confirmed.
CITY = "City to be confirmed"
COUNTY = "County to be confirmed"
STATE = "State to be confirmed"

# Display the app introduction and development status.
st.title("Your Tax Dollar")
st.write(
    "Understand your estimated taxes and the public services "
    "government budgets support."
)
st.info(
    "Prototype in development. Tax calculations and verified "
    "budget datasets are not connected yet."
)

# Use plain-text separators to avoid corrupted display characters.
st.caption(f"Pilot location: {CITY} | {COUNTY} | {STATE}")

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
        "ZIP format checked. Supported location and jurisdiction "
        "validation will be added once the pilot city is confirmed."
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
    st.write(
        "Official source links, tax year, budget fiscal years, "
        "and calculation assumptions will be listed here."
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
