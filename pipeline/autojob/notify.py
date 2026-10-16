"""Telegram digest — one message per run (chunked only if it exceeds Telegram's limit)."""
from __future__ import annotations

import html
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import requests

from autojob.normalize import company_key
from autojob.settings import Settings

logger = logging.getLogger("autojob")
MAX_LEN = 4000
TOP_N = 15
FRESH_DAYS = 3      # freshness bonus is full up to here…
STALE_DAYS = 14     # …decaying linearly to 0, and the digest drops anything scored older (report 06:
                   # nothing unreviewed past ~6 days has ever been applied)


def _send(settings: Settings, text: str) -> bool:
    tok, chat = settings.secrets.telegram_bot_token, settings.secrets.telegram_chat_id
    if not (tok and chat):
        logger.info("telegram not configured — digest:\n%s", text)
        return False
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    for chunk in _chunks(text):
        for _attempt in range(4):
            try:
                r = requests.post(url, json={"chat_id": chat, "text": chunk, "parse_mode": "HTML",
                                             "disable_web_page_preview": True}, timeout=20)
            except requests.RequestException as e:
                logger.warning("telegram send failed: %s", e)
                time.sleep(3)
                continue
            if r.status_code == 429:
                wait = int((r.json().get("parameters") or {}).get("retry_after", 5)) + 1
                time.sleep(wait)
                continue
            if r.status_code != 200:
                logger.warning("telegram error %s: %s", r.status_code, r.text[:200])
            break
    logger.info("telegram: sent %d chars in %d message(s)", len(text), len(_chunks(text)))
    return True


def _chunks(text: str) -> list[str]:
    out: list[str] = []
    while len(text) > MAX_LEN:
        cut = text.rfind("\n\n", 0, MAX_LEN)
        cut = cut if cut > 0 else text.rfind("\n", 0, MAX_LEN)
        cut = cut if cut > 0 else MAX_LEN
        out.append(text[:cut])
        text = text[cut:].lstrip("\n")
    out.append(text)
    return out


def _e(s: Any) -> str:
    return html.escape(str(s or ""), quote=False)


def digest_jobs(queued: list[dict[str, Any]], cfg: dict[str, Any], dismiss_counts: dict[str, int],
                today: datetime | None = None) -> list[dict[str, Any]]:
    """Digest candidates ranked by expected apply instead of raw score (plan 2026-10-06 item 19):
    rank = fit_score + source_prior + freshness bonus − low_confidence penalty − company dismissal count.
    Demoted classes stay in the dashboard, out of the digest: scored > 14 days ago, low_confidence=1
    (0/41 lifetime applies). Sorting happens here in Python; the SQL stays simple."""
    now = today or datetime.now(UTC)
    priors = {str(k): float(v) for k, v in (cfg.get("source_priors") or {}).items()}
    fresh_bonus = float(cfg.get("freshness_bonus", 1.0))
    low_pen = float(cfg.get("low_confidence_penalty", 1.0))
    out: list[dict[str, Any]] = []
    for j in queued:
        days = STALE_DAYS
        if j.get("scored_at"):
            try:
                days = (now - datetime.fromisoformat(j["scored_at"])).days
            except ValueError:
                pass
        low_conf = bool(j.get("low_confidence"))
        if days > STALE_DAYS or low_conf:
            continue
        rank = ((j.get("fit_score") or 0)
                + priors.get(j.get("source") or "", 0.0)
                + fresh_bonus * (1.0 if days <= FRESH_DAYS else max(0.0, (STALE_DAYS - days) / (STALE_DAYS - FRESH_DAYS)))
                - (low_pen if low_conf else 0.0)
                - float(dismiss_counts.get(company_key(j.get("company")), 0)))
        row = dict(j)
        row["_rank"] = round(rank, 2)
        out.append(row)
    out.sort(key=lambda r: (-r["_rank"], -(r.get("fit_score") or 0), r.get("id") or 0))
    return out


STRINGS = {
    "en": {"fetched": "fetched", "new": "new", "filtered": "filtered", "scored": "scored", "worth": "worth a look",
           "errors": "errors", "retired": "old postings retired", "nothing": "Nothing cleared the bar today.",
           "more": "…and {n} more in the dashboard.", "expiring": "⏳ {n} pending job{s} retire within 3 days — review now.",
           "open": "Open the review queue", "alert": "Autojob alert"},
    "fr": {"fetched": "récupérées", "new": "nouvelles", "filtered": "filtrées", "scored": "notées",
           "worth": "à regarder", "errors": "erreurs", "retired": "anciennes offres retirées",
           "nothing": "Aucune offre n'a passé le seuil aujourd'hui.", "more": "…et {n} de plus dans le tableau de bord.",
           "expiring": "⏳ {n} offre{s} en attente expire{nt} sous 3 jours — à traiter maintenant.",
           "open": "Ouvrir la file de revue", "alert": "Alerte Autojob"},
}


def _t(settings: Settings) -> dict[str, str]:
    return STRINGS.get(getattr(settings, "language", "en"), STRINGS["en"])


def _date(iso: str, lang: str) -> str:
    """2026-10-16 → 16/10/2026 in French."""
    if lang == "fr" and len(iso) == 10 and iso[4] == "-":
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    return iso


def send_digest(settings: Settings, run: dict[str, Any], queued: list[dict[str, Any]],
                expiring_soon: int = 0) -> None:
    t = _t(settings)
    lang = getattr(settings, "language", "en")
    date = _date((run.get("started_at") or "")[:10], lang)
    lines = [f"<b>Autojob — {date}</b>"]
    lines.append(
        f"{run.get('fetched', 0)} {t['fetched']} · {run.get('new_jobs', 0)} {t['new']} · "
        f"{run.get('prefiltered', 0)} {t['filtered']} · "
        f"{run.get('scored', 0)} {t['scored']} → <b>{len(queued)} {t['worth']}</b>"
        + (f" · {run['errors']} {t['errors']}" if run.get("errors") else "")
        + (f" · {run['expired']} {t['retired']}" if run.get("expired") else "")
    )
    if not queued:
        lines.append("\n" + t["nothing"])
    else:
        lines.append("")
        for j in queued[:TOP_N]:
            score = j.get("fit_score")
            flag = "🔥" if (score or 0) >= 8 else "✅"
            docs = " 📄" if j.get("status") == "docs_generated" else ""
            loc = f" · {_e(j['location'])[:40]}" if j.get("location") else ""
            lines.append(f"{flag} <b>{score}/10</b> · <a href=\"{_e(j.get('url'))}\">{_e(j.get('title'))}</a>{docs}")
            lines.append(f"    {_e(j.get('company'))}{loc} · <i>{_e(j.get('source'))}</i>")
            if j.get("fit_reasoning"):
                lines.append(f"    {_e(j['fit_reasoning'])[:220]}")
            lines.append("")
        if len(queued) > TOP_N:
            lines.append(t["more"].format(n=len(queued) - TOP_N))
    if expiring_soon:
        plural = expiring_soon != 1
        lines.append("\n" + t["expiring"].format(n=expiring_soon, s="s" if plural else "", nt="nt" if plural else ""))
    dash = os.getenv("DASHBOARD_URL") or settings.get("profile.dashboard_url")
    if dash:
        lines.append(f"\n<a href=\"{_e(dash)}\">{t['open']}</a>")
    _send(settings, "\n".join(lines))


def send_alert(settings: Settings, message: str) -> None:
    _send(settings, f"<b>{_t(settings)['alert']}</b>\n\n{_e(message)[:3000]}")
