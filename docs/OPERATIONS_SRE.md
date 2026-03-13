# Site Reliability & Day-2 Operations

This document defines the operational maturity, observability standards, and disaster recovery objectives for the High-Assurance Architecture.

## 1. Service Level Objectives (SLOs) & Error Budgets
To maintain compliance and reliability, the platform strictly monitors the following SLOs. If the Error Budget is exhausted, all feature deployments are halted until reliability is restored.

| Service Tier | Target Availability | Latency (p99) | Error Budget | Consequence of Burn |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Auth/Payments)** | 99.99% | < 200ms | 4.3 mins/month | Hard freeze on CI/CD. |
| **Tier 2 (Core API)** | 99.9% | < 500ms | 43 mins/month | Prioritize reliability backlog. |
| **Tier 3 (AI Inference)** | 99.5% | < 2500ms | 3.6 hours/month | Alert on-call. |

## 2. Observability & Log Schema
Unstructured logs are prohibited. All services must emit logs in JSON format adhering to the following schema to ensure cross-service correlation.

**Required JSON Log Schema:**
```json
{
  "timestamp": "ISO-8601 strict",
  "level": "INFO | WARN | ERROR | FATAL",
  "service_name": "string",
  "trace_id": "UUID (propagated via X-Correlation-ID)",
  "span_id": "UUID",
  "user_id": "string (Hashed/Anonymized)",
  "event": "string (Discrete event taxonomy)",
  "metrics": {}
} 


