# Client-Specific Custom Knowledge Base

This directory contains client-specific knowledge bases for B2B tenants.

## Directory Structure

```
client-custom/
├── [client_id_1]/
│   ├── website_content/       # Scraped website data
│   ├── pdf_documents/         # Uploaded PDF files
│   ├── faq_data/             # Q&A pairs
│   ├── video_transcripts/    # Transcribed video content
│   ├── structured_data/      # CSV/Excel data
│   └── metadata.json         # Client knowledge base config
├── [client_id_2]/
│   └── ...
└── README.md (this file)
```

## Supported Ingestion Methods

### 1. Website Content Scraping
- **API Endpoint**: `POST /api/knowledge-base/ingest-website`
- **Input**: Website URLs
- **Output**: Chunked text embeddings in vector store

### 2. PDF Document Upload
- **API Endpoint**: `POST /api/knowledge-base/ingest-pdf`
- **Input**: PDF files
- **Output**: Extracted text with OCR support

### 3. FAQ & Q&A Pairs
- **API Endpoint**: `POST /api/knowledge-base/ingest-faq`
- **Input**: JSON/CSV Q&A pairs
- **Output**: Direct FAQ embeddings

### 4. Video Content Transcription
- **API Endpoint**: `POST /api/knowledge-base/ingest-video`
- **Input**: Video files or YouTube URLs
- **Output**: Speech-to-text transcripts

### 5. Structured Data (CSV/Excel)
- **API Endpoint**: `POST /api/knowledge-base/ingest-structured`
- **Input**: CSV/Excel files
- **Output**: Row-based embeddings

### 6. Cloud Storage Sync
- **API Endpoint**: `POST /api/knowledge-base/sync-cloud-storage`
- **Providers**: Google Drive, Dropbox, OneDrive
- **Output**: Continuous sync of document repositories

## Data Isolation & Security

- Each client's data is stored in a separate subdirectory
- All embeddings are encrypted with AES-256-GCM
- Tenant ID filtering ensures data isolation
- HIPAA/GDPR compliant data handling

## Usage Example

```python
# Ingest client website
response = requests.post(
    "https://api.saathi.ai/api/knowledge-base/ingest-website",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "client_id": "clinic-abc-123",
        "urls": ["https://clinic-abc.com/about", "https://clinic-abc.com/services"],
        "crawl_depth": 2
    }
)
```

## Client Metadata Format

Each client subdirectory contains a `metadata.json` file:

```json
{
  "client_id": "clinic-abc-123",
  "client_name": "ABC Mental Health Clinic",
  "ingestion_sources": [
    {
      "type": "website",
      "url": "https://clinic-abc.com",
      "ingested_at": "2025-11-02T10:30:00Z",
      "pages_crawled": 15,
      "chunks_created": 87
    },
    {
      "type": "pdf",
      "filename": "treatment_protocol.pdf",
      "ingested_at": "2025-11-02T11:00:00Z",
      "pages": 24,
      "chunks_created": 52
    }
  ],
  "total_chunks": 139,
  "last_updated": "2025-11-02T11:00:00Z",
  "auto_sync_enabled": true,
  "sync_frequency": "daily"
}
```

## RAG Integration

All client-specific data is automatically:
1. Chunked into semantic units (512 tokens)
2. Embedded using OpenAI text-embedding-ada-002
3. Stored in ChromaDB with client_id filter
4. Retrieved via semantic search during conversations
5. Injected into LLM context for accurate responses

## Admin Dashboard

Clients can manage their knowledge base through:
- Web portal: `https://app.saathi.ai/knowledge-base`
- Upload interface for bulk document ingestion
- Usage analytics showing which sources are most accessed
- Gap analysis identifying unanswered questions
