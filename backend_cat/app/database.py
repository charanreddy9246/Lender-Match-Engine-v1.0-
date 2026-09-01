"""Everything database: the connection, the tables, and table creation.

Table shape: Bank -> HomeLoanProduct -> EligibilityRule, with EligibilityRule rows
pointing at an AttributeModel entry instead of hardcoding one column per criterion.

Why: the old shape had one fixed column per criterion (min_cibil_score,
required_documents, ...), so a brand new criterion type meant a schema migration
and new application code. Under this shape, adding a new criterion is a data
change — one new row in `attributes`, then one `eligibility_rules` row per
product that needs it. No migration, no code change.

- AttributeModel is the small, rarely-changing catalog of possible criteria
  (what they're called, what category they belong to, what kind of value they
  hold).
- EligibilityRuleModel is the large, frequently-edited table of actual facts:
  "this product needs this attribute to satisfy this operator against this
  value." This is the table an admin screen would add/edit/delete rows in.
  (Real data did end up needing rules scoped by employment type — see
  app/load_birbal_dataset.py — handled the same way app/domain.py already
  recommends: a bank whose criteria genuinely differ by employment type
  becomes several HomeLoanProductModel rows, one per employment type, rather
  than a scoping column on one product's rules.)

Loaded from the Birbal reference lender dataset — see app/load_birbal_dataset.py.
"""

from collections.abc import AsyncIterator

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # Supabase's connection pooler runs in transaction mode, which doesn't support
    # asyncpg's server-side prepared statement caching — without this, repeated
    # queries error with "prepared statement already exists".
    connect_args={"statement_cache_size": 0},
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


class Base(DeclarativeBase):
    pass


class BankModel(Base):
    """`source` marks where a bank row came from, so a bulk reload of one
    source (see app/load_birbal_dataset.py) can safely wipe-and-replace only
    its own rows without touching banks that came from somewhere else — e.g.
    the hand-added calibration banks from app/seed_calibration_banks.py.
    Without this, "reload the lender file" and "hand-added banks" can't
    coexist: a full-table wipe can't tell the two apart.
    """

    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    # one of: "excel_import" (app/load_birbal_dataset.py), "manual_calibration"
    # (app/seed_calibration_banks.py) — free text, not an enum, since the set
    # of sources is expected to grow as new loaders are added.
    source: Mapped[str] = mapped_column(String(40), default="excel_import", server_default="excel_import")

    products: Mapped[list["HomeLoanProductModel"]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )


class HomeLoanProductModel(Base):
    """Pricing/amount/tier info (interest rate, fee, loan amount range, approval
    tier) used to live here as fixed columns — the exact same "need a developer
    for every new field" problem the whole rest of this schema was designed to
    avoid, just one table over. Fixed now: those live as ordinary rows in
    `rules`, using the `fact` operator (see EligibilityRuleModel) instead of a
    dedicated column each. Adding "tenure" tomorrow is a new attribute + fact
    rows, not a migration.
    """

    __tablename__ = "home_loan_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"))
    product_name: Mapped[str] = mapped_column(String(120))

    bank: Mapped["BankModel"] = relationship(back_populates="products")
    rules: Mapped[list["EligibilityRuleModel"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class AttributeModel(Base):
    """The catalog of possible criteria. Small, admin-managed, rarely changes.

    Examples: key="min_cibil_score" category="Credit" data_type="number";
    key="property_type_semi_urban" category="Property" data_type="boolean";
    key="document_bank_statement" category="Documents" data_type="boolean".
    """

    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60))
    # one of: "number", "boolean", "text"
    data_type: Mapped[str] = mapped_column(String(20))

    rules: Mapped[list["EligibilityRuleModel"]] = relationship(back_populates="attribute")


class EligibilityRuleModel(Base):
    """One row = one fact about a product. Most rows are eligibility conditions:
    "this product needs this attribute to satisfy this operator against this
    value" — checked against a borrower's answer. Rows with operator="fact" are
    different: not a condition to check, just a stored value (interest rate,
    tenure, ...) for display/scoring — see domain.py's filter_eligible and
    WeightedScoringStrategy for how the two are told apart.

    Either way, this is the table that grows constantly and is where an admin
    screen would add/edit/delete rows — no other file needs to change when a
    rule or a fact is added, changed, or removed.
    """

    __tablename__ = "eligibility_rules"
    __table_args__ = (UniqueConstraint("product_id", "attribute_id", name="uq_rule_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("home_loan_products.id"))
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"))
    # one of: ">=", "<=", "==", "required", "in", "fact", "any_of", "between" (see domain.py's RuleOperator)
    operator: Mapped[str] = mapped_column(String(10))
    # always stored as text; parsed according to the attribute's data_type
    value: Mapped[str] = mapped_column(String(255))

    product: Mapped["HomeLoanProductModel"] = relationship(back_populates="rules")
    attribute: Mapped["AttributeModel"] = relationship(back_populates="rules")


class BankBiasFactModel(Base):
    """A bank's relationship/priority signal with us — e.g. how many borrowers
    we've recently placed with them — separate from anything a lender data file
    provides. Same "generic fact, not a dedicated column" idea as
    EligibilityRuleModel: a new bias signal is a new row with a new
    `metric_key`, never a schema or code change.

    Deliberately keyed by `bank_name` (a plain string) instead of a foreign key
    to `banks.id`. app/load_birbal_dataset.py deletes and recreates every bank
    row (with new IDs) each time it loads a lender file — a real foreign key
    here would either break on that reload (rows pointing at deleted banks) or
    force this table to be wiped and re-entered every time lender data
    refreshes. Bias data changes on its own schedule, not the lender file's, so
    it's matched by name at query time instead (see repository.py) and survives
    lender-data reloads untouched.
    """

    __tablename__ = "bank_bias_facts"
    __table_args__ = (UniqueConstraint("bank_name", "metric_key", name="uq_bank_bias_metric"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_name: Mapped[str] = mapped_column(String(120))
    metric_key: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(255))


async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
