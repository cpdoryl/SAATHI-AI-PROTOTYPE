#!/usr/bin/env python3
"""
SAATHI AI — Default Knowledge Base Ingestion Script
====================================================
Ingests all therapeutic knowledge into the 'default' Pinecone/ChromaDB
namespace so every tenant can fall back to it during RAG queries.

Sources ingested (in order):
  1. ML_MODEL_DATASETS/rag_knowledge_base.json     — 20 rich clinical entries
  2. rag_knowledge_base/knowledge_base/therapy_types/techniques.jsonl
  3. rag_knowledge_base/knowledge_base/therapy_types/disorders.jsonl
  4. rag_knowledge_base/knowledge_base/modalities/modalities.jsonl
  5. rag_knowledge_base/knowledge_base/crisis_protocols/crisis_protocols.jsonl
  6. rag_knowledge_base/knowledge_base/medications/medications.jsonl
  7. PDF files in rag_knowledge_base/knowledge_base/various books pdf dataset/
  8. PDF files in rag_knowledge_base/knowledge_base/Various emotion psychology

Usage (run from repo root):
    python therapeutic-copilot/server/scripts/ingest_default_kb.py

Options:
    --dry-run     Print what would be ingested without writing to vector store
    --tenant      Target namespace (default: "default")
    --skip-pdfs   Skip PDF extraction (faster for testing)
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow running from repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / "therapeutic-copilot" / "server"
sys.path.insert(0, str(SERVER_DIR))

KB_ROOT = REPO_ROOT / "rag_knowledge_base" / "knowledge_base"
DATASETS_DIR = REPO_ROOT / "ML_MODEL_DATASETS"


# -- Serialisers: convert structured KB entries to plain text

def _jsonl_entry_to_text(entry: dict) -> str:
    """Convert any JSONL KB record to a searchable text block."""
    parts = []

    title = entry.get("title") or entry.get("modality_name") or \
        entry.get("medication_name") or entry.get("disorder_name") or \
        entry.get("id", "")
    if title:
        parts.append(f"TITLE: {title}")

    for key in [
        "description", "content", "immediate_actions",
        "steps", "clinical_example", "chatbot_guidance",
        "follow_up_protocol",
    ]:
        val = entry.get(key)
        if val:
            if isinstance(val, list):
                joined = '; '.join(str(v) for v in val)
                parts.append(f"{key.upper()}: {joined}")
            else:
                parts.append(f"{key.upper()}: {val}")

    for key in [
        "therapy_modality", "modality_name", "technique_category",
        "disorder_category", "crisis_type", "drug_class", "risk_level",
        "evidence_level", "indications", "contraindications",
        "treatment_approaches", "techniques_used", "primary_applications",
        "keywords", "tags",
    ]:
        val = entry.get(key)
        if val:
            if isinstance(val, list):
                parts.append(
                    f"{key.upper()}: {', '.join(str(v) for v in val)}"
                )
            else:
                parts.append(f"{key.upper()}: {val}")

    return "\n".join(parts)


def _extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                pages.append(txt.strip())
        return "\n\n".join(pages)
    except Exception as e:
        print(f"  [WARN] PDF extraction failed for {pdf_path.name}: {e}")
        return ""


# -- Loaders

def load_json_kb(path: Path) -> list[dict]:
    """Load the main rag_knowledge_base.json (array of entries)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    docs = []
    for entry in data:
        text = entry.get("content") or _jsonl_entry_to_text(entry)
        if entry.get("title"):
            text = f"TITLE: {entry['title']}\n\n{text}"
        docs.append({
            "text": text,
            "source": entry.get("id", "rag_kb"),
            "category": entry.get("category", "general"),
            "tags": ", ".join(entry.get("tags", [])),
        })
    print(f"  Loaded {len(docs)} entries from {path.name}")
    return docs


def load_jsonl_file(path: Path, source_tag: str) -> list[dict]:
    """Load a JSONL file where each line is one KB record."""
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                text = _jsonl_entry_to_text(entry)
                if text.strip():
                    docs.append({
                        "text": text,
                        "source": entry.get("id", source_tag),
                        "category": source_tag,
                        "tags": ", ".join(entry.get("keywords", [])),
                    })
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSONL line: {e}")
    print(f"  Loaded {len(docs)} entries from {path.name}")
    return docs


def load_pdf_folder(folder: Path) -> list[dict]:
    """Extract text from all PDFs in a folder."""
    docs = []
    for pdf in sorted(folder.glob("*.pdf")):
        text = _extract_pdf_text(pdf)
        if text and len(text) > 200:
            docs.append({
                "text": text,
                "source": pdf.stem[:50],
                "category": "clinical_literature",
                "tags": "",
            })
            print(f"  Extracted {len(text):,} chars from {pdf.name}")
        else:
            print(f"  [SKIP] {pdf.name} — insufficient text")
    return docs


# -- Main ingestion

async def ingest_all(
    tenant: str = "default",
    dry_run: bool = False,
    skip_pdfs: bool = False,
):
    """Load all KB sources and ingest into the vector store."""

    if not dry_run:
        # Import service with server sys.path already set
        from services.rag_service import RAGService
        svc = RAGService()

    all_docs: list[dict] = []

    print("\n[1/6] Loading rag_knowledge_base.json ...")
    json_kb = DATASETS_DIR / "rag_knowledge_base.json"
    if json_kb.exists():
        all_docs.extend(load_json_kb(json_kb))
    else:
        print(f"  [WARN] Not found: {json_kb}")

    print("\n[2/6] Loading therapy techniques JSONL ...")
    techniques = (
        KB_ROOT / "therapy_types" / "techniques.jsonl"
    )
    if techniques.exists():
        all_docs.extend(load_jsonl_file(techniques, "techniques"))

    print("\n[3/6] Loading disorders JSONL ...")
    disorders = KB_ROOT / "therapy_types" / "disorders.jsonl"
    if disorders.exists():
        all_docs.extend(load_jsonl_file(disorders, "disorders"))

    print("\n[4/6] Loading therapy modalities JSONL ...")
    modalities = KB_ROOT / "modalities" / "modalities.jsonl"
    if modalities.exists():
        all_docs.extend(load_jsonl_file(modalities, "modalities"))

    print("\n[5/6] Loading crisis protocols JSONL ...")
    crisis = KB_ROOT / "crisis_protocols" / "crisis_protocols.jsonl"
    if crisis.exists():
        all_docs.extend(load_jsonl_file(crisis, "crisis_protocols"))

    medications = KB_ROOT / "medications" / "medications.jsonl"
    if medications.exists():
        all_docs.extend(load_jsonl_file(medications, "medications"))

    if not skip_pdfs:
        print("\n[6/6] Extracting PDFs ...")
        pdf_folder_1 = (
            KB_ROOT / "various books pdf dataset"
        )
        pdf_folder_2 = (
            KB_ROOT / "Various emotion psychology pdf dataset"
        )
        if pdf_folder_1.exists():
            all_docs.extend(load_pdf_folder(pdf_folder_1))
        if pdf_folder_2.exists():
            all_docs.extend(load_pdf_folder(pdf_folder_2))
    else:
        print("\n[6/6] PDF extraction skipped (--skip-pdfs).")

    total_chars = sum(len(d["text"]) for d in all_docs)
    print(f"\n{'='*60}")
    print(f"Total documents to ingest : {len(all_docs)}")
    print(f"Total text characters     : {total_chars:,}")
    print(f"Target namespace          : {tenant}")

    if dry_run:
        print("\n[DRY RUN] — no data written to vector store.")
        for i, doc in enumerate(all_docs[:5], 1):
            print(f"  [{i}] {doc['source'][:40]} "
                  f"({len(doc['text'])} chars)")
        if len(all_docs) > 5:
            print(f"  ... and {len(all_docs)-5} more")
        return

    # ─── Ingest ───────────────────────────────────────────────────────────
    print(f"\nIngesting into namespace '{tenant}' ...")
    total_chunks = 0
    errors = 0
    for i, doc in enumerate(all_docs, 1):
        print(
            f"  [{i:3d}/{len(all_docs)}] {doc['source'][:45]}"
            f" ({len(doc['text']):,} chars) ...",
            end=" ", flush=True,
        )
        result = await svc.ingest(
            content=doc["text"],
            tenant_id=tenant,
            metadata={
                "source":   doc["source"],
                "category": doc["category"],
                "tags":     doc["tags"],
            },
        )
        if result.get("status") == "ingested":
            n = result.get("chunks_ingested", 0)
            total_chunks += n
            print(f"-> {n} chunks")
        else:
            errors += 1
            print(f"-> ERROR: {result.get('reason', 'unknown')}")

    print(f"\n{'='*60}")
    print("Ingestion complete!")
    print(f"  Documents : {len(all_docs)}")
    print(f"  Chunks    : {total_chunks}")
    print(f"  Errors    : {errors}")
    print(f"  Namespace : {tenant}")
    print(f"  Backend   : {svc._backend()}")

    # Quick stats
    stats = svc.stats(tenant)
    print(f"\nVector store stats: {stats}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest default KB into Pinecone/ChromaDB"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without writing to vector store",
    )
    parser.add_argument(
        "--tenant", default="default",
        help="Target namespace (default: 'default')",
    )
    parser.add_argument(
        "--skip-pdfs", action="store_true",
        help="Skip PDF extraction (faster for testing)",
    )
    args = parser.parse_args()

    asyncio.run(ingest_all(
        tenant=args.tenant,
        dry_run=args.dry_run,
        skip_pdfs=args.skip_pdfs,
    ))
