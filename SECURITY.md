# Security Policy

## Reporting a vulnerability

Do not open a public issue for suspected vulnerabilities, secrets, or private
session data. Use [GitHub private vulnerability reporting](https://github.com/almondsun/agentcore/security/advisories/new).

Include a concise impact statement, affected paths, reproduction steps, and the
smallest safe remediation when known. Redact all real secrets and personal data.

## Supported versions

Security fixes are applied to the current `linux` and `windows` branches. Older
commits and preserved evaluation artifacts are not supported releases.

## Security boundaries

- Codex sandbox and permission profiles are enforcement boundaries.
- Hooks and content scanners are defense in depth, not complete security controls.
- External MCP servers, apps, browser tools, and Computer Use have separate trust
  and approval surfaces.
- Files under eval fixtures may be intentionally vulnerable and must not be reused
  as production implementations.
