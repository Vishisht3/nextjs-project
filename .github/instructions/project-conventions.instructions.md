---
name: project-conventions
description: "Apply current dependency, import, API, structure, and framework conventions across the entire project."
applyTo: "**/*"
---

## Project-Wide Rules

Use installed package types, local documentation, and declared manifests as the source of truth. Do not rely on memory for current APIs, model identifiers, imports, or dependency versions.

- Keep frontend code under `frontend/` and backend code under `backend/`.
- Keep frontend dependencies in `frontend/package.json` and `frontend/package-lock.json`.
- Keep backend dependencies in `backend/requirements.txt`.
- Do not create duplicate root `node_modules`, package manifests, virtual environments, or build output.
- Use the project virtual environment when available: `.venv/Scripts/python.exe` on Windows.
- Preserve package compatibility constraints; do not force newer transitive versions that violate parent requirements.
- Do not introduce deprecated imports, APIs, model names, or framework conventions.
- Before dependency or API changes, run `.agents/skills/dependency-api-audit/scripts/audit-project.ps1`.
- After a change, inspect only files named by audit failures and rerun the audit.

## Frontend: HeroUI and Tailwind

Use the installed `@heroui/react` package as the source of truth.

- Import HeroUI components from `@heroui/react`; do not use `@nextui-org/react`.
- Use HeroUI v3 compound APIs such as `Card.Content` and `Accordion.Item`.
- Use `TextArea`, standard `rows`, and typed React change events.
- Use Button `variant` and `isDisabled`; do not use legacy `color` or `isLoading` Button props.
- Use Tailwind classes for shadows and layout; do not use legacy component shadow props.
- Keep `globals.css` imports compatible with Tailwind CSS v4 and `@heroui/styles`.

## Backend: Python and RAG

- Keep Python imports rooted at backend packages such as `agent`, `api`, `config`, `ingestion`, `retrieval`, and `store`.
- Route document parsing through `ingestion/parsers/` and preserve parser metadata.
- Keep ingestion flow ordered as parsing, chunking, embedding, pgvector upsert, and BM25 rebuild.
- Preserve citation IDs in `[doc_id:chunk_index]` form; do not shorten or invent them.
- Keep retrieval context and verifier evidence aligned so answers cannot cite chunks not present in retrieved context.
- Use public package APIs from the installed versions of FastAPI, Groq, fastembed, bm25s, psycopg, pgvector, and parser libraries.
- Import-check all backend packages after dependency changes.

## API, Configuration, and Containers

- Keep FastAPI entrypoints and upload/streaming routes under `backend/api/`.
- Keep runtime configuration under `backend/config/`; do not hard-code secrets or service credentials.
- Keep Docker build contexts aligned with `frontend/` and `backend/` ownership.
- Update Compose paths, working directories, and commands whenever files move.
- Keep environment-specific values in environment variables or documented Compose configuration.

## Naming and Validation

- Use kebab-case for repository automation filenames, such as `audit-project.ps1` and `audit-backend-imports.py`.
- Use standard Python module naming for importable Python files and TypeScript conventions for frontend files.
- Prefer one project audit entrypoint with language-specific helpers where runtime tooling requires it.
- Treat registry/network failures as informational, but treat compile, import, build, and dependency-consistency failures as actionable.
