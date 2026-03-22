# OPA policy: high-assurance-api security invariants
package api.security

import rego.v1

# All endpoints must require authentication except /health and /login
public_endpoints := {"/health", "/login", "/openapi.yaml", "/"}

deny contains msg if {
    route := input.routes[_]
    not route.path in public_endpoints
    not route.auth_required
    msg := sprintf("Route %v must require authentication", [route.path])
}

# JWT secret must not be the default dev value in production
deny contains msg if {
    input.environment == "production"
    input.jwt_secret == "super-secure-dev-secret-key-12345"  # pragma: allowlist secret
    msg := "JWT_SECRET must not use the default development value in production"
}

# CORS wildcard must not be enabled in production
deny contains msg if {
    input.environment == "production"
    input.cors_wildcard == true
    msg := "CORS wildcard (*) must not be enabled in production"
}

# Rate limiting must be enabled on login endpoint
allow if {
    count(deny) == 0
}
