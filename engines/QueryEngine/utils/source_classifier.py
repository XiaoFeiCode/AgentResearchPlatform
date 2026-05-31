"""Source classification helpers for QueryEngine.

QueryEngine is used as the authority/fact-checking engine. These helpers keep
source trust decisions deterministic instead of relying only on prompts.
"""

from __future__ import annotations

from urllib.parse import urlparse


OFFICIAL_DOMAINS = (
    "gov.cn",
    "www.gov.cn",
    "stats.gov.cn",
    "ndrc.gov.cn",
    "mof.gov.cn",
    "miit.gov.cn",
    "pbc.gov.cn",
    "csrc.gov.cn",
    "samr.gov.cn",
    "mee.gov.cn",
    "customs.gov.cn",
    "court.gov.cn",
    "spp.gov.cn",
    "moe.gov.cn",
    "mps.gov.cn",
    "mfa.gov.cn",
    "nhc.gov.cn",
)

AUTHORITATIVE_MEDIA_DOMAINS = (
    "xinhuanet.com",
    "people.com.cn",
    "cctv.com",
    "china.com.cn",
    "chinanews.com.cn",
    "gmw.cn",
    "ce.cn",
)

ACADEMIC_DOMAINS = (
    "edu.cn",
    "ac.cn",
    "cnki.net",
)

AUTHORITY_SEARCH_DOMAINS = (
    "gov.cn",
    "stats.gov.cn",
    "ndrc.gov.cn",
    "mof.gov.cn",
    "miit.gov.cn",
)


def _hostname(url: str) -> str:
    host = urlparse(url or "").hostname or ""
    return host.lower().lstrip("www.")


def _matches_domain(host: str, domain: str) -> bool:
    domain = domain.lower().lstrip("www.")
    return host == domain or host.endswith("." + domain)


def classify_source(url: str) -> dict[str, str]:
    """Classify a search result URL into a trust tier."""
    host = _hostname(url)

    if any(_matches_domain(host, domain) for domain in OFFICIAL_DOMAINS):
        return {
            "source_type": "official",
            "credibility": "very_high",
            "source_label": "官方来源",
            "source_domain": host,
        }

    if any(_matches_domain(host, domain) for domain in ACADEMIC_DOMAINS):
        return {
            "source_type": "academic",
            "credibility": "high",
            "source_label": "学术/研究来源",
            "source_domain": host,
        }

    if any(_matches_domain(host, domain) for domain in AUTHORITATIVE_MEDIA_DOMAINS):
        return {
            "source_type": "authoritative_media",
            "credibility": "high",
            "source_label": "权威媒体",
            "source_domain": host,
        }

    return {
        "source_type": "media_or_unknown",
        "credibility": "medium",
        "source_label": "普通媒体或未知来源",
        "source_domain": host,
    }


def build_authority_queries(query: str, max_domains: int = 2) -> list[str]:
    """Build a small set of official-source-biased queries.

    Keep this intentionally small to avoid multiplying search API cost.
    """
    base = query.strip()
    if not base:
        return []

    queries = [base]
    if "site:" in base.lower():
        return queries

    for domain in AUTHORITY_SEARCH_DOMAINS[:max_domains]:
        queries.append(f"site:{domain} {base}")
    return queries


def source_rank(source_type: str) -> int:
    """Lower rank means more authoritative."""
    return {
        "official": 0,
        "academic": 1,
        "authoritative_media": 2,
        "media_or_unknown": 3,
    }.get(source_type, 4)
