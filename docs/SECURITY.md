# Security notes
Passwords: scrypt (N=2^14). Sessions: HS256 JWT (iss/aud/exp validated, `typ` access vs refresh) in HttpOnly SameSite=Lax cookies; refresh cookie scoped to /api/v1/auth. CSRF: double-submit token. 
SSRF: scheme/port allow-list, DNS resolution must be globally routable, redirects re-validated, size/time limits, robots.txt honoured, text only parsed with stdlib HTMLParser. DNS-rebinding between check and connect is **not** fully mitigated.
Prompt injection: business/web content is fenced as untrusted data and tag breakout is stripped; this reduces but does not eliminate risk. Outputs are schema-validated and no tools are exposed to the model.
Limitations: in-memory rate limiter (per process); no refresh-token revocation list; exports stored in the DB.
