"""
LLM SQL Generator — calls OpenAI or Gemini to produce structured SQL output.
Forces JSON response with {sql_query, confidence_score, tables_used}.
"""
import json
import time
from typing import Optional

from backend.config import settings
from backend.models.schemas import LLMSQLOutput
from backend.core.schema_loader import TableSchema


# ─── Few-shot examples ──────────────────────────────────────
FEW_SHOT_EXAMPLES = """
Examples of correct SQL generation:

Q: How many orders were placed last month per region?
A: {"sql_query": "SELECT region, COUNT(*) AS order_count FROM orders WHERE created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month') AND created_at < DATE_TRUNC('month', NOW()) GROUP BY region ORDER BY order_count DESC", "confidence_score": 0.95, "tables_used": ["orders"]}

Q: What are the top 5 customers by total revenue?
A: {"sql_query": "SELECT c.customer_id, c.name, SUM(o.amount) AS total_revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name ORDER BY total_revenue DESC LIMIT 5", "confidence_score": 0.92, "tables_used": ["customers", "orders"]}

Q: Show all products that are out of stock with their category names.
A: {"sql_query": "SELECT p.product_id, p.name, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE p.stock_quantity = 0", "confidence_score": 0.90, "tables_used": ["products", "categories"]}

Q: What is the average order value by month for this year?
A: {"sql_query": "SELECT DATE_TRUNC('month', created_at) AS month, AVG(amount) AS avg_order_value FROM orders WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW()) GROUP BY month ORDER BY month", "confidence_score": 0.88, "tables_used": ["orders"]}
""".strip()

SYSTEM_PROMPT = """You are an expert SQL generator. Your ONLY job is to convert natural language questions into valid, optimized SQL queries.

Rules:
1. Output ONLY valid JSON with exactly these fields: {"sql_query": "...", "confidence_score": 0.0-1.0, "tables_used": [...]}
2. Use ONLY the tables and columns provided in the schema. Do NOT hallucinate table or column names.
3. Only generate SELECT statements. Never generate DROP, DELETE, UPDATE, ALTER, INSERT, or EXEC.
4. Do NOT add a LIMIT clause unless explicitly asked — the execution layer enforces limits.
5. Use table aliases for clarity in JOINs.
6. Set confidence_score based on how well the schema matches the question (0=poor match, 1=perfect).
7. If the question cannot be answered with the provided schema, set confidence_score < 0.5 and explain in the sql_query field.
""".strip()


def _build_user_prompt(
    nl_query: str,
    relevant_tables: dict[str, TableSchema],
    error_context: Optional[str] = None,
) -> str:
    schema_block = "\n\n".join(t.to_prompt_text() for t in relevant_tables.values())

    prompt = f"""Database Schema:
{schema_block}

{FEW_SHOT_EXAMPLES}

Question: {nl_query}"""

    if error_context:
        prompt += f"""

IMPORTANT — your previous SQL failed with this error:
{error_context}

Generate a corrected SQL query that fixes this error."""

    return prompt


class LLMGenerator:
    def __init__(self):
        self._openai_client = None
        self._gemini_model = None

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai_client

    def _get_gemini_model(self):
        if self._gemini_model is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._gemini_model = genai.GenerativeModel(settings.gemini_model)
        return self._gemini_model

    async def _call_openai(
        self, system: str, user: str
    ) -> tuple[str, int, int]:
        client = self._get_openai_client()
        response = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw = response.choices[0].message.content
        usage = response.usage
        return raw, usage.prompt_tokens, usage.completion_tokens

    async def _call_gemini(
        self, system: str, user: str
    ) -> tuple[str, int, int]:
        import google.generativeai as genai
        model = self._get_gemini_model()
        full_prompt = f"{system}\n\n{user}\n\nRespond with ONLY valid JSON."
        response = await model.generate_content_async(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=settings.llm_temperature,
                response_mime_type="application/json",
            ),
        )
        raw = response.text
        # Gemini doesn't expose token counts consistently; approximate
        return raw, 0, 0

    async def generate(
        self,
        nl_query: str,
        relevant_tables: dict[str, TableSchema],
        error_context: Optional[str] = None,
    ) -> tuple[LLMSQLOutput, str, int, int]:
        """
        Returns (LLMSQLOutput, raw_json_str, prompt_tokens, completion_tokens).
        Raises ValueError if JSON parsing fails.
        """
        user_prompt = _build_user_prompt(nl_query, relevant_tables, error_context)

        if settings.llm_provider == "openai":
            raw, pt, ct = await self._call_openai(SYSTEM_PROMPT, user_prompt)
        else:
            raw, pt, ct = await self._call_gemini(SYSTEM_PROMPT, user_prompt)

        # Parse and validate response
        try:
            data = json.loads(raw)
            output = LLMSQLOutput(
                sql_query=data["sql_query"],
                confidence_score=float(data.get("confidence_score", 0.5)),
                tables_used=data.get("tables_used", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {raw}")

        return output, raw, pt, ct


# Module-level singleton
llm_generator = LLMGenerator()
