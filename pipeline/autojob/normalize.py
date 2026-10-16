"""Text/URL normalization and duplicate fingerprinting."""
from __future__ import annotations

import html as html_module
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

MAX_DESCRIPTION = 4000

_TRACKING_PARAMS = re.compile(r"^(utm_|ref$|refId$|trackingId$|source$|src$|fbclid$|gclid$|mc_|_ga$|position$|pageNum$|trk$)", re.I)

# Hosts where only one query parameter identifies the job.
_KEEP_PARAMS = {
    "indeed.com": {"jk", "vjk"},
    "jooble.org": set(),
}


def clean_html(raw: str | None) -> str:
    if not raw:
        return ""
    if "<" not in raw:
        return html_module.unescape(raw).strip()
    text = BeautifulSoup(raw, "lxml").get_text(separator="\n")
    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def truncate(text: str, limit: int = MAX_DESCRIPTION) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def snippet_of(text: str, limit: int = 220) -> str:
    one_line = re.sub(r"\s+", " ", text or "").strip()
    return one_line[:limit]


# Hosts whose bare domain redirects to the homepage (path lost) — the "www." must stay.
_KEEP_WWW = {"www.apec.fr"}


def canonical_url(url: str) -> str:
    """Strip tracking parameters and normalise host so the same posting dedupes across sources."""
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host.startswith("www.") and host not in _KEEP_WWW:
        host = host[4:]
    path = re.sub(r"/+$", "", parts.path) or "/"

    keep: set[str] | None = None
    for h, params in _KEEP_PARAMS.items():
        if host.endswith(h):
            keep = params
            break

    query_pairs = []
    for k, v in parse_qsl(parts.query, keep_blank_values=False):
        if keep is not None:
            if k in keep:
                query_pairs.append((k, v))
            continue
        if _TRACKING_PARAMS.match(k):
            continue
        query_pairs.append((k, v))

    # LinkedIn: /jobs/view/<slug>-<id> → keep only the numeric id
    if host.endswith("linkedin.com"):
        m = re.search(r"/jobs/view/(?:[^/]*?-)?(\d+)", path)
        if m:
            path = f"/jobs/view/{m.group(1)}"
            query_pairs = []
        host = "linkedin.com"

    return urlunsplit(("https", host, path, urlencode(sorted(query_pairs)), ""))


_SUFFIXES = re.compile(r"\b(inc|llc|ltd|co|corp|corporation|limited|gmbh|ag|sa|sas|sasu|sarl|eurl|sca|snc|se|plc|company"
                       r"|groupe|group)\b\.?", re.I)
# French job titles carry gender markers in every spelling: "Consultant IAM H/F", "(F/H)", "- F/H/X",
# "Consultant·e", "Consultant(e)", "Chef.fe de projet". Stripped so the same posting dedupes across boards.
_GENDER = re.compile(r"[\(\[]?\b(?:h\s*/\s*f\s*/\s*x|f\s*/\s*h\s*/\s*x|h\s*/\s*f|f\s*/\s*h|m\s*/\s*f|f\s*/\s*m|"
                     r"m\s*/\s*w\s*/\s*d|w\s*/\s*m\s*/\s*d|hf|fh)\b[\)\]]?", re.I)
_INCLUSIVE = re.compile(r"(\w)(?:[·.•]|\()(?:e|fe|se|euse|rice|trice|ne|le)s?\)?(?=\b)", re.I)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_text(text: str | None) -> str:
    text = (text or "").lower()
    text = _GENDER.sub(" ", text)
    text = _INCLUSIVE.sub(r"\1", text)
    text = strip_accents(text)
    text = _SUFFIXES.sub("", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


_LEADING_ARTICLE = re.compile(r"^(the|la|le|les|l)\s+")


def company_key(company: str | None) -> str:
    """Short, stable key for a company name so boards that spell it differently still match:
    "The University of British Columbia" / "University of British Columbia" → "university of";
    "Agentis Capital Advisors" / "Agentis Capital" → "agentis capital"."""
    c = _LEADING_ARTICLE.sub("", normalize_text(company))
    return " ".join(c.split()[:2])


def fingerprint(title: str | None, company: str | None) -> str | None:
    t, c = normalize_text(title), company_key(company)
    if not t or not c or c in ("unknown", "confidential", "not specified"):
        return None
    return f"{t}|{c}"


def domain_of(url: str) -> str:
    try:
        host = urlsplit(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host
