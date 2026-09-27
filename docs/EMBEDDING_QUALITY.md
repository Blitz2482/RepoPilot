# RepoPilot Embedding Quality Check

## Scope

The bundle requires an embedding pipeline and a quality check before integration. This offline check validates the implementation contract without fabricating measurements for a real hosted embedding provider.

## Verified locally

- The production model setting is `text-embedding-3-small`.
- Vectors are required to be exactly 1536 dimensions, matching `vector(1536)` in `backend/schema.sql`.
- Local/demo embeddings are deterministic and normalized, so tests are reproducible without credentials.
- The three-repository offline QA test exercises Python, TypeScript, and mixed repositories through ingest, parse, chunk, embed, synthesis, source citation, and Q&A retrieval.
- Retrieval returns repository-grounded citations rather than synthetic file references.

## What is intentionally not claimed

This document does **not** claim semantic accuracy for the hosted OpenAI embedding model. Measuring recall/precision of the real provider requires a configured API key and a labeled benchmark corpus; that is a deployment-time validation step.

## Production acceptance

After `OPENAI_API_KEY` is supplied, repeat the same three-repository test with `LOCAL_EMBEDDINGS=false` and record the retrieval metric used by the team. The application already rejects unexpected embedding dimensions and stores vectors in the schema-compatible 1536-dimensional column.
