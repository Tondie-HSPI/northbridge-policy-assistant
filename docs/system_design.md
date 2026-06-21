# Northbridge Policy Assistant - System Design

Northbridge Policy Assistant is a controlled applied-AI workflow for answering organization-specific policy questions with retrieval, source grounding, confidence cues, and escalation boundaries.

## Architecture Overview

The system separates responsibilities across three layers:

### Retrieval Layer

Local CSV and PDF files are loaded, converted to text, chunked, and indexed with a BM25 retriever. The assistant searches these internal materials before answering factual questions.

### LLM Layer

The language model interprets the user's question and produces a plain-English answer after calling the retrieval tool. The model is instructed to cite sources, avoid unsupported claims, and escalate when documentation is insufficient.

### Control Layer

Deterministic workflow controls sit around the LLM behavior:

- Required document search before factual answers.
- Confidence labels based on retrieval strength.
- Escalation when no relevant documentation is found.
- Source citation requirements.
- No invention of facts outside retrieved materials.

## Workflow

1. User asks a policy or operations question.
2. The assistant routes the question to the `search_documents` tool.
3. The retrieval layer returns relevant document chunks and a confidence level.
4. The assistant answers using only retrieved context.
5. If documentation is weak or missing, the assistant escalates instead of guessing.

## Why This Matters

Policy, compliance, and operations work often depends on scattered internal documents. A controlled RAG workflow can reduce manual search time while preserving human judgment and auditability.
