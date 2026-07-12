
import argparse
import os
import sys

from agent import chunk_text_items, get_embedder, get_table_retriever, get_text_store, index_tables, index_text_chunks
from parser import parse_pdf


def main():
    arg_parser = argparse.ArgumentParser(description="Index a PDF into the NovaTech Q&A system")
    arg_parser.add_argument("pdf_path", help="Path to the PDF file to index")
    arg_parser.add_argument("--title", default=None, help="Optional human-readable document title")
    args = arg_parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"File not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(args.pdf_path)
    title = args.title or filename

    print(f"[1/4] Parsing {args.pdf_path} with Docling...")
    text_items, table_items = parse_pdf(args.pdf_path)
    print(f"      -> {len(text_items)} text blocks, {len(table_items)} tables")

    print("[2/4] Chunking narrative text...")
    chunks = chunk_text_items(text_items)
    print(f"      -> {len(chunks)} chunks")

    embedder = get_embedder()

    print("[3/4] Embedding + indexing text chunks via LangChain PGVector...")
    index_text_chunks(get_text_store(embedder), filename, title, chunks)

    print("[4/4] Summarizing + indexing tables via MultiVectorRetriever...")
    index_tables(get_table_retriever(embedder), filename, title, table_items)

    print(f"Done. Indexed '{title}' ({len(chunks)} chunks, {len(table_items)} tables).")


if __name__ == "__main__":
    main()
