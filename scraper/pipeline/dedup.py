import hashlib
import pickle
import numpy as np
from openai import OpenAI
from scraper.config import OPENAI_API_KEY, SIMILARITY_THRESHOLD
from scraper.pipeline.store import get_all_hashes, get_all_embeddings

client = OpenAI(api_key=OPENAI_API_KEY)


def hash_question(text: str) -> str:
    """SHA-256 hash of normalized question text."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def embed_question(text: str) -> bytes:
    """Get embedding from OpenAI and serialize to bytes for SQLite storage."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text.strip(),
    )
    vector = response.data[0].embedding
    return pickle.dumps(vector)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_canonical(
    embedding_bytes: bytes,
    existing: list[dict],
) -> str | None:
    """
    Compare a new question's embedding against all existing questions.
    Returns the canonical_id of the best match if similarity >= threshold.
    Returns None if no match found (new canonical question).
    """
    if not existing:
        return None

    new_vector = pickle.loads(embedding_bytes)
    best_score = 0.0
    best_canonical_id = None

    for row in existing:
        if not row["embedding"]:
            continue
        existing_vector = pickle.loads(row["embedding"])
        score = cosine_similarity(new_vector, existing_vector)
        if score > best_score:
            best_score = score
            best_canonical_id = row["canonical_id"]

    if best_score >= SIMILARITY_THRESHOLD:
        return best_canonical_id

    return None


def process_question(
    question: dict,
    known_hashes: set,
    known_embeddings: list,
) -> dict | None:
    """
    Run a question through the full dedup pipeline.

    Args:
        question: question dict from extraction
        known_hashes: set of content_hash strings already in DB (updated by caller after save)
        known_embeddings: list of {id, canonical_id, embedding} dicts (updated by caller after save)

    Returns:
      - dict with content_hash, embedding, and canonical_id set → save to DB
      - None → exact duplicate, discard silently
    """
    content_hash = hash_question(question["question_text"])

    # Step 1: exact duplicate check
    if content_hash in known_hashes:
        return None  # exact duplicate — discard silently

    # Step 2: get embedding
    embedding_bytes = embed_question(question["question_text"])

    # Step 3: similarity check against existing questions
    canonical_id = find_canonical(embedding_bytes, known_embeddings)

    question["content_hash"] = content_hash
    question["embedding"] = embedding_bytes
    # canonical_id=None means it becomes its own canonical (handled in store.py)
    question["canonical_id"] = canonical_id

    return question
