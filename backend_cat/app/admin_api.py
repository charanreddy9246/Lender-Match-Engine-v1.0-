"""Admin-only endpoints for managing lender data directly — add/update/delete
banks and their eligibility rules, add/update/delete relationship (bias) data.
Every route here requires a real, verified login (see app/auth.py) via the
router-level dependency below; nothing here is reachable without it, unlike
the borrower-facing match endpoint.

Translates between the admin's plain form fields (admin_schemas.py) and the
database's generic attribute/rule rows — the same translation
app/load_birbal_dataset.py already does for the Excel file, just triggered by
a button click instead of a script.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin_schemas import AdminBankSummary, AdminBiasIn, AdminBiasOut, AdminProductDetail, AdminProductOut
from app.auth import require_admin
from app.database import (
    AttributeModel,
    BankBiasFactModel,
    BankModel,
    EligibilityRuleModel,
    HomeLoanProductModel,
    get_db,
)

admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@admin_router.get("/me")
async def whoami(admin_email: Annotated[str, Depends(require_admin)]) -> dict[str, str]:
    """Lets the frontend check "am I actually logged in" without any side
    effects — just re-verifies the token and echoes back who it belongs to."""
    return {"email": admin_email}

# Which income attribute applies for each employment type — same mapping
# app/load_birbal_dataset.py uses (its INCOME_BY_EMPLOYMENT_TYPE), minus the
# Excel-column half, since the admin form doesn't read from Excel.
INCOME_ATTRIBUTE_BY_EMPLOYMENT_TYPE = {
    "salaried": "net_monthly_salary",
    "self_employed": "annual_turnover",
    "professional": "annual_gross_receipts",
    "pensioner": "monthly_pension",
}

_REQUIRED_ATTRIBUTE_KEYS = {
    "cibil_score",
    "employment_type",
    "property_type",
    "documents_any_of",
    "min_loan_amount",
    "max_loan_amount",
    "interest_rate_pct",
    "interest_rate_range",
    "processing_fee",
    "lender_type",
    "has_co_borrower",
    *INCOME_ATTRIBUTE_BY_EMPLOYMENT_TYPE.values(),
}


async def _get_attributes(session: AsyncSession) -> dict[str, AttributeModel]:
    rows = (await session.execute(select(AttributeModel))).scalars().all()
    attributes = {a.key: a for a in rows}
    missing = _REQUIRED_ATTRIBUTE_KEYS - attributes.keys()
    if missing:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Missing attribute catalog entries {sorted(missing)} — load the main lender "
            "dataset first (python -m app.load_birbal_dataset <xlsx>).",
        )
    return attributes


def _detail_to_rules(
    product_id: int, detail: AdminProductDetail, attributes: dict[str, AttributeModel]
) -> list[EligibilityRuleModel]:
    income_key = INCOME_ATTRIBUTE_BY_EMPLOYMENT_TYPE[detail.employment_type.value]
    rules = [
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["cibil_score"].id,
            operator="between",
            value=f"{detail.min_cibil},{detail.max_cibil}",
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["employment_type"].id,
            operator="==",
            value=detail.employment_type.value,
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes[income_key].id,
            operator=">=",
            value=str(detail.income_threshold),
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["property_type"].id,
            operator="in",
            value=",".join(d.value for d in detail.property_types_accepted),
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["documents_any_of"].id,
            operator="any_of",
            value=",".join(d.value for d in detail.documents_accepted),
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["min_loan_amount"].id,
            operator="fact",
            value=str(detail.min_loan_amount),
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["max_loan_amount"].id,
            operator="fact",
            value=str(detail.max_loan_amount),
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["interest_rate_pct"].id,
            operator="fact",
            value=str(detail.interest_rate_pct),
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["interest_rate_range"].id,
            operator="fact",
            value=detail.interest_rate_range,
        ),
        EligibilityRuleModel(
            product_id=product_id,
            attribute_id=attributes["processing_fee"].id,
            operator="fact",
            value=detail.processing_fee,
        ),
        EligibilityRuleModel(
            product_id=product_id, attribute_id=attributes["lender_type"].id, operator="fact", value=detail.lender_type
        ),
    ]
    # Only Pensioner products can carry this rule at all — see
    # app/load_birbal_dataset.py's identical carve-out.
    if detail.employment_type.value == "pensioner" and detail.co_borrower_required:
        rules.append(
            EligibilityRuleModel(
                product_id=product_id, attribute_id=attributes["has_co_borrower"].id, operator="required", value="true"
            )
        )
    return rules


def _rules_to_detail(bank_name: str, product: HomeLoanProductModel) -> AdminProductOut:
    by_key = {rule.attribute.key: rule for rule in product.rules}
    employment_type = by_key["employment_type"].value
    income_key = INCOME_ATTRIBUTE_BY_EMPLOYMENT_TYPE[employment_type]
    min_cibil_str, max_cibil_str = by_key["cibil_score"].value.split(",")
    return AdminProductOut(
        bank_name=bank_name,
        employment_type=employment_type,
        min_cibil=int(min_cibil_str),
        max_cibil=int(max_cibil_str),
        min_loan_amount=int(by_key["min_loan_amount"].value),
        max_loan_amount=int(by_key["max_loan_amount"].value),
        income_threshold=int(by_key[income_key].value),
        documents_accepted=by_key["documents_any_of"].value.split(","),
        property_types_accepted=by_key["property_type"].value.split(","),
        interest_rate_pct=float(by_key["interest_rate_pct"].value),
        interest_rate_range=by_key["interest_rate_range"].value if "interest_rate_range" in by_key else "",
        processing_fee=by_key["processing_fee"].value if "processing_fee" in by_key else "",
        lender_type=by_key["lender_type"].value if "lender_type" in by_key else "",
        co_borrower_required="has_co_borrower" in by_key,
    )


async def _get_bank_or_404(session: AsyncSession, bank_name: str) -> BankModel:
    bank = (
        await session.execute(
            select(BankModel)
            .options(selectinload(BankModel.products).selectinload(HomeLoanProductModel.rules).selectinload(EligibilityRuleModel.attribute))
            .where(BankModel.name == bank_name)
        )
    ).scalar_one_or_none()
    if bank is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No bank named {bank_name!r}.")
    return bank


def _find_product(bank: BankModel, employment_type: str) -> HomeLoanProductModel | None:
    for product in bank.products:
        by_key = {rule.attribute.key: rule.value for rule in product.rules}
        if by_key.get("employment_type") == employment_type:
            return product
    return None


# ---------------------------------------------------------------------------
# Banks
# ---------------------------------------------------------------------------


@admin_router.get("/banks", response_model=list[AdminBankSummary])
async def list_banks(session: Annotated[AsyncSession, Depends(get_db)]) -> list[AdminBankSummary]:
    banks = (
        await session.execute(
            select(BankModel).options(
                selectinload(BankModel.products).selectinload(HomeLoanProductModel.rules).selectinload(EligibilityRuleModel.attribute)
            )
        )
    ).scalars().all()
    return [
        AdminBankSummary(
            bank_name=bank.name,
            source=bank.source,
            employment_types=[
                rule.value
                for product in bank.products
                for rule in product.rules
                if rule.attribute.key == "employment_type"
            ],
        )
        for bank in banks
    ]


@admin_router.get("/banks/{bank_name}/products", response_model=list[AdminProductOut])
async def get_bank_products(
    bank_name: str, session: Annotated[AsyncSession, Depends(get_db)]
) -> list[AdminProductOut]:
    bank = await _get_bank_or_404(session, bank_name)
    return [_rules_to_detail(bank.name, product) for product in bank.products]


@admin_router.post("/banks/{bank_name}/products", response_model=AdminProductOut, status_code=status.HTTP_201_CREATED)
async def create_bank_product(
    bank_name: str, detail: AdminProductDetail, session: Annotated[AsyncSession, Depends(get_db)]
) -> AdminProductOut:
    attributes = await _get_attributes(session)

    bank = (await session.execute(select(BankModel).where(BankModel.name == bank_name))).scalar_one_or_none()
    if bank is None:
        # source="admin_manual" — a third tag alongside "excel_import" and
        # "manual_calibration" (see BankModel's docstring in database.py) so
        # bulk reloads of the Excel file never touch banks added here either.
        bank = BankModel(name=bank_name, source="admin_manual")
        session.add(bank)
        await session.flush()
    else:
        existing = await _get_bank_or_404(session, bank_name)
        if _find_product(existing, detail.employment_type.value) is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{bank_name} already has a {detail.employment_type.value} product — use the update endpoint instead.",
            )

    product = HomeLoanProductModel(
        bank_id=bank.id, product_name=f"Home Loan — {detail.employment_type.value.replace('_', ' ').title()}"
    )
    session.add(product)
    await session.flush()

    session.add_all(_detail_to_rules(product.id, detail, attributes))
    await session.commit()

    bank_fresh = await _get_bank_or_404(session, bank_name)
    return _rules_to_detail(bank_name, _find_product(bank_fresh, detail.employment_type.value))


@admin_router.put("/banks/{bank_name}/products/{employment_type}", response_model=AdminProductOut)
async def update_bank_product(
    bank_name: str,
    employment_type: str,
    detail: AdminProductDetail,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminProductOut:
    if detail.employment_type.value != employment_type:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "employment_type in the URL and body must match.")
    attributes = await _get_attributes(session)
    bank = await _get_bank_or_404(session, bank_name)
    product = _find_product(bank, employment_type)
    if product is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"{bank_name} has no {employment_type} product yet — use the create endpoint instead.",
        )

    # Replace-all-rules is simpler and less error-prone than diffing field by
    # field, and this table is small enough (≤11 rows) that it's cheap.
    await session.execute(delete(EligibilityRuleModel).where(EligibilityRuleModel.product_id == product.id))
    session.add_all(_detail_to_rules(product.id, detail, attributes))
    await session.commit()

    # The bulk delete() above is a Core statement — it doesn't touch this
    # session's already-loaded `bank`/`product` objects, so without this,
    # the re-fetch below would silently hand back the stale pre-update rules
    # instead of what was just written (SQLAlchemy's identity map doesn't
    # know those Python objects are now wrong).
    session.expire_all()

    bank_fresh = await _get_bank_or_404(session, bank_name)
    return _rules_to_detail(bank_name, _find_product(bank_fresh, employment_type))


@admin_router.delete("/banks/{bank_name}/products/{employment_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_product(
    bank_name: str, employment_type: str, session: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    bank = await _get_bank_or_404(session, bank_name)
    product = _find_product(bank, employment_type)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{bank_name} has no {employment_type} product.")
    await session.delete(product)
    await session.commit()


@admin_router.delete("/banks/{bank_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank(bank_name: str, session: Annotated[AsyncSession, Depends(get_db)]) -> None:
    bank = await _get_bank_or_404(session, bank_name)
    await session.delete(bank)
    await session.commit()


# ---------------------------------------------------------------------------
# Relationship / bias data
# ---------------------------------------------------------------------------


@admin_router.get("/bias", response_model=list[AdminBiasOut])
async def list_bias(session: Annotated[AsyncSession, Depends(get_db)]) -> list[AdminBiasOut]:
    rows = (await session.execute(select(BankBiasFactModel))).scalars().all()
    by_bank: dict[str, dict[str, str]] = {}
    for row in rows:
        by_bank.setdefault(row.bank_name, {})[row.metric_key] = row.value
    return [
        AdminBiasOut(
            bank_name=name,
            recent_borrowers_processed=int(facts.get("recent_borrowers_processed", 0)),
            relationship_note=facts.get("relationship_note", ""),
        )
        for name, facts in by_bank.items()
    ]


@admin_router.put("/bias/{bank_name}", response_model=AdminBiasOut)
async def upsert_bias(
    bank_name: str, data: AdminBiasIn, session: Annotated[AsyncSession, Depends(get_db)]
) -> AdminBiasOut:
    for metric_key, value in (
        ("recent_borrowers_processed", str(data.recent_borrowers_processed)),
        ("relationship_note", data.relationship_note),
    ):
        stmt = (
            insert(BankBiasFactModel)
            .values(bank_name=bank_name, metric_key=metric_key, value=value)
            .on_conflict_do_update(index_elements=["bank_name", "metric_key"], set_={"value": value})
        )
        await session.execute(stmt)
    await session.commit()
    return AdminBiasOut(bank_name=bank_name, **data.model_dump())


@admin_router.delete("/bias/{bank_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bias(bank_name: str, session: Annotated[AsyncSession, Depends(get_db)]) -> None:
    result = await session.execute(delete(BankBiasFactModel).where(BankBiasFactModel.bank_name == bank_name))
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{bank_name} has no relationship data.")
