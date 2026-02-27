# Compound Engineering Log — Brand Analytics

## Session: 2026-02-27

### Phase 1: Testing (85 → 315 tests)

**Starting state:** 5 test files, 85 tests covering scoring utilities, report shape validation, and basic health/analysis API endpoints.

**What was added (230 new tests across 11 files):**

| File | Tests | Coverage Area |
|------|-------|---------------|
| `test_validation.py` | 38 | URL validation, email validation, string sanitization, SSRF blocklists |
| `test_jwt.py` | 19 | Password hashing, API key generation, JWT create/decode lifecycle |
| `test_circuit_breaker.py` | 19 | State machine transitions, decorator, registry, error types |
| `test_security_middleware.py` | 12 | Security headers on all response types, TrustedHostMiddleware logic |
| `test_analysis_models.py` | 26 | AnalysisRequest/Response Pydantic validation, sanitization, edge cases |
| `test_auth_models.py` | 24 | User/APIKey model validation, role defaults, token data |
| `test_db_models.py` | 17 | ORM CRUD operations, constraints, cascading deletes, custom types |
| `test_enhanced_scoring.py` | 19 | NormalizedScore, ConfidenceLevel, DataSource, BenchmarkComparison |
| `api/test_reports.py` | 14 | Report/summary/share/PDF endpoints with various analysis states |
| `api/test_payment.py` | 11 | Invoice creation validation, status retrieval, payment submission |
| `test_hardening.py` | 23 | SSRF, XSS, error leakage prevention, input validation, secure defaults |

**Patterns found:**
- Existing conftest.py had solid fixtures (in-memory SQLite, test client, dependency overrides) — easy to extend
- Pydantic model tests caught several edge cases (email validation doesn't strip before regex, NormalizedScore uses `value` not `raw_score` as primary field)
- Integration tests via httpx AsyncClient + ASGITransport are fast (~6s for 315 tests)

### Phase 2: Security Hardening

**Vulnerabilities found and fixed:**

#### 1. SSRF via URL Normalization Bypass (HIGH)
- **Issue:** `normalize_url("file:///etc/passwd")` → `"https://file///etc/passwd"` which bypassed scheme blocklists
- **Fix:** Check for blocked schemes *before* adding https:// prefix; now raises ValueError
- **Pattern:** Always validate before normalizing

#### 2. SSRF via Bare IPv6 (MEDIUM)
- **Issue:** `http://::1` bypassed SSRF blocklist because `urlparse` sets `hostname=None` for bare IPv6
- **Fix:** Also check raw `netloc` against blocklist, and try parsing stripped netloc as IP address
- **Pattern:** Don't trust `urlparse.hostname` alone; always cross-check with raw `netloc`

#### 3. Error Detail Leakage — 5 locations (MEDIUM)
- Health endpoint: `str(e)` from DB/Redis exceptions exposed to clients → replaced with `"connection_failed"`
- Reports PDF endpoint: `f"Failed to generate PDF: {str(e)}"` → generic message, server-side logging
- Payment endpoint: `detail=str(e)` on ValueError → allowlisted safe messages only
- Analysis tasks: `f"{type(e).__name__}: {str(e)}"` stored in DB → stores only exception type
- Analysis status API: error_message returned directly → now strips messages containing stack traces or file paths

#### 4. Debug Errors Enabled by Default (MEDIUM)
- **Issue:** `ENABLE_DEBUG_ERRORS: bool = True` meant production would leak full exception details unless explicitly configured
- **Fix:** Default changed to `False`
- **Pattern:** Security-sensitive defaults should always be the safe option

#### 5. Missing Input Validation on Payment Address (LOW)
- **Issue:** Payment invoice endpoint only checked `startswith("0x")` and `len == 42`, not hex format
- **Fix:** Added Pydantic `field_validator` with `^0x[0-9a-fA-F]{40}$` regex
- **Pattern:** Use Pydantic validators over manual checks in route handlers

#### 6. CORS Missing Required Headers (LOW)
- **Issue:** `X-API-Key` and `X-Invoice-ID` not in CORS `allow_headers`; rate limit headers not in `expose_headers`
- **Fix:** Added both sets of headers
- **Pattern:** CORS config should include all custom headers used by the frontend

### Remaining Opportunities (not addressed this session)

1. **Rate limiting has Redis dependency** — if Redis is down, rate limiting is silently bypassed. Consider in-memory fallback.
2. **JWT secret key default** — `"change-me-in-production..."` is weak; could add startup validation that rejects the default in non-dev environments.
3. **No CSRF protection** — FastAPI APIs are typically stateless (Bearer auth), but the cookie-based session flow (if any) would need SameSite/CSRF tokens.
4. **API key iteration** — `require_api_key` loads ALL active keys and iterates with bcrypt verify, which is O(n) and slow at scale. Consider prefix-based lookup.
5. **SQL injection** — SQLAlchemy ORM with parameterized queries handles this well; no raw SQL concatenation found. ✅
6. **Analyzer error messages** — Individual analyzers (seo.py, social.py, etc.) still store `str(e)` in their results, but these are in the `report` JSON, not directly exposed as error messages.

### Architecture Notes

- **Stack:** FastAPI + SQLAlchemy async + Pydantic v2 + bcrypt/jose
- **Test runner:** pytest + pytest-asyncio with in-memory SQLite
- **Middleware chain:** RequestLogging → CORS → TrustedHost → SecurityHeaders
- **Auth:** API key + JWT dual-mode with optional enforcement
- **Payment:** x402 EIP-3009 via Plasma network
- **Analysis:** Modular analyzer pattern with circuit breakers and background tasks
