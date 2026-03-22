# Security, Architecture & Compliance Policies

This document defines the strict operational parameters, trust boundaries, and data handling requirements enforced by the 20-Tier High-Assurance Architecture.

## 1. Data Classification & Handling Policy
All data handled by the platform must be classified into one of four tiers. The pipeline enforces storage, encryption, and retention rules based on these classifications.

| Classification | Definition | Encryption Requirements | Retention Policy |
| :--- | :--- | :--- | :--- |
| **Public** | Data intended for unauthenticated external consumption (e.g., Marketing copy, public endpoints). | TLS 1.3 in transit. | Indefinite. |
| **Internal** | Operational data (e.g., non-PII application logs, internal metrics). | TLS 1.3 in transit, AES-256 at rest. | 90 days (hot), 1 year (cold archive). |
| **Confidential** | PII, User data, Session tokens, Financial records. | TLS 1.3 (mTLS preferred), AES-256 at rest (KMS managed). | Retained strictly per GDPR/CCPA user lifecycle. Deleted upon account closure. |
| **Restricted** | Cryptographic keys, DB root credentials, System access tokens. | Vault / AWS Secrets Manager. Never stored in DB. | Ephemeral / Rotated on schedule. |

*Note: The Tier 4 Compliance Scanner enforces that no **Confidential** or **Restricted** data is leaked into **Internal** logs.*

## 2. Trust Boundary & Network Perimeter
The architecture operates on a **Zero-Trust** model.

* **External Perimeter:** Enforced by **AWS API Gateway** combined with **AWS WAF**. All external traffic is implicitly untrusted.
* **Internal Perimeter (Service Mesh):** Inter-service communication is authenticated via **mTLS**. Microservices do not implicitly trust requests from sibling microservices.
* **AI/MCP Trust Boundary:** AI Agents and Model Context Protocol (MCP) tool-calls are treated as hostile external inputs. All AI-generated outputs are sanitized and strictly validated against a predefined allowed-tool JSON Schema before execution.

## 3. Secret Rotation Schedule
Detection of leaked secrets is insufficient without a defined rotation schedule. The platform mandates the following lifecycle for cryptographic assets:

* **JWT Signing Keys:** Rotated automatically every 30 days.
* **Database Application Credentials:** Rotated every 90 days.
* **API Access Tokens (External):** Rotated every 90 days or immediately upon suspected compromise.
* **TLS Certificates:** Automated renewal triggered 30 days prior to expiry (Max validity: 90 days via Let's Encrypt / ACM).

## 4. Threat Simulation Profiles (WAF & DDoS)
The Tier 7 (Edge Infrastructure) tests do not broadly "test DDoS." They execute specifically bounded attack profiles to verify WAF rule sets:
* **HTTP Flood / Botnet Simulation:** Verified via `k6` executing rapid, distributed `GET` requests from rotating IPs. Expected response: HTTP 429 after $N$ requests/min.
* **Slowloris Attack:** Verification that the API Gateway drops connections holding open incomplete HTTP headers beyond 5 seconds.
* **BOLA/IDOR Vectors:** Parameter-tampering tests iterating sequentially through UUIDs to ensure HTTP 403 Forbidden is returned for unauthorized resource access.

## 5. Incident Response & Secret Leak Runbook
If the Tier 13 (Dependency Secrets) Git-hook fails, or a secret is detected in CI:
1. **Pipeline Halt:** The CI/CD pipeline immediately fails and locks.
2. **Alerting:** PagerDuty alerts the on-call Security Engineer (triggered via n8n).
3. **Remediation:** The leaked key is immediately revoked at the provider level (e.g., AWS IAM).
4. **Audit:** Git history is rewritten (via BFG Repo-Cleaner) to purge the secret, and a post-mortem is documented.
