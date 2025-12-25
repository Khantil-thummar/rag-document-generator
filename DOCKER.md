# Docker Setup Guide

Run the RAG Document Generator using Docker without any local Python setup.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system
- OpenAI API key

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rag-document-generator
```

### 2. Create Environment File

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. Build the Docker Image

```bash
docker build --network=host -t rag-document-generator .
```

### 4. Run the Container

```bash
docker run -d \
  --name rag-api \
  --network=host \
  --env-file .env \
  -v $(pwd)/qdrant_data:/app/qdrant_data \
  rag-document-generator
```

**Flags explained:**
- `-d` : Run in detached mode (background)
- `--name rag-api` : Container name for easy reference
- `--network=host` : Use host network (required for OpenAI API access)
- `--env-file .env` : Load environment variables from file
- `-v $(pwd)/qdrant_data:/app/qdrant_data` : Persist Qdrant data to host

### 5. Verify It's Running

```bash
# Check container status
docker ps

# Check health
curl http://localhost:8000/health
```

---

## Access Points

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

---

## Testing with UI

A simple web UI is included to test all API endpoints visually.

### How to Use

1. **Start the container** (see Quick Start above)
2. **Open `index.html`** in your browser by double-clicking the file in your file manager
3. **Test all features:**
   - Upload documents (drag & drop supported)
   - View and delete documents
   - Generate content (FAQ, summary, blog, report)

The UI connects to `http://localhost:8000` automatically. No additional setup required.

---

## Container Management

### View Logs

```bash
docker logs rag-api
```

### Follow Logs (live)

```bash
docker logs -f rag-api
```

### Stop Container

```bash
docker stop rag-api
```

### Start Container (after stop)

```bash
docker start rag-api
```

### Remove Container

```bash
docker rm rag-api
```

### Rebuild (after code changes)

```bash
docker stop rag-api
docker rm rag-api
docker build --network=host -t rag-document-generator .
docker run -d --name rag-api --network=host --env-file .env -v $(pwd)/qdrant_data:/app/qdrant_data rag-document-generator
```

---

## Data Persistence

The Qdrant vector database is stored in the `qdrant_data/` folder on your host machine. This means:

- ✅ Data survives container restarts
- ✅ Data survives container removal (as long as you don't delete the folder)
- ✅ You can backup the folder to backup your data

To **reset all data**, simply delete the `qdrant_data/` folder:

```bash
rm -rf qdrant_data/
```

---

## Troubleshooting

### Container won't start

Check logs for errors:

```bash
docker logs rag-api
```

### "OPENAI_API_KEY not configured"

Ensure your `.env` file exists and contains a valid API key:

```bash
cat .env
# Should show: OPENAI_API_KEY=sk-...
```

### Port 8000 already in use

When using `--network=host`, the container uses the host's port 8000 directly. If it's in use, either:

1. Stop the process using port 8000, or
2. Modify the CMD in Dockerfile to use a different port

---

## Next Steps

For API usage, sample curl commands, and endpoint documentation, see the main **[README.md](README.md)**.

