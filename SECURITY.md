# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x (alpha) | Yes, for documentation and configuration issues |

The project is at an early stage. There is no production service, deployment or
data distribution yet.

## Reporting a vulnerability

Please do not open a public issue for a security-sensitive report.

Use GitHub's private vulnerability reporting for this repository, or contact a
maintainer privately. Include:

- a description of the issue,
- the affected file or component,
- reproduction steps or a proof of concept,
- the potential impact,
- any suggested mitigation.

Do not include real credentials, restricted data, or personal information in a
report. If a credential has been exposed, revoke it first.

## Scope

Security-relevant areas include:

- accidental commit of credentials, tokens or private keys,
- accidental commit of data payloads, indexes or run artifacts,
- path traversal or unsafe file handling in future ingestion code,
- prompt-injection or citation-forgery risks in future retrieval and answer code,
- dependency vulnerabilities.

## Data handling

- The public repository must not contain data payloads, indexes, run outputs or
  state databases.
- Do not send `restricted` sources to external model APIs.
- Do not submit vessel-identifying or personal information.
- See [docs/data-policy.md](docs/data-policy.md) for the data boundary.

## Response

Maintainers will acknowledge a report as soon as practical, assess impact,
coordinate a fix, and credit the reporter if desired. Please allow reasonable
time for a fix before public disclosure.
