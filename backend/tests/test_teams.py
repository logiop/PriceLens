def _demo_team_id(client, auth) -> int:
    teams = client.get("/api/teams", headers=auth).json()
    return teams[0]["id"]


def test_list_teams(auth, client):
    resp = client.get("/api/teams", headers=auth)
    assert resp.status_code == 200
    teams = resp.json()
    assert len(teams) >= 1
    team = teams[0]
    assert team["name"] == "PriceLens HQ"
    assert team["role"] == "owner"
    assert team["member_count"] == 2


def test_colleague_sees_shared_team(client, colleague_token):
    headers = {"Authorization": f"Bearer {colleague_token}"}
    teams = client.get("/api/teams", headers=headers).json()
    assert len(teams) == 1
    products = client.get("/api/products", headers=headers).json()
    assert len(products) == 12  # same team data


def test_create_team_and_switch(auth, client):
    created = client.post("/api/teams", headers=auth, json={"name": "Team Nuovo"})
    assert created.status_code == 201
    new_team = created.json()
    assert new_team["role"] == "owner"

    # switching via X-Team-Id to the new (empty) team
    headers = {**auth, "X-Team-Id": str(new_team["id"])}
    products = client.get("/api/products", headers=headers).json()
    assert products == []

    # unknown team -> 403
    forbidden = client.get("/api/products", headers={**auth, "X-Team-Id": "999999"})
    assert forbidden.status_code == 403


def test_add_and_remove_member(auth, client):
    demo_team = _demo_team_id(client, auth)

    reg = client.post(
        "/api/auth/register",
        json={"email": "member@test.it", "password": "password123"},
    )
    assert reg.status_code == 201

    added = client.post(
        f"/api/teams/{demo_team}/members",
        headers=auth,
        json={"email": "member@test.it", "role": "member"},
    )
    assert added.status_code == 201
    assert added.json()["email"] == "member@test.it"

    # duplicate membership
    dup = client.post(
        f"/api/teams/{demo_team}/members",
        headers=auth,
        json={"email": "member@test.it", "role": "member"},
    )
    assert dup.status_code == 409

    # the new member now sees the shared data with the team header
    member_token = client.post(
        "/api/auth/login", json={"email": "member@test.it", "password": "password123"}
    ).json()["access_token"]
    member_headers = {
        "Authorization": f"Bearer {member_token}",
        "X-Team-Id": str(demo_team),
    }
    products = client.get("/api/products", headers=member_headers).json()
    assert len(products) == 12

    # removing the owner is refused
    owner_id = client.get(f"/api/teams/{demo_team}/members", headers=auth).json()[0]["user_id"]
    cannot_remove_owner = client.delete(
        f"/api/teams/{demo_team}/members/{owner_id}", headers=auth
    )
    assert cannot_remove_owner.status_code == 400

    # remove the member
    member_id = added.json()["user_id"]
    removed = client.delete(f"/api/teams/{demo_team}/members/{member_id}", headers=auth)
    assert removed.status_code == 204


def test_audit_log_records_actions(auth, client):
    # create a product, then read the audit log
    payload = {
        "sku": "AUDIT-SKU-1",
        "name": "Audit Product",
        "brand": "Test",
        "category": "Test",
        "cost_price": 10.0,
        "current_price": 20.0,
    }
    created = client.post("/api/products", headers=auth, json=payload)
    assert created.status_code == 201

    resp = client.get("/api/audit", headers=auth, params={"limit": 50})
    assert resp.status_code == 200
    actions = [e["action"] for e in resp.json()]
    assert "product.create" in actions
    assert "auth.login" in actions
    assert all("user_email" in e for e in resp.json())


def test_audit_isolated_between_teams(auth, client):
    created = client.post("/api/teams", headers=auth, json={"name": "Team Audit"})
    team_id = created.json()["id"]
    audit = client.get("/api/audit", headers={**auth, "X-Team-Id": str(team_id)}).json()
    # only the team.create entry for this fresh team
    assert [e["action"] for e in audit] == ["team.create"]
