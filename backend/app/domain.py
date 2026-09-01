"""The matching engine: pure Python, no HTTP, no database.

Reading order: models -> eligibility (who qualifies) -> scoring (who ranks where) ->
matcher (ties the two together into "top N lenders").

Eligibility used to be five hardcoded rule classes (MinCibilRule, MinSalaryRule, ...),
one per criterion. That meant a new criterion type meant a new class, plus a new
column in the database, plus wiring it into DEFAULT_RULES — a developer had to be
involved every time. Eligibility is now a single generic check driven by data:
each AttributeDef says what kind of value a criterion holds (number, boolean, text),
and each EligibilityRuleDef says what a specific product needs that value to satisfy.
Adding a new criterion is now adding rows, not writing a new class.

Pricing/amount/tier info (interest rate, fee, loan amount range, approval tier)
used to be fixed fields on HomeLoanProduct — the same "developer needed for every
new field" problem, one level up. Fixed the same way: those are now rows in
`rules` too, using the "fact" operator (a stored value, not a condition to check
against a borrower's answer) instead of a dedicated field each. `get_fact` below
reads them back out.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

AttributeDataType = Literal["number", "boolean", "text"]
RuleOperator = Literal[">=", "<=", "==", "required", "in", "fact", "any_of", "between"]

# Approval-likelihood tiers are a small, deliberately fixed vocabulary used only
# for scoring weight below — unlike borrower/product criteria, this isn't something
# an admin adds new values to, so it stays a plain constant rather than going
# through the attribute catalog.
_TIER_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


@dataclass(frozen=True)
class AttributeDef:
    """One entry in the small, rarely-changing criteria catalog."""

    key: str
    label: str
    category: str
    data_type: AttributeDataType


@dataclass(frozen=True)
class EligibilityRuleDef:
    """Usually a condition: a product needs `attribute_key` to satisfy `operator`
    against `value`, checked against a borrower's answer. `value` is always text;
    it's interpreted using the attribute's data_type.

    When `operator` is "fact", this row isn't a condition at all — it's a stored
    value (interest rate, tenure, ...) for display/scoring, and filter_eligible
    skips it entirely rather than checking it against the borrower. See get_fact.

    An earlier version had an `employment_type` field to scope a rule to one
    employment type. Removed — no real data has needed that distinction yet. If
    it's needed later, it should come back as a general "scope by any attribute"
    mechanism, not a field limited to employment type alone (see database.py).
    """

    attribute_key: str
    operator: RuleOperator
    value: str


@dataclass(frozen=True)
class BorrowerProfile:
    """`answers` holds every criterion-shaped fact about the borrower — CIBIL score,
    income, which documents they have, which property type they chose — keyed by
    the same attribute key the catalog and rules use. `loan_amount_required` gets
    its own field since it's used directly in scoring, not just as a rule answer.
    """

    employment_type: str
    loan_amount_required: int
    answers: dict[str, str]


@dataclass(frozen=True)
class HomeLoanProduct:
    id: int
    bank_name: str
    product_name: str
    rules: list[EligibilityRuleDef]


def get_fact(product: HomeLoanProduct, key: str) -> str | None:
    """Reads a stored "fact" row (interest rate, loan amount range, tier, ...)
    off a product, or None if that fact hasn't been loaded for this product yet.
    None is treated as "not known", never as zero — see filter_eligible and
    WeightedScoringStrategy for how each fact is used once found.
    """
    for rule in product.rules:
        if rule.operator == "fact" and rule.attribute_key == key:
            return rule.value
    return None


@dataclass(frozen=True)
class ScoredProduct:
    product: HomeLoanProduct
    score: float
    reasons: list[str]


# ---------------------------------------------------------------------------
# Eligibility — hard filters a product must pass before it's ranked at all
# ---------------------------------------------------------------------------


def _rule_satisfied(rule: EligibilityRuleDef, data_type: AttributeDataType, profile: BorrowerProfile) -> bool:
    if rule.operator == "any_of":
        # "at least one of a document set" (OR), not AND-of-everything like every
        # other operator here. `value` holds the comma-separated document keys this
        # product accepts beyond the always-mandatory bank statement. Documents are
        # individual "document_<key>": "true" answers (see service.py's _to_answers),
        # not one attribute this rule can point `attribute_key` at directly, so this
        # scans the whole answer set instead of a single answer.
        # A borrower who ticked no extra documents (bank statement only) always
        # passes — there's nothing to check "at least one of" against.
        accepted = {v.strip() for v in rule.value.split(",")}
        ticked = {
            key.removeprefix("document_")
            for key, value in profile.answers.items()
            if key.startswith("document_") and key != "document_bank_statement" and value.strip().lower() == "true"
        }
        return not ticked or bool(ticked & accepted)

    answer = profile.answers.get(rule.attribute_key)
    if answer is None:
        return False

    if data_type == "number":
        try:
            answer_value = float(answer)
        except ValueError:
            return False
        if rule.operator == "between":
            # A single rule covering a min-and-max band (e.g. CIBIL 708-900), not
            # two separate ">=" and "<=" rows — the database only allows one rule
            # row per (product, attribute) pair (see uq_rule_scope in database.py),
            # so a band has to be one rule, "low,high" in `value`.
            try:
                low_str, high_str = rule.value.split(",")
                low, high = float(low_str), float(high_str)
            except ValueError:
                return False
            return low <= answer_value <= high
        try:
            threshold = float(rule.value)
        except ValueError:
            return False
        if rule.operator == ">=":
            return answer_value >= threshold
        if rule.operator == "<=":
            return answer_value <= threshold
        if rule.operator == "==":
            return answer_value == threshold
        return False

    if data_type == "boolean":
        answer_is_true = answer.strip().lower() == "true"
        if rule.operator == "required":
            return answer_is_true
        if rule.operator == "==":
            return answer_is_true == (rule.value.strip().lower() == "true")
        return False

    # text
    if rule.operator == "==":
        return answer == rule.value
    if rule.operator == "in":
        # "in" holds a comma-separated set of acceptable values in a single rule —
        # e.g. a product accepting three property types is one rule, not three
        # independent ones, since "must be one of these" is an OR, and a plain
        # AND-of-rules engine can't express OR by stacking more rules.
        return answer in {v.strip() for v in rule.value.split(",")}
    return False


def filter_eligible(
    profile: BorrowerProfile,
    products: list[HomeLoanProduct],
    attributes_by_key: dict[str, AttributeDef],
) -> list[HomeLoanProduct]:
    """A product is eligible if the requested loan amount fits its range and every
    one of its *condition* rules is satisfied — "fact" rows (interest rate, tenure,
    ...) are skipped here entirely, since they're stored values, not conditions to
    check against the borrower. `attributes_by_key` supplies the data_type each
    condition is checked as — it's the same catalog an admin screen would manage,
    passed in rather than hardcoded here.
    """
    eligible: list[HomeLoanProduct] = []
    for product in products:
        # Unknown loan-amount range (fact not yet loaded for this product) means
        # no constraint — never treated as "any amount fails".
        min_amount_raw, max_amount_raw = get_fact(product, "min_loan_amount"), get_fact(product, "max_loan_amount")
        if min_amount_raw is not None and max_amount_raw is not None:
            min_amount, max_amount = int(min_amount_raw), int(max_amount_raw)
            if not (min_amount <= profile.loan_amount_required <= max_amount):
                continue

        condition_rules = [rule for rule in product.rules if rule.operator != "fact"]
        if all(
            _rule_satisfied(rule, attributes_by_key[rule.attribute_key].data_type, profile)
            for rule in condition_rules
        ):
            eligible.append(product)
    return eligible


# ---------------------------------------------------------------------------
# Scoring — ranks whoever survives eligibility
# ---------------------------------------------------------------------------

# a lower rate than this scores the max rate component; a higher rate scores 0
_RATE_FLOOR_PCT = 7.0
_RATE_CEILING_PCT = 12.0


class ScoringStrategy(Protocol):
    def score(self, profile: BorrowerProfile, product: HomeLoanProduct) -> tuple[float, list[str]]: ...


class WeightedScoringStrategy:
    """Combines interest rate, headroom on the requested amount, and approval
    likelihood into one score. Lender relationship/priority ("bias") is
    deliberately NOT blended in here — it's a hard override applied afterward,
    in find_top_products' rank_key, not one ingredient among several. A bank
    with any bias data always outranks one without, regardless of this score;
    this score only decides ordering *within* each of those two groups.

    Weights are deliberately simple and adjustable — this is the one place that would
    change if the ranking priorities (e.g. "prefer fastest approval") change later.
    """

    def __init__(self, rate_weight: float = 0.5, headroom_weight: float = 0.2, tier_weight: float = 0.3):
        self.rate_weight = rate_weight
        self.headroom_weight = headroom_weight
        self.tier_weight = tier_weight

    def score(self, profile: BorrowerProfile, product: HomeLoanProduct) -> tuple[float, list[str]]:
        """Each component only contributes if its underlying fact has been loaded,
        and the result is normalized by the weight actually used — a product
        missing all pricing facts scores 0 with a clear reason, rather than
        crashing or silently being scored as if its rate/amount/tier were zero.
        """
        reasons: list[str] = []
        weighted_sum = 0.0
        weight_used = 0.0

        interest_rate_raw = get_fact(product, "interest_rate_pct")
        if interest_rate_raw is not None:
            interest_rate_pct = float(interest_rate_raw)
            rate_span = _RATE_CEILING_PCT - _RATE_FLOOR_PCT
            rate_score = (_RATE_CEILING_PCT - interest_rate_pct) / rate_span
            rate_score = min(max(rate_score, 0.0), 1.0)
            weighted_sum += self.rate_weight * rate_score
            weight_used += self.rate_weight
            reasons.append(f"interest rate {interest_rate_pct}%")

        min_amount_raw, max_amount_raw = get_fact(product, "min_loan_amount"), get_fact(product, "max_loan_amount")
        if min_amount_raw is not None and max_amount_raw is not None:
            min_amount, max_amount = int(min_amount_raw), int(max_amount_raw)
            amount_span = max_amount - min_amount
            headroom_score = 0.5
            if amount_span > 0:
                headroom_score = (max_amount - profile.loan_amount_required) / amount_span
                headroom_score = min(max(headroom_score, 0.0), 1.0)
            weighted_sum += self.headroom_weight * headroom_score
            weight_used += self.headroom_weight
            reasons.append(f"eligible up to {max_amount:,}")

        tier = get_fact(product, "approval_likelihood_tier")
        if tier is not None:
            tier_score = _TIER_WEIGHT[tier]
            weighted_sum += self.tier_weight * tier_score
            weight_used += self.tier_weight
            reasons.append(f"{tier} approval likelihood")

        # Bias facts (recent_borrowers_processed, relationship_note) are
        # deliberately NOT added to weighted_sum/weight_used here — see this
        # class's docstring. They still appear as reasons, since a bank that
        # got bumped to the top by the rank_key override should visibly say
        # why, not just show a rate that doesn't explain the ordering.
        recent_borrowers_raw = get_fact(product, "recent_borrowers_processed")
        if recent_borrowers_raw is not None:
            recent_borrowers = float(recent_borrowers_raw)
            plural = "" if recent_borrowers == 1 else "s"
            reasons.append(f"processed {int(recent_borrowers)} of our borrower{plural} recently — prioritized for this")

        relationship_note = get_fact(product, "relationship_note")
        if relationship_note is not None:
            reasons.append(relationship_note)

        if weight_used == 0:
            reasons.append("no pricing data yet — ranked neutrally")
            return 0.0, reasons

        return weighted_sum / weight_used, reasons


DEFAULT_SCORING = WeightedScoringStrategy()


# ---------------------------------------------------------------------------
# Matcher — orchestrates eligibility -> scoring -> top N
# ---------------------------------------------------------------------------


def _rank_key(scored_product: ScoredProduct) -> tuple[int, float, float]:
    """Bias override: any bank with recent_borrowers_processed data outranks
    every bank without it, full stop — not "worth 25% of the decision" like
    the other factors, an actual override. Sorting is by this 3-part key,
    descending:
      1. has bias data at all? (1 beats 0) — the override itself.
      2. recent_borrowers_processed, higher first — tie-break BETWEEN bias
         banks (see WeightedScoringStrategy's docstring for why this lives
         here and not in the score formula).
      3. the ordinary rate/headroom/tier score — tie-break within each group;
         it's what decides ordering among the no-bias banks entirely, since
         they all share the same (0, 0.0) prefix.
    """
    recent_borrowers_raw = get_fact(scored_product.product, "recent_borrowers_processed")
    has_bias = recent_borrowers_raw is not None
    bias_value = float(recent_borrowers_raw) if has_bias else 0.0
    return (1 if has_bias else 0, bias_value, scored_product.score)


def find_top_products(
    profile: BorrowerProfile,
    products: list[HomeLoanProduct],
    attributes_by_key: dict[str, AttributeDef],
    *,
    scoring: ScoringStrategy | None = None,
    top_n: int = 3,
) -> list[ScoredProduct]:
    active_scoring = scoring if scoring is not None else DEFAULT_SCORING

    eligible = filter_eligible(profile, products, attributes_by_key)
    scored = [
        ScoredProduct(product=product, score=score, reasons=reasons)
        for product in eligible
        for score, reasons in [active_scoring.score(profile, product)]
    ]
    scored.sort(key=_rank_key, reverse=True)
    return scored[:top_n]
