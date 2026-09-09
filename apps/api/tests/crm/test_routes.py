import pytest

from app.crm.routes import router


@pytest.mark.unit
def test_crm_router_exposes_the_operational_contract() -> None:
    paths = {(route.path, method) for route in router.routes for method in route.methods}
    assert {
        ("/api/accounts", "GET"),
        ("/api/accounts", "POST"),
        ("/api/accounts/{account_id}", "GET"),
        ("/api/accounts/{account_id}", "PATCH"),
        ("/api/accounts/{account_id}/archive", "POST"),
        ("/api/accounts/import/preview", "POST"),
        ("/api/accounts/import", "POST"),
        ("/api/case-studies/seed", "POST"),
        ("/api/case-studies/{account_id}/metrics", "GET"),
        ("/api/case-studies/{account_id}/metrics", "PUT"),
        ("/api/contacts", "GET"),
        ("/api/contacts", "POST"),
        ("/api/contacts/{contact_id}", "PATCH"),
        ("/api/opportunities", "GET"),
        ("/api/opportunities", "POST"),
        ("/api/opportunities/{opportunity_id}", "PATCH"),
        ("/api/opportunities/{opportunity_id}/stage", "POST"),
        ("/api/opportunities/{opportunity_id}/assign", "POST"),
        ("/api/activities", "GET"),
        ("/api/activities", "POST"),
        ("/api/activities/{activity_id}", "PATCH"),
        ("/api/sales/my-day", "GET"),
        ("/api/sales/pipeline", "GET"),
        ("/api/sales/leaderboard", "GET"),
    } <= paths
