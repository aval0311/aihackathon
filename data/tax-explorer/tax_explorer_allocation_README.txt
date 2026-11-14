TAX EXPLORER ALLOCATION NOTES — prototype 2026-11-14

FILES:
- tax_explorer_prototype_v3_reconciled.csv: published hierarchy, residuals, accounting sources, program metrics.
- tax_explorer_tax_dollar_weights_v1.csv: exactly normalized tax-dollar allocations for five tax pools.

WHAT THE APP SHOWS:
1) Household estimates taxes by taxing jurisdiction (federal, Utah state, city, county,
   school district; and other taxing districts if modeled separately).
2) Allocate each dollar paid to each jurisdiction to its corresponding pool. DO NOT add
   an entire district spending budget to the state's spending budget. These are
   overlapping funding/service-delivery views, not mutually exclusive expenditure totals.
3) Sum household-allocated dollar amounts by citizen_category across tax pools.
4) For selective deep dives, show deeper categories only when available; remaining
   dollar amounts flow to explicit 'Other...' residual nodes.

DEFAULT POOLS:
- Federal: positive program outlays; negative offsetting receipts remain in the
  accounting dataset only; federal interest is still included in allocation.
- Utah: all-source major budget areas are an *approximation* of state tax-supported spending.
- County: all-funds budget is a *rough* approximation, including some fees, visitor taxes,
  internal charges and federal grants, not a consolidated county-tax-funded budget.
- City: General Fund department budget, not all of city enterprise spending.
- School district: General Fund functions for property tax dollars attributable to schools;
  not a complete estimate of school district services or all financing funds.

KEY FINANCING DISTINCTION:
- Do not treat corporate taxes, tourism fees, and federal borrowing as a separately
  estimated tax that an individual's salary determines. The incidence of corporate
  taxes is distributed among owners, workers, customers (including out-of-state
  and foreign households). Avoid an unsupported numerical attribution.
- Show direct household taxes by default. Optionally show a separately labeled
  *economic incidence scenario* with explicit assumptions rather than adding
  unverified amounts to the tax estimate.
- Bond principal repayments should be labeled financing, not added to project capital
  costs in a separate 'new spending' roll-up.
- Per capita/household government spending is NOT taxes paid or benefits received.

COMPUTING A HOUSEHOLD DOLLAR ESTIMATE:
  household_spend_in_category = SUM(taxes_allocated_to_pool * normalized_share)
  where normalized_share comes from tax_explorer_tax_dollar_weights_v1.csv.
  For display of deep branches, use a parent child spending split as a conditional
  weight and multiply by the amount already allocated to that parent. Avoid
  summing parent and child dollars.

PAYROLL AND PROPERTY MODEL INPUTS:
- For married two-earner households, calculate income taxes under married-filing-jointly
  brackets with standard deduction, credits, and state deductions; calculate Social
  Security wage base cap separately for each earner; Medicare payroll appropriately.
- Sales tax requires an estimate of taxable *spending*, not income; ZIP alone is an
  approximation to local rates.
- Apply Utah's primary-residence assessment exemption where eligible; actual tax
  district depends on property parcel, not a unique ZIP mapping.

LIMITATION: Source fiscal years differ. These CSVs are a hackathon prototype, not
an audited intergovernmental consolidated accounts dataset. Read the caveat column.