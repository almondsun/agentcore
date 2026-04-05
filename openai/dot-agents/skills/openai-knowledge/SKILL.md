---
name: openai-knowledge
description: "Use only for OpenAI platform work: OpenAI APIs, model and config behavior, Responses or Chat Completions usage, ChatGPT Apps SDK, Codex, platform docs, or closely related OpenAI integration questions. Trigger when current official documentation should be checked before answering. Do not trigger for non-OpenAI APIs, generic LLM advice, or ordinary repo work unrelated to OpenAI products."
---

# OpenAI Knowledge

Use official OpenAI developer documentation before answering from memory.

## Workflow

1. Start with the `openaiDeveloperDocs` MCP if it is available.
2. Use `search_openai_docs` for focused retrieval and `list_openai_docs` only when the right page is unclear.
3. Use `fetch_openai_doc` to pull the exact section before answering, and use `get_openapi_spec` when the question is endpoint- or schema-specific.
4. If the MCP is unavailable or does not answer the question, fall back to official OpenAI documentation sources only.
5. State when guidance comes from current docs rather than stable background knowledge, and separate documented facts from inference.

## Rules

- Prefer official OpenAI documentation and MCP-backed retrieval over memory.
- Treat `openaiDeveloperDocs` as the first retrieval path, not an optional convenience.
- Avoid speculative answers when the docs should settle the question.
- Keep scope narrow to OpenAI platform and product work.
- Cite the source used when giving guidance that could change over time.
- If the docs do not answer the question, say so directly instead of filling gaps from memory.
- Restrict fallback browsing to official OpenAI domains.

## Output Contract

- Answer with current, source-backed guidance.
- Mention the product area consulted when relevant, such as API docs, Apps SDK docs, or Codex docs.
- Call out uncertainty or version sensitivity explicitly.
- Name the MCP or fallback source path used when that context matters to the answer.
