"""Adds two new facts per bank — FOIR% and max tenure — to every product that
bank already has in Lender_Matching. Placeholder numbers, invented the same
way the original Birbal dataset's numbers were: realistic-for-the-lender-type,
not real client data. Replace with real numbers once the client sends them.

Run with: python -m app.add_foir_tenure_data
Safe to re-run — updates existing fact rows instead of duplicating them.
"""

import asyncio
import os
import urllib.parse

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import AttributeModel, BankModel, EligibilityRuleModel, HomeLoanProductModel

ATTRIBUTE_CATALOG = [
    {"key": "foir_pct", "label": "FOIR (%)", "category": "Affordability", "data_type": "number"},
    {"key": "max_tenure_years", "label": "Maximum tenure (years)", "category": "Affordability", "data_type": "number"},
]

# bank name -> (FOIR%, max tenure in years). Placeholder values — no two
# banks share an identical pair on purpose, so a demo run shows real
# variation between banks instead of repeating the same numbers.
# NOTE: kept here for reference only — the live values now live in Supabase,
# not this database. See update_foir_tenure_supabase.py (scratchpad) for the
# script that actually applied these.
FOIR_TENURE_DATA = {
    "State Bank Of India": (58, 30),
    "Canara Bank": (52, 28),
    "Bank Of Baroda": (55, 30),
    "Bank Of India": (50, 25),
    "Indian Overseas Bank": (48, 28),
    "Central Bank of India": (51, 27),
    "Punjab National Bank": (54, 30),
    "ICICI Bank Ltd": (62, 30),
    "HDFC Bank Ltd": (60, 28),
    "Karur Vysya Bank Ltd": (47, 22),
    "Kotak Mahindra Bank Ltd": (56, 25),
    "DCB Bank": (49, 24),
    "Repco Home Finance Limited": (55, 18),
    "Bajaj Housing Finance Ltd": (65, 30),
    "Tata Capital Ltd": (61, 26),
    "Incred Finance Ltd": (58, 18),
    "Home First Finance Company India Ltd": (57, 20),
    "Chola Mandelam Ltd": (59, 22),
    "Piramal Finance Ltd": (53, 19),
    "Bajaj Finserv": (67, 27),
    "Sundaram finance Ltd": (52, 21),
    "Fin Care Financial Services Ltd": (63, 16),
    "Muthoot Housing Finance Ltd": (57, 20),
}


def _lender_matching_engine():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    user = os.environ["POSTGRES_USER"]
    password = urllib.parse.quote(os.environ["POSTGRES_PASSWORD"], safe="")
    db = os.environ["POSTGRES_DB"]
    url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    return create_async_engine(url, echo=False, connect_args={"statement_cache_size": 0})


async def load() -> None:
    engine = _lender_matching_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        attributes = {a.key: a for a in (await session.execute(select(AttributeModel))).scalars().all()}
        for attr in ATTRIBUTE_CATALOG:
            if attr["key"] not in attributes:
                model = AttributeModel(
                    key=attr["key"], label=attr["label"], category=attr["category"], data_type=attr["data_type"]
                )
                session.add(model)
                attributes[attr["key"]] = model
        await session.flush()

        banks = (await session.execute(select(BankModel))).scalars().all()
        products_by_bank_id = {}
        for bank in banks:
            products = (
                (await session.execute(select(HomeLoanProductModel).where(HomeLoanProductModel.bank_id == bank.id)))
                .scalars()
                .all()
            )
            products_by_bank_id[bank.id] = products

        updated = 0
        created = 0
        skipped_banks = []
        for bank in banks:
            if bank.name not in FOIR_TENURE_DATA:
                skipped_banks.append(bank.name)
                continue
            foir_pct, max_tenure = FOIR_TENURE_DATA[bank.name]
            for product in products_by_bank_id[bank.id]:
                existing_rules = {
                    r.attribute_id: r
                    for r in (
                        await session.execute(
                            select(EligibilityRuleModel).where(EligibilityRuleModel.product_id == product.id)
                        )
                    )
                    .scalars()
                    .all()
                }
                for key, value in (("foir_pct", foir_pct), ("max_tenure_years", max_tenure)):
                    attr_id = attributes[key].id
                    if attr_id in existing_rules:
                        existing_rules[attr_id].value = str(value)
                        updated += 1
                    else:
                        session.add(
                            EligibilityRuleModel(
                                product_id=product.id, attribute_id=attr_id, operator="fact", value=str(value)
                            )
                        )
                        created += 1

        await session.commit()
        print(f"FOIR/tenure facts: {created} created, {updated} updated.")
        if skipped_banks:
            print(f"No FOIR/tenure data for: {skipped_banks}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load())
