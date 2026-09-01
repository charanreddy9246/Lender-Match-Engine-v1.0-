"""The API contract: what the website sends us, and what we send back.

These enums are a validation convenience at the API boundary only — the form the
customer fills in today asks a known, fixed set of questions, so it's reasonable
to validate them strictly here. That's independent of the database and matching
engine underneath, which no longer know about any of these specific values; see
app.domain for how a fixed request like this gets turned into generic attribute
answers. Adding a brand new question to the form still means adding a field here
(this is API contract, not eligibility data) — but it no longer means touching the
database schema or the matching logic.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EmploymentType(StrEnum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    PROFESSIONAL = "professional"
    PENSIONER = "pensioner"
    # The two extra income types from the client's property-eligibility
    # workbook (see app/load_client_property_data.py) — not in the original
    # Birbal dataset, which is why they weren't here before.
    CASH_INCOME = "cash_income"
    NRI = "nri"


class DocumentType(StrEnum):
    ITR_FORM16 = "itr_form16"
    ITR = "itr"
    SALARY_SLIP = "salary_slip"
    CASH_INCOME = "cash_income"
    BANK_STATEMENT = "bank_statement"
    GST = "gst"
    BUSINESS_PROOF = "business_proof"
    PENSION_PROOF = "pension_proof"


class PropertyType(StrEnum):
    STANDARD_URBAN = "standard_urban"
    SEMI_URBAN_VILLAGE = "semi_urban_village"
    UNDER_CONSTRUCTION = "under_construction"
    OTHERS = "others"


class ApprovalTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BorrowerProfileIn(BaseModel):
    """Which income field actually applies depends on `employment_type` — a
    Salaried borrower fills `net_monthly_salary`, a Self-employed borrower fills
    `annual_turnover`, and so on. All four are optional here rather than one
    required field, since only one is relevant per submission; app.service reads
    whichever ones are set. `has_co_borrower` only matters for Pensioner profiles
    (some lenders require one) but is always sent — it's simply ignored by every
    rule that doesn't check for it.
    """

    model_config = ConfigDict(extra="ignore")

    cibil_score: int = Field(ge=300, le=900)
    loan_amount_required: int = Field(gt=0)
    employment_type: EmploymentType
    net_monthly_salary: int | None = Field(default=None, gt=0)
    annual_turnover: int | None = Field(default=None, gt=0)
    annual_gross_receipts: int | None = Field(default=None, gt=0)
    monthly_pension: int | None = Field(default=None, gt=0)
    has_co_borrower: bool = False
    documents_available: list[DocumentType]
    property_type: PropertyType

    # Future optional fields go here, e.g.:
    # age: int | None = None
    # existing_emi_monthly: int | None = None
    # city: str | None = None


class ProductMatchOut(BaseModel):
    bank_name: str
    product_name: str
    # None where a lender's pricing/amount data hasn't been loaded yet — see
    # app/domain.py's HomeLoanProduct and WeightedScoringStrategy docstrings.
    interest_rate_pct: float | None
    interest_rate_range: str | None
    processing_fee_pct: float | None
    processing_fee: str | None
    lender_type: str | None
    max_eligible_amount: int | None
    approval_likelihood_tier: ApprovalTier | None
    # Relationship/priority standing with this lender — see app/domain.py's
    # WeightedScoringStrategy and app/database.py's BankBiasFactModel. None
    # where no bias data has been entered for this bank.
    recent_borrowers_processed: int | None
    relationship_note: str | None
    score: float
    reasons: list[str]


class MatchMeta(BaseModel):
    products_considered: int
    products_eligible: int


class MatchResponse(BaseModel):
    lenders: list[ProductMatchOut]
    meta: MatchMeta
