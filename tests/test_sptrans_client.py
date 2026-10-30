"""Testes do cliente SPTrans com respostas simuladas (sem rede)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from src.api.sptrans_client import (
    SPTransAuthError,
    SPTransClient,
    SPTransError,
    parse_lines,
    parse_positions,
    parse_utc_timestamp,
)

TOKEN = "a" * 64

LINES_JSON = [
    {"cl": 1273, "lc": False, "lt": "8000", "sl": 1, "tl": 10, "tp": "PCA.RAMOS DE AZEVEDO", "ts": "TERMINAL LAPA"},
    {"cl": 34041, "lc": False, "lt": "8000", "sl": 2, "tl": 10, "tp": "PCA.RAMOS DE AZEVEDO", "ts": "TERMINAL LAPA"},
]

POSITIONS_JSON = {
    "hr": "19:57",
    "vs": [
        {"p": 11433, "a": False, "ta": "2026-11-01T22:57:21Z", "py": -23.540150375, "px": -46.64414075},
        {"p": "11434", "a": True, "ta": "2026-11-01T22:56:00Z", "py": -23.5412, "px": -46.6450},
        {"p": "BAD1", "a": True, "ta": "2026-11-01T22:56:00Z", "py": None, "px": -46.6},  # sem latitude
        {"p": "BAD2", "a": True, "ta": "2026-11-01T22:56:00Z", "py": 0, "px": 0},  # null island
        {"p": "BAD3", "a": True, "ta": "2026-11-01T22:56:00Z", "py": 40.7, "px": -74.0},  # fora de SP
        {"a": True, "ta": "2026-11-01T22:56:00Z", "py": -23.5, "px": -46.6},  # sem prefixo
        {"p": "11435", "a": None, "ta": "invalido", "py": "-23.55", "px": "-46.63"},  # horário inválido
    ],
}


class FakeResponse:
    def __init__(self, status=200, json_data=None, text=None):
        self.status_code = status
        self._json = json_data
        self.text = text if text is not None else ("" if json_data is None else str(json_data))

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeSession:
    """Simula requests.Session registrando as chamadas."""

    def __init__(self, posts=None, gets=None):
        self.headers = {}
        self.posts = list(posts or [])
        self.gets = list(gets or [])
        self.calls = []

    def _next(self, queue, method, url, params):
        self.calls.append((method, url, params))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def post(self, url, params=None, timeout=None):
        return self._next(self.posts, "POST", url, params)

    def get(self, url, params=None, timeout=None):
        return self._next(self.gets, "GET", url, params)


def make_client(posts=None, gets=None):
    s = FakeSession(posts, gets)
    return SPTransClient(TOKEN, "https://api.example/v2.1", timeout=1, session=s), s


# ------------------------------------------------------------- autenticação
def test_requires_token():
    with pytest.raises(SPTransAuthError):
        SPTransClient("")


def test_authenticate_success_uses_correct_endpoint():
    client, s = make_client(posts=[FakeResponse(200, text="true")])
    assert client.authenticate() is True
    method, url, params = s.calls[0]
    assert method == "POST" and url.endswith("/v2.1/Login/Autenticar") and params == {"token": TOKEN}


def test_authenticate_rejected():
    client, _ = make_client(posts=[FakeResponse(200, text="false")])
    with pytest.raises(SPTransAuthError, match="retornou false"):
        client.authenticate()


def test_authenticate_http_error():
    client, _ = make_client(posts=[FakeResponse(500, text="erro")])
    with pytest.raises(SPTransError):
        client.authenticate()


def test_timeout_is_wrapped():
    client, _ = make_client(posts=[requests.Timeout()])
    with pytest.raises(SPTransError, match="Tempo esgotado"):
        client.authenticate()


def test_network_error_message_does_not_leak_token():
    err = requests.ConnectionError(f"Max retries exceeded with url: /v2.1/Login/Autenticar?token={TOKEN}")
    client, _ = make_client(posts=[err])
    with pytest.raises(SPTransError) as exc:
        client.authenticate()
    assert TOKEN not in str(exc.value) and "***" in str(exc.value)


def test_reauthenticates_when_session_expires():
    client, s = make_client(
        posts=[FakeResponse(200, text="true"), FakeResponse(200, text="true")],
        gets=[FakeResponse(401, json_data={"Message": "Authorization has been denied"}), FakeResponse(200, json_data=LINES_JSON)],
    )
    lines = client.search_lines("8000")
    assert len(lines) == 2
    assert [c[0] for c in s.calls] == ["POST", "GET", "POST", "GET"]


def test_invalid_json_raises():
    client, _ = make_client(posts=[FakeResponse(200, text="true")], gets=[FakeResponse(200, json_data=None, text="<html>")])
    with pytest.raises(SPTransError, match="JSON"):
        client.search_lines("8000")


def test_empty_search_does_not_call_api():
    client, s = make_client()
    assert client.search_lines("   ") == []
    assert s.calls == []


# --------------------------------------------------------------- adaptadores
def test_parse_lines_distinguishes_code_and_sign():
    lines = parse_lines(LINES_JSON)
    assert [l.code for l in lines] == [1273, 34041]
    assert all(l.sign == "8000-10" for l in lines)
    assert lines[0].direction == 1 and lines[0].origin == "PCA.RAMOS DE AZEVEDO" and lines[0].destination == "TERMINAL LAPA"
    assert lines[1].direction == 2 and lines[1].origin == "TERMINAL LAPA"


def test_parse_lines_ignores_invalid_items():
    data = LINES_JSON + [{"lt": "X"}, "lixo", {"cl": 1, "sl": 9, "lt": "1", "tl": 10}]
    assert len(parse_lines(data)) == 2


def test_parse_lines_rejects_non_list():
    with pytest.raises(SPTransError):
        parse_lines({"erro": 1})


def test_parse_positions_normalizes_and_validates():
    collected = datetime(2026, 11, 1, 22, 58, tzinfo=timezone.utc)
    snap = parse_positions(POSITIONS_JSON, 1273, collected)
    ids = sorted(v.vehicle_id for v in snap.vehicles)
    assert ids == ["11433", "11434", "11435"]  # prefixo numérico vira string
    assert snap.discarded == 4
    assert snap.api_reference_time == "19:57"
    v = next(v for v in snap.vehicles if v.vehicle_id == "11433")
    assert v.latitude == pytest.approx(-23.540150375) and v.longitude == pytest.approx(-46.64414075)
    assert v.position_time_utc == datetime(2026, 11, 1, 22, 57, 21, tzinfo=timezone.utc)
    assert v.accessible is False
    bad_time = next(v for v in snap.vehicles if v.vehicle_id == "11435")
    assert bad_time.position_time_utc is None and bad_time.accessible is None


def test_parse_positions_without_vehicles():
    snap = parse_positions({"hr": "03:10", "vs": []}, 1, datetime.now(timezone.utc))
    assert snap.vehicles == [] and snap.discarded == 0
    snap2 = parse_positions({"hr": "03:10"}, 1, datetime.now(timezone.utc))
    assert snap2.vehicles == []
    snap3 = parse_positions(None, 1, datetime.now(timezone.utc))
    assert snap3.vehicles == []


def test_parse_positions_keeps_latest_duplicate():
    data = {
        "hr": "10:00",
        "vs": [
            {"p": "1", "ta": "2026-01-01T10:00:00Z", "py": -23.5, "px": -46.6},
            {"p": "1", "ta": "2026-01-01T10:01:00Z", "py": -23.51, "px": -46.61},
        ],
    }
    snap = parse_positions(data, 1, datetime.now(timezone.utc))
    assert len(snap.vehicles) == 1 and snap.vehicles[0].latitude == -23.51


def test_get_positions_end_to_end_with_fake_session():
    client, s = make_client(posts=[FakeResponse(200, text="true")], gets=[FakeResponse(200, json_data=POSITIONS_JSON)])
    snap = client.get_positions(1273)
    assert s.calls[1][1].endswith("/Posicao/Linha") and s.calls[1][2] == {"codigoLinha": 1273}
    assert len(snap.vehicles) == 3 and snap.source == "real"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-11-01T22:57:21Z", datetime(2026, 11, 1, 22, 57, 21, tzinfo=timezone.utc)),
        ("2026-11-01T19:57:21-03:00", datetime(2026, 11, 1, 22, 57, 21, tzinfo=timezone.utc)),
        ("2026-11-01T22:57:21", datetime(2026, 11, 1, 22, 57, 21, tzinfo=timezone.utc)),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_parse_utc_timestamp(value, expected):
    assert parse_utc_timestamp(value) == expected
