"""Local embedding-based opportunity ranking."""

import asyncio
import logging
import math
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Sequence

from fastembed import TextEmbedding

from app.models.opportunity import Opportunity
from app.models.user import User

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "fastembed_cache"
MAX_CACHED_EMBEDDINGS = 4096
BATCH_SIZE = 64
MAX_OPPORTUNITY_TEXT_LENGTH = 4000
DEFAULT_PROFILE = (
    "A student looking for early-career technology jobs, software internships, "
    "open-source fellowships, and student programs."
)

_embedding_lock = threading.Lock()
_embedding_model: TextEmbedding | None = None
_embedding_cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()


class RecommendationModelUnavailable(Exception):
    """Raised when the local embedding model cannot be initialized or run."""


def _profile_text(user: User) -> str:
    parts = [
        ("Career interests", user.target_roles),
        ("Skills", user.skills),
        ("About", user.bio),
        ("Education", user.college),
        ("Location", user.location),
    ]
    profile = ". ".join(f"{label}: {value.strip()}" for label, value in parts if value and value.strip())
    return profile or DEFAULT_PROFILE


def _opportunity_text(opportunity: Opportunity) -> str:
    tags = [
        tag.strip()
        for tag in (opportunity.tags or "").split(",")
        if tag.strip() and not tag.strip().lower().startswith("email:")
    ]
    parts = [
        f"Role: {opportunity.title}",
        f"Organization: {opportunity.organization}",
        opportunity.description or "",
        f"Skills and categories: {', '.join(tags)}" if tags else "",
        f"Location: {opportunity.location}" if opportunity.location else "",
        "Remote role" if opportunity.is_remote else "",
        f"Stipend: {opportunity.stipend}" if opportunity.stipend else "",
    ]
    text = ". ".join(part.strip() for part in parts if part and part.strip())
    return text[:MAX_OPPORTUNITY_TEXT_LENGTH]


def _get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        MODEL_CACHE_PATH.mkdir(parents=True, exist_ok=True)
        _embedding_model = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=str(MODEL_CACHE_PATH),
            threads=2,
        )
    return _embedding_model


def _embed_texts(texts: Sequence[str]) -> list[tuple[float, ...]]:
    try:
        with _embedding_lock:
            missing = list(dict.fromkeys(text for text in texts if text not in _embedding_cache))
            if missing:
                model = _get_embedding_model()
                vectors = model.embed(missing, batch_size=BATCH_SIZE)
                for text, vector in zip(missing, vectors):
                    _embedding_cache[text] = tuple(float(value) for value in vector.tolist())
                    _embedding_cache.move_to_end(text)
                while len(_embedding_cache) > MAX_CACHED_EMBEDDINGS:
                    _embedding_cache.popitem(last=False)

            embeddings = []
            for text in texts:
                vector = _embedding_cache[text]
                _embedding_cache.move_to_end(text)
                embeddings.append(vector)
            return embeddings
    except Exception as error:
        logger.exception("local_recommendation_embeddings_failed")
        raise RecommendationModelUnavailable("Could not load or run the local embedding model") from error


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _sort_opportunities(
    opportunities: Sequence[Opportunity],
    profile_embedding: Sequence[float],
    opportunity_embeddings: Sequence[Sequence[float]],
    limit: int,
) -> list[Opportunity]:
    ranked = zip(opportunities, opportunity_embeddings)

    def score(item: tuple[Opportunity, Sequence[float]]) -> float:
        opportunity, embedding = item
        relevance = _cosine_similarity(profile_embedding, embedding)
        contextual_bonus = 0.0
        contextual_bonus += 0.015 if opportunity.is_remote else 0.0
        contextual_bonus += 0.015 if opportunity.stipend else 0.0
        contextual_bonus += 0.02 if "intern" in (opportunity.tags or "").lower() else 0.0
        contextual_bonus += 0.01 if opportunity.source == "curated" else 0.0
        return relevance + contextual_bonus

    return [
        opportunity
        for opportunity, _ in sorted(ranked, key=score, reverse=True)[:limit]
    ]


async def rank_opportunities(
    user: User,
    opportunities: Sequence[Opportunity],
    limit: int,
) -> list[Opportunity]:
    """Rank opportunities against a user's profile without blocking the event loop."""
    if not opportunities:
        return []

    profile = _profile_text(user)
    texts = [profile, *(_opportunity_text(opportunity) for opportunity in opportunities)]
    embeddings = await asyncio.to_thread(_embed_texts, texts)
    return _sort_opportunities(opportunities, embeddings[0], embeddings[1:], limit)
