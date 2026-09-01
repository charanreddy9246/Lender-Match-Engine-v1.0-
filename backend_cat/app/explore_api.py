"""The filter-sidebar testing endpoint — browses whatever is currently
loaded in the database via checkbox-style category filters, instead of
requiring a full borrower profile like /api/v1/lenders/match does. See
app/explore.py for the matching/faceting logic."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain import (
    HomeLoanProduct,
    calculate_customer_foir_pct,
    calculate_final_tenure_years,
    calculate_max_emi,
    calculate_max_loan_amount,
    get_bank_interest_rate_pct,
    get_bank_interest_rate_upper_pct,
    get_fact,
)
from app.explore import FILTERABLE_CATEGORIES, facet_counts, filter_products
from app.explore_schemas import ExploreFiltersIn, ExploreProductOut, ExploreResponseOut, FacetOptionOut, LiveRateOut
from app.repository import LenderRepository, SqlLenderRepository

explore_router = APIRouter(prefix="/api/v1/explore")


def get_lender_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> LenderRepository:
    return SqlLenderRepository(db)


def _rule_value_list(product: HomeLoanProduct, attribute_key: str) -> list[str]:
    for rule in product.rules:
        if rule.attribute_key == attribute_key and rule.operator == "in":
            return [v.strip() for v in rule.value.split(",") if v.strip()]
    return []


def _rule_single_value(product: HomeLoanProduct, attribute_key: str) -> str:
    for rule in product.rules:
        if rule.attribute_key == attribute_key and rule.operator == "==":
            return rule.value
    return ""


def _to_out(product: HomeLoanProduct, filters: ExploreFiltersIn) -> ExploreProductOut:
    bank_foir_raw = get_fact(product, "foir_pct")
    bank_foir_pct = float(bank_foir_raw) if bank_foir_raw is not None else None
    bank_max_tenure_raw = get_fact(product, "max_tenure_years")
    bank_max_tenure_years = float(bank_max_tenure_raw) if bank_max_tenure_raw is not None else None
    interest_rate_pct, interest_rate_is_estimated = get_bank_interest_rate_pct(product)
    interest_rate_upper_pct = get_bank_interest_rate_upper_pct(product)

    customer_foir_pct: float | None = None
    foir_pass: bool | None = None
    max_emi: float | None = None
    if filters.monthly_income is not None:
        total_obligations = sum(filters.obligations)
        customer_foir_pct = calculate_customer_foir_pct(filters.monthly_income, total_obligations)
        if bank_foir_pct is not None:
            foir_pass = customer_foir_pct <= bank_foir_pct
            max_emi = calculate_max_emi(bank_foir_pct, filters.monthly_income, total_obligations)

    final_tenure_years: float | None = None
    if filters.age is not None and bank_max_tenure_years is not None:
        final_tenure_years = calculate_final_tenure_years(filters.age, bank_max_tenure_years)

    # Needs both a Max EMI and a final tenure — only computable once the
    # customer has given income/obligations *and* age.
    max_loan_amount: float | None = None
    if max_emi is not None and final_tenure_years is not None:
        max_loan_amount = calculate_max_loan_amount(max_emi, final_tenure_years, interest_rate_pct)

    return ExploreProductOut(
        bank_name=product.bank_name,
        product_name=product.product_name,
        employment_type=_rule_single_value(product, "employment_type"),
        property_type=_rule_value_list(product, "property_type"),
        property_usage=_rule_value_list(product, "property_usage"),
        property_stage=_rule_value_list(product, "property_stage"),
        property_location=_rule_value_list(product, "property_location"),
        bank_foir_pct=bank_foir_pct,
        customer_foir_pct=customer_foir_pct,
        foir_pass=foir_pass,
        max_emi=max_emi,
        bank_max_tenure_years=bank_max_tenure_years,
        final_tenure_years=final_tenure_years,
        max_loan_amount=max_loan_amount,
        interest_rate_pct=interest_rate_pct,
        interest_rate_is_estimated=interest_rate_is_estimated,
        interest_rate_upper_pct=interest_rate_upper_pct,
    )


@explore_router.get("/live-rates", response_model=list[LiveRateOut], tags=["explore"])
async def live_rates(repository: Annotated[LenderRepository, Depends(get_lender_repository)]) -> list[LiveRateOut]:
    """Powers the scrolling rate ticker in the UI — every bank whose rate
    was actually confirmed against Ambak (interest_rate_is_estimated is
    false), one entry per bank, lowest rate first. Banks we couldn't verify
    (see scrape_ambak_rates.py's UNMATCHABLE_BANKS) are deliberately left
    out — the ticker is meant to show live-verified numbers, not guesses.
    """
    products = await repository.list_products()
    by_bank: dict[str, float] = {}
    for product in products:
        rate, is_estimated = get_bank_interest_rate_pct(product)
        if not is_estimated:
            by_bank[product.bank_name] = rate

    return sorted(
        (LiveRateOut(bank_name=name, rate_pct=rate) for name, rate in by_bank.items()),
        key=lambda r: r.rate_pct,
    )


@explore_router.post("/banks", response_model=ExploreResponseOut, tags=["explore"])
async def explore_banks(
    filters: ExploreFiltersIn,
    repository: Annotated[LenderRepository, Depends(get_lender_repository)],
) -> ExploreResponseOut:
    products = await repository.list_products()
    filter_map = {category: getattr(filters, category) for category in FILTERABLE_CATEGORIES}

    matched = filter_products(products, filter_map)
    facets = facet_counts(products, filter_map)

    return ExploreResponseOut(
        results=[_to_out(p, filters) for p in matched],
        total=len(matched),
        facets={
            category: [FacetOptionOut(value=o.value, label=o.label, count=o.count) for o in options]
            for category, options in facets.items()
        },
    )
