from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import CHAT_MODEL
from prompts import CLASSIFY_PROMPT


class QueryClassification(BaseModel):
    query_type: Literal["text", "analytical", "hybrid"] = Field(
        description=(
            "'text' if the answer lives in narrative/paragraph content "
            "(summaries, highlights, descriptions). 'analytical' if it "
            "requires computing over a data table (sums, max/min, "
            "comparisons, growth rates). 'hybrid' if it requires a table "
            "computation AND narrative interpretation."
        )
    )
    reasoning: str = Field(description="One-sentence justification for the classification")


_llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
_classifier = _llm.with_structured_output(QueryClassification)


def classify_query(question: str) -> QueryClassification:
    return _classifier.invoke(CLASSIFY_PROMPT.format(question=question))
