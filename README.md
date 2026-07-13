# Hybrid-RAG


A Hybrid Retrieval-Augmented Generation (Hybrid-RAG) system for querying PDF document.
This project demonstrates how to build an document question-answering system capable of answering:

- **Textual Questions** using semantic search over document chunks.
- **Analytical Questions** by extracting tables from PDFs and executing computations on them.
- **Hybrid Questions** that require combining information from both retrieved text and analytical results.


## Files description

- `parser.py` – Extracts text, tables, and metadata from PDF documents using Docling, preparing them for indexing.
- `agent.py` – Contains the core Hybrid-RAG workflow, including document chunking, vector indexing, retrieval, question answering, and the logic for handling textual, analytical, and hybrid queries.
- `router.py` – Uses an LLM to classify incoming questions as textual, analytical, or hybrid, ensuring each request is routed through the appropriate pipeline.
- `postgres_store.py` – Implements the PostgreSQL-backed byte store used to persist and retrieve parent documents associated with extracted tables.
- `prompts.py` – Centralizes all prompt templates used by the application, keeping prompt definitions separate from business logic.
- `config.py` – Loads application configuration and environment variables from the local `.env` file.
- `main.py` – Command-line entry point for indexing PDF documents into the system.
- `app.py` – FastAPI application exposing the API endpoints for querying indexed documents.
- `schema.sql` – Initializes the PostgreSQL database by enabling the `pgvector` extension and creating the document store required by the application.



## Running it with Docker



```bash
docker compose up --build -d
docker compose logs -f api    
```

Indexing a new PDF:
```bash
docker build -t novatech-indexer .
docker run -it --rm \
  --network <run "docker network ls" and paste the real name here> \
  --env-file .env \
  -e DATABASE_URL=postgresql+psycopg://novatech:novatech@db:5432/novatech \
  -v $(pwd)/sample_data:/data \
  novatech-indexer python main.py /data/novatech_q4_2024_report.pdf
```
(Compose derives the network name from the project folder — it won't just be
`sqope-ai-assessment_default` if you renamed the folder, so check first.)

