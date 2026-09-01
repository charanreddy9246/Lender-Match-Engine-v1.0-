"""Daily job: pulls home loan interest rates from ambak.com and updates the
"interest_rate_pct" fact on any of our banks it can match, only writing a
change when the scraped number actually differs from what's stored.

IMPORTANT CONTEXT — read before touching this file: ambak.com's own Terms &
Conditions (Section 7.2) prohibit reproducing/copying platform data for
commercial use without their written consent, and Birbal Club is a
commercial product in the same space as Ambak. This script exists anyway at
the explicit, informed request of the project owner as a temporary measure,
who was shown that exact clause and chose to proceed pending an internal
discussion — see the conversation this was built from. If that decision
changes, disable the "BirbalClub-ScrapeAmbakRates" Windows Scheduled Task
rather than deleting this file outright.

Matching bank names: Ambak's displayed names don't always match ours
exactly (e.g. we store "HDFC Bank Ltd", Ambak shows "HDFC Bank"; we store
"Kotak Mahindra Bank Ltd", Ambak shows "Kotak Bank"). NAME_ALIASES below
covers the handful that don't resolve through simple normalization (strip
common suffixes, lowercase, collapse whitespace). Six of our current banks
(see UNMATCHABLE_BANKS) simply aren't on Ambak's list at all — no alias can
fix that, so they're just skipped and logged, not treated as an error.

This always re-reads the *current* list of banks from the database (not a
hardcoded list), so a bank added to the database later is automatically
picked up on the next run without any code change here.

Banks with no Ambak match at all (including future ones — not just the
current UNMATCHABLE_BANKS) get their "interest_rate_is_estimated" fact set
to true, whatever rate happens to already be stored for them — since it
can't be verified against a live source, the UI should show it as an
estimate, not present it as confirmed.
"""

import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AttributeModel, BankModel, EligibilityRuleModel, HomeLoanProductModel, async_session_factory

logger = logging.getLogger("scrape_ambak_rates")

AMBAK_URL = "https://ambak.com/home-loans/interestrates"
PAGE_COUNT = 7  # matches ambak.com's own pagination ("76 Banks Found" across 7 pages) as of 2026-08

# Suffixes stripped from both sides before comparing names — differences
# like "Ltd" vs no suffix shouldn't count as a real mismatch.
_SUFFIXES = [" ltd", " limited", " pvt ltd", " private limited", " co", " company", " finance ltd"]

# Bank names that don't resolve through normalization alone — see the module
# docstring. Keyed by our database's bank name, valued by Ambak's own text.
NAME_ALIASES: dict[str, str] = {
    "Kotak Mahindra Bank Ltd": "Kotak Bank",
    "Chola Mandelam Ltd": "Cholamandalam Finance",
    "Sundaram finance Ltd": "Sundaram Home Finance",
    # Fincare merged into AU Small Finance Bank in 2024 — same institution now.
    "Fin Care Financial Services Ltd": "AU Small Finance Bank",
}

# Common short names for banks/HFCs in this space, mapped to the full name
# they'd normally be stored/shown under — tried after a normalized exact
# match fails, before giving up. This is deliberately a plain lookup table,
# not fuzzy/approximate text matching: a wrong guess here would mean showing
# someone the wrong bank's interest rate, so anything not covered by an
# exact known abbreviation still falls through to "unmatched" rather than
# risk a mismatch. Extend this list as new short-name banks come up — it's
# checked for every bank on every run, not a one-time fix.
COMMON_ABBREVIATIONS: dict[str, str] = {
    "sbi": "state bank of india",
    "pnb": "punjab national bank",
    "bob": "bank of baroda",
    "boi": "bank of india",
    "iob": "indian overseas bank",
    "hdfc": "hdfc bank",
    "icici": "icici bank",
    "kvb": "karur vysya bank",
    "idbi": "idbi bank",
    "uco": "uco bank",
    "rbl": "rbl bank",
    "idfc": "idfc first bank",
    "au sfb": "au small finance bank",
    "lichfl": "lic housing finance",
    "pnb hfl": "pnb housing finance",
    "l&t": "l&t housing finance",
    "iifl": "iifl finance",
}

# Confirmed absent from Ambak's 76-lender list as of 2026-08 — listed here so
# a run that finds nothing for them is understood as expected, not a bug.
UNMATCHABLE_BANKS = {
    "Repco Home Finance Limited",
    "Tata Capital Ltd",
    "Incred Finance Ltd",
    "Home First Finance Company India Ltd",
    "Bajaj Finserv",
    "Muthoot Housing Finance Ltd",
}


def _normalize(name: str) -> str:
    n = name.strip().lower()
    for suffix in _SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return re.sub(r"\s+", " ", n)


@dataclass(frozen=True)
class ScrapedRate:
    name: str
    rate_pct: float


def _parse_cards(body_text: str) -> list[ScrapedRate]:
    """Ambak's lender cards render as plain stacked text lines (no stable
    CSS classes to hook a selector on), so this parses the rendered text
    directly: each card is a run of lines ending in the literal "Apply Now"
    button label, with the lender's name as the block's first line and the
    rate as the first "N%"-shaped line after the literal "ROI" label.
    """
    lines = [ln.strip() for ln in body_text.split("\n")]
    try:
        start = lines.index("Special Offers") + 1
    except ValueError:
        start = 0

    results: list[ScrapedRate] = []
    block_start = start
    for idx in range(start, len(lines)):
        if lines[idx] != "Apply Now":
            continue
        block = lines[block_start:idx]
        name = next((b for b in block if b), None)
        rate = None
        if "ROI" in block:
            roi_pos = block.index("ROI")
            for b in block[roi_pos + 1 :]:
                if b:
                    m = re.match(r"([\d.]+)%", b)
                    if m:
                        rate = float(m.group(1))
                    break
        if name and rate is not None:
            results.append(ScrapedRate(name=name, rate_pct=rate))
        block_start = idx + 1
    return results


async def scrape_ambak_rates() -> dict[str, float]:
    """Returns {lender_name_as_shown_on_ambak: rate_pct} for every lender
    found across all of Ambak's pages. Raises if the page structure has
    changed enough that nothing could be parsed at all, so a broken scraper
    fails loudly instead of silently reporting zero rates.
    """
    all_rates: dict[str, float] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(AMBAK_URL, wait_until="networkidle", timeout=30_000)
            await page.wait_for_timeout(1500)

            for page_num in range(1, PAGE_COUNT + 1):
                text = await page.inner_text("body")
                for card in _parse_cards(text):
                    all_rates[card.name] = card.rate_pct

                if page_num < PAGE_COUNT:
                    next_label = str(page_num + 1)
                    btn = page.get_by_role("button", name=next_label, exact=True)
                    if await btn.count() == 0:
                        btn = page.locator(f"text='{next_label}'").first
                    await btn.click()
                    await page.wait_for_timeout(1500)
        finally:
            await browser.close()

    if not all_rates:
        raise RuntimeError("Parsed zero lenders from ambak.com — the page structure likely changed.")
    return all_rates


def _match_rate(bank_name: str, scraped: dict[str, float]) -> float | None:
    alias = NAME_ALIASES.get(bank_name)
    if alias is not None:
        return scraped.get(alias)

    target = _normalize(bank_name)
    for scraped_name, rate in scraped.items():
        if _normalize(scraped_name) == target:
            return rate

    # Not a suffix/case difference — try expanding a known short name (e.g.
    # "SBI" -> "state bank of india") and matching *that* instead. Only exact
    # known abbreviations, never approximate/fuzzy text matching — see
    # COMMON_ABBREVIATIONS' comment for why.
    expanded = COMMON_ABBREVIATIONS.get(target)
    if expanded is not None:
        for scraped_name, rate in scraped.items():
            if _normalize(scraped_name) == expanded:
                return rate

    return None


async def update_rates_from_ambak() -> None:
    scraped = await scrape_ambak_rates()
    logger.info("Scraped %d lenders from ambak.com", len(scraped))

    async with async_session_factory() as session:
        rate_attr = (
            await session.execute(select(AttributeModel).where(AttributeModel.key == "interest_rate_pct"))
        ).scalar_one()
        estimated_attr = (
            await session.execute(select(AttributeModel).where(AttributeModel.key == "interest_rate_is_estimated"))
        ).scalar_one()

        banks = (
            (
                await session.execute(
                    select(BankModel).options(
                        selectinload(BankModel.products).selectinload(HomeLoanProductModel.rules)
                    )
                )
            )
            .scalars()
            .all()
        )

        updated, unchanged, unmatched = [], [], []
        for bank in banks:
            new_rate = _match_rate(bank.name, scraped)
            if new_rate is None:
                if bank.name not in UNMATCHABLE_BANKS:
                    logger.warning("No Ambak match found for %r (not in the known-absent list either)", bank.name)
                unmatched.append(bank.name)

                # A bank we can't verify against Ambak has no live-confirmed
                # rate, whatever number happens to be stored for it — flag it
                # as an estimate so the UI shows that clearly, rather than
                # only doing this for banks with literally no number at all.
                for product in bank.products:
                    existing_estimated_rule = next(
                        (r for r in product.rules if r.attribute_id == estimated_attr.id), None
                    )
                    if existing_estimated_rule:
                        existing_estimated_rule.value = "true"
                    else:
                        session.add(
                            EligibilityRuleModel(
                                product_id=product.id, attribute_id=estimated_attr.id, operator="fact", value="true"
                            )
                        )
                continue

            bank_changed = False
            for product in bank.products:
                existing_rate_rule = next(
                    (r for r in product.rules if r.attribute_id == rate_attr.id), None
                )
                existing_val = float(existing_rate_rule.value) if existing_rate_rule else None

                if existing_val is not None and abs(existing_val - new_rate) < 1e-9:
                    continue  # unchanged — leave as is, per the "only touch what actually varies" requirement

                bank_changed = True
                if existing_rate_rule:
                    existing_rate_rule.value = str(new_rate)
                else:
                    session.add(
                        EligibilityRuleModel(
                            product_id=product.id, attribute_id=rate_attr.id, operator="fact", value=str(new_rate)
                        )
                    )

                # A rate we just pulled live from Ambak is no longer an estimate.
                existing_estimated_rule = next(
                    (r for r in product.rules if r.attribute_id == estimated_attr.id), None
                )
                if existing_estimated_rule and existing_estimated_rule.value == "true":
                    existing_estimated_rule.value = "false"

            (updated if bank_changed else unchanged).append((bank.name, new_rate))

        await session.commit()

    logger.info("Changed (%d): %s", len(updated), updated)
    logger.info("Unchanged, already matched Ambak (%d): %s", len(unchanged), unchanged)
    logger.info("Unmatched (%d): %s", len(unmatched), unmatched)


LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "scrape_ambak.log"


def main() -> None:
    # Writes its own log file directly (rather than relying on shell
    # redirection, e.g. "python ... >> log.txt") because the Windows
    # Scheduled Task that runs this daily executes in a context where
    # cmd.exe/PowerShell redirection was unreliable in testing — a
    # FileHandler here works regardless of how or by what the process was
    # launched.
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    asyncio.run(update_rates_from_ambak())


if __name__ == "__main__":
    sys.exit(main())
