"""Prompt assembly + OpenAI gpt-4o-mini generation (with graceful fallback)."""

from openai import AsyncOpenAI, OpenAIError

from backend.config import settings


SYSTEM_PROMPT = """You are a helpful assistant for TechNova Inc. Answer the employee's question using ONLY the information provided in the Context below.

Rules:
- Only use information from the provided context
- Cite which source number [Source X] your answer comes from
- Be specific with numbers, dates, and amounts
- If the context doesn't contain enough information, say so clearly
- Never make up information not in the context"""


def assemble_prompt(query: str, chunks: list[dict]) -> str:
    """Build the full RAG prompt from retrieved chunks."""
    if not chunks:
        context_block = "[No context retrieved.]"
    else:
        context_parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            doc = chunk.get("doc_name", "Unknown")
            page = chunk.get("page_number", "?")
            text = chunk.get("text", "")
            context_parts.append(
                f"[Source {i}] ({doc}, page {page})\n{text}"
            )
        context_block = "\n\n".join(context_parts)

    return (
        f"SYSTEM INSTRUCTION:\n{SYSTEM_PROMPT}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION:\n{query}\n\n"
        f"ANSWER:"
    )


async def generate_answer(query: str, chunks: list[dict]) -> tuple[str, str]:
    """Assemble prompt and call gpt-4o-mini. Falls back gracefully if no API key.

    Returns (answer, assembled_prompt).
    """
    prompt = assemble_prompt(query, chunks)

    if not settings.openai_api_key:
        fallback = (
            "[LLM not configured — returning assembled prompt + retrieved chunks]\n\n"
            + prompt
        )
        return fallback, prompt

    if not chunks:
        return (
            "I couldn't find any relevant information to answer that question.",
            prompt,
        )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Context:\n"
                        + "\n\n".join(
                            f"[Source {i+1}] ({c.get('doc_name', '?')}, page {c.get('page_number', '?')})\n{c.get('text', '')}"
                            for i, c in enumerate(chunks)
                        )
                        + f"\n\nQuestion: {query}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=600,
        )
        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            answer = "[Empty response from LLM]"
        return answer, prompt
    except OpenAIError as exc:
        return (
            f"[LLM call failed: {exc}. Returning assembled prompt.]\n\n{prompt}",
            prompt,
        )
