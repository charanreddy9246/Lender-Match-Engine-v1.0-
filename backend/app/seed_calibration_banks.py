"""Adds real banks, observed from the live birbal.club reference site, into the
local database — so giving the same input locally produces the same lenders it
returns in production. This is calibration data (one real, observed example
per bank), not a full replica of that bank's actual policy — see the caveats
below.

Uses the exact same attributes/eligibility_rules schema as
app/load_birbal_dataset.py, since these banks need to actually compete in
matching, not just sit in a side table (contrast with app/seed_bank_bias.py,
which deliberately doesn't touch this schema).

Caveat #1 — thresholds are a best guess, not real policy. The live site was
only observed for ONE profile per bank (Salaried, CIBIL 780, loan 50L, salary
60k, standard urban property, salary slip + bank statement). The eligibility
bands below (CIBIL, loan range, salary, documents, property) are set generous
enough to guarantee that ONE known profile matches and produces the observed
rate — they are not derived from each bank's real underlying policy, since we
don't have it. Test more profiles on the live site and feed the results back
into CALIBRATION_BANKS to tighten this over time.

Caveat #2 — only "Salaried" is covered here, since that's the only employment
type actually observed for these banks. Add more `employment_types` entries
once verified against the live site for Self-employed/Professional/Pensioner.

These banks are tagged source="manual_calibration" (see BankModel's docstring
in database.py) specifically so that re-running app/load_birbal_dataset.py —
which only wipes source="excel_import" rows — never touches them.

Run with: python -m app.seed_calibration_banks
Safe to re-run — replaces just these banks' own rows, leaves everything else untouched.
"""

import asyncio

from sqlalchemy import delete, select

from app.database import (
    AttributeModel,
    BankModel,
    EligibilityRuleModel,
    HomeLoanProductModel,
    async_session_factory,
    create_all_tables,
)

# One real, observed example per bank — see the module docstring for what
# "observed" means and its limits.
CALIBRATION_BANKS = [
    {
        "bank_name": "HDFC Bank",
        "lender_type": "Private Bank",
        "min_cibil": 700,
        "max_cibil": 900,
        "min_loan_amount": 300_000,
        "max_loan_amount": 100_000_000,
        "employment_types": ["salaried"],
        "min_net_monthly_salary": 25_000,
        "documents_accepted": ["salary_slip", "itr_form16", "bank_statement"],
        "property_types": ["standard_urban", "semi_urban_village", "under_construction", "others"],
        "interest_rate_pct": 7.25,
        "interest_rate_range": "7.25%-9.50%",
        "processing_fee": "0.50% of loan amount",
    },
    {
        "bank_name": "Central Bank of India",
        "lender_type": "Public Sector Bank",
        "min_cibil": 700,
        "max_cibil": 900,
        "min_loan_amount": 300_000,
        "max_loan_amount": 100_000_000,
        "employment_types": ["salaried"],
        "min_net_monthly_salary": 25_000,
        "documents_accepted": ["salary_slip", "itr_form16", "bank_statement"],
        "property_types": ["standard_urban", "semi_urban_village", "under_construction", "others"],
        "interest_rate_pct": 7.25,
        "interest_rate_range": "7.25%-9.60%",
        "processing_fee": "0.35% of loan amount",
    },
    {
        "bank_name": "Bank of India",
        "lender_type": "Public Sector Bank",
        "min_cibil": 700,
        "max_cibil": 900,
        "min_loan_amount": 300_000,
        "max_loan_amount": 100_000_000,
        "employment_types": ["salaried"],
        "min_net_monthly_salary": 25_000,
        "documents_accepted": ["salary_slip", "itr_form16", "bank_statement"],
        "property_types": ["standard_urban", "semi_urban_village", "under_construction", "others"],
        "interest_rate_pct": 7.30,
        "interest_rate_range": "7.30%-9.55%",
        "processing_fee": "0.35% of loan amount",
    },
]


async def seed() -> None:
    await create_all_tables()

    async with async_session_factory() as session:
        attr_rows = (await session.execute(select(AttributeModel))).scalars().all()
        attributes = {a.key: a for a in attr_rows}
        missing = {
            "cibil_score",
            "employment_type",
            "net_monthly_salary",
            "property_type",
            "documents_any_of",
            "min_loan_amount",
            "max_loan_amount",
            "interest_rate_pct",
            "interest_rate_range",
            "processing_fee",
            "lender_type",
        } - attributes.keys()
        if missing:
            raise RuntimeError(
                f"Missing attributes {missing} — run `python -m app.load_birbal_dataset <xlsx>` first "
                "so the shared attribute catalog exists."
            )

        for entry in CALIBRATION_BANKS:
            existing_bank = (
                await session.execute(select(BankModel).where(BankModel.name == entry["bank_name"]))
            ).scalar_one_or_none()
            if existing_bank is not None:
                await session.execute(delete(HomeLoanProductModel).where(HomeLoanProductModel.bank_id == existing_bank.id))
                bank = existing_bank
            else:
                # source="manual_calibration" — see BankModel's docstring:
                # this tag is what protects these banks from being wiped the
                # next time app/load_birbal_dataset.py reloads its own data.
                bank = BankModel(name=entry["bank_name"], source="manual_calibration")
                session.add(bank)
                await session.flush()

            for emp_type in entry["employment_types"]:
                product = HomeLoanProductModel(bank_id=bank.id, product_name="Home Loan — Salaried")
                session.add(product)
                await session.flush()

                rules = [
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["cibil_score"].id,
                        operator="between",
                        value=f"{entry['min_cibil']},{entry['max_cibil']}",
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["employment_type"].id,
                        operator="==",
                        value=emp_type,
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["net_monthly_salary"].id,
                        operator=">=",
                        value=str(entry["min_net_monthly_salary"]),
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["property_type"].id,
                        operator="in",
                        value=",".join(entry["property_types"]),
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["documents_any_of"].id,
                        operator="any_of",
                        value=",".join(entry["documents_accepted"]),
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["min_loan_amount"].id,
                        operator="fact",
                        value=str(entry["min_loan_amount"]),
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["max_loan_amount"].id,
                        operator="fact",
                        value=str(entry["max_loan_amount"]),
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["interest_rate_pct"].id,
                        operator="fact",
                        value=str(entry["interest_rate_pct"]),
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["interest_rate_range"].id,
                        operator="fact",
                        value=entry["interest_rate_range"],
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["processing_fee"].id,
                        operator="fact",
                        value=entry["processing_fee"],
                    ),
                    EligibilityRuleModel(
                        product_id=product.id,
                        attribute_id=attributes["lender_type"].id,
                        operator="fact",
                        value=entry["lender_type"],
                    ),
                ]
                session.add_all(rules)

        await session.commit()
        print(f"Calibration banks on file: {len(CALIBRATION_BANKS)}")


if __name__ == "__main__":
    asyncio.run(seed())
