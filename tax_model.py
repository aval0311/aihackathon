"""Small tax and allocation model for a married Salt Lake City household."""
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING

TAX_YEAR = 2026
STANDARD_DEDUCTION = 32200  # Married filing jointly, both adults under 65.
MEDIAN_PERSONAL_EARNINGS = Decimal('62180')
MEDIAN_MARRIED_FAMILY_INCOME = Decimal('127972')
MEDIAN_HOME_VALUE = Decimal('539500')
# Ratios of citywide medians define a scenario, not an individual prediction.
HOUSEHOLD_INCOME_MULTIPLIER = MEDIAN_MARRIED_FAMILY_INCOME / MEDIAN_PERSONAL_EARNINGS
HOME_TO_HOUSEHOLD_INCOME_MULTIPLIER = MEDIAN_HOME_VALUE / MEDIAN_MARRIED_FAMILY_INCOME
LOCAL_HOME_VALUE_MULTIPLIER = MEDIAN_HOME_VALUE / MEDIAN_PERSONAL_EARNINGS
LOCAL_TAXABLE_HOME_SHARE = 0.55
CITY_PROPERTY_RATE = 0.002374  # Salt Lake City general operations levy only.
COUNTY_PROPERTY_RATE = 0.001349  # Sum of approved countywide levy components.


def money(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def estimate_taxes(salary):
    """Individual salary -> modeled joint income; one qualifying child under 17."""
    salary = Decimal(str(salary))
    if not salary.is_finite() or not 0 <= salary <= 10000000:
        raise ValueError('Salary must be between zero and 10 million dollars.')
    household_income = Decimal(str(money(salary * HOUSEHOLD_INCOME_MULTIPLIER)))
    taxable_income = max(0, household_income - STANDARD_DEDUCTION)
    brackets = [(24800, Decimal('.10')), (100800, Decimal('.12')), (211400, Decimal('.22')),
                (403550, Decimal('.24')), (512450, Decimal('.32')), (768700, Decimal('.35')),
                (Decimal('Infinity'), Decimal('.37'))]
    federal, lower = 0, 0
    for upper, rate in brackets:
        federal += max(0, min(taxable_income, upper) - lower) * rate
        lower = upper
        if taxable_income <= upper:
            break
    # Nonrefundable child credit; refundable ACTC and EITC are not modeled.
    excess_income = max(Decimal('0'), household_income - 400000)
    phaseout_steps = (excess_income / 1000).quantize(Decimal('1'), rounding=ROUND_CEILING)
    available_child_credit = max(0, 2200 - 50 * phaseout_steps)
    applied_child_credit = min(federal, available_child_credit)
    federal = max(0, federal - applied_child_credit)
    # Utah includes one qualifying dependent in the taxpayer tax-credit base.
    utah_credit = max(0, Decimal('.06') * (STANDARD_DEDUCTION + 2167)
                      - Decimal('.013') * max(0, household_income - 37392))
    utah = max(0, household_income * Decimal('.0445') - utah_credit)
    assumed_home_value = Decimal(str(money(household_income * HOME_TO_HOUSEHOLD_INCOME_MULTIPLIER)))
    taxable_home_value = assumed_home_value * Decimal(str(LOCAL_TAXABLE_HOME_SHARE))
    return {
        'Federal': money(federal),
        'State': money(utah),
        'County': money(taxable_home_value * Decimal(str(COUNTY_PROPERTY_RATE))),
        'City': money(taxable_home_value * Decimal(str(CITY_PROPERTY_RATE))),
        'assumed_home_value': money(assumed_home_value),
        'household_income': money(household_income),
        'federal_child_credit': money(applied_child_credit),
        'utah_taxpayer_credit': money(min(household_income * Decimal('.0445'), utah_credit)),
    }


def allocate_tax_dollars(rows, annual_tax):
    """Return ranked allocations that reconcile exactly to the nearest cent."""
    amount = Decimal(str(annual_tax))
    if not amount.is_finite() or amount < 0:
        raise ValueError('Tax amount must be nonnegative and finite.')
    weights = [int(row['weight']) for row in rows]
    if not weights or any(value < 0 for value in weights) or sum(weights) <= 0:
        raise ValueError('Spending weights must be nonnegative with a positive total.')
    total = sum(weights)
    cents = int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    parts = [divmod(cents * weight, total) for weight in weights]
    allocations = [part[0] for part in parts]
    order = sorted(range(len(parts)), key=lambda index: parts[index][1], reverse=True)
    for index in order[:cents - sum(allocations)]:
        allocations[index] += 1
    result = [
        {'Category': row['category'], 'Your allocation (USD)': allocated / 100,
         'Share (%)': weight / total * 100}
        for row, allocated, weight in zip(rows, allocations, weights)
    ]
    return sorted(result, key=lambda row: (row['Your allocation (USD)'], row['Share (%)']), reverse=True)
