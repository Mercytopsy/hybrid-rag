from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem


def parse_pdf(pdf_path: str):

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    text_items = []
    for item, _level in doc.iterate_items():
        if isinstance(item, TableItem):
            continue
        text = getattr(item, "text", None)
        if not text or not text.strip():
            continue
        page_no = item.prov[0].page_no if getattr(item, "prov", None) else None
        text_items.append({"page": page_no, "text": text.strip()})

    table_items = []
    for idx, table in enumerate(doc.tables):
        df = table.export_to_dataframe()
        page_no = table.prov[0].page_no if getattr(table, "prov", None) else None
        try:
            caption = table.caption_text(doc) or ""
        except Exception:
            caption = ""
        table_items.append(
            {
                "index": idx,
                "page": page_no,
                "caption": caption,
                "dataframe": df,
                "markdown": df.to_markdown(index=False),
            }
        )

    return text_items, table_items
