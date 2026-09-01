"""What the admin panel sends and receives. Deliberately shaped as plain,
friendly fields (CIBIL range, documents, property types...) instead of the raw
attribute/operator/value rule rows the database actually stores — the admin
never sees "rules," only normal form boxes. app/admin_api.py translates
between the two directions, the same way app/load_birbal_dataset.py already
translates an Excel row into rule rows.
"""

from pydantic import BaseModel, Field

from app.schemas import DocumentType, EmploymentType, PropertyType


class AdminProductDetail(BaseModel):
    employment_type: EmploymentType
    min_cibil: int = Field(ge=300, le=900)
    max_cibil: int = Field(ge=300, le=900)
    min_loan_amount: int = Field(gt=0)
    max_loan_amount: int = Field(gt=0)
    # Which field this is depends on employment_type — Salaried -> min salary,
    # Self-employed -> min turnover, etc. — same mapping the borrower form and
    # app/load_birbal_dataset.py already use (see INCOME_BY_EMPLOYMENT_TYPE).
    income_threshold: int = Field(gt=0)
    documents_accepted: list[DocumentType] = Field(min_length=1)
    property_types_accepted: list[PropertyType] = Field(min_length=1)
    interest_rate_pct: float = Field(gt=0)
    interest_rate_range: str = ""
    processing_fee: str = ""
    lender_type: str = ""
    # Only meaningful when employment_type is "pensioner" — ignored otherwise.
    co_borrower_required: bool = False


class AdminProductOut(AdminProductDetail):
    bank_name: str


class AdminBankSummary(BaseModel):
    bank_name: str
    source: str
    employment_types: list[EmploymentType]


class AdminBiasIn(BaseModel):
    recent_borrowers_processed: int = Field(ge=0)
    relationship_note: str = ""


class AdminBiasOut(AdminBiasIn):
    bank_name: str
