"""Tests for the structured knowledge-base REST endpoints."""
from __future__ import annotations


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["retrieval"]["n_documents"] >= 20


def test_overview_with_derived_counts(client):
    r = client.get("/api/v1/kb/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "中国农业大学"
    assert body["college_count"] >= 20
    assert body["dept_count"] > body["college_count"]


def test_colleges_listing(client):
    r = client.get("/api/v1/kb/colleges")
    assert r.status_code == 200
    items = r.json()["items"]
    assert r.json()["count"] == len(items) >= 20
    assert any(c["id"] == "agronomy" for c in items)


def test_college_detail(client):
    r = client.get("/api/v1/kb/colleges/agronomy")
    assert r.status_code == 200
    c = r.json()
    assert c["name"] == "农学院"
    assert len(c["depts"]) >= 1
    assert any("农学" in m["name"] for m in c["majors"])


def test_college_404(client):
    r = client.get("/api/v1/kb/colleges/not-a-college")
    assert r.status_code == 404


def test_majors_listing(client):
    r = client.get("/api/v1/kb/majors")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["items"])
    first = body["items"][0]
    assert {"name", "college", "directions", "key_discipline"} <= set(first)


def test_professors(client):
    r = client.get("/api/v1/kb/professors")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 5
    names = {p["name"] for p in items}
    assert "张福锁" in names
    p = [x for x in items if x["id"] == "zhang-fusuo"][0]
    assert p["college"] == "资源与环境学院"
    assert "科技小院" in p["achievements"]


def test_professor_detail(client):
    r = client.get("/api/v1/kb/professors/li-defa")
    assert r.status_code == 200
    assert r.json()["name"] == "李德发"


def test_achievements(client):
    r = client.get("/api/v1/kb/achievements")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["items"]) >= 5
    assert any("基因组" in a["title"] for a in body["items"])