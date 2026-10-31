# Documentation Style Guide

## Language

- English is canonical for documentation, code comments, commit messages, issue
  and pull request templates.
- [README.zh-CN.md](../README.zh-CN.md) mirrors [README.md](../README.md).
- `PROJECT.zh-CN.md` mirrors [PROJECT.md](../PROJECT.md).
- Architecture, plan, evaluation and data-policy documents carry a 3–5 line
  Chinese summary at the top. They are not fully translated.
- Community and legal texts stay in English.

## Structure

- One H1 per document; sentence-case headings.
- Start with purpose and status; end with references.
- Keep tables narrow enough to read on GitHub.

## Links

- Use relative links inside the repository; no absolute local paths.
- Do not link to internal programme material, task identifiers or private repositories.
- The public-tree check validates relative links.

## Dates and numbers

- Use ISO 8601 dates (`2026-10-31`).
- State the unit and the source for every number.
- Do not mix statistical definitions from different sources.

## Citations

- Use `[doc_id p.page]` for source evidence; add section or table anchors when useful.
- Every factual claim must be traceable to a source or a recorded decision.

## Terminology

- Use [glossary.md](glossary.md); add a term to the glossary before using it in a
  new sense.

## Versioning

- No version numbers, tags or release notes.
- Refer to a commit SHA or a date.

## Data and security

- No data payloads, indexes, run artifacts, credentials or personal information.
- No internal names, task identifiers or absolute local paths.
- Follow [data-policy.md](data-policy.md) and
  [SECURITY.md](../.github/SECURITY.md).

## Chinese summaries

- 3–5 lines; summarise the document, introduce no new facts, and link to the
  English document.

## Commit messages

- Short imperative English subject; no version numbers.
- Examples: `Add corpus licence fields`, `Fix citation link validation`.

## Pull request checklist

- The change matches the scope in [PROJECT.md](../PROJECT.md).
- Relative links resolve; the public-tree check passes.
- No data, secrets or internal identifiers.
- The Chinese mirror is updated when English changes.
