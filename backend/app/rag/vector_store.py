"""Chroma wrapper (Section 3.6: "Chroma for local development/prototyping" — matches this
project's own "no unnecessary infrastructure for a locally-run prototype" stance from
plan.md Section 10). One collection, `policy_chunks`, holds every indexed PolicyChunk.
"""

import uuid

import chromadb
from chromadb.api.models.Collection import Collection

COLLECTION_NAME = "policy_chunks"


def get_persistent_collection(persist_dir: str) -> Collection:
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(COLLECTION_NAME)


def get_ephemeral_collection() -> Collection:
    """In-memory collection for tests. Each call gets its own uniquely-named collection on a
    fresh EphemeralClient — chromadb caches its underlying System by client settings, so two
    same-named collections from separate EphemeralClient() calls in the same test process can
    otherwise resolve to the same cached collection (and its already-fixed embedding
    dimension), breaking the isolated-per-test guarantee `mongomock`'s `db` fixture gives us
    elsewhere."""
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(f"{COLLECTION_NAME}_{uuid.uuid4().hex}")


def upsert_chunks(
    collection: Collection,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    if not ids:
        return
    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def count(collection: Collection) -> int:
    return collection.count()


def existing_ids(collection: Collection) -> set[str]:
    """All chunk_ids already indexed — lets ingestion skip re-embedding (and re-spending
    embedding-API quota on) chunks a prior, quota-interrupted run already persisted."""
    return set(collection.get(include=[])["ids"])
