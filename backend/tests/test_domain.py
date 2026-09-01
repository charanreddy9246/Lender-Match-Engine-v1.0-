"""Tests for the matching engine (app/domain.py) — eligibility, scoring, and the
end-to-end matcher. This is the highest-value code to test since it's pure Python
with zero I/O and it's the actual business logic of the product.

Products are built from generic EligibilityRuleDef rows plus an attributes_by_key
catalog, instead of one fixed EligibilityCriteria dataclass — this mirrors how a real
product loaded from the database looks (see app/database.py and app/load_birbal_dataset.py).
AND-of-rules is the default (every condition rule must pass); "at least one of a
document set" (OR) is covered separately by the "any_of" operator tests below.
"""

from app.domain import (
    AttributeDef,
    BorrowerProfile,
    EligibilityRuleDef,
    HomeLoanProduct,
    WeightedScoringStrategy,
    filter_eligible,
    find_top_products,
)

# ---------------------------------------------------------------------------
# Attribute catalog (mirrors app/load_birbal_dataset.py's ATTRIBUTE_CATALOG,
# trimmed to what these tests use)
# ---------------------------------------------------------------------------

ATTRIBUTES: dict[str, AttributeDef] = {
    "cibil_score": AttributeDef(key="cibil_score", label="CIBIL score", category="Credit", data_type="number"),
    "net_monthly_salary": AttributeDef(
        key="net_monthly_salary", label="Net monthly salary", category="Income", data_type="number"
    ),
    "property_type": AttributeDef(key="property_type", label="Property type", category="Property", data_type="text"),
    "employment_type": AttributeDef(
        key="employment_type", label="Employment type", category="Income", data_type="text"
    ),
    "document_bank_statement": AttributeDef(
        key="document_bank_statement", label="Bank statement", category="Documents", data_type="boolean"
    ),
    "document_itr_form16": AttributeDef(
        key="document_itr_form16", label="ITR / Form 16", category="Documents", data_type="boolean"
    ),
    "document_salary_slip": AttributeDef(
        key="document_salary_slip", label="Salary slip", category="Documents", data_type="boolean"
    ),
    "document_cash_income": AttributeDef(
        key="document_cash_income", label="Cash income", category="Documents", data_type="boolean"
    ),
    # Not a real answer key — see domain.py's "any_of" operator. data_type is
    # irrelevant for it (the operator is special-cased before data_type is used),
    # "text" is just a plausible label for the catalog entry.
    "documents_any_of": AttributeDef(
        key="documents_any_of", label="Any income document", category="Documents", data_type="text"
    ),
}


def rule(attribute_key: str, operator: str, value: str) -> EligibilityRuleDef:
    return EligibilityRuleDef(attribute_key=attribute_key, operator=operator, value=value)


def property_rules(*property_types: str) -> list[EligibilityRuleDef]:
    """One "in" rule covering every accepted type, not one rule per type —
    "must be one of these" is an OR, and stacking independent "==" rules would
    demand a single answer match every one of them. See domain.py's `in` operator."""
    return [rule("property_type", "in", ",".join(property_types))]


# ---------------------------------------------------------------------------
# Fixture products
# ---------------------------------------------------------------------------


def make_product(
    id: int,
    bank_name: str,
    interest_rate_pct: float | None = 8.5,
    approval_likelihood_tier: str | None = "medium",
    min_loan_amount: int | None = 100_000,
    max_loan_amount: int | None = 5_000_000,
    rules: list[EligibilityRuleDef] | None = None,
) -> HomeLoanProduct:
    if rules is None:
        rules = [
            *property_rules("standard_urban"),
            rule("cibil_score", ">=", "700"),
            rule("net_monthly_salary", ">=", "20000"),
            rule("document_bank_statement", "required", "true"),
        ]
    # Pricing/amount/tier facts, not conditions — see domain.py's get_fact. None
    # means "not loaded", so those simply aren't added as rows (a missing fact
    # row is what get_fact returns None for).
    facts = [rule("processing_fee_pct", "fact", "0.5")]
    if interest_rate_pct is not None:
        facts.append(rule("interest_rate_pct", "fact", str(interest_rate_pct)))
    if min_loan_amount is not None:
        facts.append(rule("min_loan_amount", "fact", str(min_loan_amount)))
    if max_loan_amount is not None:
        facts.append(rule("max_loan_amount", "fact", str(max_loan_amount)))
    if approval_likelihood_tier is not None:
        facts.append(rule("approval_likelihood_tier", "fact", approval_likelihood_tier))
    return HomeLoanProduct(
        id=id,
        bank_name=bank_name,
        product_name=f"{bank_name} Home Loan",
        rules=[*facts, *rules],
    )


STRICT_BANK = make_product(
    id=1,
    bank_name="Strict Bank",
    interest_rate_pct=8.0,
    approval_likelihood_tier="high",
    rules=[
        *property_rules("standard_urban"),
        rule("cibil_score", ">=", "780"),
        rule("net_monthly_salary", ">=", "50000"),
        rule("document_bank_statement", "required", "true"),
        rule("document_itr_form16", "required", "true"),
    ],
)

LENIENT_BANK = make_product(
    id=2,
    bank_name="Lenient Bank",
    interest_rate_pct=9.5,
    approval_likelihood_tier="low",
    rules=[
        *property_rules("standard_urban", "semi_urban_village", "others"),
        rule("cibil_score", ">=", "600"),
        rule("net_monthly_salary", ">=", "10000"),
        rule("document_bank_statement", "required", "true"),
    ],
)

FIXTURE_PRODUCTS = [STRICT_BANK, LENIENT_BANK]


def make_profile(
    cibil_score: int = 800,
    loan_amount_required: int = 1_000_000,
    employment_type: str = "salaried",
    net_monthly_salary: int = 60_000,
    documents_available: frozenset[str] = frozenset({"bank_statement", "itr_form16"}),
    property_type: str = "standard_urban",
) -> BorrowerProfile:
    answers = {
        "cibil_score": str(cibil_score),
        "net_monthly_salary": str(net_monthly_salary),
        "property_type": property_type,
    }
    for document in documents_available:
        answers[f"document_{document}"] = "true"
    return BorrowerProfile(employment_type=employment_type, loan_amount_required=loan_amount_required, answers=answers)


def strong_salaried_profile(**overrides) -> BorrowerProfile:
    return make_profile(**overrides)


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def test_strong_profile_is_eligible_for_strict_bank():
    assert filter_eligible(strong_salaried_profile(), [STRICT_BANK], ATTRIBUTES) == [STRICT_BANK]


def test_cibil_just_below_threshold_is_rejected():
    profile = strong_salaried_profile(cibil_score=779)
    assert filter_eligible(profile, [STRICT_BANK], ATTRIBUTES) == []


def test_cibil_exactly_at_threshold_is_accepted():
    profile = strong_salaried_profile(cibil_score=780)
    assert filter_eligible(profile, [STRICT_BANK], ATTRIBUTES) == [STRICT_BANK]


def test_missing_required_document_rejects():
    profile = strong_salaried_profile(documents_available=frozenset({"bank_statement"}))
    # STRICT_BANK requires both bank_statement and itr_form16
    assert filter_eligible(profile, [STRICT_BANK], ATTRIBUTES) == []


def test_lenient_bank_accepts_when_required_doc_present():
    profile = strong_salaried_profile(
        cibil_score=650,
        net_monthly_salary=15_000,
        documents_available=frozenset({"bank_statement"}),
    )
    assert filter_eligible(profile, [LENIENT_BANK], ATTRIBUTES) == [LENIENT_BANK]


def test_lenient_bank_rejects_when_required_doc_missing():
    profile = strong_salaried_profile(
        cibil_score=650,
        net_monthly_salary=15_000,
        documents_available=frozenset(),  # missing bank_statement
    )
    assert filter_eligible(profile, [LENIENT_BANK], ATTRIBUTES) == []


def test_property_type_not_accepted_rejects():
    profile = strong_salaried_profile(property_type="under_construction")
    # STRICT_BANK only allows standard_urban
    assert filter_eligible(profile, [STRICT_BANK], ATTRIBUTES) == []


def test_loan_amount_outside_range_rejects():
    profile = strong_salaried_profile(loan_amount_required=10_000_000)
    assert filter_eligible(profile, [STRICT_BANK], ATTRIBUTES) == []


def test_loan_amount_unset_on_product_means_no_constraint():
    unset_range_bank = make_product(id=99, bank_name="No Range Bank", min_loan_amount=None, max_loan_amount=None)
    profile = strong_salaried_profile(loan_amount_required=999_999_999)
    assert filter_eligible(profile, [unset_range_bank], ATTRIBUTES) == [unset_range_bank]


def test_empty_documents_rejects_bank_requiring_bank_statement():
    profile = strong_salaried_profile(documents_available=frozenset())
    assert filter_eligible(profile, FIXTURE_PRODUCTS, ATTRIBUTES) == []


def test_no_products_match_returns_empty_list_not_error():
    profile = strong_salaried_profile(cibil_score=300, net_monthly_salary=1)
    assert filter_eligible(profile, FIXTURE_PRODUCTS, ATTRIBUTES) == []


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

SCORING_PROFILE = make_profile(documents_available=frozenset({"bank_statement"}))


def test_lower_interest_rate_scores_higher_all_else_equal():
    strategy = WeightedScoringStrategy()
    cheap = make_product(id=1, bank_name="Cheap Bank", interest_rate_pct=8.0)
    expensive = make_product(id=2, bank_name="Expensive Bank", interest_rate_pct=11.0)

    cheap_score, _ = strategy.score(SCORING_PROFILE, cheap)
    expensive_score, _ = strategy.score(SCORING_PROFILE, expensive)

    assert cheap_score > expensive_score


def test_higher_approval_tier_scores_higher_all_else_equal():
    strategy = WeightedScoringStrategy()
    high_tier = make_product(id=1, bank_name="High Tier", approval_likelihood_tier="high")
    low_tier = make_product(id=2, bank_name="Low Tier", approval_likelihood_tier="low")

    high_score, _ = strategy.score(SCORING_PROFILE, high_tier)
    low_score, _ = strategy.score(SCORING_PROFILE, low_tier)

    assert high_score > low_score


def test_more_headroom_on_max_amount_scores_higher():
    strategy = WeightedScoringStrategy()
    tight = make_product(id=1, bank_name="Tight", min_loan_amount=500_000, max_loan_amount=1_100_000)
    roomy = make_product(id=2, bank_name="Roomy", min_loan_amount=500_000, max_loan_amount=9_000_000)

    tight_score, _ = strategy.score(SCORING_PROFILE, tight)
    roomy_score, _ = strategy.score(SCORING_PROFILE, roomy)

    assert roomy_score > tight_score


def test_reasons_are_populated():
    strategy = WeightedScoringStrategy()
    product = make_product(id=1, bank_name="Any Bank")
    _, reasons = strategy.score(SCORING_PROFILE, product)
    assert len(reasons) > 0


def test_missing_pricing_data_scores_zero_with_reason_not_a_crash():
    strategy = WeightedScoringStrategy()
    product = make_product(
        id=1,
        bank_name="No Pricing Bank",
        interest_rate_pct=None,
        min_loan_amount=None,
        max_loan_amount=None,
        approval_likelihood_tier=None,
    )
    score, reasons = strategy.score(SCORING_PROFILE, product)
    assert score == 0.0
    assert any("no pricing data" in r for r in reasons)


# ---------------------------------------------------------------------------
# Matcher (eligibility + scoring together)
# ---------------------------------------------------------------------------


def test_golden_profile_strong_salaried_prefers_lower_rate_when_both_eligible():
    profile = strong_salaried_profile()
    results = find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES)
    result_ids = [r.product.id for r in results]
    assert STRICT_BANK.id in result_ids
    # STRICT_BANK (8.0%) should outrank LENIENT_BANK (9.5%) since both are eligible
    assert results[0].product.id == STRICT_BANK.id


def test_weak_profile_only_matches_lenient_bank():
    profile = strong_salaried_profile(
        cibil_score=610,
        net_monthly_salary=12_000,
        documents_available=frozenset({"bank_statement"}),
        property_type="semi_urban_village",
    )
    results = find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES)
    assert [r.product.id for r in results] == [LENIENT_BANK.id]


def test_no_eligible_products_returns_empty_list():
    profile = strong_salaried_profile(
        cibil_score=300,
        loan_amount_required=1,
        net_monthly_salary=1,
        documents_available=frozenset(),
        property_type="others",
    )
    assert find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES) == []


def test_top_n_is_respected():
    profile = strong_salaried_profile(documents_available=frozenset({"bank_statement", "itr_form16", "cash_income"}))
    results = find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES, top_n=1)
    assert len(results) == 1


def test_deterministic_same_input_same_output():
    profile = strong_salaried_profile()
    first = [r.product.id for r in find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES)]
    second = [r.product.id for r in find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES)]
    assert first == second


# ---------------------------------------------------------------------------
# "any_of" operator — "at least one of a document set" (OR), the one case the
# rest of the engine can't express by stacking more AND rules. See the Birbal
# reference dataset's README: bank statement is always mandatory and not part
# of this check; this only covers the *extra* documents a borrower ticks.
# ---------------------------------------------------------------------------

ANY_OF_BANK = make_product(
    id=3,
    bank_name="Any Doc Bank",
    rules=[
        *property_rules("standard_urban"),
        rule("cibil_score", ">=", "700"),
        rule("net_monthly_salary", ">=", "20000"),
        rule("documents_any_of", "any_of", "itr_form16,salary_slip"),
    ],
)


def test_any_of_passes_when_one_accepted_document_is_ticked():
    profile = strong_salaried_profile(documents_available=frozenset({"bank_statement", "itr_form16"}))
    assert filter_eligible(profile, [ANY_OF_BANK], ATTRIBUTES) == [ANY_OF_BANK]


def test_any_of_rejects_when_ticked_document_is_not_in_accepted_set():
    profile = strong_salaried_profile(documents_available=frozenset({"bank_statement", "cash_income"}))
    assert filter_eligible(profile, [ANY_OF_BANK], ATTRIBUTES) == []


def test_any_of_passes_when_no_extra_document_is_ticked():
    # Bank statement is mandatory on the real form and implicit here; ticking no
    # *extra* document means there's nothing to check "at least one of" against.
    profile = strong_salaried_profile(documents_available=frozenset({"bank_statement"}))
    assert filter_eligible(profile, [ANY_OF_BANK], ATTRIBUTES) == [ANY_OF_BANK]


# ---------------------------------------------------------------------------
# Employment-type scoping — a product that only serves one employment type,
# same "==" operator every text rule already uses, just applied to this key.
# ---------------------------------------------------------------------------

SALARIED_ONLY_BANK = make_product(
    id=4,
    bank_name="Salaried Only Bank",
    rules=[
        *property_rules("standard_urban"),
        rule("cibil_score", ">=", "700"),
        rule("net_monthly_salary", ">=", "20000"),
        rule("employment_type", "==", "salaried"),
        rule("document_bank_statement", "required", "true"),
    ],
)


def test_employment_type_match_is_eligible():
    profile = strong_salaried_profile()  # employment_type defaults to "salaried"
    answers = {**profile.answers, "employment_type": "salaried"}
    profile = BorrowerProfile(
        employment_type=profile.employment_type, loan_amount_required=profile.loan_amount_required, answers=answers
    )
    assert filter_eligible(profile, [SALARIED_ONLY_BANK], ATTRIBUTES) == [SALARIED_ONLY_BANK]


def test_employment_type_mismatch_is_rejected():
    profile = strong_salaried_profile()
    answers = {**profile.answers, "employment_type": "self_employed"}
    profile = BorrowerProfile(
        employment_type=profile.employment_type, loan_amount_required=profile.loan_amount_required, answers=answers
    )
    assert filter_eligible(profile, [SALARIED_ONLY_BANK], ATTRIBUTES) == []


# ---------------------------------------------------------------------------
# "between" operator — a min-and-max band in one rule, since the database only
# allows one rule row per (product, attribute) pair (uq_rule_scope), so a CIBIL
# band can't be two separate ">=" and "<=" rows on the same product.
# ---------------------------------------------------------------------------

BAND_BANK = make_product(
    id=5,
    bank_name="Band Bank",
    rules=[
        *property_rules("standard_urban"),
        rule("cibil_score", "between", "700,750"),
        rule("net_monthly_salary", ">=", "20000"),
        rule("document_bank_statement", "required", "true"),
    ],
)


def test_between_accepts_value_inside_the_band():
    profile = strong_salaried_profile(cibil_score=725)
    assert filter_eligible(profile, [BAND_BANK], ATTRIBUTES) == [BAND_BANK]


def test_between_accepts_value_at_each_edge():
    assert filter_eligible(strong_salaried_profile(cibil_score=700), [BAND_BANK], ATTRIBUTES) == [BAND_BANK]
    assert filter_eligible(strong_salaried_profile(cibil_score=750), [BAND_BANK], ATTRIBUTES) == [BAND_BANK]


def test_between_rejects_value_outside_the_band():
    assert filter_eligible(strong_salaried_profile(cibil_score=699), [BAND_BANK], ATTRIBUTES) == []
    assert filter_eligible(strong_salaried_profile(cibil_score=751), [BAND_BANK], ATTRIBUTES) == []


# ---------------------------------------------------------------------------
# Bias override — a bank with relationship/priority data ("recent_borrowers_
# processed") always outranks one without it, regardless of rate. Not a
# weighted ingredient like rate/headroom/tier — see domain.py's
# WeightedScoringStrategy docstring and find_top_products' _rank_key.
# ---------------------------------------------------------------------------

NO_BIAS_CHEAP_RATE = make_product(id=6, bank_name="Cheap No-Bias Bank", interest_rate_pct=7.5)

BIAS_EXPENSIVE_RATE = make_product(
    id=7,
    bank_name="Expensive Bias Bank",
    interest_rate_pct=11.0,
    rules=[
        *property_rules("standard_urban"),
        rule("cibil_score", ">=", "700"),
        rule("net_monthly_salary", ">=", "20000"),
        rule("document_bank_statement", "required", "true"),
        rule("recent_borrowers_processed", "fact", "5"),
    ],
)


def test_bias_bank_outranks_cheaper_non_bias_bank():
    profile = strong_salaried_profile()
    results = find_top_products(profile, [NO_BIAS_CHEAP_RATE, BIAS_EXPENSIVE_RATE], ATTRIBUTES)
    assert results[0].product.id == BIAS_EXPENSIVE_RATE.id
    assert results[1].product.id == NO_BIAS_CHEAP_RATE.id


def test_higher_recent_borrower_count_wins_between_two_bias_banks():
    low_bias_better_rate = make_product(
        id=8,
        bank_name="Low Bias Better Rate",
        interest_rate_pct=7.5,
        rules=[
            *property_rules("standard_urban"),
            rule("cibil_score", ">=", "700"),
            rule("net_monthly_salary", ">=", "20000"),
            rule("document_bank_statement", "required", "true"),
            rule("recent_borrowers_processed", "fact", "2"),
        ],
    )
    high_bias_worse_rate = make_product(
        id=9,
        bank_name="High Bias Worse Rate",
        interest_rate_pct=11.0,
        rules=[
            *property_rules("standard_urban"),
            rule("cibil_score", ">=", "700"),
            rule("net_monthly_salary", ">=", "20000"),
            rule("document_bank_statement", "required", "true"),
            rule("recent_borrowers_processed", "fact", "8"),
        ],
    )
    profile = strong_salaried_profile()
    results = find_top_products(profile, [low_bias_better_rate, high_bias_worse_rate], ATTRIBUTES)
    assert results[0].product.id == high_bias_worse_rate.id
    assert results[1].product.id == low_bias_better_rate.id


def test_no_bias_banks_still_rank_by_score_alone():
    # Sanity check the override doesn't disturb ordinary ranking when nobody
    # has bias data — same expectation as the pre-bias behavior.
    profile = strong_salaried_profile()
    results = find_top_products(profile, FIXTURE_PRODUCTS, ATTRIBUTES)
    assert results[0].product.id == STRICT_BANK.id
