"""Standalone terminal tool: asks the same questions birbal.club/find-best-lender
asks (CIBIL, loan amount, employment type, the income question that matches it,
documents, property type), then shows which real lenders match, straight from
the database.

No web server, no UI — just a quick way to try real customer profiles by hand.

Run with: python -m app.terminal_match
"""

import asyncio

from app.database import async_session_factory
from app.domain import BorrowerProfile, find_top_products, get_fact
from app.repository import SqlLenderRepository

EMPLOYMENT_TYPES = ["Salaried", "Self-employed", "Professional", "Pensioner"]
PROPERTY_TYPES = ["Standard urban property", "Semi-urban village", "Under construction", "Others"]
PROPERTY_TYPE_MAP = {
    "Standard urban property": "standard_urban",
    "Semi-urban village": "semi_urban_village",
    "Under construction": "under_construction",
    "Others": "others",
}
EMPLOYMENT_TYPE_MAP = {
    "Salaried": "salaried",
    "Self-employed": "self_employed",
    "Professional": "professional",
    "Pensioner": "pensioner",
}
# Which income question to ask, and which answer key it becomes, per employment
# type — same mapping app/load_birbal_dataset.py uses to decide which rule
# applies (see INCOME_BY_EMPLOYMENT_TYPE there).
INCOME_QUESTION_BY_EMPLOYMENT_TYPE = {
    "salaried": ("Net monthly salary", "net_monthly_salary"),
    "self_employed": ("Annual business turnover", "annual_turnover"),
    "professional": ("Annual gross receipts", "annual_gross_receipts"),
    "pensioner": ("Monthly pension", "monthly_pension"),
}
DOCUMENT_OPTIONS = [
    ("ITR / Form 16", "itr_form16"),
    ("ITR", "itr"),
    ("Salary slip", "salary_slip"),
    ("Cash income", "cash_income"),
    ("GST", "gst"),
    ("Business proof", "business_proof"),
    ("Pension proof", "pension_proof"),
]


def ask_number(label: str) -> str:
    while True:
        raw = input(f"{label}: ").strip().replace(",", "")
        if raw.isdigit():
            return raw
        print("Enter a whole number, e.g. 50000")


def ask_choice(label: str, options: list[str]) -> str:
    print(f"\n{label}")
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    while True:
        choice = input("Enter a number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Not a valid option, try again.")


def ask_yes_no(label: str) -> bool:
    while True:
        choice = input(f"{label} (y/n): ").strip().lower()
        if choice in ("y", "yes"):
            return True
        if choice in ("n", "no"):
            return False
        print("Enter y or n.")


def ask_documents() -> dict[str, str]:
    print("\nDocuments you can provide (beyond bank statement, which is always required)")
    print("Enter the numbers, comma-separated (e.g. 1,3), or leave blank for none:")
    for i, (label, _key) in enumerate(DOCUMENT_OPTIONS, start=1):
        print(f"  {i}. {label}")
    raw = input("Documents: ").strip()
    answers: dict[str, str] = {"document_bank_statement": "true"}
    if not raw:
        return answers
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(DOCUMENT_OPTIONS):
            _label, key = DOCUMENT_OPTIONS[int(part) - 1]
            answers[f"document_{key}"] = "true"
    return answers


async def main():
    print("Answer a few quick questions to find matching lenders.\n")

    cibil_score = ask_number("CIBIL score")
    loan_amount_required = int(ask_number("Loan amount required (INR)"))
    employment_display = ask_choice("Employment type", EMPLOYMENT_TYPES)
    employment_type = EMPLOYMENT_TYPE_MAP[employment_display]

    income_label, income_key = INCOME_QUESTION_BY_EMPLOYMENT_TYPE[employment_type]
    income_value = ask_number(income_label)

    answers = {
        "cibil_score": cibil_score,
        "employment_type": employment_type,
        income_key: income_value,
    }

    has_co_borrower = False
    if employment_type == "pensioner":
        has_co_borrower = ask_yes_no("Do you have a co-borrower?")
    answers["has_co_borrower"] = "true" if has_co_borrower else "false"

    answers.update(ask_documents())

    property_display = ask_choice("Property type", PROPERTY_TYPES)
    answers["property_type"] = PROPERTY_TYPE_MAP[property_display]

    profile = BorrowerProfile(
        employment_type=employment_type, loan_amount_required=loan_amount_required, answers=answers
    )

    async with async_session_factory() as session:
        repo = SqlLenderRepository(session)
        products = await repo.list_products()
        attributes_by_key = await repo.get_attributes()

    top = find_top_products(profile, products, attributes_by_key, top_n=3)

    print(f"\n--- Top {len(top)} matches ---")
    for scored in top:
        rate_range = get_fact(scored.product, "interest_rate_range")
        print(f"  - {scored.product.bank_name} ({scored.product.product_name}) — rate {rate_range}")
    if not top:
        print("  No eligible lenders for this profile.")


if __name__ == "__main__":
    asyncio.run(main())
