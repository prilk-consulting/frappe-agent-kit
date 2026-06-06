# Sample `/frappe-audit` report

This is a real, lightly-sanitized report produced by running `/frappe-audit` against a
production Frappe app (~13 DocTypes, 31 whitelisted methods, KYC + document-signing
domain). App name and a few identifiers are generalized; the findings, line-citation
style, and severity calls are unchanged.

The audit ran three specialist agents in parallel (`frappe-security`, `frappe-schema`,
`frappe-quality`), then the orchestrator verified the two headline security findings
against source before writing them up — the workflow's verify-before-report step in action.

---

## Summary

A mature, well-structured app — hooks all resolve, patches are uniformly guarded and
idempotent, install routines symmetric, build artifacts gitignored. The two issues to
fix first are both data-exposure holes: a provider `client_secret` written unredacted to
Integration Request logs, and a guest-accessible endpoint that leaks PII and private file
URLs without a permission check. The highest-value structural fix is enforcing a
uniqueness invariant the whole codebase assumes but nothing guarantees.

## Critical

_None._ (A self-approval path that would otherwise be Critical is properly closed by a
role-gated approval workflow + `before_insert` forcing a pending state — verified.)

## High

- [ ] **Plaintext `client_secret` persisted to Integration Request logs** — `<provider>.py:246` via `integrations.py:32` — the API secret goes into the logged `payload` dict; the logger's own docstring says "no redaction." Anyone with Integration Request read (or a DB backup) recovers the live secret. **Fix:** redact before logging (the code already intends this for a sibling field). _Verified at source._
- [ ] **Guest endpoint leaks roster PII + private file URLs** — `api/envelope.py:231` — `@frappe.whitelist(allow_guest=True)`, takes attacker-controlled identifiers, returns private file URLs + every participant's email/role/status with no permission check. A sibling endpoint gates correctly — this one doesn't. **Fix:** drop `allow_guest`, gate on the sibling's check, or restrict to records the session user participates in. _Verified at source._
- [ ] **Missing "one active record per user" constraint** — `<doctype>.json` (link field not unique, no validate guard) — the codebase does `db.get_value(..., {"user":..., "status":"Active"})` in 3+ hot paths; a 1:N match returns an arbitrary row → nondeterministic behavior. **Fix:** validate-throw on a second active row per user (field-level `unique` won't work — multiple inactive rows per user are valid).
- [ ] **No tests for any DocType** — security-critical logic has zero `test_*.py`. **Fix:** start with the workflow-gated doctype and the two pure resolver/verifier modules.

## Medium _(abridged)_

- [ ] Webhook accepts unsigned requests — HMAC check runs only `if header present` and is wrapped in `try/except: pass`.
- [ ] A second read endpoint returns the full roster + file URLs to any authenticated user.
- [ ] Provider stored as free-text `Data`, not `Link` to the existing master → no referential integrity.
- [ ] Transactional doc not submittable / mutable after completion → audit chain editable.
- [ ] Audit-log doctype lacks `track_changes` and is writable → evidence trail can be silently altered.
- [ ] `db.commit()` in ~30 request handlers → defeats request atomicity.
- [ ] Custom buttons duplicate on re-refresh (no `remove_custom_button` before re-add).

## Low _(abridged)_

File-by-basename read without ownership check · unscoped `read` on a PII-bearing log ·
manual-insert path leaves an expiry field null · `index_web_pages_for_search` on a
PII doctype · editable-but-never-computed expiry field · missing `search_index` on a
daily-scanned status field · untranslated `throw` messages.

## Reviewed, confirmed OK

No path traversal (basenaming blocks `../`); `subprocess.run` uses argv lists (no shell
injection); patch `db.sql` interpolates only allowlisted column names; OAuth guest
callbacks validate state tokens and block open-redirect; no hardcoded secrets; self-
approval closed by workflow; single-default enforced server-side; build artifacts
gitignored.

---

_Every finding cites `file:line`. The "Reviewed, OK" section records dangerous-looking
patterns the agents confirmed safe, so you know they were covered rather than missed._
