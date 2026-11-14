"""Small, deterministic tax and allocation model for the Draper hackathon pilot."""
from decimal import Decimal, ROUND_HALF_UP

TAX_YEAR = 2026
STANDARD_DEDUCTION = 16100
LOCAL_HOME_VALUE_MULTIPLIER = 3  # Project scenario assumption, not observed data.
LOCAL_TAXABLE_HOME_SHARE = 0.55
CITY_PROPERTY_RATE = 0.001128
COUNTY_PROPERTY_RATE = 0.001509


def money(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def estimate_taxes(salary):
    """Single wage earner; local amounts are hypothetical homeowner scenarios."""
    salary = Decimal(str(salary))
    if not salary.is_finite() or not 0 <= salary <= 10000000:
        raise ValueError('Salary must be between zero and 10 million dollars.')
    taxable_income = max(0, salary - STANDARD_DEDUCTION)
    brackets = [(12400, Decimal('.10')), (50400, Decimal('.12')), (105700, Decimal('.22')),
                (201775, Decimal('.24')), (256225, Decimal('.32')), (640600, Decimal('.35')),
                (Decimal('Infinity'), Decimal('.37'))]
    federal, lower = 0, 0
    for upper, rate in brackets:
        federal += max(0, min(taxable_income, upper) - lower) * rate
        lower = upper
        if taxable_income <= upper:
            break
    # Utah taxes assumed state taxable income before its taxpayer tax credit.
    utah_credit = max(0, Decimal('.06') * STANDARD_DEDUCTION - Decimal('.013') * max(0, salary - 18696))
    utah = max(0, salary * Decimal('.0445') - utah_credit)
    assumed_home_value = salary * LOCAL_HOME_VALUE_MULTIPLIER
    taxable_home_value = assumed_home_value * Decimal(str(LOCAL_TAXABLE_HOME_SHARE))
    return {
        'Federal': money(federal),
        'State': money(utah),
        'County': money(taxable_home_value * Decimal(str(COUNTY_PROPERTY_RATE))),
        'City': money(taxable_home_value * Decimal(str(CITY_PROPERTY_RATE))),
        'assumed_home_value': money(assumed_home_value),
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
