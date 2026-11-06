# ADR 0008: Playbooks and terms as the internalisation layer

- Status: Accepted
- Date: 2026-11-06

## Context

The verified fact layer answers "what is the rule" but not "what do I do next".
A captain asking about the closure needs a short, ordered walk-through with the
documents, deadlines and penalties attached. Fishery workers also use colloquial
names and local variants that the formal corpus does not contain, so a correct
document can be missed by a lexical search.

## Decision

- Add **playbooks**: short, persona-specific procedures whose every step cites
  one or more approved facts. A playbook cannot be approved when a step has no
  source or when a cited fact is stale.
- Add a **term and alias layer**: standard term, variants, dialect, region and
  source. Aliases expand retrieval only; the answer still cites the standard
  term and the source text.
- Keep facts and FAQs as the atomic layer. Facts carry verbatim evidence,
  effective dates, conflict checks and a review date. FAQs resolve to approved
  facts.
- Update the layers only through the weekly discovery-and-review loop. A changed
  source or a new notice creates a candidate; a human approves the source, the
  fact and the playbook in that order.

## Consequences

- Content work becomes the bottleneck, not code. The first batch is deliberately
  small: fifteen playbooks, 150 terms, 200 facts.
- Playbooks need their own validator and a coverage matrix by persona and task.
- A playbook is not a substitute for the law: it always links the underlying
  provision and says that the official text prevails.
- The term layer improves recall but cannot make an unsupported answer valid.

## References

- [Knowledge notes](../knowledge.md)
- [Knowledge policy](../knowledge-policy.md)
- [Data model](../data-model.md)
