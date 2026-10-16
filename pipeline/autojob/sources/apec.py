"""APEC.fr — French job board for cadres (managers/graduates). Hidden JSON search, no key.

``POST /cms/webservices/rechercheOffre`` with ``typesContrat=[101888]`` (CDI) and
``typesTeletravail=[20767]``. The code mapping was verified from APEC's own referential
(``/cms/webservices/referentielstatique/presentations/code/LISTE_OPTIONS_TELETRAVAIL/visuels``):
20767 "Télétravail total possible", 20765 partial, 20766 occasional, 20949 none. So only
full-remote CDI postings come back — the candidate lives in Vancouver.

Only the search endpoint is open; detail pages and the detail JSON sit behind DataDome (403 +
captcha), so the ~300-character ``texteOffre`` excerpt is the description the scorer sees. Search is
full-text and loose ("opérations" matches "opérateur", "chargé d'opération" is mostly construction),
so titles are filtered here with ``title_keywords`` and ``title_exclude``.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

import requests

from autojob.models import RawJob
from autojob.normalize import canonical_url, clean_html, snippet_of, truncate
from autojob.settings import Settings
from autojob.sources.base import USER_AGENT, title_matches

NAME = "apec"
logger = logging.getLogger("autojob")
SEARCH_URL = "https://www.apec.fr/cms/webservices/rechercheOffre"
DETAIL_URL = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{num}"
CDI = "101888"
FULL_REMOTE = "20767"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json",
           "Origin": "https://www.apec.fr", "Referer": "https://www.apec.fr/candidat/recherche-emploi.html/emploi"}


class Blocked(Exception):
    """DataDome answered instead of the API."""


TELETRAVAIL_LABEL = {"20767": "télétravail total possible", "20765": "télétravail partiel",
                     "20766": "télétravail occasionnel", "20949": "pas de télétravail"}


def build_body(query: str, per_page: int, start: int = 0, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    contrats = [str(c) for c in cfg.get("contrats", [CDI]) or []]
    tele = cfg.get("teletravail", [FULL_REMOTE])
    body = {"motsCles": query, "sorts": [{"type": "DATE", "direction": "DESCENDING"}],
            "pagination": {"range": per_page, "startIndex": start}, "activeFiltre": True}
    if contrats:
        body["typesContrat"] = contrats
    if tele:
        body["typesTeletravail"] = [str(t) for t in tele]
    if cfg.get("lieux"):
        body["lieux"] = [str(x) for x in cfg["lieux"]]
    return body


def search(s: requests.Session, query: str, per_page: int, start: int = 0, cfg: dict | None = None) -> dict:
    r = s.post(SEARCH_URL, json=build_body(query, per_page, start, cfg), headers=HEADERS, timeout=30)
    if r.status_code == 403 or "captcha-delivery" in r.text[:300]:
        raise Blocked(f"HTTP {r.status_code}")
    r.raise_for_status()
    return r.json()


def to_raw(o: dict, default_tele: str | None = FULL_REMOTE) -> RawJob:
    """``default_tele``: the télétravail code implied by the search filter when the hit has none."""
    num = o.get("numeroOffre") or str(o.get("id"))
    excerpt = " ".join(clean_html(o.get("texteOffre") or "").split())
    salary = (o.get("salaireTexte") or "").strip()
    city = (o.get("lieuTexte") or "").strip()
    tele_code = str(o.get("idNomTeletravail") or default_tele or "")
    tele = TELETRAVAIL_LABEL.get(tele_code, "")
    full_remote = tele_code == FULL_REMOTE
    contrat = {"101888": "CDI", "101887": "CDD"}.get(str(o.get("typeContrat") or ""), "CDI" if not o.get("typeContrat") else str(o.get("typeContrat")))
    header = " · ".join(p for p in ("APEC", contrat, tele, f"lieu : {city or 'n/a'}", salary) if p)
    return RawJob(
        url=canonical_url(DETAIL_URL.format(num=num)), title=(o.get("intitule") or "").strip(),
        company=(o.get("nomCommercial") or "").strip(), source=NAME,
        location=(f"Télétravail total — France ({city})" if city else "Télétravail total — France") if full_remote
        else (f"{city}, France" + (f" ({tele})" if tele and tele_code != "20949" else "") if city else "France"),
        description=truncate(f"{header}\n\n{excerpt}"), snippet=snippet_of(excerpt),
        salary_currency="EUR" if salary else None, employment_type=contrat,
        posted_at=(o.get("datePublication") or "")[:10] or None, remote=full_remote or None,
        extra={"numero": num, "confidential": o.get("offreConfidentielle")},
    )


def fetch(settings: Settings) -> list[RawJob]:
    cfg = settings.source(NAME)
    # "" = every full-remote CDI posting, newest first (~500/week): cheaper and more complete than
    # keyword searches, which are full-text and loose anyway. Titles are filtered below.
    queries = list(cfg.get("queries") or [""])
    keywords = list(cfg.get("title_keywords") or [])
    exclude = [w.lower() for w in cfg.get("title_exclude", []) or []]
    per_page = int(cfg.get("results_per_page", 100))
    max_pages = int(cfg.get("max_pages", 8))
    max_age = int(cfg.get("max_days_old", 7))
    cutoff = (datetime.now(UTC) - timedelta(days=max_age)).strftime("%Y-%m-%d")
    delay = float(cfg.get("delay_s", 1.0))
    s = requests.Session()
    out: list[RawJob] = []
    seen: set[str] = set()
    fetched = 0
    for q in queries:
        for page in range(max_pages):
            try:
                data = search(s, q, per_page, page * per_page, cfg)
            except Blocked as e:
                logger.warning("[apec] blocked by DataDome (%s) — skipping APEC this run", e)
                logger.info("[apec] %d jobs (%d results)", len(out), fetched)
                return out
            except Exception as e:  # noqa: BLE001
                logger.warning("[apec] '%s' page %d failed: %s", q, page, str(e)[:120])
                break
            res = data.get("resultats") or []
            fetched += len(res)
            for o in res:
                num = o.get("numeroOffre") or str(o.get("id"))
                title = (o.get("intitule") or "").lower()
                if num in seen or (o.get("datePublication") or "")[:10] < cutoff:
                    continue
                seen.add(num)
                if keywords and not title_matches(title, keywords):
                    continue
                if any(w in title for w in exclude):
                    continue
                tele_filter = [str(t) for t in cfg.get("teletravail", [FULL_REMOTE]) or []]
                out.append(to_raw(o, tele_filter[0] if len(tele_filter) == 1 else None))
            time.sleep(delay)
            if len(res) < per_page or (res[-1].get("datePublication") or "")[:10] < cutoff:
                break
    logger.info("[apec] %d jobs (%d results, %d queries)", len(out), fetched, len(queries))
    return out
