TAX EXPLORER — SINGLE CSV INTEGRATION GUIDE (2026-11-14)
===========================================================
CANONICAL FILE (only spending CSV to use):
data/tax-explorer/tax_explorer_prototype_v3_reconciled.csv

The previous tax_explorer_tax_dollar_weights_v1.csv has been consolidated into this
hierarchy and is no longer needed. The original official spending classifications
remain traceable in Git history and individual rows' source URLs.

HOW TO USE THE CSV
------------------
1. Tax estimator returns a household's estimated taxes separately for each relevant
   pool. For Salt Lake City the current identifiers are:
     federal_positive_programs
     state_all_sources_proxy
     county_all_funds_proxy
     city_general_fund
     school_general_fund
2. Filter allocation_status == "spending" AND depth == 1 for the complete
   first level of each pool. Each pool's depth-1 normalized_share sums to 1.0.
   Root rows are depth=0 and have normalized_share=1.0; do NOT add roots or
   multi-depth records into the same total.
3. Your personal amount for any node = estimated household taxes assigned to
   that node's tax_allocation_pool * normalized_share.
4. Build expandable drilldowns using node_id / parent_id. Every group of spending
   children sums to its parent. share_of_parent is the conditional share; for
   example, when clicking Police, its Personnel row has share_of_parent ~= 0.9188.
   normalized_share on that same Personnel row is already the FULL pool share,
   so do NOT multiply it by the parent share again.
5. Group depth-1 personal allocations by citizen_category to create a combined
   purpose-first view. Keep jurisdiction/pool IDs to prevent cross-government
   double counting. Optionally show deeper rows while hiding their parents.
6. To reconcile rounded household dollars exactly, calculate in cents and
   distribute the rounding remainder among siblings (largest remainder method).
7. allocation_status == "metric" rows (five in this file) carry FTE or lane-mile
   values rather than spending. Their normalized dollar shares are intentionally
   blank and must never be included in money totals.

COLUMN GUIDE
------------
node_id, parent_id        Hierarchy keys; parents always exist in this file.
depth                    0=root, 1=top-level, 2+=selective drilldown.
level_1...level_5        Fully materialized citizen-friendly display path.
plain_english_name       Display label.
citizen_category         Purpose category for cross-government aggregation.
citizen_subcategory      More precise program label.
official_amount_usd      Published dollar figure for that spending line, if any.
attributed_spending_usd  MODEL amount after shared/financing overhead attribution.
normalized_share         ABSOLUTE fraction of this household's pool (0..1).
share_of_parent          CONDITIONAL fraction of its parent (0..1).
cents_per_tax_dollar     normalized_share * 100 (cents per one pool tax dollar).
tax_allocation_pool      One of five mutually distinct household tax pools.
allocation_method        direct_plus_prorated_shared_costs, official_within_parent,
                         normalized_known_components, direct_plus_school_debt, etc.
source_url, source_page  Published provenance.
metric_value, metric_unit  Non-financial context, where applicable.
notes                    Important source and modeling limitations.

ABSTRACT ACCOUNTING COSTS — ASSUMED ALLOCATION
-----------------------------------------------
CITY: $132,595,369 (~25.9% of City General Fund) of unassigned/shared costs
     was allocated in proportion to identifiable departmental spending.
COUNTY: $72,917,601 of Parks and Recreation was extracted from the county
        General Fund and allocated directly to Parks. The remaining General Fund
        and several county debt, fleet, benefits, facilities and shared costs
        (~$693,251,441; ~42.8% of this proxy pool) were allocated in proportion
        to identifiable services. This county distribution is PARTICULARLY ROUGH.
STATE: Executive Appropriations and General Government ($689m; ~2.2%)
       attributed proportionally across seven identified services.
FEDERAL: Net Interest and General Government (~$1.005T; ~14.0% of positive
         outlays) attributed proportionally to identifiable program functions.
         This does not imply those programs caused the historical debt.
SCHOOL: $612,976 of General Fund debt service attributed to school facilities.
        A separate school-capital/bond tax allocation is NOT yet modeled here.
For deeper branches where some source rows include offsets (Medicare premiums)
or accounting reconciliation items, positive published programs are scaled
proportionally to match the parent's net allocation. See allocation_method.

CRITICAL ACCURACY CAVEATS
-------------------------
- "attributed_spending_usd" is an illustrative allocation, NOT an official
  departmental expenditure. official_amount_usd preserves sourced values.
- City pool is the General Fund only, NOT airport/water/sewer enterprise funds.
- County pool is an all-funds approximation, potentially including fees,
  visitor taxes, internal services, and transfers. Distinct household
  county tax dollars are NOT the same as all county revenues.
- Utah pool includes federal financing and transfers; tax-funded shares are
  illustrative, NOT intergovernmentally consolidated.
- Federal pool uses POSITIVE outlay functions (not net outlays); historical
  interest is redistributed for display. Federal borrowing is financing
  context, not the user's personal income tax.
- School pool uses the School District General Fund. It excludes dedicated
  capital and bond funds and the district's separately funded ~ $13.65m child
  nutrition fund. General Fund school meal support is much smaller and must
  NOT be presented as total school-meal spending.
- Do NOT apply state education budgets and district budgets as additional
  tax bills for the same dollars. Assign household taxes to separate levy/
  government pools; the resulting education allocations are an illustration.
- County/City/School property-tax rates depend on the actual property taxing
  district, not ZIP alone. School operating/capital/bond levies must be
  classified separately when the estimator includes them.
- Annual budget periods differ; federal FY2025 outlays, local/state FY2026
  budgets. Not exact personal benefits or tax incidence.
- The model includes ONLY selected detailed drilldowns but FULL first-level
  classified spending for each selected tax pool. No fake precision.

The prototype application currently reads data/spending_snapshots.json. Your
interface partner should switch its loader to the canonical CSV above and
map tax-estimator amounts to tax_allocation_pool. No application code changed.
