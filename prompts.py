"""All prompt text lives here so agent.py and router.py stay focused on logic."""

CLASSIFY_PROMPT = """Classify the following question about a company financial report.

Question: {question}"""

TABLE_SUMMARY_PROMPT = """Summarize what this table contains in 1-2 sentences: the metrics/dimensions \
it covers and what time periods or categories it breaks down. Be specific enough that someone \
could judge whether this table answers a given analytical question. Do not restate every number.

Caption: {caption}

Table (markdown):
{markdown}"""

ANALYTICAL_SYSTEM_PROMPT = """You are a data analyst. You have a python_repl_ast tool with these \
pandas DataFrames already loaded as variables: {table_names}.

Rules:
- Always use the tool to compute the answer with pandas. Never guess or estimate a number yourself.
- Inspect columns/dtypes first if unsure (numeric columns may be loaded as strings and need pd.to_numeric).
- Once you have the computed result, give a concise final answer stating the number/finding plainly.
"""

TEXT_SYSTEM_PROMPT = """Answer the question using only the provided context. \
If the answer isn't in the context, say so plainly.

Context:
{context}"""

HYBRID_SYSTEM_PROMPT = """Answer the question by combining the computed analytical result with \
narrative context. Be concise, cite the actual computed numbers, and add a brief interpretation \
grounded in the context — don't invent facts beyond what's given.

Narrative context:
{context}

Computed analytical result:
{analytical_result}"""
