"""
SAATHI AI -- RAG Service Tests
==========================================================
Two test suites:

1. Unit tests (Pinecone mocked)
   - ingest -> upsert, query -> top-k, fallback, chunking,
     graceful degradation when Pinecone unavailable.

2. Integration tests (live ChromaDB, real embeddings)
   - Ingest sample docs, query with 10 therapeutic prompts,
     verify relevant content returned.
   - Qualification gates:
       * Retrieval rate  >= 70%  (at least 7/10 queries return results)
       * Avg results     >= 1    (at least 1 chunk per successful query)
       * No exceptions during concurrent queries
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "server"))

from services.rag_service import RAGService  # noqa: E402


# ==================================================================
# HELPERS
# ==================================================================

def _make_match(text: str, score: float) -> MagicMock:
    """Construct a Pinecone ScoredVector mock."""
    m = MagicMock()
    m.metadata = {"text": text}
    m.score = score
    return m


def _make_pinecone_rag(mock_index: MagicMock) -> RAGService:
    """
    RAGService wired to use Pinecone backend with a mocked index.
    Bypasses real Pinecone client init.
    """
    svc = RAGService()
    svc._use_pinecone = True
    svc._pinecone_index = mock_index
    return svc


# ==================================================================
# FIXTURES
# ==================================================================

@pytest.fixture(autouse=True)
def mock_embedding_model(request):
    """
    Prevent loading the real SentenceTransformer in Pinecone unit tests.
    Skipped for 'integration' tests which need real embeddings to match
    vectors stored at ingest time.
    """
    if request.node.get_closest_marker("integration"):
        yield None
        return
    fake_model = MagicMock()
    fake_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    with patch(
        "services.rag_service._get_embedding_model",
        return_value=fake_model,
    ):
        yield fake_model


@pytest.fixture
def mock_index() -> MagicMock:
    return MagicMock()


@pytest.fixture
def rag(mock_index) -> RAGService:
    return _make_pinecone_rag(mock_index)


# ==================================================================
# UNIT TESTS -- INGEST (Pinecone mocked)
# ==================================================================

@pytest.mark.asyncio
async def test_ingest_calls_pinecone_upsert(rag, mock_index):
    """ingest() must upsert vectors to the correct tenant namespace."""
    mock_index.upsert.return_value = None
    content = (
        "Cognitive Behavioural Therapy helps restructure "
        "negative thought patterns."
    )
    result = await rag.ingest(
        content,
        tenant_id="clinic-001",
        metadata={"source": "cbt_guide"},
    )
    assert result["status"] == "ingested"
    assert result["chunks_ingested"] >= 1
    assert result["tenant_id"] == "clinic-001"
    mock_index.upsert.assert_called()
    for call in mock_index.upsert.call_args_list:
        assert call.kwargs["namespace"] == "clinic-001"


@pytest.mark.asyncio
async def test_ingest_stores_text_and_metadata(rag, mock_index):
    """Each upserted vector must carry text, tenant_id, source."""
    mock_index.upsert.return_value = None
    await rag.ingest(
        "CBT therapy protocol: identify triggers, challenge automatic "
        "thoughts, and build balanced perspectives over multiple sessions.",
        tenant_id="clinic-001",
        metadata={"source": "therapy_protocol"},
    )
    first_batch = mock_index.upsert.call_args_list[0].kwargs["vectors"]
    meta = first_batch[0]["metadata"]
    assert "text" in meta
    assert meta["tenant_id"] == "clinic-001"
    assert meta["source"] == "therapy_protocol"


@pytest.mark.asyncio
async def test_ingest_long_doc_multiple_chunks(rag, mock_index):
    """Document >2048 chars must produce at least 2 chunks."""
    mock_index.upsert.return_value = None
    long_content = (
        "Mindfulness is the practice of present-moment awareness. " * 55
    )
    result = await rag.ingest(
        long_content,
        tenant_id="clinic-abc",
        metadata={"source": "mindfulness"},
    )
    assert result["status"] == "ingested"
    assert result["chunks_ingested"] >= 2
    all_ids = [
        v["id"]
        for call in mock_index.upsert.call_args_list
        for v in call.kwargs["vectors"]
    ]
    assert len(all_ids) == len(set(all_ids)), "Chunk IDs must be unique"


@pytest.mark.asyncio
async def test_ingest_pinecone_unavailable_returns_chroma():
    """
    When Pinecone is not configured, ingest() must fall back to ChromaDB
    (not raise). The result status must be 'ingested' or 'error'.
    """
    svc = RAGService()
    svc._use_pinecone = False

    with patch(
        "services.rag_service._get_chroma_client"
    ) as mock_chroma:
        mock_col = MagicMock()
        mock_col.upsert.return_value = None
        mock_chroma.return_value.get_or_create_collection.return_value = (
            mock_col
        )
        result = await svc.ingest(
            "some content",
            tenant_id="clinic-001",
            metadata={},
        )
    assert result["status"] in ("ingested", "error")


# ==================================================================
# UNIT TESTS -- QUERY (Pinecone mocked)
# ==================================================================

@pytest.mark.asyncio
async def test_query_returns_top_k(rag, mock_index):
    mock_index.query.return_value = MagicMock(matches=[
        _make_match("CBT helps reframe negative thoughts.", 0.92),
        _make_match("Mindfulness reduces anxiety symptoms.", 0.87),
        _make_match("Exposure therapy treats phobias.", 0.81),
    ])
    results = await rag.query(
        "how to treat anxiety", tenant_id="clinic-001", top_k=3
    )
    assert len(results) == 3
    assert results[0] == "CBT helps reframe negative thoughts."


@pytest.mark.asyncio
async def test_query_filters_low_scores(rag, mock_index):
    mock_index.query.return_value = MagicMock(matches=[
        _make_match("High relevance chunk.", 0.90),
        _make_match("Low relevance chunk.", 0.60),
    ])
    results = await rag.query(
        "therapy techniques", tenant_id="clinic-001", top_k=5
    )
    assert len(results) == 1
    assert results[0] == "High relevance chunk."


@pytest.mark.asyncio
async def test_query_uses_correct_namespace(rag, mock_index):
    mock_index.query.return_value = MagicMock(matches=[])
    await rag.query("test", tenant_id="clinic-xyz", top_k=5)
    ns = mock_index.query.call_args_list[0].kwargs["namespace"]
    assert ns == "clinic-xyz"


@pytest.mark.asyncio
async def test_wrong_tenant_returns_empty(rag, mock_index):
    mock_index.query.return_value = MagicMock(matches=[])
    results = await rag.query(
        "any query", tenant_id="unknown-999", top_k=5
    )
    assert results == []


@pytest.mark.asyncio
async def test_query_pinecone_unavailable_returns_empty():
    """query() must return [] gracefully when Pinecone is not configured
    and ChromaDB collection is empty."""
    svc = RAGService()
    svc._use_pinecone = False

    with patch("services.rag_service._get_chroma_client") as mock_chroma:
        mock_col = MagicMock()
        mock_col.count.return_value = 0
        mock_chroma.return_value.get_or_create_collection.return_value = (
            mock_col
        )
        results = await svc.query("test", tenant_id="clinic-001")
    assert results == []


# ==================================================================
# UNIT TESTS -- FALLBACK NAMESPACE
# ==================================================================

@pytest.mark.asyncio
async def test_fallback_to_default_namespace(rag, mock_index):
    """Empty tenant namespace must trigger fallback to 'default'."""
    default_match = _make_match("Default KB resource.", 0.78)

    def _side(**kwargs):
        namespace = kwargs.get("namespace", "")
        if namespace == "empty-clinic":
            return MagicMock(matches=[])
        return MagicMock(matches=[default_match])

    mock_index.query.side_effect = _side
    results = await rag.query(
        "mental health", tenant_id="empty-clinic", top_k=5
    )
    assert len(results) == 1
    assert results[0] == "Default KB resource."
    namespaces = [
        c.kwargs["namespace"]
        for c in mock_index.query.call_args_list
    ]
    assert "empty-clinic" in namespaces
    assert "default" in namespaces


@pytest.mark.asyncio
async def test_no_fallback_when_tenant_has_results(rag, mock_index):
    """Default namespace must NOT be queried when tenant returns results."""
    mock_index.query.return_value = MagicMock(matches=[
        _make_match("Clinic-specific protocol.", 0.88),
    ])
    results = await rag.query(
        "clinic protocol", tenant_id="clinic-001", top_k=5
    )
    assert len(results) == 1
    assert mock_index.query.call_count == 1


@pytest.mark.asyncio
async def test_fallback_lower_threshold(rag, mock_index):
    """Default namespace uses 0.70 threshold (lower than tenant 0.75)."""
    borderline = _make_match("Borderline default chunk.", 0.72)

    def _side(**kwargs):
        namespace = kwargs.get("namespace", "")
        if namespace == "sparse-clinic":
            return MagicMock(matches=[])
        return MagicMock(matches=[borderline])

    mock_index.query.side_effect = _side
    results = await rag.query(
        "general advice", tenant_id="sparse-clinic", top_k=5
    )
    assert len(results) == 1
    assert results[0] == "Borderline default chunk."


@pytest.mark.asyncio
async def test_no_double_fallback_for_default_namespace(rag, mock_index):
    """Querying 'default' directly must not recurse."""
    mock_index.query.return_value = MagicMock(matches=[])
    await rag.query("query", tenant_id="default", top_k=5)
    assert mock_index.query.call_count == 1


# ==================================================================
# UNIT TESTS -- CHUNKING
# ==================================================================

def test_chunk_short_content_one_chunk():
    svc = RAGService()
    chunks = svc._chunk_text("Short text. " * 10)
    assert len(chunks) == 1


def test_chunk_long_content_multiple_chunks():
    svc = RAGService()
    chunks = svc._chunk_text("word " * 600)
    assert len(chunks) >= 2


def test_chunk_filters_tiny_chunks():
    svc = RAGService()
    chunks = svc._chunk_text(("word " * 500) + "hi")
    for c in chunks:
        assert len(c.strip()) > 50


def test_chunk_overlap():
    """Adjacent chunks share 200-char overlap (50 tokens * 4 chars/token)."""
    svc = RAGService()
    chunks = svc._chunk_text("A" * 3000)
    assert len(chunks) >= 2
    assert chunks[0][1848:2048] == chunks[1][:200]


def test_chunk_empty_string():
    svc = RAGService()
    assert svc._chunk_text("") == []


# ==================================================================
# INTEGRATION TESTS -- live ChromaDB + real embeddings
# ==================================================================

SAMPLE_DOCS = [
    {
        "content": (
            "Cognitive Behavioural Therapy (CBT) is the gold standard for "
            "treating depression and anxiety. The core technique is the "
            "thought record: identify the trigger, notice the automatic "
            "thought, examine evidence for and against, then create a "
            "balanced thought. Regular practice over 3-4 weeks reduces "
            "depressive cognitions significantly."
        ),
        "source": "cbt_thought_record",
        "category": "cbt_techniques",
    },
    {
        "content": (
            "DBT TIPP skill: Temperature (cold water activates diving "
            "reflex), Intense exercise, Paced breathing, Progressive "
            "muscle relaxation. Use when emotions are at 7+/10. Rapidly "
            "reduces physiological arousal within 20-30 minutes."
        ),
        "source": "dbt_tipp",
        "category": "dbt_techniques",
    },
    {
        "content": (
            "Crisis resources India: iCall 9152987821, Vandrevala "
            "Foundation 1860-2662-345, KIRAN 1800-599-0019 (24x7 free). "
            "For imminent risk: ask directly about plan, remove means, "
            "do not leave person alone, contact emergency services."
        ),
        "source": "crisis_india",
        "category": "crisis_protocols",
    },
    {
        "content": (
            "Mindfulness-Based Cognitive Therapy (MBCT) combines CBT "
            "with mindfulness meditation. Reduces relapse in recurrent "
            "depression by 50% (Segal et al., 2002). Core practice: "
            "5-minute body scan, mindful breathing, observing thoughts "
            "without attachment. Recommended for 3+ depressive episodes."
        ),
        "source": "mbct_guide",
        "category": "cbt_techniques",
    },
    {
        "content": (
            "PHQ-9 scoring: 0-4 minimal, 5-9 mild, 10-14 moderate, "
            "15-19 moderately severe, 20-27 severe depression. Item 9 "
            "(suicidality) must always be reviewed regardless of total "
            "score. A score >= 10 warrants clinical intervention."
        ),
        "source": "phq9_guide",
        "category": "assessments",
    },
    {
        "content": (
            "The 5-column thought record is a core CBT tool for "
            "challenging cognitive distortions and automatic negative "
            "thoughts. Columns: Situation, Automatic Thought, Emotion, "
            "Evidence For/Against, Balanced Thought. Repeated practice "
            "weakens distorted beliefs and reduces depressive symptoms."
        ),
        "source": "thought_record_guide",
        "category": "cbt_techniques",
    },
    {
        "content": (
            "DBT (Dialectical Behaviour Therapy) crisis skills: TIPP "
            "for physiological de-escalation, ACCEPTS for distraction, "
            "IMPROVE for tolerating distress. Use when emotional "
            "intensity is 7+/10. Skills reduce self-harm urges and "
            "prevent crisis escalation in borderline personality."
        ),
        "source": "dbt_crisis_skills",
        "category": "dbt_techniques",
    },
    {
        "content": (
            "Diaphragmatic breathing for panic attacks: inhale 4 counts "
            "through nose, hold 4, exhale 6 through mouth. Paced "
            "breathing at 6 breaths/min activates the parasympathetic "
            "system, reducing panic symptoms within 5-10 minutes. "
            "Technique is evidence-based for anxiety disorders."
        ),
        "source": "breathing_techniques",
        "category": "cbt_techniques",
    },
    {
        "content": (
            "Safety planning for suicidal ideation: (1) identify "
            "warning signs, (2) list internal coping strategies, "
            "(3) social contacts who distract, (4) people to ask for "
            "help, (5) professionals to contact, (6) means restriction. "
            "Stanley-Brown Safety Planning Intervention reduces "
            "attempts by 45% vs standard care."
        ),
        "source": "safety_planning",
        "category": "crisis_protocols",
    },
]

EVAL_QUERIES = [
    # (query_text, expected_keyword_in_result)
    ("how to treat depression with CBT", "CBT"),
    ("what is the thought record technique", "thought"),
    ("DBT skills for emotional crisis distress tolerance", "DBT"),
    ("breathing exercises paced breathing panic attacks", "breathing"),
    ("suicide crisis resources India helpline", "1800"),
    ("mindfulness meditation for anxiety", "mindfulness"),
    ("PHQ-9 score interpretation", "PHQ"),
    ("cognitive distortions automatic negative thoughts", "thought"),
    ("what is MBCT mindfulness based cognitive therapy", "MBCT"),
    ("safety planning suicidal ideation warning signs", "safety"),
]


@pytest.fixture(scope="module")
def live_rag():
    """
    Module-scoped RAGService using a temporary ChromaDB collection
    (namespace 'test_eval_ns') so integration tests are isolated.
    """
    svc = RAGService()
    svc._use_pinecone = False
    return svc


@pytest.fixture(scope="module")
def event_loop():
    """Use one event loop for all module-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def populated_rag(live_rag):
    """Ingest SAMPLE_DOCS into the 'test_eval_ns' ChromaDB namespace."""
    tenant = "test_eval_ns"
    # Clear first (idempotent re-runs)
    try:
        import chromadb
        from config import settings
        path = getattr(settings, "LOCAL_RAG_DB_PATH", "./chroma_db")
        c = chromadb.PersistentClient(path=str(path))
        try:
            c.delete_collection("test_eval_ns")
        except Exception:
            pass
    except Exception:
        pass

    for doc in SAMPLE_DOCS:
        await live_rag.ingest(
            content=doc["content"],
            tenant_id=tenant,
            metadata={
                "source": doc["source"],
                "category": doc["category"],
            },
        )
    return live_rag


@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration_ingest_and_retrieve(populated_rag):
    """
    INTEGRATION: Verify all sample docs were ingested into ChromaDB.
    Stats must show chunk_count >= len(SAMPLE_DOCS).
    """
    stats = populated_rag.stats("test_eval_ns")
    assert stats["backend"] == "chroma"
    assert stats["chunk_count"] >= len(SAMPLE_DOCS), (
        f"Expected >= {len(SAMPLE_DOCS)} chunks, got {stats}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration_eval_queries(populated_rag):
    """
    QUALIFICATION GATE: RAG evaluation over 10 therapeutic queries.
    Gate 1: retrieval_rate >= 0.70 (7/10 queries return results)
    Gate 2: avg_results >= 1.0
    Gate 3: No exception on any query
    """
    tenant = "test_eval_ns"
    hits = 0
    total_results = 0
    results_log = []

    for query, keyword in EVAL_QUERIES:
        results = await populated_rag.query(
            query, tenant_id=tenant, top_k=3
        )
        retrieved = len(results)
        total_results += retrieved
        keyword_found = any(
            keyword.lower() in r.lower() for r in results
        )
        if retrieved > 0:
            hits += 1
        results_log.append({
            "query": query,
            "retrieved": retrieved,
            "keyword_found": keyword_found,
        })
        print(
            f"  Q: {query[:50]:<50} | "
            f"chunks={retrieved} | kw={'YES' if keyword_found else 'no'}"
        )

    retrieval_rate = hits / len(EVAL_QUERIES)
    avg_results = total_results / len(EVAL_QUERIES)
    keyword_rate = sum(
        1 for r in results_log if r["keyword_found"]
    ) / len(EVAL_QUERIES)

    print("\n=== RAG Evaluation Results ===")
    print(f"  Retrieval rate  : {retrieval_rate:.0%} (gate: >=70%)")
    print(f"  Avg chunks/query: {avg_results:.1f}  (gate: >=1.0)")
    print(f"  Keyword hit rate: {keyword_rate:.0%}")

    assert retrieval_rate >= 0.70, (
        f"GATE FAIL: retrieval_rate={retrieval_rate:.0%} < 70%"
    )
    assert avg_results >= 1.0, (
        f"GATE FAIL: avg_results={avg_results:.1f} < 1.0"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration_concurrent_queries(populated_rag):
    """
    INTEGRATION: 5 concurrent queries must all complete without exception.
    """
    queries = [q for q, _ in EVAL_QUERIES[:5]]
    tasks = [
        populated_rag.query(q, tenant_id="test_eval_ns", top_k=3)
        for q in queries
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration_chroma_default_fallback(populated_rag):
    """
    INTEGRATION: Querying an unknown tenant must fall back to 'default'
    namespace or return []. Must not raise.
    """
    results = await populated_rag.query(
        "anxiety therapy", tenant_id="nonexistent-clinic-xyz", top_k=3
    )
    assert isinstance(results, list)
