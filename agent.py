import json
import uuid
from collections import OrderedDict

import pandas as pd
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.tools.python.tool import PythonAstREPLTool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHAT_MODEL, CHUNK_OVERLAP, CHUNK_SIZE, CONNECTION_STRING, EMBEDDING_MODEL, ID_KEY, TABLE_COLLECTION, TEXT_COLLECTION
from postgres_store import PostgresByteStore
from prompts import ANALYTICAL_SYSTEM_PROMPT, HYBRID_SYSTEM_PROMPT, TABLE_SUMMARY_PROMPT, TEXT_SYSTEM_PROMPT

_llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)



def get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def get_text_store(embedder) -> PGVector:
    return PGVector(
        embeddings=embedder,
        collection_name=TEXT_COLLECTION,
        connection=CONNECTION_STRING,
        use_jsonb=True,
    )


def get_table_retriever(embedder) -> MultiVectorRetriever:

    vectorstore = PGVector(
        embeddings=embedder,
        collection_name=TABLE_COLLECTION,
        connection=CONNECTION_STRING,
        use_jsonb=True,
    )
    byte_store = PostgresByteStore(CONNECTION_STRING, TABLE_COLLECTION)
    return MultiVectorRetriever(vectorstore=vectorstore, byte_store=byte_store, id_key=ID_KEY)



def chunk_text_items(text_items: list) -> list:
  
    pages = OrderedDict()
    for item in text_items:
        pages.setdefault(item["page"], []).append(item["text"])

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for page, texts in pages.items():
        full_text = "\n".join(texts)
        for i, chunk in enumerate(splitter.split_text(full_text)):
            chunks.append({"page": page, "chunk_index": i, "content": chunk})
    return chunks


def index_text_chunks(store: PGVector, filename: str, title: str, chunks: list) -> None:
    if not chunks:
        return
    docs = [
        Document(
            page_content=c["content"],
            metadata={
                "filename": filename,
                "title": title,
                "page": c["page"],
                "chunk_index": c["chunk_index"],
            },
        )
        for c in chunks
    ]
    store.add_documents(docs)


def summarize_table(caption: str, markdown: str) -> str:
    prompt = TABLE_SUMMARY_PROMPT.format(caption=caption or "(no caption)", markdown=markdown)
    return _llm.invoke(prompt).content


def index_tables(retriever: MultiVectorRetriever, filename: str, title: str, tables: list) -> None:
    if not tables:
        return

    doc_ids = [str(uuid.uuid4()) for _ in tables]
    summary_docs = []
    full_docs = []

    for table, doc_id in zip(tables, doc_ids):
        df = table["dataframe"]
        table_name = f"table_{table['index']}"
        summary = summarize_table(table["caption"], table["markdown"])

        summary_docs.append(
            Document(
                page_content=summary,
                metadata={ID_KEY: doc_id, "filename": filename, "title": title, "table_name": table_name},
            )
        )

      
        full_docs.append(
            (
                doc_id,
                Document(
                    page_content=table["markdown"],
                    metadata={
                        "filename": filename,
                        "title": title,
                        "table_name": table_name,
                        "caption": table["caption"],
                        "page": table["page"],
                        "columns": [str(c) for c in df.columns],
                        "rows": df.astype(str).to_dict(orient="records"),
                        "markdown": table["markdown"],
                    },
                ),
            )
        )

    retriever.vectorstore.add_documents(summary_docs)
    retriever.docstore.mset(full_docs)


def retrieve_text_chunks(store: PGVector, query: str, k: int = 5) -> list:
    retriever = store.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(query)
    return [
        {
            "content": d.page_content,
            "page": d.metadata.get("page"),
            "filename": d.metadata.get("filename"),
        }
        for d in docs
    ]


def retrieve_tables(retriever: MultiVectorRetriever, query: str, k: int = 2) -> list:
    retriever.search_kwargs = {"k": k}
    docs = retriever.invoke(query)
    return [
        {
            "table_name": d.metadata.get("table_name"),
            "caption": d.metadata.get("caption"),
            "columns": d.metadata.get("columns"),
            "rows": d.metadata.get("rows"),
            "markdown": d.metadata.get("markdown"),
            "page": d.metadata.get("page"),
            "filename": d.metadata.get("filename"),
        }
        for d in docs
    ]




def build_dataframes(tables: list) -> dict:
    dfs = {}
    for t in tables:
        rows = t["rows"]
        rows = json.loads(rows) if isinstance(rows, str) else rows
        dfs[t["table_name"]] = pd.DataFrame(rows)
    return dfs


def run_analytical_query(question: str, tables: list) -> dict:

    dfs = build_dataframes(tables)
    python_tool = PythonAstREPLTool(locals=dfs)
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANALYTICAL_SYSTEM_PROMPT.format(table_names=list(dfs.keys()))),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    agent = create_tool_calling_agent(llm, [python_tool], prompt)
    executor = AgentExecutor(agent=agent, tools=[python_tool], verbose=False, max_iterations=8)
    result = executor.invoke({"input": question})

    return {"answer": result["output"], "tables_used": list(dfs.keys())}


def answer_text_query(question: str, chunks: list) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [("system", TEXT_SYSTEM_PROMPT), ("human", "{question}")]
    )
    context = "\n\n".join(f"[p.{c['page']}] {c['content']}" for c in chunks)
    chain = prompt | _llm
    result = chain.invoke({"context": context, "question": question})
    return result.content


def answer_hybrid_query(question: str, chunks: list, analytical_result: dict) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [("system", HYBRID_SYSTEM_PROMPT), ("human", "{question}")]
    )
    context = "\n\n".join(f"[p.{c['page']}] {c['content']}" for c in chunks)
    chain = prompt | _llm
    result = chain.invoke(
        {
            "context": context,
            "analytical_result": analytical_result["answer"],
            "question": question,
        }
    )
    return result.content
