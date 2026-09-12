"""Deterministic, dependency-free search-query generation and video ranking for the Form
Guide's YouTube tutorial recommendation. Kept entirely separate from `client.py` (the actual
YouTube API calls) and `service.py` (caching/orchestration) so the ranking math itself is
directly unit-testable with plain dicts — no network, no mocking required.

Scoring approach (documented here since the brief asks for the reasoning to be explicit):

    overall = TITLE_WEIGHT   * title_relevance      (highest weight — a wrong-topic video
                                                       must never win just because it's popular)
            + KEYWORD_WEIGHT * keyword_relevance     (does it look like a how-to-apply video
                                                       at all, independent of the specific scheme)
            + VIEW_WEIGHT    * view_score            (log-normalized WITHIN the candidate set,
                                                       so one viral-but-unrelated video can't
                                                       single-handedly blow out the scale)
            + LIKE_WEIGHT    * like_score            (log-normalized the same way)
            + RECENCY_WEIGHT * recency_score          (newer content is likelier to reflect the
                                                       current, real application process)

A candidate below MIN_RELEVANCE_THRESHOLD is never selected — the Form Guide would rather show
"no suitable video" than a confidently-wrong recommendation (Section 10 of the brief).
"""

import math
import re
from datetime import datetime, timezone

_STOPWORDS = {"the", "a", "an", "of", "for", "and", "to", "in", "on", "is", "how"}

_HOWTO_KEYWORDS = [
    "form", "registration", "register", "apply", "application", "online",
    "fill", "filling", "process", "guide", "tutorial", "step by step",
    "kaise bhare", "kaise apply", "how to fill", "how to apply", "aavedan",
]

TITLE_WEIGHT = 0.45
KEYWORD_WEIGHT = 0.25
VIEW_WEIGHT = 0.15
LIKE_WEIGHT = 0.08
RECENCY_WEIGHT = 0.07

MIN_RELEVANCE_THRESHOLD = 0.35
RECENCY_HALF_LIFE_DAYS = 1825  # ~5 years — a linear floor, not a hard cutoff


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}


def build_search_query(scheme_name: str, category: str | None = None, issuing_authority: str | None = None) -> str:
    """Generates a specific, scheme-grounded query rather than a generic one (Section 13's
    "avoid overly generic queries" requirement) — the scheme's own name always anchors the
    query, with category/authority appended only as light disambiguating context, and a fixed
    how-to-apply phrase so results skew toward tutorials rather than news coverage."""
    parts = [scheme_name.strip()]
    if category:
        # Categories here are comma-joined (e.g. "Agriculture,Rural & Environment") — only the
        # first, most specific segment adds useful search signal; the rest is often too broad.
        first_category = category.split(",")[0].strip()
        if first_category:
            parts.append(first_category)
    parts.append("registration form filling online application process")
    return " ".join(parts)


def title_relevance(reference_tokens: set[str], video_title: str) -> float:
    if not reference_tokens:
        return 0.0
    title_tokens = _tokenize(video_title)
    matched = reference_tokens & title_tokens
    return len(matched) / len(reference_tokens)


def keyword_relevance(video_title: str, video_description: str) -> float:
    haystack = f"{video_title} {video_description or ''}".lower()
    matched = sum(1 for kw in _HOWTO_KEYWORDS if kw in haystack)
    return min(1.0, matched / 3)  # 3+ matched how-to phrases already reads as fully relevant


def _log_normalize(value: int, max_value: int) -> float:
    if max_value <= 0:
        return 0.0
    return math.log1p(max(0, value)) / math.log1p(max_value)


def recency_score(published_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_days = max(0, (now - published_at).days)
    return max(0.0, 1.0 - (age_days / RECENCY_HALF_LIFE_DAYS))


def score_video(video: dict, reference_tokens: set[str], max_views: int, max_likes: int, now: datetime | None = None) -> dict:
    """`video` is expected to carry: title, description, view_count, like_count, published_at
    (a real `datetime`). Returns the overall score plus every sub-score, so a caller (or a
    test) can see exactly why a video ranked where it did — never an opaque single number."""
    t_rel = title_relevance(reference_tokens, video["title"])
    k_rel = keyword_relevance(video["title"], video.get("description", ""))
    v_score = _log_normalize(video.get("view_count") or 0, max_views)
    l_score = _log_normalize(video.get("like_count") or 0, max_likes)
    r_score = recency_score(video["published_at"], now) if video.get("published_at") else 0.0

    overall = (
        TITLE_WEIGHT * t_rel
        + KEYWORD_WEIGHT * k_rel
        + VIEW_WEIGHT * v_score
        + LIKE_WEIGHT * l_score
        + RECENCY_WEIGHT * r_score
    )
    return {
        "overall": overall,
        "title_relevance": t_rel,
        "keyword_relevance": k_rel,
        "view_score": v_score,
        "like_score": l_score,
        "recency_score": r_score,
    }


def select_best_video(videos: list[dict], scheme_name: str, category: str | None = None) -> dict | None:
    """Ranks every candidate and returns the single best one — or None if nothing clears
    MIN_RELEVANCE_THRESHOLD, per Section 10's "do not recommend a weakly related video"."""
    if not videos:
        return None

    reference_tokens = _tokenize(scheme_name) | (_tokenize(category.split(",")[0]) if category else set())
    max_views = max((v.get("view_count") or 0) for v in videos)
    max_likes = max((v.get("like_count") or 0) for v in videos)

    now = datetime.now(timezone.utc)
    ranked = []
    for video in videos:
        scores = score_video(video, reference_tokens, max_views, max_likes, now)
        ranked.append({**video, **scores})
    ranked.sort(key=lambda v: v["overall"], reverse=True)

    best = ranked[0]
    if best["overall"] < MIN_RELEVANCE_THRESHOLD:
        return None
    return best
