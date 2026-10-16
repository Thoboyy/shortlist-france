"""France Travail (ex-Pôle emploi) — API officielle « Offres d'emploi v2 ». Gratuit, clé requise.

Inscription : https://francetravail.io → « Créer une application » → souscrire à l'API
« Offres d'emploi v2 ». Mettre ``FRANCETRAVAIL_CLIENT_ID`` / ``FRANCETRAVAIL_CLIENT_SECRET`` dans ``.env``.

* Jeton OAuth2 (client_credentials, realm ``/partenaire``, scope ``api_offresdemploiv2 o2dsoffre``),
  valable ~25 min ; il est mis en cache pour la durée du run.
* ``GET /partenaire/offresdemploi/v2/offres/search`` : 150 offres max par page (``range=0-149``),
  3 150 max par recherche. HTTP 206 = page partielle (normal), 204 = aucun résultat.
* Une passe par entrée de ``passes`` (commune INSEE + rayon, ou département, ou toute la France)
  × chaque requête. Les offres France Travail incluent beaucoup d'offres partenaires (Indeed,
  HelloWork, APEC…) : ``origineOffre.urlOrigine`` est gardé en ``extra`` mais l'URL canonique reste
  celle de France Travail (stable, dédupliquée par le fingerprint titre+entreprise).
* La description est complète : aucun scraping nécessaire.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from autojob.models import RawJob
from autojob.normalize import canonical_url, clean_html, snippet_of, truncate
from autojob.settings import Settings
from autojob.sources.base import USER_AGENT, title_matches

NAME = "francetravail"
logger = logging.getLogger("autojob")
TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
DETAIL_URL = "https://candidat.francetravail.fr/offres/recherche/detail/{id}"
SCOPE = "api_offresdemploiv2 o2dsoffre"
PAGE = 150
MAX_START = 3000          # l'API refuse range au-delà de 3149

_token: tuple[str, float] | None = None


def get_token(client_id: str, client_secret: str, s: requests.Session | None = None) -> str:
    global _token
    if _token and _token[1] > time.time() + 30:
        return _token[0]
    r = (s or requests).post(TOKEN_URL, params={"realm": "/partenaire"}, timeout=20, data={
        "grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret, "scope": SCOPE})
    r.raise_for_status()
    data = r.json()
    _token = (data["access_token"], time.time() + int(data.get("expires_in", 1499)))
    return _token[0]


def build_params(query: str, pc: dict[str, Any], start: int, cfg: dict[str, Any]) -> dict[str, Any]:
    """Paramètres de recherche d'une passe. Clés vides/None = non envoyées."""
    p: dict[str, Any] = {
        "motsCles": query or None,
        "range": f"{start}-{start + PAGE - 1}",
        "sort": 1,                                   # 1 = date de création décroissante
        "publieeDepuis": cfg.get("publiee_depuis", 7),   # 1, 3, 7, 14 ou 31 jours
        "commune": pc.get("commune"),               # code INSEE (69123 = Lyon, 69266 = Villeurbanne)
        "distance": pc.get("distance_km") if pc.get("commune") else None,
        "departement": pc.get("departement"),       # "69" ou "69,01,38" (5 max)
        "region": pc.get("region"),                 # "84" = Auvergne-Rhône-Alpes
        "typeContrat": pc.get("type_contrat", cfg.get("type_contrat")),       # "CDI,CDD,MIS,LIB"…
        "qualification": pc.get("qualification", cfg.get("qualification")),  # 9 = cadre
        "experience": pc.get("experience", cfg.get("experience")),            # 1 <1 an, 2 1-3 ans, 3 >3 ans
        "codeROME": pc.get("code_rome", cfg.get("code_rome")),
        "tempsPlein": pc.get("temps_plein", cfg.get("temps_plein")),
    }
    return {k: v for k, v in p.items() if v not in (None, "", [])}


def _location(o: dict[str, Any]) -> str:
    lieu = (o.get("lieuTravail") or {}).get("libelle") or ""      # "69 - LYON 03"
    # "69 - LYON 03" → "Lyon 03 (69), France" — lisible et reconnu par le prefilter
    if " - " in lieu:
        dep, city = lieu.split(" - ", 1)
        lieu = f"{city.strip().title()} ({dep.strip()})"
    return f"{lieu}, France" if lieu else "France"


def _remote_hint(text: str) -> bool | None:
    t = text.lower()
    if "full remote" in t or "100% télétravail" in t or "télétravail complet" in t or "télétravail total" in t:
        return True
    return None


def to_raw(o: dict[str, Any]) -> RawJob:
    desc = clean_html(o.get("description") or "")
    sal = (o.get("salaire") or {}).get("libelle") or ""
    contrat = o.get("typeContratLibelle") or o.get("typeContrat") or ""
    header = " · ".join(p for p in (
        f"France Travail · {contrat}" if contrat else "France Travail",
        o.get("dureeTravailLibelle") or "", o.get("experienceLibelle") or "", sal) if p)
    entreprise = o.get("entreprise") or {}
    return RawJob(
        url=canonical_url(DETAIL_URL.format(id=o.get("id"))), title=(o.get("intitule") or "").strip(),
        company=(entreprise.get("nom") or "").strip(), source=NAME, location=_location(o),
        description=truncate(f"{header}\n\n{desc}"), snippet=snippet_of(desc),
        salary_currency="EUR" if sal else None, employment_type=o.get("typeContrat") or None,
        posted_at=(o.get("dateCreation") or "")[:10] or None, remote=_remote_hint(desc),
        extra={"ft_id": o.get("id"), "rome": o.get("romeCode"), "url_origine": (o.get("origineOffre") or {}).get("urlOrigine"),
               "qualification": o.get("qualificationLibelle"), "secteur": o.get("secteurActiviteLibelle")},
    )


def fetch(settings: Settings) -> list[RawJob]:
    sec = settings.secrets
    if not (sec.francetravail_client_id and sec.francetravail_client_secret):
        logger.info("[francetravail] pas d'identifiants API (FRANCETRAVAIL_CLIENT_ID/SECRET), source ignorée")
        return []
    cfg = settings.source(NAME)
    keywords = list(cfg.get("title_keywords") or [])
    exclude = [w.lower() for w in cfg.get("title_exclude", []) or []]
    max_pages = int(cfg.get("max_pages", 2))
    delay = float(cfg.get("delay_s", 0.3))      # quota API : ~10 appels/s
    passes = list(cfg.get("passes") or [{"name": "france"}])
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        token = get_token(sec.francetravail_client_id, sec.francetravail_client_secret, s)
    except Exception as e:  # noqa: BLE001
        logger.warning("[francetravail] jeton refusé : %s", str(e)[:160])
        return []
    out: list[RawJob] = []
    seen: set[str] = set()
    for pc in passes:
        n_pass = 0
        queries = pc.get("queries") or settings.source_queries(NAME)
        for q in queries[: int(pc.get("max_queries", cfg.get("max_queries", 20)))]:
            for page in range(max_pages):
                start = page * PAGE
                if start > MAX_START:
                    break
                try:
                    r = s.get(SEARCH_URL, params=build_params(q, pc, start, cfg),
                              headers={"Authorization": f"Bearer {token}"}, timeout=30)
                    if r.status_code == 429:
                        time.sleep(2)
                        r = s.get(SEARCH_URL, params=build_params(q, pc, start, cfg),
                                  headers={"Authorization": f"Bearer {token}"}, timeout=30)
                    if r.status_code == 204:
                        break
                    r.raise_for_status()
                    res = (r.json() or {}).get("resultats") or []
                except Exception as e:  # noqa: BLE001
                    logger.warning("[francetravail] %s/'%s' page %d : %s", pc.get("name"), q, page, str(e)[:120])
                    break
                for o in res:
                    oid = str(o.get("id") or "")
                    title = o.get("intitule") or ""
                    if not oid or oid in seen:
                        continue
                    seen.add(oid)
                    if keywords and not title_matches(title, keywords):
                        continue
                    if any(w in title.lower() for w in exclude):
                        continue
                    out.append(to_raw(o))
                    n_pass += 1
                time.sleep(delay)
                if len(res) < PAGE:
                    break
        logger.info("[francetravail] %s : %d offres", pc.get("name", "?"), n_pass)
    logger.info("[francetravail] %d offres", len(out))
    return out
