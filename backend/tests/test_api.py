def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_unauthorized(client):
    resp = client.get("/api/products")
    assert resp.status_code == 401


def test_auth_flow(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "demo@pricelens.it", "password": "demo1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["email"] == "demo@pricelens.it"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "demo@pricelens.it"

    bad = client.post(
        "/api/auth/login",
        json={"email": "demo@pricelens.it", "password": "wrong"},
    )
    assert bad.status_code == 401


def test_register(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    dup = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert dup.status_code == 409


def test_dashboard(auth, client):
    resp = client.get("/api/dashboard", headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["kpis"]["products"] >= 1
    assert data["kpis"]["competitors"] >= 1
    assert "top_movers" in data
    assert "recent_alerts" in data


def test_products_list(auth, client):
    resp = client.get("/api/products", headers=auth)
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) >= 1
    first = products[0]
    for field in ("id", "sku", "name", "current_price", "competitors_tracked", "position"):
        assert field in first


def test_product_detail(auth, client):
    products = client.get("/api/products", headers=auth).json()
    product_id = products[0]["id"]
    resp = client.get(f"/api/products/{product_id}", headers=auth)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == product_id
    assert len(detail["competitors"]) >= 1
    assert detail["recommendation"] is not None
    assert detail["recommendation"]["suggested_price"] > 0


def test_product_history(auth, client):
    products = client.get("/api/products", headers=auth).json()
    product_id = products[0]["id"]
    resp = client.get(f"/api/products/{product_id}/history", headers=auth)
    assert resp.status_code == 200
    series = resp.json()
    assert len(series) >= 1
    assert all(len(s["points"]) >= 1 for s in series)


def test_categories(auth, client):
    resp = client.get("/api/products/categories", headers=auth)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_product_conflict(auth, client):
    existing = client.get("/api/products", headers=auth).json()[0]
    payload = {
        "sku": existing["sku"],
        "name": "Duplicato",
        "brand": "Test",
        "category": "Test",
        "cost_price": 10.0,
        "current_price": 20.0,
    }
    resp = client.post("/api/products", headers=auth, json=payload)
    assert resp.status_code == 409


def test_create_and_delete_product(auth, client):
    payload = {
        "sku": "TEST-SKU-001",
        "name": "Prodotto Test",
        "brand": "Test",
        "category": "Test",
        "cost_price": 10.0,
        "current_price": 25.0,
        "msrp": 30.0,
        "map_price": 20.0,
    }
    resp = client.post("/api/products", headers=auth, json=payload)
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    updated = client.patch(
        f"/api/products/{product_id}",
        headers=auth,
        json={"current_price": 24.0, "strategy": "undercut"},
    )
    assert updated.status_code == 200
    assert updated.json()["current_price"] == 24.0

    deleted = client.delete(f"/api/products/{product_id}", headers=auth)
    assert deleted.status_code == 204


def test_competitors_list_and_crud(auth, client):
    resp = client.get("/api/competitors", headers=auth)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    created = client.post(
        "/api/competitors",
        headers=auth,
        json={"name": "Test Shop", "domain": "test.it", "type": "retailer"},
    )
    assert created.status_code == 201
    competitor_id = created.json()["id"]

    deleted = client.delete(f"/api/competitors/{competitor_id}", headers=auth)
    assert deleted.status_code == 204


def test_alerts_flow(auth, client):
    resp = client.get("/api/alerts", headers=auth, params={"limit": 20})
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) >= 1
    assert all("message" in a and "severity" in a for a in alerts)

    unread = [a for a in alerts if not a["read"]]
    if unread:
        alert_id = unread[0]["id"]
        marked = client.post(f"/api/alerts/{alert_id}/read", headers=auth)
        assert marked.status_code == 200
        assert marked.json()["read"] is True

    read_all = client.post("/api/alerts/read-all", headers=auth)
    assert read_all.status_code == 200

    counts = client.get("/api/alerts/counts", headers=auth).json()
    assert counts["unread"] == 0


def test_repricing_preview_and_apply(auth, client):
    preview = client.get("/api/repricing/preview", headers=auth)
    assert preview.status_code == 200
    recs = preview.json()["recommendations"]
    assert len(recs) >= 1

    target = recs[0]
    applied = client.post(
        "/api/repricing/apply",
        headers=auth,
        json={"product_id": target["product_id"], "suggested_price": target["suggested_price"]},
    )
    assert applied.status_code == 200
    assert applied.json()["current_price"] == target["suggested_price"]


def test_collect(auth, client):
    resp = client.post("/api/collect", headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["collected"] >= 1
    assert "alerts_created" in data


def test_export_products_csv(auth, client):
    resp = client.get("/api/export/products?format=csv", headers=auth)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "sku" in resp.text


def test_export_products_xlsx(auth, client):
    resp = client.get("/api/export/products?format=xlsx", headers=auth)
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]


def test_export_history(auth, client):
    products = client.get("/api/products", headers=auth).json()
    product_id = products[0]["id"]
    resp = client.get(f"/api/export/history/{product_id}?format=csv", headers=auth)
    assert resp.status_code == 200
    assert "competitor" in resp.text


def test_scheduler_status(auth, client):
    resp = client.get("/api/scheduler/status", headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "interval_seconds" in data


def test_cross_user_isolation(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "other@test.it", "password": "password123"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    products = client.get("/api/products", headers=headers).json()
    assert products == []

    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["kpis"]["products"] == 0
