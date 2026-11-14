# Your Tax Dollar

**Your money. Your community. See the connection.**

Your Tax Dollar is a public Streamlit prototype that helps Salt Lake City residents explore where their estimated tax dollars are allocated. Enter an **individual annual gross salary** and a **ZIP code** to see federal, state, county, and city spending illustrations, ranked from largest to smallest.

**[Open the live app](https://your-tax-dollar.streamlit.app/)** | **[Public repository](https://github.com/aval0311/aihackathon)**

## Try the demo

1. Enter a salary, such as **100,000**, and ZIP **84103**.
2. Select **Show where my tax dollars go**.
3. Choose Federal, State, County, or City.
4. Select **+** beside a broad category to see named subcategories. More **+** controls appear where deeper data is available.
5. Select **Change salary or ZIP** to return to the inputs.

The same link works in desktop and mobile browsers. No account is required.

## Why we built it

Public budgets are difficult to connect to everyday life. This project translates spending proportions into personal dollar amounts and lets residents explore services beneath the broad categories. Its value is a simple, two-input experience with visible assumptions, sources, and expandable detail.

These are **proportional spending illustrations**, not a record of where a person's actual payments went or a measure of the benefits they received.

## Demo profile and tax assumptions

> You are married, own a home in Salt Lake City, and have one child under 17.

To keep the interface simple, the model assumes married filing jointly, both adults under 65, one qualifying child with the required Social Security numbers, and no additional spouse income. It uses the entered individual salary directly; it does not multiply that salary to add spouse earnings.

- **Federal:** simplified 2026 income-tax brackets, a $32,200 joint standard deduction, and one nonrefundable child tax credit, including its modeled phaseout.
- **Utah:** a simplified 2026 income-tax estimate using the rate and taxpayer-credit rules documented in the app.
- **Home scenario:** individual salary multiplied by **$539,500 / $62,180 = approximately 8.67642**. This ratio of citywide medians supplies a hypothetical home value, not a prediction of the user's actual property value.
- **Local taxes:** 55% of that home value is treated as taxable. The city scenario uses a general-operations levy of **0.002374**; the county scenario uses countywide levy components totaling **0.001349**, excluding the separate library levy. Neither is a complete property-tax bill.
- **Location:** selected Salt Lake City ZIPs select the pilot. ZIP alone does not verify a city boundary, parcel, or property taxing district.

Supported ZIPs: `84101`, `84102`, `84103`, `84104`, `84105`, `84106`, `84108`, `84111`, `84112`, and `84116`.

Payroll taxes, sales taxes, school-district taxes, refundable credits, and several other tax adjustments are not modeled. Detailed tax-rule links are available under **Tax rules, assumptions, and sources** in the app.

## Data and allocation method

The app reads one canonical spending file:

[`data/tax-explorer/tax_explorer_prototype_v3_reconciled.csv`](data/tax-explorer/tax_explorer_prototype_v3_reconciled.csv)

| App tab | CSV allocation pool | Spending period |
| --- | --- | --- |
| Federal | `federal_positive_programs` | FY2025 |
| State | `state_all_sources_proxy` | FY2026 |
| County | `county_all_funds_proxy` | FY2026 |
| City | `city_general_fund` | FY2026 |

The CSV also contains school-district records. **The app excludes that pool and has no school-district tab.** The older `spending_snapshots.json` file is not used by the current app.

The loader validates identifiers, parent relationships, spending shares, and reconciliation within the four selected pools. It groups depth-one spending records by `citizen_category` to produce the broad view, then follows `node_id` and `parent_id` for drilldowns. Informational metrics such as staffing counts never enter money totals.

Personal dollars are apportioned among broad categories and then among their descendants. A largest-remainder method distributes rounding cents so broad categories sum to the displayed estimate and spending children sum to their parent. Parents and children are not added together as separate taxes.

The CSV preserves source URLs, page references, official amounts, attributed amounts, allocation methods, and notes. Attributed amounts include modeled cost redistribution and must not be presented as official department budgets. The [dataset guide](data/tax-explorer/tax_explorer_allocation_README.txt) explains its construction; this project README describes the current app behavior.

### Important dataset limitations

- Federal interest and general-government costs are redistributed across programs rather than displayed as separate categories. Positive spending functions are used as the allocation base.
- Utah uses an all-source spending proxy, including federal financing, rather than only uses of individual state income-tax revenue.
- The county proxy redistributes substantial General Fund and shared costs. It does **not separately identify public safety** and includes library and fee-funded services outside the modeled levy. Treat that panel as a broad illustration, not a faithful tracing of county property-tax payments. The supplied county source URL could not be verified during review.
- The city uses its General Fund and distributes shared/non-departmental costs across identified departments. Enterprise funds such as airport, water, and sewer are excluded.
- Funding sources, periods, and scopes differ. Intergovernmental transfers and internal transactions may be present; these are not consolidated government accounts. Do not add the underlying government budget totals together.
- Sources and extraction notes have not all been independently verified. Some deeper figures are proposed, approximate, or normalized to their parent, as recorded in the CSV.

## Run locally

Use a Python environment compatible with the Streamlit version installed from `requirements.txt`.

```bash
git clone https://github.com/aval0311/aihackathon.git
cd aihackathon
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Run from the repository directory so Streamlit picks up `.streamlit/config.toml`. No API key or database is needed. In Streamlit Community Cloud, select this repository and `app.py` as the entry point.

## Project files

| File | Purpose |
| --- | --- |
| [`app.py`](app.py) | Interface, input validation, navigation, charts, and expandable categories |
| [`tax_model.py`](tax_model.py) | Simplified tax estimates and cent-based apportionment |
| [`spending_data.py`](spending_data.py) | CSV validation, broad-category grouping, and hierarchical allocations |
| [`requirements.txt`](requirements.txt) | Streamlit dependency |
| [`.streamlit/config.toml`](.streamlit/config.toml) | Public demo theme |
| [`YourtTaxDollars_v1.ipynb`](YourtTaxDollars_v1.ipynb) | Colab development notebook with current app code |

The notebook does not embed every backend module or the CSV. Keep it alongside the repository files; the Python files are the deployed source of truth. Its download cell is intended for Google Colab.

## AI use and privacy

ChatGPT/Codex assisted with implementation, interface revisions, and validation during development. **The deployed prototype uses deterministic Python calculations and does not currently call Gemini or another AI model.** AI explanations are a possible future feature, not an implemented capability.

The application code keeps salary and ZIP in Streamlit session state. It does not explicitly write those inputs to a database or send them to an AI API. This describes the application code, not a guarantee about hosting-provider infrastructure or logging.

## Validation performed

- Valid salary/ZIP submission, comma formatting, validation feedback, and return navigation with restored inputs.
- Broad and nested cent reconciliation at salaries of $0, $60,000, $100,000, and $10,000,000.
- Rejection of corrupted hierarchy/shares, exclusion of metrics and school-district allocations, and named drilldown rendering.
- Signed-out access to the public app and repository.
- Chrome mobile emulation at **390 x 844** and **360 x 800**, covering readable charts, tab switching, nested disclosures, and input restoration. Physical iOS/Android device testing remains future work.

These were development checks, not a professional audit of tax calculations or every source figure. There is not yet a committed automated test suite.

## Hackathon submission and team

- **Project:** Your Tax Dollar
- **Repository owner:** [aval0311](https://github.com/aval0311)
- **Team name:** To be completed by the team
- **Selected track:** To be confirmed by the team
- **Contributor names and contact emails:** Complete in the submission form
- **Work areas:** application/calculation development and dataset sourcing/reconciliation; the team should confirm individual attribution

For a short demonstration: enter **100,000 / 84103**, show the four estimates, open **City**, and expand **Protection & Safety**, then **Police Department** to show the available detail. Close by explaining that amounts are illustrative and sources are visible.

## After the event

Priorities are to improve the county source and spending classification; align spending mixes with the taxes being estimated; preserve financing/shared-cost transparency; independently verify detailed sources; and add automated regression tests and physical-device checks. A later Gemini feature could explain reviewed data in plain language with citations while leaving numerical calculations deterministic.

## License

Project code and original documentation are available under the [MIT License](LICENSE). Government source documents, third-party datasets, and dependencies retain their respective terms; this license does not relicense third-party material.
