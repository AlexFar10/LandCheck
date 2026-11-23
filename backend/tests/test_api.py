import jsonschema


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_one_result_per_risk(client, parcel):
    response = client.post("/analyze", json=parcel)
    assert response.status_code == 200
    risks = [r["risk"] for r in response.json()["results"]]
    assert sorted(risks) == [
        "flood_history",
        "flood_susceptibility",
        "ground_stability",
        "land_use_history",
    ]


def test_analyze_results_match_schema(client, parcel, result_schema):
    for result in client.post("/analyze", json=parcel).json()["results"]:
        jsonschema.validate(result, result_schema)


def test_analyze_includes_unknown_with_null_value(client, parcel):
    results = client.post("/analyze", json=parcel).json()["results"]
    unknown = [r for r in results if r["level"] == "Unknown"]
    assert unknown, "expected at least one Unknown result"
    assert all(r["value"] is None for r in unknown)


def test_analyze_rejects_non_polygon(client):
    response = client.post("/analyze", json={"type": "Point", "coordinates": [21.2, 45.75]})
    assert response.status_code == 422


def test_analyze_rejects_open_ring(client):
    ring = [[21.20, 45.75], [21.21, 45.75], [21.21, 45.76], [21.20, 45.76]]
    response = client.post("/analyze", json={"type": "Polygon", "coordinates": [ring]})
    assert response.status_code == 422


def test_analyze_rejects_out_of_range_coordinates(client):
    ring = [[200.0, 45.75], [21.21, 45.75], [21.21, 45.76], [200.0, 45.75]]
    response = client.post("/analyze", json={"type": "Polygon", "coordinates": [ring]})
    assert response.status_code == 422
