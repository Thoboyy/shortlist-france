"""Adaptation marché français : config FR, prefilter (départements), France Travail, normalisation H/F,
scorer configurable, digest en français."""
from pathlib import Path

import yaml

from autojob import sources as S
from autojob.normalize import fingerprint, normalize_text
from autojob.notify import _date
from autojob.prefilter import french_departement, prefilter_reason
from autojob.scorer import compute_v2
from autojob.settings import ROOT, Settings, load_settings
from autojob.sources.adzuna import CURRENCY
from autojob.sources.apec import build_body
from autojob.sources.francetravail import build_params, to_raw

FR_PATH = ROOT / "config" / "search.fr.yaml"
FR = yaml.safe_load(FR_PATH.read_text(encoding="utf-8"))
PF = FR["prefilter"]


def test_fr_config_is_complete():
    assert FR["profile"]["country"] == "FR" and FR["profile"]["language"] == "fr"
    assert FR["scoring"]["models"] and FR["scoring"]["docs_models"] and FR["queries"]
    for name, sub in FR["sources"].items():
        assert name in S.SOURCE_NAMES, name
        assert isinstance(sub, dict) and "enabled" in sub, name
    assert FR["sources"]["francetravail"]["enabled"]


def test_fr_prompts_are_selected():
    st = load_settings(FR_PATH)
    assert st.language == "fr"
    assert "Tu lis UNE offre" in st.prompt("scorer_v2")
    assert "EN FRANÇAIS" in st.prompt("cover_letter")
    assert "role family" in Settings(raw={}).prompt("scorer_v2").lower()   # default stays English


def _r(title, loc, remote=None):
    return prefilter_reason({"title": title, "location": loc, "remote": remote}, PF)


def test_fr_location_rules():
    assert _r("Consultant IAM H/F", "Lyon 03 (69), France") is None
    assert _r("Consultant IAM H/F", "69100 Villeurbanne") is None
    assert _r("Consultant IAM H/F", "Grenoble (38)") is None
    assert _r("Consultant IAM H/F", "Saint-Denis-en-Bugey (01), France") is None   # local dép. beats deny_cities
    assert _r("Consultant IAM H/F", "Télétravail total — France (Paris 08 - 75)", True) is None
    assert _r("Consultant IAM H/F", "Nanterre (92), France")
    assert _r("Consultant IAM H/F", "Paris (télétravail partiel)")                   # hybride Paris
    assert _r("Consultant IAM H/F", "Courbevoie 92400")
    assert _r("Consultant IAM H/F", "Remote - EMEA", True)
    assert _r("Consultant IAM H/F", "") is None


def test_fr_title_rules():
    assert _r("Stagiaire IAM", "Lyon")
    assert _r("Technicien support", "Lyon")
    assert _r("Ingénieur d'affaires cybersécurité", "Lyon")
    assert _r("Ingénieur sécurité IAM", "Lyon") is None


def test_french_departement():
    assert french_departement("Paris 08 - 75") == "75"
    assert french_departement("92 - NANTERRE") == "92"
    assert french_departement("Ajaccio (2A)") == "2a"
    assert french_departement("97400 Saint-Denis") == "974"
    assert french_departement("Lyon 03") is None


def test_gender_markers_dedupe():
    assert normalize_text("Consultant IAM H/F") == normalize_text("Consultant(e) IAM (F/H/X)") == "consultant iam"
    assert normalize_text("Chef·fe de projet Sécurité") == "chef de projet securite"
    assert fingerprint("Consultant IAM - F/H", "Sopra Steria SA") == fingerprint("Consultant·e IAM", "Sopra Steria")


def test_francetravail_mapping():
    p = build_params("consultant IAM", {"commune": "69266", "distance_km": 40}, 150, {"publiee_depuis": 7})
    assert p["range"] == "150-299" and p["commune"] == "69266" and p["distance"] == 40 and "departement" not in p
    job = to_raw({"id": "201ABCD", "intitule": "Consultant IAM (H/F)", "description": "Vous intégrez <b>Evidian</b>…",
                  "dateCreation": "2026-10-14T09:12:00.000Z", "lieuTravail": {"libelle": "69 - LYON 03"},
                  "entreprise": {"nom": "ACME"}, "typeContrat": "CDI", "typeContratLibelle": "Contrat à durée indéterminée",
                  "salaire": {"libelle": "Annuel de 45000,00 Euros à 55000,00 Euros"}})
    assert job.url == "https://candidat.francetravail.fr/offres/recherche/detail/201ABCD"
    assert job.location == "Lyon 03 (69), France" and job.employment_type == "CDI" and job.posted_at == "2026-10-14"
    assert job.salary_currency == "EUR" and "<b>" not in job.description
    assert _r(job.title, job.location) is None


def test_apec_body_configurable():
    b = build_body("IAM", 100, 0, {"contrats": ["101888"], "teletravail": []})
    assert b["typesContrat"] == ["101888"] and "typesTeletravail" not in b


def test_adzuna_currency():
    assert CURRENCY["fr"] == "EUR"


def test_scorer_families_from_config():
    w = FR["scoring"]["v2"]
    facts = {"role_family": "iam_iga", "duties_match": 3, "seniority": "senior", "years_required": 5,
             "employment_type": "permanent", "employer_type": "esn", "location_ok": True,
             "signals": ["tool_overlap", "telework"]}
    out = compute_v2(facts, w)
    assert not out["skip"] and out["fit_score"] >= 8, out
    out = compute_v2({**facts, "employment_type": "freelance"}, w)
    assert out["skip"] and "freelance" in out["skip_reason"]
    out = compute_v2({**facts, "role_family": "helpdesk_support"}, w)
    assert out["skip"]


def test_digest_date_fr():
    assert _date("2026-10-16", "fr") == "16/10/2026" and _date("2026-10-16", "en") == "2026-10-16"


def test_fr_templates_parse():
    from autojob.docs import parse_resume
    parts = parse_resume((ROOT / "profile.example.fr" / "resume.tex").read_text(encoding="utf-8"))
    assert parts.summary_text.startswith("Consultant IAM")
    assert [len(s.bullets) for s in parts.sections] == [5, 2]
    assert Path(ROOT / "profile.example.fr" / "candidate.md").exists()
