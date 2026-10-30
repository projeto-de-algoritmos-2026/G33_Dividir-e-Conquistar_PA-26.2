"""Cliente da API Olho Vivo (SPTrans).

Contrato (documentação oficial, v2.1):
    POST /Login/Autenticar?token={token}        → corpo ``true`` / ``false``
    GET  /Linha/Buscar?termosBusca={termo}      → [{cl, lc, lt, sl, tl, tp, ts}]
    GET  /Posicao/Linha?codigoLinha={cl}        → {hr, vs: [{p, a, ta, py, px}]}

A autenticação devolve um cookie (``apiCredentials``) que precisa ser reenviado
em todas as chamadas — por isso usamos ``requests.Session``.

Segurança:
    - O token vem de ``SPTRANS_API_TOKEN`` (nunca do código-fonte).
    - Logs registram apenas o caminho do endpoint, nunca a URL completa.
    - Mensagens de exceção passam por ``_redact`` antes de serem expostas,
      porque o ``requests`` inclui a URL (com o token) em algumas mensagens.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from src.geo.coordinates import is_in_sao_paulo_region, is_valid_lat_lon
from src.models import BusLine, PositionsSnapshot, VehiclePosition

logger = logging.getLogger("twobus.sptrans")
# O urllib3 em nível DEBUG registraria URLs com o token: limitamos a WARNING.
logging.getLogger("urllib3").setLevel(logging.WARNING)


class SPTransError(Exception):
    """Erro genérico de comunicação com a API (mensagem já sem segredos)."""


class SPTransAuthError(SPTransError):
    """Autenticação não concluída; a API pode não informar a causa."""


class SPTransClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://api.olhovivo.sptrans.com.br/v2.1",
        timeout: float = 15,
        session: requests.Session | None = None,
    ) -> None:
        if not token:
            raise SPTransAuthError("SPTRANS_API_TOKEN não configurado (veja .env.example).")
        self._token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "TwoBus/1.0 (academic)"})
        self.authenticated = False

    # ------------------------------------------------------------ segurança
    def _redact(self, text: str) -> str:
        return text.replace(self._token, "***") if self._token else text

    # ------------------------------------------------------- autenticação
    def authenticate(self) -> bool:
        """POST /Login/Autenticar. Levanta SPTransAuthError se recusado."""
        path = "/Login/Autenticar"
        try:
            resp = self.session.post(
                f"{self.base_url}{path}", params={"token": self._token}, timeout=self.timeout
            )
        except requests.Timeout as exc:
            raise SPTransError(f"Tempo esgotado ao autenticar ({self.timeout}s).") from None
        except requests.RequestException as exc:
            raise SPTransError(f"Falha de rede ao autenticar: {self._redact(str(exc))}") from None

        if resp.status_code != 200:
            raise SPTransError(f"Autenticação retornou HTTP {resp.status_code}.")
        body = resp.text.strip().lower()
        ok = body == "true"
        self.authenticated = ok
        logger.info("POST %s → %s", path, "ok" if ok else "recusado")
        if not ok:
            raise SPTransAuthError("A SPTrans retornou false na autenticação; a API não informou a causa.")
        return True

    # ---------------------------------------------------------- requisições
    def _get(self, path: str, params: dict[str, Any]) -> Any:
        """GET autenticado com 1 nova tentativa em caso de sessão expirada."""
        if not self.authenticated:
            self.authenticate()

        for attempt in (1, 2):
            try:
                resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            except requests.Timeout:
                raise SPTransError(f"Tempo esgotado em {path} ({self.timeout}s).") from None
            except requests.RequestException as exc:
                raise SPTransError(f"Falha de rede em {path}: {self._redact(str(exc))}") from None

            logger.info("GET %s → HTTP %s", path, resp.status_code)
            if resp.status_code in (401, 403) and attempt == 1:
                # Sessão expirada: autentica novamente e repete uma única vez.
                logger.info("Sessão expirada; reautenticando.")
                self.authenticated = False
                self.authenticate()
                continue
            if resp.status_code != 200:
                raise SPTransError(f"{path} retornou HTTP {resp.status_code}.")
            try:
                return resp.json()
            except ValueError:
                raise SPTransError(f"{path} retornou um corpo que não é JSON válido.") from None
        raise SPTransAuthError("Não foi possível manter a sessão autenticada.")

    # ------------------------------------------------------------ endpoints
    def search_lines(self, term: str) -> list[BusLine]:
        term = (term or "").strip()
        if not term:
            return []
        data = self._get("/Linha/Buscar", {"termosBusca": term})
        return parse_lines(data)

    def get_positions(self, line_code: int) -> PositionsSnapshot:
        data = self._get("/Posicao/Linha", {"codigoLinha": int(line_code)})
        collected_at = datetime.now(timezone.utc)
        return parse_positions(data, int(line_code), collected_at)


# ============================================================== adaptadores
# Funções puras: convertem o JSON da API em modelos internos. São testadas
# com respostas simuladas, sem rede.


def parse_lines(data: Any) -> list[BusLine]:
    if not isinstance(data, list):
        raise SPTransError("Resposta inesperada de /Linha/Buscar (esperava uma lista).")
    lines: list[BusLine] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            code = int(item["cl"])
            direction = int(item["sl"])
            if direction not in (1, 2):
                continue
            lines.append(
                BusLine(
                    code=code,
                    circular=bool(item.get("lc", False)),
                    sign_prefix=str(item.get("lt", "")).strip(),
                    sign_suffix=int(item.get("tl", 0) or 0),
                    direction=direction,
                    main_terminal=str(item.get("tp", "") or "").strip(),
                    secondary_terminal=str(item.get("ts", "") or "").strip(),
                )
            )
        except (KeyError, TypeError, ValueError):
            logger.debug("Linha ignorada por campos inválidos.")
            continue
    return lines


def parse_utc_timestamp(value: Any) -> datetime | None:
    """Converte ``ta`` (ISO 8601, UTC, ex. 2024-05-07T09:38:21Z) em datetime aware."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_vehicle(item: Any) -> VehiclePosition | None:
    """Normaliza um veículo. Retorna None se identificador/coordenadas forem inválidos."""
    if not isinstance(item, dict):
        return None
    vid = item.get("p")
    if vid is None or str(vid).strip() == "":
        return None
    lat, lon = item.get("py"), item.get("px")
    if not is_valid_lat_lon(lat, lon):
        return None
    lat, lon = float(lat), float(lon)
    if not is_in_sao_paulo_region(lat, lon):
        return None
    acc = item.get("a")
    return VehiclePosition(
        vehicle_id=str(vid).strip(),
        latitude=lat,
        longitude=lon,
        position_time_utc=parse_utc_timestamp(item.get("ta")),
        accessible=acc if isinstance(acc, bool) else None,
    )


def parse_positions(data: Any, line_code: int, collected_at_utc: datetime) -> PositionsSnapshot:
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise SPTransError("Resposta inesperada de /Posicao/Linha (esperava um objeto).")
    raw = data.get("vs") or []
    if not isinstance(raw, list):
        raw = []

    vehicles: dict[str, VehiclePosition] = {}
    discarded = 0
    for item in raw:
        v = parse_vehicle(item)
        if v is None:
            discarded += 1
            continue
        # Se o mesmo prefixo aparecer duas vezes, mantém a posição mais recente.
        prev = vehicles.get(v.vehicle_id)
        if prev is not None:
            discarded += 1
            if (v.position_time_utc or datetime.min.replace(tzinfo=timezone.utc)) <= (
                prev.position_time_utc or datetime.min.replace(tzinfo=timezone.utc)
            ):
                continue
        vehicles[v.vehicle_id] = v

    hr = data.get("hr")
    return PositionsSnapshot(
        line_code=line_code,
        collected_at_utc=collected_at_utc,
        api_reference_time=str(hr) if hr else None,
        vehicles=list(vehicles.values()),
        discarded=discarded,
        source="real",
    )
