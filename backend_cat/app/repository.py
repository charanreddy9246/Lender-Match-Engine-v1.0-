"""Where lender data comes from: PostgreSQL, loaded from the Birbal reference lender
dataset (see app/load_birbal_dataset.py).

LenderRepository is the interface the rest of the app relies on. SqlLenderRepository
is the only implementation — if the data source ever changes again, it still loads
through this same class, so nothing else in the app needs to change.

Also exposes the attribute catalog (`get_attributes`) — the matching engine needs
each rule's data_type (number/boolean/text) to know how to compare it, and that
lives on AttributeModel, not on the rule itself.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AttributeModel, BankBiasFactModel, EligibilityRuleModel, HomeLoanProductModel
from app.domain import AttributeDef, EligibilityRuleDef, HomeLoanProduct


class LenderRepository(Protocol):
    async def list_products(self) -> list[HomeLoanProduct]: ...
    async def get_attributes(self) -> dict[str, AttributeDef]: ...


class SqlLenderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_products(self) -> list[HomeLoanProduct]:
        stmt = select(HomeLoanProductModel).options(
            selectinload(HomeLoanProductModel.bank),
            selectinload(HomeLoanProductModel.rules).selectinload(EligibilityRuleModel.attribute),
        )
        result = await self._session.execute(stmt)
        products = result.scalars().all()

        bias_by_bank_name = await self._bias_facts_by_bank_name()
        return [self._to_domain(row, bias_by_bank_name.get(row.bank.name, [])) for row in products]

    async def get_attributes(self) -> dict[str, AttributeDef]:
        stmt = select(AttributeModel)
        result = await self._session.execute(stmt)
        return {
            row.key: AttributeDef(key=row.key, label=row.label, category=row.category, data_type=row.data_type)
            for row in result.scalars().all()
        }

    async def _bias_facts_by_bank_name(self) -> dict[str, list[BankBiasFactModel]]:
        # bank_bias_facts is matched by name, not by home_loan_products' bank_id
        # FK — see BankBiasFactModel's docstring for why. This table is small
        # (one row per bank per bias metric), so fetching it whole and grouping
        # in Python is simpler than a join per product.
        result = await self._session.execute(select(BankBiasFactModel))
        by_name: dict[str, list[BankBiasFactModel]] = {}
        for fact in result.scalars().all():
            by_name.setdefault(fact.bank_name, []).append(fact)
        return by_name

    @staticmethod
    def _to_domain(row: HomeLoanProductModel, bias_facts: list[BankBiasFactModel]) -> HomeLoanProduct:
        rules = [
            EligibilityRuleDef(attribute_key=rule.attribute.key, operator=rule.operator, value=rule.value)
            for rule in row.rules
        ]
        # Bias facts merge in as ordinary "fact" rules, indistinguishable to
        # domain.py from pricing facts loaded straight off the product — the
        # scoring engine doesn't need to know these came from a different table.
        bias_rules = [
            EligibilityRuleDef(attribute_key=fact.metric_key, operator="fact", value=fact.value)
            for fact in bias_facts
        ]
        return HomeLoanProduct(
            id=row.id, bank_name=row.bank.name, product_name=row.product_name, rules=[*rules, *bias_rules]
        )
