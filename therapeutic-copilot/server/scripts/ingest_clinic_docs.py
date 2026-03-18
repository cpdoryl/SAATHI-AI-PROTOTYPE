#!/usr/bin/env python3
"""
SAATHI AI — Per-Clinic Document Ingestion Script
=================================================
Ingests a clinic's custom documents (FAQs, protocols, bios) into their
private Pinecone/ChromaDB namespace so the AI can answer clinic-specific
questions (pricing, therapist bios, local resources, etc.).

Usage:
    python therapeutic-copilot/server/scripts/ingest_clinic_docs.py \\
        --tenant <clinic-id> \\
        --folder /path/to/clinic/docs/

Supported formats: .txt, .md, .json, .jsonl, .pdf

Options:
    --tenant     Clinic tenant ID (required)
    --folder     Folder containing documents to ingest (required)
    --dry-run    Preview without writing
    --clear      Clear existing vectors for this tenant before ingesting
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / "therapeutic-copilot" / "server"
sys.path.insert(0, str(SERVER_DIR))


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n\n".join(
            p.extract_text().strip()
            for p in reader.pages
            if p.extract_text()
        )
    except Exception as e:
        print(f"  [WARN] PDF error {path.name}: {e}")
        return ""


def _load_document(path: Path) -> list[dict]:
    """Load a single file and return list of {text, source, category} dicts."""
    suffix = path.suffix.lower()
    docs = []

    if suffix in (".txt", ".md"):
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            docs.append({
                "text": text,
                "source": path.stem[:50],
                "category": "clinic_document",
            })

    elif suffix == ".pdf":
        text = _extract_pdf_text(path)
        if len(text) > 200:
            docs.append({
                "text": text,
                "source": path.stem[:50],
                "category": "clinic_pdf",
            })

    elif suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                text = item.get("content") or item.get("text") or \
                    json.dumps(item)
                src = item.get("id") or item.get("title") or path.stem
                docs.append({
                    "text": text,
                    "source": str(src)[:50],
                    "category": "clinic_json",
                })
        elif isinstance(data, dict):
            text = data.get("content") or data.get("text") or \
                json.dumps(data)
            docs.append({
                "text": text,
                "source": path.stem[:50],
                "category": "clinic_json",
            })

    elif suffix == ".jsonl":
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    text = item.get("content") or item.get("text") or \
                        json.dumps(item)
                    src = item.get("id") or item.get("title") or path.stem
                    docs.append({
                        "text": text,
                        "source": str(src)[:50],
                        "category": "clinic_jsonl",
                    })
                except json.JSONDecodeError:
                    pass

    return docs


async def ingest_clinic(
    tenant: str,
    folder: Path,
    dry_run: bool = False,
    clear: bool = False,
):
    """Ingest all documents in folder into the clinic's namespace."""

    if not folder.exists():
        print(f"[ERROR] Folder not found: {folder}")
        sys.exit(1)

    supported = {".txt", ".md", ".pdf", ".json", ".jsonl"}
    files = [
        f for f in sorted(folder.iterdir())
        if f.is_file() and f.suffix.lower() in supported
    ]

    if not files:
        print(f"[WARN] No supported files found in {folder}")
        return

    print(f"\nSAATHI AI — Clinic Document Ingestion")
    print(f"  Tenant   : {tenant}")
    print(f"  Folder   : {folder}")
    print(f"  Files    : {len(files)}")

    all_docs = []
    for f in files:
        loaded = _load_document(f)
        print(
            f"  Loaded {len(loaded)} doc(s) from {f.name}"
            f" ({f.stat().st_size // 1024} KB)"
        )
        all_docs.extend(loaded)

    total_chars = sum(len(d["text"]) for d in all_docs)
    print(f"\n  Total documents : {len(all_docs)}")
    print(f"  Total chars     : {total_chars:,}")

    if dry_run:
        print("\n[DRY RUN] — no data written.")
        for i, doc in enumerate(all_docs[:5], 1):
            print(f"  [{i}] {doc['source'][:45]} ({len(doc['text'])} chars)")
        if len(all_docs) > 5:
            print(f"  ... and {len(all_docs)-5} more")
        return

    from services.rag_service import RAGService
    svc = RAGService()

    if clear:
        print(f"\n[CLEAR] Clearing existing vectors for tenant '{tenant}' ...")
        try:
            backend = svc._backend()
            if backend == "chroma":
                client = svc._get_chroma_collection(tenant)
                # ChromaDB: delete and recreate collection
                import chromadb
                chroma_c = chromadb.PersistentClient(
                    path=str(getattr(
                        __import__("config").settings,
                        "LOCAL_RAG_DB_PATH", "./chroma_db"
                    ))
                )
                safe_name = svc._safe_collection_name(tenant)  # noqa
                try:
                    chroma_c.delete_collection(safe_name)
                    print(f"  Deleted ChromaDB collection '{safe_name}'")
                except Exception:
                    pass
        except Exception as e:
            print(f"  [WARN] Clear failed: {e}")

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
            },
        )
        if result.get("status") == "ingested":
            n = result.get("chunks_ingested", 0)
            total_chunks += n
            print(f"→ {n} chunks")
        else:
            errors += 1
            print(f"→ ERROR: {result.get('reason')}")

    print(f"\n{'─'*60}")
    print(f"Ingestion complete!")
    print(f"  Documents : {len(all_docs)}")
    print(f"  Chunks    : {total_chunks}")
    print(f"  Errors    : {errors}")
    stats = svc.stats(tenant)
    print(f"  Stats     : {stats}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest clinic-specific docs into their namespace"
    )
    parser.add_argument(
        "--tenant", required=True,
        help="Clinic tenant ID (e.g. 'clinic_abc123')",
    )
    parser.add_argument(
        "--folder", required=True,
        help="Path to folder containing clinic documents",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without writing to vector store",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear existing tenant vectors before ingesting",
    )
    args = parser.parse_args()

    asyncio.run(ingest_clinic(
        tenant=args.tenant,
        folder=Path(args.folder),
        dry_run=args.dry_run,
        clear=args.clear,
    ))
