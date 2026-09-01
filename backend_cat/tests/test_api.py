"""Integration test for the /api/v1/lenders/match endpoint.

Uses an in-memory repository double instead of a real Postgres connection, so this
runs fast and doesn't need a database — it's still testing the real HTTP path
(routing, validation, response shape), just not the database layer.
"""

from httpx import ASGITransport, AsyncClient

from app.api import get_lender_repository
from app.domain import AttributeDef, HomeLoanProduct
from app.main import app
from tests.test_domain import ATTRIBUTES, FIXTURE_PRODUCTS


class InMemoryLenderRepository:
    def __init__(self, products: list[HomeLoanProduct], attributes: dict[str, AttributeDef]):
        self._products = products
        self._attributes = attributes

    async def list_products(self) -> list[HomeLoanProduct]:
        return self._products

    async def get_attributes(self) -> dict[str, AttributeDef]:
        return self._attributes


app.dependency_overrides[get_lender_repository] = lambda: InMemoryLenderRepository(FIXTURE_PRODUCTS, ATTRIBUTES)

VALID_PROFILE = {
    "cibil_score": 800,
    "loan_amount_required": 1_000_000,
    "employment_type": "salaried",
    "net_monthly_salary": 60_000,
    "documents_available": ["bank_statement", "itr_form16"],
    "property_type": "standard_urban",
}


async def test_match_endpoint_returns_ranked_lenders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/lenders/match", json=VALID_PROFILE)

    assert response.status_code == 200
    body = response.json()
    assert "lenders" in body
    assert "meta" in body
    assert len(body["lenders"]) >= 1
    assert body["meta"]["products_considered"] == len(FIXTURE_PRODUCTS)


async def test_match_endpoint_rejects_invalid_cibil_score():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad_profile = {**VALID_PROFILE, "cibil_score": 950}
        response = await client.post("/api/v1/lenders/match", json=bad_profile)

    assert response.status_code == 422


async def test_match_endpoint_ignores_unknown_extra_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        profile_with_extra = {**VALID_PROFILE, "some_future_field": "anything"}
        response = await client.post("/api/v1/lenders/match", json=profile_with_extra)

    assert response.status_code == 200


async def test_match_endpoint_returns_empty_lenders_for_ineligible_profile():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        weak_profile = {**VALID_PROFILE, "cibil_score": 301, "net_monthly_salary": 1, "documents_available": []}
        response = await client.post("/api/v1/lenders/match", json=weak_profile)

    assert response.status_code == 200
    assert response.json()["lenders"] == []
