# RAG Document Generator

An AI-powered backend service that generates new textual documents using existing documents as the source of truth. The generated content is **grounded**, **transparent**, and **explainable**.

---

## 📖 Overview

### What This System Does

This RAG (Retrieval-Augmented Generation) system allows you to:

1. **Upload documents** → Automatically chunks and embeds them for semantic search
2. **Generate new content** → Create FAQs, summaries, blogs, or reports based on your documents
3. **Get transparent citations** → Every generated response shows which sources were used and why

### Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| **LLM** | OpenAI GPT-4o-mini | Cost-effective, fast, high-quality generation with good instruction following |
| **Embeddings** | OpenAI text-embedding-3-small | 1536 dimensions, excellent semantic understanding, affordable pricing |
| **Vector DB** | Qdrant (persistent disk storage) | Scalable to millions of documents, supports metadata filtering, open-source, no GPU required |
| **Framework** | FastAPI | Async support, automatic OpenAPI docs, production-ready |

### Why Qdrant?

- **Scalability**: Designed to handle millions of vectors efficiently
- **Metadata Filtering**: Native support for filtering during vector search
- **Persistence**: Data persists to disk (survives restarts)
- **No GPU Required**: Runs on CPU, perfect for this use case
- **Full Control**: Not a black-box solution; complete control over indexing and retrieval

### Metadata Storage

Each document chunk stored in Qdrant includes:

```json
{
    "document_id": "uuid-xxx-xxx",
    "filename": "remote_work_policy.txt",
    "chunk_index": 3,
    "total_chunks": 12,
    "chunk_text": "The actual text content...",
    "uploaded_at": "2025-12-24T10:00:00Z"
}
```

### Using Metadata for Filtering

When generating content, you can filter which documents to search:

```json
{
    "query": "Create a FAQ about leave policies",
    "filters": {
        "document_ids": ["uuid-1", "uuid-2"],
        "filenames": ["leave", "benefits"]
    }
}
```

- **document_ids**: Search only in specific documents (exact match)
- **filenames**: Search documents whose filename contains the pattern (partial match)

---

## 🛠️ Setup and Installation

### Prerequisites

- Python 3.11 or higher (recommended: 3.11.x or 3.12.x)
- OpenAI API key

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd rag-document-generator
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file in the project root:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### Environment Variables Explained

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | - | Your OpenAI API key |
---

## 🚀 Running the Server

### Start the FastAPI Server

```bash
# From project root, with virtual environment activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access Points

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Interactive Swagger UI |
| http://localhost:8000/health | Health check endpoint |

---

## 📡 API Endpoints

### Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and system status |
| `/upload` | POST | Upload documents (.txt, .pdf, .docx) |
| `/documents` | GET | List all uploaded documents |
| `/documents/{document_id}` | DELETE | Delete a specific document |
| `/generate` | POST | Generate new content from documents |

---

### 1. Health Check

**Endpoint:** `GET /health`

Check the service status, Qdrant connection, and document statistics.

**Response:**
```json
{
    "status": "healthy",
    "qdrant_connected": true,
    "openai_configured": true,
    "total_documents": 5,
    "total_chunks": 47
}
```

---

### 2. Upload Documents

**Endpoint:** `POST /upload`

Upload one or more documents to the knowledge base. Text is automatically extracted (for PDF/DOCX), chunked, embedded, and stored in Qdrant.

**Supported Formats:** `.txt`, `.pdf`, `.docx`

> ⚠️ **Note:** Only `.docx` (modern Word format) is supported, not `.doc` (legacy format).

**Request:** Multipart form data with file(s)

**Response:**
```json
{
    "message": "Successfully uploaded 3 document(s)",
    "total_files": 3,
    "successful_uploads": 3,
    "failed_uploads": 0,
    "files": [
        {
            "filename": "remote_work_policy.txt",
            "document_id": "abc123-def456-...",
            "chunks_created": 8,
            "status": "success"
        },
        {
            "filename": "annual_report.pdf",
            "document_id": "pdf789-...",
            "chunks_created": 15,
            "status": "success"
        },
        {
            "filename": "handbook.docx",
            "document_id": "docx012-...",
            "chunks_created": 10,
            "status": "success"
        }
    ]
}
```

---

### 3. List Documents

**Endpoint:** `GET /documents`

Get a list of all documents in the knowledge base with their metadata.

**Response:**
```json
{
    "total_documents": 2,
    "documents": [
        {
            "document_id": "abc123-def456-...",
            "filename": "remote_work_policy.txt",
            "total_chunks": 8,
            "uploaded_at": "2025-12-24T10:00:00Z"
        },
        {
            "document_id": "xyz789-...",
            "filename": "leave_policy.txt",
            "total_chunks": 12,
            "uploaded_at": "2025-12-24T10:05:00Z"
        }
    ]
}
```

---

### 4. Delete Document

**Endpoint:** `DELETE /documents/{document_id}`

Delete a document and all its chunks from the knowledge base.

**Response:**
```json
{
    "message": "Document successfully deleted",
    "document_id": "abc123-def456-...",
    "success": true
}
```

---

### 5. Generate Content

**Endpoint:** `POST /generate`

Generate new content (FAQ, summary, blog, report) based on your documents.

**Request Body:**
```json
{
    "query": "Create a FAQ about the remote work policy",
    "generation_type": "faq",
    "filters": {
        "filenames": ["remote_work"]
    },
    "top_k": 5
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | ✅ Yes | What content to generate (10-2000 chars) |
| `generation_type` | string | No | One of: `faq`, `summary`, `blog`, `report`, `general` (default: `general`) |
| `filters` | object | No | Metadata filters to narrow search |
| `filters.document_ids` | array | No | List of document IDs to search |
| `filters.filenames` | array | No | List of filename patterns (partial match) |
| `top_k` | integer | No | Number of chunks to retrieve (default: 5) |

**Response:**
```json
{
    "generated_content": "# FAQ: Remote Work Policy\n\nQ: What are the core hours?\nA: Core collaboration hours are 10 AM - 3 PM in your local timezone...",
    "sources": [
        {
            "document_id": "abc123-...",
            "filename": "remote_work_policy.txt",
            "relevance_score": 0.89,
            "excerpt": "TechNova Solutions embraces a flexible, remote-first work culture...",
            "chunk_index": 0,
            "reason": "Very high semantic similarity (89%) - directly relevant to your query"
        }
    ],
    "db_search_time": 0.0452,
    "warning": null
}
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| `generated_content` | The AI-generated text based on source documents |
| `sources` | List of source documents used with relevance scores |
| `db_search_time` | Time taken for vector DB search (in seconds) |
| `warning` | Warning message if sources are weak or missing |

---

## 📋 cURL Examples

### 1. Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

---

### 2. Upload Single Document

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "files=@new_documents/remote_work_policy.txt"
```

---

### 3. Upload Multiple Documents (Mixed Formats)

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "files=@new_documents/remote_work_policy.txt" \
  -F "files=@reports/annual_report.pdf" \
  -F "files=@docs/employee_handbook.docx"
```

---

### 4. List All Documents

```bash
curl -X GET "http://localhost:8000/documents"
```

---

### 5. Delete a Document

```bash
curl -X DELETE "http://localhost:8000/documents/abc123-def456-789-xyz"
```

---

### 6. Generate FAQ (No Filter)

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a comprehensive FAQ about employee benefits and perks",
    "generation_type": "faq"
  }'
```

---

### 7. Generate Summary

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the key points of the security policy",
    "generation_type": "summary"
  }'
```

---

### 8. Generate Blog Post

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Write a blog post about work-life balance at our company",
    "generation_type": "blog"
  }'
```

---

### 9. Generate Report

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Generate a formal report on the hiring and onboarding process",
    "generation_type": "report"
  }'
```

---

### 10. Generate with Filename Filter

Only search documents whose filename contains "remote" or "communication":

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a FAQ about working remotely and communication best practices",
    "generation_type": "faq",
    "filters": {
        "filenames": ["remote", "communication"]
    }
  }'
```

---

### 11. Generate with Document ID Filter

Only search specific documents by their IDs:

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the leave and benefits policies",
    "generation_type": "summary",
    "filters": {
        "document_ids": [
            "abc123-def456-...",
            "xyz789-uvw012-..."
        ]
    },
    "top_k": 10
  }'
```

---

### 12. Generate with Combined Filters

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key policies employees should know about?",
    "generation_type": "general",
    "filters": {
        "document_ids": ["specific-doc-id"],
        "filenames": ["policy", "guide"]
    },
    "top_k": 8
  }'
```

---

## 🛡️ Anti-Hallucination Measures

1. **Strict Prompting**: LLM is explicitly instructed to only use provided context
2. **Similarity Threshold**: Chunks below 0.3 similarity score are filtered out
3. **Source Transparency**: Every response includes full source attribution
4. **Missing Data Handling**: Clear error message when no relevant sources found
5. **Low Confidence Warnings**: Alerts when average relevance is below 40%
6. **Low Temperature**: Set to 0.3 for more factual, less creative responses

---

## 📁 Project Structure

```
rag-document-generator/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Settings and configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py        # Route aggregation
│   │       ├── health.py          # GET /health
│   │       ├── upload.py          # POST /upload
│   │       ├── documents.py       # GET /documents
│   │       ├── delete.py          # DELETE /documents/{id}
│   │       └── generate.py        # POST /generate
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── embedding_service.py   # OpenAI embeddings
│       ├── vector_store.py        # Qdrant operations
│       ├── document_processor.py  # Chunking and ingestion
│       ├── file_parser.py         # Text extraction (TXT/PDF/DOCX)
│       └── llm_service.py         # Content generation
├── new_documents/                 # Sample documents
├── qdrant_data/                   # Qdrant persistent storage (auto-created)
├── .env                           # Environment variables
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## 📄 Sample Documents

The `new_documents/` folder contains sample HR policy documents from a fictional company "TechNova Solutions":

- `benefits_overview.txt` - Employee benefits and perks
- `code_of_conduct.txt` - Workplace behavior guidelines
- `communication_guidelines.txt` - Communication best practices
- `data_privacy_policy.txt` - Data handling and privacy
- `diversity_inclusion.txt` - DEI policies
- `equipment_policy.txt` - Company equipment usage
- `expense_policy.txt` - Expense reimbursement
- `hiring_process.txt` - Recruitment procedures
- `learning_development.txt` - Training and growth
- `leave_policy.txt` - PTO and leave types
- `onboarding_guide.txt` - New employee guide
- `performance_review.txt` - Review process
- `promotion_policy.txt` - Career advancement
- `remote_work_policy.txt` - Remote work guidelines
- `security_policy.txt` - Security requirements
- `termination_policy.txt` - Offboarding process
- `workplace_safety.txt` - Safety guidelines

---

## 🔧 Troubleshooting

### "OpenAI API key not configured"

Ensure your `.env` file contains a valid `OPENAI_API_KEY`.

### "No relevant source documents found"

- Upload documents first using `/upload`
- Check if your query matches the content of your documents
- Try lowering the similarity threshold in `.env`

### "Document already exists"

Delete the existing document first using `DELETE /documents/{document_id}`, then re-upload.

### Qdrant data persistence

Data is stored in `./qdrant_data/` by default. To reset, delete this folder and restart the server.

### "Unsupported file type"

Only `.txt`, `.pdf`, and `.docx` files are supported. Note that `.doc` (legacy Word format pre-2007) is **not supported**—please convert to `.docx` first.

---

## 🐳 Docker

For running with Docker (no local Python setup required), see **[DOCKER.md](DOCKER.md)**.

---

## 📝 License

MIT License
