# Hybrid-RAG


A Hybrid Retrieval-Augmented Generation (Hybrid-RAG) system for querying PDF document.
This project demonstrates how to build an document question-answering system capable of answering:

- **Textual Questions** using semantic search over document chunks.
- **Analytical Questions** by extracting tables from PDFs and executing computations on them.
- **Hybrid Questions** that require combining information from both retrieved text and analytical results.


## Files description

- `parser.py` — pulls text and tables out of a PDF with Docling
- `agent.py` — the actual logic: chunking, indexing, retrieval, and the three answer
  paths (RAG for text, pandas agent for analytical, a synthesis step for hybrid)
- `router.py` — one LLM call, structured output, decides text / analytical / hybrid
- `postgres_store.py` — the byte store backing the table retriever
- `prompts.py` — every prompt string, kept out of the logic files
- `config.py` — env vars, loads `.env` locally
- `main.py` — CLI: `python main.py some_report.pdf`
- `app.py` — FastAPI app, one route: `POST /query`
- `schema.sql` — just the `vector` extension + the `docstore` table (PGVector
  manages its own tables automatically)



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

