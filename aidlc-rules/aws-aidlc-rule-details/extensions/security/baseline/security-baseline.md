# Baseline Security Rules

## Overview
MANDATORY cross-cutting constraints across all AI-DLC phases. Not optional guidance — hard constraints enforced during questions, design, code generation, and completion messages.

**Enforcement**: Verify compliance before every stage completion message.

### Blocking Finding Behavior
1. List finding in completion message under "Security Findings" with rule ID
2. Do NOT present "Continue to Next Stage" — only "Request Changes"
3. Log in `audit.md` with rule ID, description, stage context
4. N/A rules (e.g., SECURITY-01 when no data stores exist) are not blocking

All rules are **blocking** by default.

---

## SECURITY-01: Encryption at Rest and in Transit
Every data store MUST have encryption at rest (managed/customer keys) and encryption in transit (TLS 1.2+).
- **Verify**: No storage without encryption config; no unencrypted connection strings; object storage enforces TLS via policy
- **AWS**: `StorageEncrypted: true` on RDS; `BucketEncryption` on S3; KMS CMKs; `aws:SecureTransport` policy
- **Azure**: `infrastructureEncryption` on SQL; Key Vault managed keys; `supportsHttpsTrafficOnly: true`

## SECURITY-02: Access Logging on Network Intermediaries
Every network-facing intermediary MUST have access logging enabled.
- Load balancers → access logs to persistent store
- API gateways → execution + access logging
- CDN → standard/real-time logs
- **Verify**: No LB/gateway/CDN without logging config

## SECURITY-03: Application-Level Logging
Every app component MUST have structured logging: framework configured, output to centralized service, includes timestamp/correlation-ID/level/message. No secrets/PII in logs.
- **Verify**: Every entry point has logger; no ad-hoc logging; no secrets logged

## SECURITY-04: HTTP Security Headers (Web Apps)
Required on all HTML-serving endpoints:

| Header | Value |
|--------|-------|
| Content-Security-Policy | Restrictive (min `default-src 'self'`) |
| Strict-Transport-Security | `max-age=31536000; includeSubDomains` |
| X-Content-Type-Options | `nosniff` |
| X-Frame-Options | `DENY` (or `SAMEORIGIN` if framing needed) |
| Referrer-Policy | `strict-origin-when-cross-origin` |

- **Verify**: Middleware sets all headers; no `unsafe-inline`/`unsafe-eval` without justification

## SECURITY-05: Input Validation on All API Parameters
Every API endpoint MUST validate all inputs: type checking, length/size bounds, format validation (allowlists), sanitization (XSS prevention), injection prevention (parameterized queries only).
- **Verify**: Every handler uses validation schema; no raw input concatenated into SQL/commands; string max-lengths set; request body limits configured

## SECURITY-06: Least-Privilege Access Policies
Every IAM policy MUST use specific resources and actions — NEVER wildcards (document exceptions). Separate read/write permissions.
- **AWS**: Specific `Action`/`Resource` ARNs; `Condition` blocks; prefer managed policies
- **Azure**: RBAC scoped to resource (not subscription); Managed Identities over secrets
- **Verify**: No wildcard actions/resources without exception; no over-broad roles

## SECURITY-07: Restrictive Network Configuration
Deny-by-default. Only open required ports. No `0.0.0.0/0` inbound except LB 80/443. Private subnets via NAT (not IGW). Use private endpoints.
- **Verify**: No wide-open firewall rules; DB/app restricted to specific CIDRs/SGs; private endpoints for cloud services

## SECURITY-08: Application-Level Access Control
- Deny by default (all routes require auth unless explicitly public)
- Object-level authz (verify caller owns resource — prevent IDOR)
- Function-level authz (admin checks server-side)
- CORS restricted to explicit origins (no `*` on authenticated endpoints)
- Token validation server-side on every request
- **Verify**: Auth middleware on every handler; no IDOR; role checks server-side; CORS restricted

## SECURITY-09: Security Hardening
- No default credentials; minimal installation; generic production errors (no stack traces)
- Disable directory listing; block public cloud storage; use supported versions
- **Verify**: No default creds in config; no stack traces in prod responses; no sample apps deployed

## SECURITY-10: Software Supply Chain
- Pin all dependency versions (lock files); configure vulnerability scanning
- Remove unused deps; trusted sources only; generate SBOM for production
- No `latest` tags in Dockerfiles/CI
- **Verify**: Lock file committed; vuln scanning in CI; no unpinned images

## SECURITY-11: Secure Design Principles
- Separate security-critical logic into dedicated modules
- Defense in depth (layer controls)
- Rate limiting on public endpoints
- Consider misuse/abuse cases
- **Verify**: Security logic encapsulated; rate limiting configured; abuse scenario documented

## SECURITY-12: Authentication & Credential Management
- Passwords: min 8 chars, check breached lists, adaptive hashing
- MFA for admin (available for all users)
- Sessions: server-side expiration, invalidate on logout, secure/httpOnly/sameSite cookies
- Brute-force protection (lockout/delay/CAPTCHA)
- No hardcoded credentials — use secrets manager
- **Verify**: Adaptive hashing; secure cookies; brute-force protection; no hardcoded creds; MFA for admin

## SECURITY-13: Software & Data Integrity
- Safe deserialization (validation/allowlists); artifact integrity (checksums/signatures)
- CI/CD access-controlled; external CDN scripts use SRI hashes
- Critical data changes auditable (who/what/when)
- **Verify**: No unsafe deserialization; SRI on CDN resources; CI/CD changes auditable

## SECURITY-14: Alerting & Monitoring
- Alert on: auth failures, privilege escalation, unusual access, authz failures
- Append-only/tamper-evident log storage; min 90-day retention
- Monitoring dashboard for security/operational metrics
- **Verify**: Alerts for auth/authz failures; retention policies set; app can't delete own logs

## SECURITY-15: Exception Handling & Fail-Safe Defaults
- All external calls have explicit error handling (no unhandled rejections)
- Fail closed (deny on error, never fail open)
- Resource cleanup in error paths (try/finally)
- Generic user-facing errors; global error handler
- **Verify**: All external calls wrapped; global handler configured; error paths don't bypass authz

---

## Enforcement Integration
At each stage: evaluate all rules → include "Security Compliance" section in completion summary (compliant/non-compliant/N/A) → block on non-compliance.

## OWASP Mapping

| Rule | OWASP 2021 |
|------|-----------|
| 01 | A02 Cryptographic Failures |
| 02, 14 | A09 Logging & Monitoring Failures |
| 05, 15 | A03 Injection |
| 08 | A01 Broken Access Control |
| 09 | A05 Security Misconfiguration |
| 10 | A06 Vulnerable Components |
| 11 | A04 Insecure Design |
| 12 | A07 Authentication Failures |
| 13 | A08 Integrity Failures |
