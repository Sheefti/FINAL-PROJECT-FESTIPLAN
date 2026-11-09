"""
Tests d'intégration HTTP (adaptateurs) — festivals.
Non-régression + nouvelles règles de publication.
"""
import pytest


def _create_festival(client, start="2027-06-20T00:00:00", end="2027-06-22T23:59:00"):
    r = client.post("/festivals", json={
        "name": "Test Festival", "location": "Clisson",
        "start_date": start, "end_date": end,
    })
    assert r.status_code == 201
    return r.json()


def _create_artist(client):
    r = client.post("/artists", json={"name": "Artiste", "genre": "Metal", "required_equipment": []})
    assert r.status_code == 201
    return r.json()


def _create_stage(client, festival_id):
    r = client.post("/stages", json={"festival_id": festival_id, "name": "Grande Scène", "capacity": 5000, "available_equipment": []})
    assert r.status_code == 201
    return r.json()


def _create_concert(client, festival_id, artist_id, stage_id):
    r = client.post("/concerts", json={
        "festival_id": festival_id, "artist_id": artist_id, "stage_id": stage_id,
        "start_time": "2027-06-20T10:00:00", "end_time": "2027-06-20T12:00:00",
    })
    assert r.status_code == 201
    return r.json()


class TestFestivalCreation:
    def test_valid_festival_created(self, client):
        r = _create_festival(client)
        assert r["status"] == "preparation"

    def test_end_before_start_rejected(self, client):
        r = client.post("/festivals", json={
            "name": "Bad Festival", "location": "Nowhere",
            "start_date": "2027-06-20T10:00:00",
            "end_date": "2027-06-19T10:00:00",
        })
        assert r.status_code == 400


class TestPublishFestival:
    """Non-régression Défaut 3 — publication avec garde-fous."""

    def test_publish_unknown_festival_returns_404(self, client):
        r = client.post("/festivals/999/publish")
        assert r.status_code == 404

    def test_publish_empty_festival_rejected(self, client):
        """Un festival sans concert ne peut pas être publié."""
        f = _create_festival(client)
        r = client.post(f"/festivals/{f['id']}/publish")
        assert r.status_code == 400

    def test_publish_with_concerts_succeeds(self, client):
        f = _create_festival(client)
        a = _create_artist(client)
        s = _create_stage(client, f["id"])
        _create_concert(client, f["id"], a["id"], s["id"])
        r = client.post(f"/festivals/{f['id']}/publish")
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    def test_publish_already_published_rejected(self, client):
        f = _create_festival(client)
        a = _create_artist(client)
        s = _create_stage(client, f["id"])
        _create_concert(client, f["id"], a["id"], s["id"])
        client.post(f"/festivals/{f['id']}/publish")
        r = client.post(f"/festivals/{f['id']}/publish")
        assert r.status_code == 400
