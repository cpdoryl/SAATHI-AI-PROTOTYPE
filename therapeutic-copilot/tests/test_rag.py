"""
SAATHI AI — RAG Service Unit Tests
Tests: ingest → Pinecone upsert, query → top-k chunks, wrong tenant → empty,
       fallback to default namespace, chunking, Pinecone-unavailable graceful degradation.
All tests use mocks — no real Pinecone or SentenceTransformer calls.
"""
import pytest
from unittest.mock import MagicMock, patch

from services.rag_service import RAGService


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_match(text: str, score: float) -> MagicMock:
    """Construct a Pinecone ScoredVector mock."""
    m = MagicMock()
    m.metadata = {"text": text}
    m.score = score
    return m


# ─── Session-scoped fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_embedding_model():
    """
    Prevent loading the real SentenceTransformer in every test.
    Patches _get_embedding_model() to return a mock that produces
    a deterministic 384-dim vector.
    """
    fake_model = MagicMock()
    fake_model.encode.return_value.tolist.return_value = [0.1] * 384
    with patch("services.rag_service._get_embedding_model", return_value=fake_model):
        yield fake_model


@pytest.fixture
def mock_index() -> MagicMock:
    """A bare Pinecone Index mock."""
    return MagicMock()


@pytest.fixture
def rag(mock_index) -> RAGService:
    """
    RAGService with a mocked Pinecone index injected directly,
    bypassing the real Pinecone client initialisation.
    """
    service = RAGService()
    service._client = MagicMock()
    service._index = mock_index
    return service


# ─── Ingest tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_calls_pinecone_upsert(rag, mock_index):
    """ingest() must upsert at least one vector to the correct tenant namespace."""
    mock_index.upsert.return_value = None
    content = "Cognitive Behavioural Therapy helps restructure negative thought patterns."

    result = await rag.ingest(content, tenant_id="clinic-001", metadata={"source": "cbt_guide"})

    assert result["status"] == "ingested"
    assert result["chunks_ingested"] >= 1
    assert result["tenant_id"] == "clinic-001"
    mock_index.upsert.assert_called()
    # Every upsert call must target the correct namespace
    for call in mock_index.upsert.call_args_list:
        assert call.kwargs["namespace"] == "clinic-001"


@pytest.mark.asyncio
async def test_ingest_stores_text_and_metadata_in_vector(rag, mock_index):
    """Each upserted vector must carry 'text', 'tenant_id', and 'source' in metadata."""
    mock_index.upsert.return_value = None

    await rag.ingest(
        "Sample therapy document.",
        tenant_id="clinic-001",
        metadata={"source": "therapy_protocol"},
    )

    mock_index.upsert.assert_called()
    first_batch = mock_index.upsert.call_args_list[0].kwargs["vectors"]
    assert len(first_batch) >= 1
    meta = first_batch[0]["metadata"]
    assert "text" in meta
    assert meta["tenant_id"] == "clinic-001"
    assert meta["source"] == "therapy_protocol"


@pytest.mark.asyncio
async def test_ingest_long_document_produces_multiple_chunks(rag, mock_index):
    """
    A document longer than one chunk window (>2048 chars) must be split into
    at least 2 chunks, each upserted with a unique chunk_id.
    """
    mock_index.upsert.return_value = None
    # 55 × 57 chars ≈ 3135 chars — exceeds 2048-char chunk window
    long_content = "Mindfulness is the practice of present-moment awareness. " * 55

    result = await rag.ingest(long_content, tenant_id="clinic-abc", metadata={"source": "mindfulness"})

    assert result["status"] == "ingested"
    assert result["chunks_ingested"] >= 2
    # All chunk_ids must be unique
    all_ids = [
        v["id"]
        for call in mock_index.upsert.call_args_list
        for v in call.kwargs["vectors"]
    ]
    assert len(all_ids) == len(set(all_ids)), "Chunk IDs must be unique"


@pytest.mark.asyncio
async def test_ingest_when_pinecone_unavailable():
    """ingest() must return an error dict when Pinecone is not configured."""
    service = RAGService()  # _client stays None → _get_client() returns None

    result = await service.ingest("some content", tenant_id="clinic-001", metadata={})

    assert result["status"] == "error"
    assert "reason" in result


# ─── Query tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_returns_top_k_chunks(rag, mock_index):
    """query() must return the text of all high-scoring Pinecone matches."""
    mock_index.query.return_value = MagicMock(matches=[
        _make_match("CBT helps reframe negative thoughts.", 0.92),
        _make_match("Mindfulness reduces anxiety symptoms.", 0.87),
        _make_match("Exposure therapy treats phobias effectively.", 0.81),
    ])

    results = await rag.query("how to treat anxiety", tenant_id="clinic-001", top_k=3)

    assert len(results) == 3
    assert results[0] == "CBT helps reframe negative thoughts."
    assert results[1] == "Mindfulness reduces anxiety symptoms."
    assert results[2] == "Exposure therapy treats phobias effectively."


@pytest.mark.asyncio
async def test_query_filters_low_similarity_scores(rag, mock_index):
    """
    query() must exclude matches with score below the tenant similarity
    threshold (0.75). Low-scoring results must not reach the LLM context.
    """
    mock_index.query.return_value = MagicMock(matches=[
        _make_match("High relevance chunk.", 0.90),
        _make_match("Low relevance chunk — should be excluded.", 0.60),
    ])

    results = await rag.query("therapy techniques", tenant_id="clinic-001", top_k=5)

    assert len(results) == 1
    assert results[0] == "High relevance chunk."


@pytest.mark.asyncio
async def test_query_uses_correct_namespace(rag, mock_index):
    """query() must pass tenant_id as the Pinecone namespace."""
    mock_index.query.return_value = MagicMock(matches=[])

    await rag.query("test", tenant_id="clinic-xyz", top_k=5)

    first_call_kwargs = mock_index.query.call_args_list[0].kwargs
    assert first_call_kwargs["namespace"] == "clinic-xyz"


@pytest.mark.asyncio
async def test_wrong_tenant_returns_empty(rag, mock_index):
    """
    Querying a tenant namespace that has no documents must return []
    without raising. Both tenant and default namespace return no matches.
    """
    mock_index.query.return_value = MagicMock(matches=[])

    results = await rag.query("any query text", tenant_id="unknown-tenant-999", top_k=5)

    assert results == []


@pytest.mark.asyncio
async def test_query_when_pinecone_unavailable():
    """query() must return [] gracefully when Pinecone is not configured."""
    service = RAGService()  # _client stays None

    results = await service.query("test query", tenant_id="clinic-001")

    assert results == []


# ─── Fallback namespace tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fallback_to_default_namespace_when_tenant_empty(rag, mock_index):
    """
    When the tenant namespace yields no results above the threshold,
    query() must fall back to the 'default' namespace and return its chunks.
    """
    default_match = _make_match("General mental health resource from default KB.", 0.78)

    def _side_effect(**kwargs):
        if kwargs.get("namespace") == "empty-clinic":
            return MagicMock(matches=[])
        if kwargs.get("namespace") == "default":
            return MagicMock(matches=[default_match])
        return MagicMock(matches=[])

    mock_index.query.side_effect = _side_effect

    results = await rag.query("mental health tips", tenant_id="empty-clinic", top_k=5)

    assert len(results) == 1
    assert results[0] == "General mental health resource from default KB."
    # Must have queried both namespaces
    assert mock_index.query.call_count == 2
    namespaces_queried = [c.kwargs["namespace"] for c in mock_index.query.call_args_list]
    assert "empty-clinic" in namespaces_queried
    assert "default" in namespaces_queried


@pytest.mark.asyncio
async def test_fallback_not_triggered_when_tenant_has_results(rag, mock_index):
    """
    When the tenant namespace returns results above the threshold,
    the 'default' namespace must never be queried.
    """
    mock_index.query.return_value = MagicMock(matches=[
        _make_match("Clinic-specific protocol.", 0.88),
    ])

    results = await rag.query("clinic protocol", tenant_id="clinic-001", top_k=5)

    assert len(results) == 1
    assert mock_index.query.call_count == 1  # only tenant namespace queried


@pytest.mark.asyncio
async def test_fallback_uses_lower_threshold_for_default_namespace(rag, mock_index):
    """
    The default namespace fallback must apply a lower threshold (0.70)
    than the tenant namespace (0.75), so borderline-relevant default
    content can still be returned.
    """
    # score=0.72 — below tenant threshold (0.75), above default threshold (0.70)
    borderline_match = _make_match("Borderline-relevant default chunk.", 0.72)

    def _side_effect(**kwargs):
        if kwargs.get("namespace") == "sparse-clinic":
            return MagicMock(matches=[])
        if kwargs.get("namespace") == "default":
            return MagicMock(matches=[borderline_match])
        return MagicMock(matches=[])

    mock_index.query.side_effect = _side_effect

    results = await rag.query("general advice", tenant_id="sparse-clinic", top_k=5)

    assert len(results) == 1
    assert results[0] == "Borderline-relevant default chunk."


@pytest.mark.asyncio
async def test_no_double_fallback_for_default_namespace(rag, mock_index):
    """
    Querying the 'default' namespace directly must not trigger recursive fallback.
    Only one Pinecone call must be made.
    """
    mock_index.query.return_value = MagicMock(matches=[])

    results = await rag.query("query", tenant_id="default", top_k=5)

    assert results == []
    assert mock_index.query.call_count == 1  # must not query default twice


# ─── Chunking unit tests ──────────────────────────────────────────────────────

def test_chunk_text_short_content_produces_one_chunk():
    """Content shorter than the chunk window must produce exactly 1 chunk."""
    service = RAGService()
    text = "Short therapeutic text. " * 10  # ~240 chars — well below 2048
    chunks = service._chunk_text(text)
    assert len(chunks) == 1


def test_chunk_text_long_content_produces_multiple_chunks():
    """Content longer than one chunk window must be split into at least 2 chunks."""
    service = RAGService()
    text = "word " * 600  # 3000 chars > 2048-char window
    chunks = service._chunk_text(text)
    assert len(chunks) >= 2


def test_chunk_text_filters_tiny_chunks():
    """_chunk_text() must discard all chunks of 50 chars or fewer."""
    service = RAGService()
    text = ("word " * 500) + "hi"  # tail is 2 chars — too tiny
    chunks = service._chunk_text(text)
    for chunk in chunks:
        assert len(chunk.strip()) > 50


def test_chunk_text_overlap_creates_shared_content():
    """
    Adjacent chunks must share overlap content.
    chunk_size=512 tokens → 2048 chars; overlap=50 tokens → 200 chars.
    Stride = 2048 - 200 = 1848.
    chunk[0][1848:2048] must equal chunk[1][:200].
    """
    service = RAGService()
    text = "A" * 3000  # predictable content for easy overlap verification
    chunks = service._chunk_text(text)
    assert len(chunks) >= 2
    # Stride is 1848; the tail of chunk[0] (chars 1848–2048) == head of chunk[1] (chars 0–200)
    assert chunks[0][1848:2048] == chunks[1][:200]


def test_chunk_text_empty_string_returns_no_chunks():
    """_chunk_text() with empty input must return an empty list."""
    service = RAGService()
    chunks = service._chunk_text("")
    assert chunks == []
