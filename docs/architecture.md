# Architecture

Northbridge Policy Assistant follows a retrieval-first architecture.

## Main Flow

1. Load approved CSV and PDF documents.
2. Convert them into plain-text document objects.
3. Chunk long documents into smaller searchable sections.
4. Index chunks with a BM25 retriever.
5. Expose retrieval through a `search_documents` tool.
6. Use a LangGraph assistant node to decide when to call the tool.
7. Return grounded answers with source references and confidence cues.

## Design Principle

The model should not be the source of truth. It should coordinate the workflow, interpret the question, call the retrieval tool, and explain the retrieved material.

## Control Points

- Required tool call before factual answers.
- Confidence threshold for weak retrieval results.
- Escalation language when documentation is insufficient.
- Source citation requirement.
- No API keys stored in the repository.
