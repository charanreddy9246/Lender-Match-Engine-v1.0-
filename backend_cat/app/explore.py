"""A second, exploratory way to query the same lender data domain.py's
match_lenders uses — built for a filter-sidebar testing UI (checkboxes per
category; checking several boxes in one category is "any of these", picking
across categories is "all of these"), not for a real borrower application.
That's why match_lenders (which requires a full profile: CIBIL, loan amount,
one employment type...) isn't reused here — this dataset doesn't have that
numeric data yet, and this UI is explicitly about browsing what *is* loaded
so far (see app/load_client_property_data.py).

Doesn't reuse domain.py's _rule_satisfied either, because the comparison
shape is reversed: that function checks one borrower answer against a bank's
accepted set. Here it's a set of *selected filter values* against a bank's
accepted set — "does this bank accept any of what I picked" — so this module
reads eligibility_rules' "in"/"==" values directly instead.
"""

from dataclasses import dataclass

from app.domain import HomeLoanProduct

# Order controls both the sidebar's section order and how facet counts are
# computed. Keys match the attribute keys app/load_client_property_data.py
# writes into eligibility_rules.
FILTERABLE_CATEGORIES = [
    "employment_type",
    "property_type",
    "property_usage",
    "property_stage",
    "property_location",
]

CATEGORY_LABELS = {
    "employment_type": "Employment / Income Type",
    "property_type": "Property Type",
    "property_usage": "Property Usage",
    "property_stage": "Property Stage",
    "property_location": "Property Location",
}

# The full, canonical set of possible values per category, in the order the
# client's workbook presents them — NOT just whatever happens to appear in
# the loaded data. Some of these (e.g. every Industrial option) currently
# have zero banks that accept them — real banks in this file only finance
# residential property under "Home Loan" — but the category still needs to
# show up in the sidebar (with a 0) so it's clear that's a real "nobody
# accepts this yet" answer, not a category we forgot to wire up.
CATEGORY_VALUES: dict[str, list[tuple[str, str]]] = {
    "employment_type": [
        ("salaried", "Salaried"),
        ("self_employed", "Self-Employed"),
        ("pensioner", "Pensioner"),
        ("cash_income", "Cash Income"),
        ("nri", "NRI"),
    ],
    "property_type": [
        ("residential_vacant_land", "Residential — Vacant Land"),
        ("residential_apartment", "Residential — Apartment"),
        ("residential_independent_building", "Residential — Independent Building"),
        ("residential_semi_independent_uds", "Residential — Semi-Independent (UDS)"),
        ("commercial_farm_land", "Commercial — Farm Land"),
        ("commercial_vacant_land", "Commercial — Vacant Land"),
        ("commercial_independent_building", "Commercial — Independent Building"),
        ("commercial_semi_independent_uds", "Commercial — Semi-Independent (UDS)"),
        ("commercial_temporary_structure", "Commercial — Temporary Structure"),
        ("industrial_vacant_land", "Industrial — Vacant Land"),
        ("industrial_warehouse", "Industrial — Warehouse"),
        ("res_cum_comm_independent_building", "Residential cum Commercial — Independent Building"),
        ("res_cum_comm_building", "Residential cum Commercial — Building"),
        ("res_cum_comm_multi_unit", "Residential cum Commercial — Multi-Unit"),
    ],
    "property_usage": [
        ("self_occupied", "Self-Occupied"),
        ("let_out", "Let-Out"),
        ("lease", "Lease"),
    ],
    "property_stage": [
        ("new_purchase", "New Purchase"),
        ("resale", "Resale"),
        ("under_construction", "Under Construction"),
        ("take_over", "Take Over"),
    ],
    "property_location": [
        ("standard_urban", "Standard Urban"),
        ("peri_urban", "Peri-Urban"),
        ("rural", "Rural"),
    ],
}

VALUE_LABELS = {value: label for values in CATEGORY_VALUES.values() for value, label in values}


def label_for(value: str) -> str:
    return VALUE_LABELS.get(value, value)


@dataclass(frozen=True)
class FacetOption:
    value: str
    label: str
    count: int


def _rule_values(product: HomeLoanProduct, attribute_key: str) -> set[str]:
    for rule in product.rules:
        if rule.attribute_key == attribute_key and rule.operator in ("in", "=="):
            return {v.strip() for v in rule.value.split(",") if v.strip()}
    return set()


def matches(product: HomeLoanProduct, filters: dict[str, list[str]]) -> bool:
    """A product matches if, for every category the user picked at least one
    value in, the product's accepted set overlaps with what was picked.
    Categories with nothing picked don't filter anything out."""
    for category in FILTERABLE_CATEGORIES:
        selected = filters.get(category) or []
        if not selected:
            continue
        if not _rule_values(product, category) & set(selected):
            return False
    return True


def filter_products(products: list[HomeLoanProduct], filters: dict[str, list[str]]) -> list[HomeLoanProduct]:
    return [p for p in products if matches(p, filters)]


def facet_counts(
    products: list[HomeLoanProduct], filters: dict[str, list[str]]
) -> dict[str, list[FacetOption]]:
    """For each category, how many currently-visible-if-this-were-also-picked
    products each of its possible values would leave — computed against
    products filtered by every *other* category's current selection, so
    ticking one box doesn't collapse its own siblings' counts (matches how
    the Accenture reference site's sidebar behaves).

    Always returns every value in CATEGORY_VALUES, even ones sitting at 0 —
    a value that's always 0 is a real, meaningful answer ("no bank accepts
    this yet"), not something to hide as if it didn't exist as an option.
    """
    result: dict[str, list[FacetOption]] = {}
    for category in FILTERABLE_CATEGORIES:
        other_filters = {k: v for k, v in filters.items() if k != category}
        base = [p for p in products if matches(p, other_filters)]
        counts: dict[str, int] = {value: 0 for value, _ in CATEGORY_VALUES[category]}
        for product in base:
            for value in _rule_values(product, category):
                if value in counts:
                    counts[value] += 1
        result[category] = [
            FacetOption(value=value, label=label, count=counts[value]) for value, label in CATEGORY_VALUES[category]
        ]
    return result
