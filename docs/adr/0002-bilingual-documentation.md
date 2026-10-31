# ADR 0002: Bilingual documentation

- Status: Accepted
- Date: 2026-10-31

## Context

The primary audience reads Chinese, while GitHub renders the default English
README. A single Chinese README linked only at the bottom of the English README was
not discoverable from the repository landing page.

## Decision

- English is the canonical language for documentation, code comments, commit
  messages and issue/PR templates.
- [README.zh-CN.md](../../README.zh-CN.md) is a full Chinese mirror of
  [README.md](../../README.md).
- `PROJECT.zh-CN.md` is a full Chinese mirror of [PROJECT.md](../../PROJECT.md).
- Architecture, plan, evaluation and data-policy documents carry a short Chinese
  summary at the top; they are not fully translated.
- The language switch sits directly under the title in both READMEs.
- [docs/glossary.md](../glossary.md) is the shared bilingual terminology source.

## Consequences

- English changes must update the Chinese mirror; reviewers check parity.
- Summaries are short and introduce no new facts.
- Community and legal texts stay in English.

## References

- [Style guide](../style-guide.md)
- [Glossary](../glossary.md)
