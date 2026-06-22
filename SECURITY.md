# Security Policy

`office_bot` is currently a public preview within OpenHRI for simulation and
repeatable workflow development. It is not a safety-certified robot product and
should not be used for unsupervised physical robot operation.

## Supported Versions

| Version | Security support |
| --- | --- |
| `0.1.0-preview` | Best-effort source and workflow issue triage |

## Reporting A Vulnerability

Do not include secrets, private logs, credentials, or sensitive deployment
details in a public issue.

For repository, container, dependency, or workflow security issues, use GitHub
private vulnerability reporting if it is enabled for the repository. If private
reporting is unavailable, open a minimal public issue that asks for a security
contact path without disclosing exploit details.

For hardware safety concerns, use the hardware bringup issue template and omit
private location, operator, or customer details from public artifacts.

## Scope Limits

- The current branch documents simulation and source readiness only.
- Physical robot safety, emergency stop behavior, battery handling, and shared
  workspace use are not covered until the hardware readiness checklist has dated
  evidence.
- Third-party simulation assets retain their own license and provenance risks as
  described in [docs/asset-attribution.md](docs/asset-attribution.md).
