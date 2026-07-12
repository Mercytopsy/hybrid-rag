# table-aware-rag

A small system for asking questions over PDF reports that mix narrative text with data
tables — things like quarterly financial reports, where "what were the highlights"
and "what's the sum of headcount in Q3" both need to work, but obviously can't be
answered the same way.

The core idea: text questions go through normal RAG (embed, retrieve, ask an LLM).
Table questions don't — asking an LLM to eyeball numbers off a markdown table and
add them up is how you get confidently wrong answers. So instead, table questions
get routed to an agent that writes actual pandas code and runs it against the real
extracted table. A router decides which path a question needs (or both, for
questions that need a computed number plus some interpretation), and it all sits
behind one `/query` endpoint.

## How it's put together

```
PDF ──▶ Docling (parsing) ──▶ text chunks ──▶ PGVector ─────┐
                          └──▶ tables ──▶ summarized ──▶ MultiVectorRetriever
                                                              │
question ──▶ classifier (text / analytical / hybrid) ──▶ retrieval ──▶ answer
                                                              │
                              analytical ──▶ pandas agent (PythonAstREPLTool)
```

Text chunks are stored in a plain PGVector collection — embed the chunk, retrieve
the chunk, nothing fancy needed there.

Tables are handled differently. Embedding a raw table (numbers mixed with headers)
gives you a bad embedding — numbers don't carry much semantic meaning, so similarity
search against them is noisy. Instead each table gets a short LLM-written summary
("departmental headcount and cost breakdown by quarter..."), and *that's* what gets
embedded. The full table — actual rows, columns, markdown — is stored separately in
a Postgres-backed byte store, keyed by an id the summary points back to. This is a
`MultiVectorRetriever` pattern: search matches on the summary, but you get the real
table back. `langchain_postgres` doesn't ship a persistent byte store out of the box
(the default is in-memory, which means restart the API and your tables are gone), so
`postgres_store.py` is a small hand-rolled one, backed by a `docstore` table.

## What's in each file

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

## Running it locally (no Docker)

You need Postgres with the `pgvector` extension. On Ubuntu/WSL:

```bash
sudo apt install postgresql postgresql-16-pgvector
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER novatech WITH PASSWORD 'novatech' SUPERUSER;"
sudo -u postgres psql -c "CREATE DATABASE novatech OWNER novatech;"
psql "postgresql://novatech:novatech@localhost:5432/novatech" -f schema.sql
```

Then:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env .env.local   # or just edit .env directly
```

Fill in `.env`:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://novatech:novatech@localhost:5432/novatech
```

Index the sample report:
```bash
python3 main.py sample_data/novatech_q4_2024_report.pdf --title "NovaTech Q4 2024"
```

Run the API:
```bash
uvicorn app:app --reload --port 8000
```

Ask it something:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the sum of Headcount in Q3?"}'
```

Response looks something like this (numbers below are illustrative — swap in
whatever your own run actually returns):
```json
{
  "question": "What is the sum of Headcount in Q3?",
  "query_type": "analytical",
  "answer": "The sum of Headcount in Q3 is [replace with actual computed value].",
  "sources": { "tables": ["table_2"] }
}
```

## Running it with Docker

One image, two jobs — the same Dockerfile serves the API by default and runs the
indexer when you override the command:

```bash
docker compose up --build -d
docker compose logs -f api    # wait for "Application startup complete"
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

## A couple of things worth knowing before you rely on this

**docling-core has to be pinned alongside docling.** `docling==2.28.0` doesn't pin
its own `docling-core` version, and letting it resolve to latest breaks the import
chain entirely — the module layout changed enough between versions that
`docling.document_converter` stops existing. `requirements.txt` pins
`docling-core<2.30` for exactly this reason. Found this the hard way; if you ever
bump the docling version, check this pin still holds.

**Analytical answers should be spot-checked.** The pandas agent is reliable at
*doing arithmetic correctly once it has the right table*, but retrieval still has
to find the right table in the first place. If a report has multiple tables that
could plausibly answer a question, worth checking `sources.tables` in the response
against what you'd expect.

**Table size assumption.** Each table indexes as one unit — no row-level chunking.
Fine for report-sized tables (a handful of rows to a few dozen). A table with
hundreds of rows would ship as one big blob to the pandas agent, which nobody's
tested here.

**First run downloads Docling's models.** The first time you run `main.py`, Docling
pulls its layout/OCR models from Hugging Face. That takes a minute and needs
network access to `huggingface.co` — if indexing hangs on the first PDF, that's
probably why.
