"""Request/response shapes for the filter-sidebar explore endpoint — see
app/explore.py for the matching logic these wrap."""

from pydantic import BaseModel, Field


class ExploreFiltersIn(BaseModel):
    employment_type: list[str] = Field(default_factory=list)
    property_type: list[str] = Field(default_factory=list)
    property_usage: list[str] = Field(default_factory=list)
    property_stage: list[str] = Field(default_factory=list)
    property_location: list[str] = Field(default_factory=list)

    # Affordability inputs — entered fresh each time, never stored. Multiple
    # obligations (home loan, education loan, ...) get summed before the
    # FOIR calculation — see app/domain.py's calculate_customer_foir_pct.
    age: int | None = None
    monthly_income: float | None = None
    obligations: list[float] = Field(default_factory=list)


class ExploreProductOut(BaseModel):
    bank_name: str
    product_name: str
    employment_type: str
    property_type: list[str]
    property_usage: list[str]
    property_stage: list[str]
    property_location: list[str]

    # Only populated when the corresponding inputs were provided, and only
    # when the bank has the matching fact loaded (see app/add_foir_tenure_data.py).
    bank_foir_pct: float | None = None
    customer_foir_pct: float | None = None
    foir_pass: bool | None = None
    max_emi: float | None = None
    bank_max_tenure_years: float | None = None
    final_tenure_years: float | None = None
    max_loan_amount: float | None = None

    # Always populated once the product is loaded — doesn't depend on any
    # affordability inputs, unlike the fields above. is_estimated is true
    # only when this bank has no real rate on file (see
    # get_bank_interest_rate_pct) and the flat fallback was used instead.
    interest_rate_pct: float
    interest_rate_is_estimated: bool
    # Only set for banks whose source published a real range (not just
    # "X% onwards") — see get_bank_interest_rate_upper_pct.
    interest_rate_upper_pct: float | None = None
    # Only set for a bank whose source actually published a range — see
    # get_bank_interest_rate_upper_pct. None means show a single fixed rate,
    # not a slider.
    interest_rate_upper_pct: float | None = None


class FacetOptionOut(BaseModel):
    value: str
    label: str
    count: int


class ExploreResponseOut(BaseModel):
    results: list[ExploreProductOut]
    total: int
    facets: dict[str, list[FacetOptionOut]]


class LiveRateOut(BaseModel):
    bank_name: str
    rate_pct: float
