"""Seeds fake-but-illustrative lender relationship/priority data — "how many
borrowers have we recently placed with this bank, and what's the relationship
like" — into bank_bias_facts. See that model's docstring in database.py for why
this is a separate table, matched by bank name, independent of the main lender
loader (app/load_birbal_dataset.py).

This is placeholder data standing in for a real "recent placements" feed, the
same way app/load_birbal_dataset.py's old fake-seed predecessor stood in for
real lender data before that existed. The bank names below are real rows from
the currently-loaded dataset (fictional lenders, per that file's own README —
not real institutions) — swap in real relationship data whenever it exists,
same table, no code change needed.

Run with: python -m app.seed_bank_bias
Safe to re-run — upserts by (bank_name, metric_key), never duplicates rows.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database import BankBiasFactModel, async_session_factory, create_all_tables

# (bank_name, recent_borrowers_processed, relationship_note) — a mix of high,
# low, and zero activity, and a mix of lender types, to make the effect on
# ranking visible across different kinds of profiles.
BANK_BIAS_DATA: list[tuple[str, int, str]] = [
    # The 3 real, hand-calibrated banks (app/seed_calibration_banks.py) get
    # bias numbers too, deliberately higher than every fake test bank below —
    # so the bias override treats them the same as everyone else (no special
    # case in the code), while still preserving their real observed order
    # (HDFC > Central Bank of India > Bank of India) as the tie-break.
    ("HDFC Bank", 15, "Our top real-world partner — consistently fast, reliable turnarounds."),
    ("Central Bank of India", 14, "Strong real-world partner, close second to HDFC on volume."),
    ("Bank of India", 13, "Solid real-world partner, steady placement volume."),
    ("Kendra Sahakari Bank", 8, "Strong repeat partner — fast turnarounds on every referral so far."),
    ("Ganga Sagar Bank", 3, "Steady partner, a handful of borrowers placed recently."),
    ("Northstar Bank", 5, "Reliable mid-tier partner, consistent approvals."),
    ("Nivara Housing Finance", 0, "New relationship — no borrowers placed with them yet."),
    ("CreditNova NBFC", 10, "Our most active NBFC partner this quarter."),
    ("QuickFund NBFC", 1, "Just one placement so far, still building trust."),
    ("Falcon Private Bank", 6, "Good track record, slightly slower disbursal than top partners."),
]


async def seed() -> None:
    await create_all_tables()

    async with async_session_factory() as session:
        for bank_name, recent_count, note in BANK_BIAS_DATA:
            for metric_key, value in (
                ("recent_borrowers_processed", str(recent_count)),
                ("relationship_note", note),
            ):
                stmt = (
                    insert(BankBiasFactModel)
                    .values(bank_name=bank_name, metric_key=metric_key, value=value)
                    .on_conflict_do_update(
                        index_elements=["bank_name", "metric_key"],
                        set_={"value": value},
                    )
                )
                await session.execute(stmt)
        await session.commit()

        total = (await session.execute(select(BankBiasFactModel))).scalars().all()
        print(f"Bias facts now on file: {len(total)} rows across {len(BANK_BIAS_DATA)} banks.")


if __name__ == "__main__":
    asyncio.run(seed())
