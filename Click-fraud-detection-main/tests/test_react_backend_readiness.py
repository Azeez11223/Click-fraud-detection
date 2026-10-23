def test_cors_allows_vite_origin(client):
    response = client.get("/healthz", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_openapi_declares_response_schemas(client):
    paths = client.get("/openapi.json").json()["paths"]
    typed_routes = {
        ("/auth/login", "post"),
        ("/auth/me", "get"),
        ("/stats", "get"),
        ("/campaigns", "get"),
        ("/campaigns", "post"),
        ("/campaigns/{campaign_id}", "get"),
        ("/campaigns/{campaign_id}/stats", "get"),
        ("/campaigns/{campaign_id}/clicks", "get"),
        ("/campaigns/{campaign_id}/threshold-analysis", "get"),
        ("/campaigns/{campaign_id}/realtime-feed", "get"),
        ("/campaigns/{campaign_id}/hourly-breakdown", "get"),
        ("/ip-lists", "get"),
        ("/ip-lists/counts", "get"),
        ("/ip-datasets", "get"),
    }
    for path, method in typed_routes:
        schema = paths[path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert "$ref" in schema or "$ref" in schema.get("items", {}), (path, method)


def test_alerts_aggregate_campaigns_for_authenticated_user(client, user_a, user_b):
    campaign = client.post("/campaigns", headers=user_a["headers"], json={
        "name": "Alerts campaign",
        "ad_type": "Search",
        "platform": "Google",
        "purpose": "Sales",
    })
    assert campaign.status_code == 200
    campaign_id = campaign.json()["campaign_id"]

    import database

    conn = database.get_connection()
    conn.executemany(
        "INSERT INTO campaign_clicks (campaign_id,ip_address,classification,fraud_reason) VALUES (?,?,?,?)",
        [(campaign_id, f"192.0.2.{index}", "FRAUD", "test") for index in range(10)],
    )
    conn.commit()
    conn.close()

    response = client.get("/alerts", headers=user_a["headers"])
    assert response.status_code == 200
    campaign_alerts = [alert for alert in response.json() if alert["campaign_id"] == campaign_id]
    assert campaign_alerts == [
        {
            "level": "high",
            "message": "[WARNING] 10 fraud clicks total",
            "campaign_id": campaign_id,
            "campaign_name": "Alerts campaign",
        },
        {
            "level": "critical",
            "message": "[CRITICAL] 10 fraud clicks in last hour!",
            "campaign_id": campaign_id,
            "campaign_name": "Alerts campaign",
        },
    ]
    assert client.get("/alerts", headers=user_b["headers"]).json() == []
    assert client.get("/alerts").status_code == 401
