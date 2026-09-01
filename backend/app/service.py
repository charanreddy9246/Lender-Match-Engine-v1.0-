"""Glue: converts between the API's types and the matching engine's types.

The API still asks a fixed set of named questions (see schemas.py) — that part of
the form doesn't need to be dynamic today. What changes here is turning those fixed
answers into the generic {attribute_key: value} shape the matching engine and
database now speak, using the same keys the attribute catalog and eligibility
rules use: "cibil_score", "net_monthly_salary", "property_type" (the chosen value,
checked against a product's rule with the "in" operator), and "document_<value>"
for each document the borrower has. Adding a new question to the form later means
adding one more line here — nothing in app.domain or the database needs to change.
"""

from app.domain import BorrowerProfile, filter_eligible, find_top_products, get_fact
from app.repository import LenderRepository
from app.schemas import BorrowerProfileIn, MatchMeta, MatchResponse, ProductMatchOut


def _to_answers(profile_in: BorrowerProfileIn) -> dict[str, str]:
    answers = {
        "cibil_score": str(profile_in.cibil_score),
        "employment_type": profile_in.employment_type.value,
        "property_type": profile_in.property_type.value,
        "has_co_borrower": "true" if profile_in.has_co_borrower else "false",
    }
    # Only one of these is ever relevant for a given employment_type — see
    # BorrowerProfileIn's docstring — so only the one actually submitted becomes
    # an answer. A product's rule for the other three simply never matches this
    # profile, since filter_eligible treats a missing answer as "not satisfied"
    # and only one employment_type's product carries each rule anyway.
    income_fields = {
        "net_monthly_salary": profile_in.net_monthly_salary,
        "annual_turnover": profile_in.annual_turnover,
        "annual_gross_receipts": profile_in.annual_gross_receipts,
        "monthly_pension": profile_in.monthly_pension,
    }
    for key, value in income_fields.items():
        if value is not None:
            answers[key] = str(value)
    for document in profile_in.documents_available:
        answers[f"document_{document.value}"] = "true"
    return answers


async def match_lenders(profile_in: BorrowerProfileIn, repository: LenderRepository) -> MatchResponse:
    profile = BorrowerProfile(
        employment_type=profile_in.employment_type.value,
        loan_amount_required=profile_in.loan_amount_required,
        answers=_to_answers(profile_in),
    )

    products = await repository.list_products()
    attributes_by_key = await repository.get_attributes()
    eligible_count = len(filter_eligible(profile, products, attributes_by_key))
    top_matches = find_top_products(profile, products, attributes_by_key)

    def _out(sp) -> ProductMatchOut:
        interest_rate_raw = get_fact(sp.product, "interest_rate_pct")
        processing_fee_raw = get_fact(sp.product, "processing_fee_pct")
        max_amount_raw = get_fact(sp.product, "max_loan_amount")
        recent_borrowers_raw = get_fact(sp.product, "recent_borrowers_processed")
        return ProductMatchOut(
            bank_name=sp.product.bank_name,
            product_name=sp.product.product_name,
            interest_rate_pct=float(interest_rate_raw) if interest_rate_raw is not None else None,
            interest_rate_range=get_fact(sp.product, "interest_rate_range"),
            processing_fee_pct=float(processing_fee_raw) if processing_fee_raw is not None else None,
            processing_fee=get_fact(sp.product, "processing_fee"),
            lender_type=get_fact(sp.product, "lender_type"),
            max_eligible_amount=int(max_amount_raw) if max_amount_raw is not None else None,
            approval_likelihood_tier=get_fact(sp.product, "approval_likelihood_tier"),
            recent_borrowers_processed=int(float(recent_borrowers_raw)) if recent_borrowers_raw is not None else None,
            relationship_note=get_fact(sp.product, "relationship_note"),
            score=round(sp.score, 4),
            reasons=sp.reasons,
        )

    lenders = [_out(sp) for sp in top_matches]

    return MatchResponse(
        lenders=lenders,
        meta=MatchMeta(products_considered=len(products), products_eligible=eligible_count),
    )
