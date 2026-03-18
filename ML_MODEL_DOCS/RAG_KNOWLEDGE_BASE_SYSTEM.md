# SAATHI AI — RAG Knowledge Base System
## Document: Retrieval-Augmented Generation Pipeline
### Version: 1.0 | Date: 2026-03-17 | Status: COMPLETE

---

## 1. SYSTEM OVERVIEW

The RAG (Retrieval-Augmented Generation) system provides every patient
message with relevant clinical context before LLM inference. It grounds
Qwen 2.5-7B's responses in evidence-based therapeutic knowledge —
CBT techniques, DBT skills, crisis protocols, disorder information,
and therapy modality guides.

### How it fits in the pipeline

```
Patient message
      |
      v
[TherapeuticAIService.process_message()]
      |
      +---> crisis_detector.scan()            (<100ms)
      |
      +---> RAGService.query(msg, tenant_id)  (embedding + vector search)
      |         |
      |         +--> tenant namespace (clinic-specific KB)
      |         |         score >= 0.75? YES -> return contexts
      |         |
      |         +--> "default" namespace (fallback if tenant miss)
      |                   score >= 0.70? YES -> return contexts
      |
      +---> Build LLM prompt with RAG context injected
      |
      v
[QwenInferenceService.generate()]
```

---

## 2. ARCHITECTURE

### 2.1 Backend Selection (Automatic)

| Environment | Config | Backend |
|-------------|--------|---------|
| Production  | `PINECONE_API_KEY` set | Pinecone (cloud, per-tenant namespaces) |
| Dev / Demo  | `PINECONE_API_KEY` empty | ChromaDB (local persistent store) |

No code changes needed to switch between backends — the service
auto-detects based on config.

### 2.2 Embedding Model

| Property | Value |
|----------|-------|
| Model | `all-MiniLM-L6-v2` (sentence-transformers) |
| Dimensions | 384 |
| Distance metric | Cosine similarity |
| Inference | CPU (singleton, loaded once at server start) |
| Load time | ~2s on first call, then cached |

### 2.3 Chunking Strategy

```
chunk_size  = 512 tokens  (~2048 chars)
overlap     = 50 tokens   (~200 chars)
stride      = chunk_size - overlap = 1848 chars
min_length  = 50 chars    (tiny chunks discarded)
```

A 10,000-char document produces ~5-6 overlapping chunks.
Overlap ensures context continuity across chunk boundaries.

### 2.4 Similarity Thresholds

| Namespace | Threshold | Rationale |
|-----------|-----------|-----------|
| Tenant (clinic-specific) | 0.75 | High precision for custom protocols |
| Default (shared KB) | 0.70 | Slightly lower — broader clinical knowledge |

Queries returning no results silently return `[]`, causing the LLM
to respond from its own knowledge without injected context.

---

## 3. KNOWLEDGE BASE CONTENT

### 3.1 Default Namespace (pre-ingested, shared across all tenants)

| Source File | Entries | Category |
|-------------|---------|----------|
| `ML_MODEL_DATASETS/rag_knowledge_base.json` | 20 | CBT/DBT/ACT techniques, crisis protocols |
| `knowledge_base/therapy_types/techniques.jsonl` | 3 | CBT, Behavioral Activation, Mindfulness |
| `knowledge_base/therapy_types/disorders.jsonl` | 3 | MDD, GAD, Bipolar I |
| `knowledge_base/modalities/modalities.jsonl` | 3 | CBT, DBT, ACT |
| `knowledge_base/crisis_protocols/crisis_protocols.jsonl` | 3 | Suicidal ideation, panic, aggression |
| `knowledge_base/medications/medications.jsonl` | 3 | Sertraline, Quetiapine, Alprazolam |
| PDF books (NLP, psychology, therapy) | ~25 | Clinical literature |

**Total ingested (JSONL/JSON only): 35 chunks**
**With PDFs: ~500-1000+ chunks** (depends on PDF text quality)

### 3.2 Per-Clinic Namespace

Each clinic can upload custom documents via:
- Admin Panel UI (`POST /api/v1/rag/ingest`)
- CLI ingestion script (`scripts/ingest_clinic_docs.py`)

Typical per-clinic content:
- Clinic FAQ (therapist bios, pricing, timings)
- Clinic-specific therapy protocols
- Cultural/regional language guides
- Patient onboarding materials

---

## 4. API ENDPOINTS

### 4.1 Query Knowledge Base
```
POST /api/v1/rag/query
Content-Type: application/json

{
  "query": "how to manage panic attacks",
  "tenant_id": "clinic_abc123",
  "top_k": 5
}

Response:
{
  "results": [
    "Diaphragmatic breathing for panic attacks...",
    "CBT for anxiety disorders..."
  ]
}
```

### 4.2 Ingest Document
```
POST /api/v1/rag/ingest
Content-Type: application/json

{
  "content": "Our clinic FAQ: We offer sessions on Monday...",
  "tenant_id": "clinic_abc123",
  "metadata": {
    "source": "clinic_faq",
    "category": "clinic_info"
  }
}

Response:
{
  "status": "ingested",
  "backend": "chroma",
  "chunks_ingested": 3,
  "tenant_id": "clinic_abc123"
}
```

---

## 5. INGESTION SCRIPTS

### 5.1 Ingest Default Knowledge Base
```bash
# From repo root — ingests all JSONL/JSON + PDF sources
python therapeutic-copilot/server/scripts/ingest_default_kb.py

# Skip PDFs (faster, for CI/testing)
python therapeutic-copilot/server/scripts/ingest_default_kb.py --skip-pdfs

# Dry run (preview without writing)
python therapeutic-copilot/server/scripts/ingest_default_kb.py --dry-run
```

### 5.2 Ingest Per-Clinic Documents
```bash
python therapeutic-copilot/server/scripts/ingest_clinic_docs.py \
    --tenant clinic_abc123 \
    --folder /path/to/clinic/docs/

# Clear existing vectors first
python therapeutic-copilot/server/scripts/ingest_clinic_docs.py \
    --tenant clinic_abc123 \
    --folder /path/to/clinic/docs/ \
    --clear
```

**Supported file types:** `.txt`, `.md`, `.pdf`, `.json`, `.jsonl`

---

## 6. ENVIRONMENT VARIABLES

### Local Development (ChromaDB — no API keys needed)
```env
# No PINECONE_API_KEY → auto-uses ChromaDB
LOCAL_RAG_DB_PATH=./chroma_db   # optional, defaults to ./chroma_db
```

### Production (Pinecone)
```env
PINECONE_API_KEY=<your-key-from-pinecone.io>
PINECONE_INDEX=therapeutic-kb
PINECONE_ENVIRONMENT=us-east-1-aws
```

### Pinecone Index Setup (one-time, production only)
```python
from pinecone import Pinecone, ServerlessSpec
pc = Pinecone(api_key=PINECONE_API_KEY)
pc.create_index(
    name="therapeutic-kb",
    dimension=384,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)
```

---

## 7. INTEGRATION WITH THERAPEUTIC AI SERVICE

RAG is called on **every patient message** in `process_message()`:

```python
# therapeutic_ai_service.py — lines 217-230
tenant_id = "default"
if session:
    patient = await db.execute(select(Patient)...)
    if patient and patient.tenant_id:
        tenant_id = patient.tenant_id

rag_context = await self.rag.query(
    query=message, tenant_id=tenant_id, top_k=3
)

# Injected into LLM prompt via chatbot_service.build_response_prompt()
prompt = self.chatbot.build_response_prompt(
    message=message,
    stage=stage,
    rag_context=rag_context,
    current_step=current_step,
)
```

The RAG context appears as a **"Relevant Knowledge"** block in the
system prompt, before the patient message. The LLM uses this to
ground its response in clinical knowledge.

---

## 8. EVALUATION RESULTS

### Test Suite: `tests/test_rag.py`

**Unit Tests (Pinecone mocked): 18/18 PASS**

| Test Category | Tests | Result |
|---------------|-------|--------|
| Ingest — upsert calls | 4 | PASS |
| Query — top-k, threshold, namespace | 5 | PASS |
| Fallback to default namespace | 4 | PASS |
| Chunking logic | 5 | PASS |

**Integration Tests (live ChromaDB, real embeddings): 4/4 PASS**

| Test | Result |
|------|--------|
| Ingest 10 docs into ChromaDB | PASS |
| Eval 10 therapeutic queries | PASS |
| Concurrent queries (5 parallel) | PASS |
| Default namespace fallback | PASS |

### Qualification Gates

| Gate | Target | Achieved | Status |
|------|--------|----------|--------|
| Retrieval rate (10 queries) | >= 70% | **90%** | PASS |
| Avg chunks per query | >= 1.0 | **1.2** | PASS |
| Keyword hit rate | — | **90%** | INFO |
| No exceptions on concurrent queries | required | confirmed | PASS |

---

## 9. LOCAL VECTOR STORE (ChromaDB)

The ChromaDB store persists to disk at `./chroma_db` (relative to
the server working directory):

```
therapeutic-copilot/server/chroma_db/
  ├── default/          # shared default namespace (35+ chunks)
  ├── test_eval_ns/     # integration test namespace (cleaned per run)
  └── <clinic_id>/      # per-clinic namespaces (created on first ingest)
```

Stats check (from Python):
```python
from services.rag_service import RAGService
svc = RAGService()
print(svc.stats("default"))
# {'backend': 'chroma', 'namespace': 'default', 'chunk_count': 35}
```

---

## 10. KNOWN LIMITATIONS & NEXT STEPS

| Item | Priority | Notes |
|------|----------|-------|
| PDF text quality varies — scanned PDFs produce no text | P2 | Use OCR (pytesseract) for scanned PDFs |
| No re-indexing on document update | P2 | Use `--clear` flag to rebuild |
| No hybrid search (BM25 + dense) | P3 | Can improve recall for exact-match queries |
| Admin UI for document upload | P1 | `POST /api/v1/rag/ingest` endpoint is ready; UI pending |
| HF_TOKEN warning on model load | P3 | Set env var to suppress |

---

## 11. FILES CHANGED / CREATED

| File | Change |
|------|--------|
| `server/services/rag_service.py` | Dual-backend (Pinecone + ChromaDB fallback), chunking, thresholds |
| `server/scripts/ingest_default_kb.py` | NEW — ingests all KB sources into default namespace |
| `server/scripts/ingest_clinic_docs.py` | NEW — per-clinic document ingestion |
| `tests/test_rag.py` | Full rewrite — 18 unit + 4 integration tests |
| `pytest.ini` | Added `integration` marker |
| `chroma_db/` | NEW — local vector store (auto-created on first ingest) |
