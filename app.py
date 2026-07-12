from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import (
    answer_hybrid_query,
    answer_text_query,
    get_embedder,
    get_table_retriever,
    get_text_store,
    retrieve_tables,
    retrieve_text_chunks,
    run_analytical_query,
)
from router import classify_query

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedder = get_embedder()
    state["text_store"] = get_text_store(embedder)
    state["table_retriever"] = get_table_retriever(embedder)
    yield


app = FastAPI(title="NovaTech Document Q&A API", lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str
    top_k_text: int = 5
    top_k_tables: int = 2


class QueryResponse(BaseModel):
    question: str
    query_type: str
    answer: str
    sources: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    classification = classify_query(req.question)
    sources: dict = {}

    if classification.query_type == "text":
        chunks = retrieve_text_chunks(state["text_store"], req.question, req.top_k_text)
        if not chunks:
            raise HTTPException(404, "No relevant content found")
        answer = answer_text_query(req.question, chunks)
        sources["text_chunks"] = chunks

    elif classification.query_type == "analytical":
        tables = retrieve_tables(state["table_retriever"], req.question, req.top_k_tables)
        if not tables:
            raise HTTPException(404, "No relevant tables found")
        result = run_analytical_query(req.question, tables)
        answer = result["answer"]
        sources["tables"] = [t["table_name"] for t in tables]

    else:  # hybrid
        chunks = retrieve_text_chunks(state["text_store"], req.question, req.top_k_text)
        tables = retrieve_tables(state["table_retriever"], req.question, req.top_k_tables)
        if not tables:
            raise HTTPException(404, "No relevant tables found")
        analytical_result = run_analytical_query(req.question, tables)
        answer = answer_hybrid_query(req.question, chunks, analytical_result)
        sources["text_chunks"] = chunks
        sources["tables"] = [t["table_name"] for t in tables]

    return QueryResponse(
        question=req.question,
        query_type=classification.query_type,
        answer=answer,
        sources=sources,
    )
