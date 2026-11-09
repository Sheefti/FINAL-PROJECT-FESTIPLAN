"""
Tests d'intégration HTTP (adaptateurs) — concerts.

Tests de non-régression sur les routes HTTP.
Vérifie le comportement de bout en bout (FastAPI + SQLite en mémoire).
"""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_festival(client, start="2027-06-20T00:00:00", end="2027-06-22T23:59:00"):
    r = client.post("/festivals", json={
        "name": "Test Festival", "location": "Clisson",
        "start_date": start, "end_date": end,
    })
    assert r.status_code == 201
    return r.json()


def _create_artist(client, name="Artiste Test", equipment=None):
    r = client.post("/artists", json={
        "name": name, "genre": "Metal",
        "required_equipment": equipment or [],
    })
    assert r.status_code == 201
    return r.json()


def _create_stage(client, festival_id, name="Scène Test", capacity=5000, equipment=None):
    r = client.post("/stages", json={
        "festival_id": festival_id, "name": name,
        "capacity": capacity,
        "available_equipment": equipment or [],
    })
    assert r.status_code == 201
    return r.json()


def _create_concert(client, festival_id, artist_id, stage_id,
                    start="2027-06-20T10:00:00", end="2027-06-20T12:00:00"):
    return client.post("/concerts", json={
        "festival_id": festival_id, "artist_id": artist_id,
        "stage_id": stage_id, "start_time": start, "end_time": end,
    })


# ---------------------------------------------------------------------------
# Tests fondamentaux
# ---------------------------------------------------------------------------

class TestCreateConcert:
    def test_valid_concert_created(self, client):
        f = _create_festival(client)
        a = _create_artist(client)
        s = _create_stage(client, f["id"])
        r = _create_concert(client, f["id"], a["id"], s["id"])
        assert r.status_code == 201
        assert r.json()["status"] == "scheduled"

    def test_end_before_start_rejected(self, client):
        r = _create_concert(client, 1, 1, 1,
                             start="2027-06-20T12:00:00",
                             end="2027-06-20T10:00:00")
        assert r.status_code in (400, 422)

    def test_unknown_festival_rejected(self, client):
        r = _create_concert(client, 9999, 1, 1)
        assert r.status_code == 400

    def test_equipment_mismatch_rejected(self, client):
        f = _create_festival(client)
        a = _create_artist(client, name="Heavy Artist", equipment=["sono pro"])
        s = _create_stage(client, f["id"], equipment=[])  # pas la sono
        r = _create_concert(client, f["id"], a["id"], s["id"])
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests — Défaut 1 : conflits lors du reschedule (non-régression)
# ---------------------------------------------------------------------------

class TestRescheduleConflicts:
    """
    Tests de non-régression pour le Défaut 1.
    Avant le fix : reschedule_concert() n'appelait pas _check_conflicts().
    """

    def _setup(self, client):
        f = _create_festival(client)
        a1 = _create_artist(client, name="Artiste A")
        a2 = _create_artist(client, name="Artiste B")
        s = _create_stage(client, f["id"])
        c1 = _create_concert(client, f["id"], a1["id"], s["id"],
                              start="2027-06-20T10:00:00", end="2027-06-20T12:00:00")
        c2 = _create_concert(client, f["id"], a2["id"], s["id"],
                              start="2027-06-20T14:00:00", end="2027-06-20T16:00:00")
        return f, s, c1.json(), c2.json()

    def test_valid_reschedule_accepted(self, client):
        _, _, c1, _ = self._setup(client)
        r = client.patch(f"/concerts/{c1['id']}/reschedule", json={
            "start_time": "2027-06-20T12:30:00",
            "end_time": "2027-06-20T13:30:00",
        })
        assert r.status_code == 200

    def test_stage_conflict_rejected(self, client):
        """Déplacer c1 sur le créneau de c2 (même scène) doit être refusé."""
        _, _, c1, _ = self._setup(client)
        r = client.patch(f"/concerts/{c1['id']}/reschedule", json={
            "start_time": "2027-06-20T14:00:00",
            "end_time": "2027-06-20T16:00:00",
        })
        assert r.status_code == 409

    def test_artist_on_two_stages_rejected(self, client):
        """Un artiste ne peut pas jouer sur deux scènes simultanément."""
        f = _create_festival(client)
        a = _create_artist(client, name="Artiste Solo")
        s1 = _create_stage(client, f["id"], name="Scène 1")
        s2 = _create_stage(client, f["id"], name="Scène 2")
        # C1 : artiste A sur scène 1
        c1 = _create_concert(client, f["id"], a["id"], s1["id"],
                              start="2027-06-20T10:00:00", end="2027-06-20T12:00:00")
        # C2 : artiste A sur scène 2 (créneau différent pour créer initialement)
        c2 = _create_concert(client, f["id"], a["id"], s2["id"],
                              start="2027-06-20T14:00:00", end="2027-06-20T16:00:00")
        # Déplacer c2 sur le même créneau que c1 → conflit artiste
        r = client.patch(f"/concerts/{c2.json()['id']}/reschedule", json={
            "start_time": "2027-06-20T10:00:00",
            "end_time": "2027-06-20T12:00:00",
        })
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# Tests — Défaut 3 : festival publié bloque le reschedule (non-régression)
# ---------------------------------------------------------------------------

class TestPublishedFestivalLock:
    def test_reschedule_after_publish_rejected(self, client):
        f = _create_festival(client)
        a = _create_artist(client)
        s = _create_stage(client, f["id"])
        c = _create_concert(client, f["id"], a["id"], s["id"])
        assert c.status_code == 201

        # Publication
        pub = client.post(f"/festivals/{f['id']}/publish")
        assert pub.status_code == 200

        # Reschedule après publication → 409
        r = client.patch(f"/concerts/{c.json()['id']}/reschedule", json={
            "start_time": "2027-06-20T12:30:00",
            "end_time": "2027-06-20T13:30:00",
        })
        assert r.status_code == 409

    def test_cancel_after_publish_rejected(self, client):
        f = _create_festival(client)
        a = _create_artist(client)
        s = _create_stage(client, f["id"])
        c = _create_concert(client, f["id"], a["id"], s["id"])
        client.post(f"/festivals/{f['id']}/publish")

        r = client.post(f"/concerts/{c.json()['id']}/cancel")
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# Tests — Non-régression généraux
# ---------------------------------------------------------------------------

def test_cancel_unknown_concert(client):
    r = client.post("/concerts/9999/cancel")
    assert r.status_code == 404


def test_get_concert_not_found(client):
    r = client.get("/concerts/9999")
    assert r.status_code == 404


def test_health_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
