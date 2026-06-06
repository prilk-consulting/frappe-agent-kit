---
name: frappe-dev
description: Frappe Framework core development reference. Use proactively for DocType controllers, server scripts, whitelisted APIs, database operations, hooks.py, permissions, background jobs, caching, client scripts, Jinja/print formats, and custom app structure on Frappe v15+ and ERPNext.
---

# Frappe Framework Core Reference

## Usage

Use this skill when:

- Writing or reviewing DocType controllers, whitelisted API methods, or hooks.py wiring
- Database access decisions (`get_list` vs `get_all`, query builder vs raw SQL)
- Permission enforcement, background jobs, caching, desk client scripts
- Structuring a custom app that extends other apps' DocTypes
- Debugging Jinja/print-format errors → see [references/jinja-and-print-formats.md](references/jinja-and-print-formats.md)

## Document Lifecycle Hooks

```python
class MyDocType(Document):
    def before_insert(self): ...     # before first save
    def after_insert(self): ...      # after first save
    def validate(self): ...          # before save (insert/update)
    def before_save / on_update(self): ...
    def before_submit / on_submit(self): ...
    def before_cancel / on_cancel(self): ...
    def on_trash(self): ...          # before delete
```

## API Development

Two surfaces:

| Shape | URL | Use for |
|-------|-----|---------|
| **REST** | `/api/resource/<DocType>` (v1) or `/api/v2/document/<DocType>` (v15+) | Standard CRUD |
| **RPC** | `/api/method/<dotted.path>` | Custom server logic |
| **Webhook** | Webhook DocType (configured in UI) | Notify external systems |

### Whitelisted methods

```python
@frappe.whitelist()
def get_balance(customer):
    frappe.has_permission("Customer", "read", doc=customer, throw=True)
    return frappe.db.get_value("Customer", customer, "outstanding_amount")

@frappe.whitelist(methods=["POST"])
def create_payment(customer, amount): ...

@frappe.whitelist(allow_guest=True)
def public_status(): return {"status": "ok"}
```

Decorator options: `methods=[...]` (restrict HTTP verbs), `allow_guest=True` (never on state changes), `xss_safe=True` (skip XSS escape).

Response shapes: RPC returns `{"message": <value>}`, REST returns `{"data": ...}`. `frappe.throw()` returns HTTP **417** with the message in `_server_messages`.

### REST CRUD

Always send `Accept: application/json` (without it, Frappe may return HTML). List query params: `fields`, `filters`, `or_filters`, `order_by`, `limit_start`, `limit_page_length` (or `limit` alias on v15+). Filter operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`, `is set`, `is not set`, `between`.

```python
filters = [
    ["status", "in", ["Open", "Pending"]],
    ["date", "between", ["2024-01-01", "2024-12-31"]],
]
```

### Authentication

```python
headers = {"Authorization": "token api_key:api_secret", "Accept": "application/json"}
```

Generate keys: User → Settings → API Access → Generate Keys (shown once). Create a dedicated API user per integration; never use Administrator's key.

### File upload

```python
requests.post(f"{base_url}/api/method/upload_file",
    files={"file": ("doc.pdf", open("doc.pdf", "rb"), "application/pdf")},
    data={"doctype": "Customer", "docname": "CUST-001", "is_private": 1},
    headers={"Authorization": "token ..."})
# Do NOT set Content-Type — requests adds the multipart boundary itself.
```

### Client-side calls (Desk JavaScript)

- `frappe.xcall("method", args)` — preferred, async/await
- `frappe.call({ method, args, freeze, freeze_message })` — promise/callback
- `frm.call("server_method")` — sends current form values to a doc method
  - **Gotcha:** `frm.call` writes form values back; if the server method writes a Password field, the round-trip clobbers it. Use `frappe.xcall` instead.

Webhooks send `X-Frappe-Webhook-Signature` = base64(HMAC-SHA256(payload, secret)). Always set a secret and verify on the receiving side.

### Log every outbound request via `Integration Request`

ALL outbound HTTP calls to third parties (payment gateways, signing providers, e-invoicing access points, custom webhooks) SHOULD be logged via the **Integration Request** DocType. Same for inbound webhook receipts. This gives you: audit trail, retry path, debugging UI in `/app/integration-request`, and proof-of-attempt for compliance.

```python
from frappe.integrations.utils import create_request_log

# 1. Create the log BEFORE making the call
req = create_request_log(
    data=payload,                     # dict — auto-serialized to JSON
    service_name="MyProvider",        # shows up as the column in the list view
    request_headers=headers,
    url=endpoint,
    request_description="Submit invoice",
    is_remote_request=1,              # marks this as outbound (vs. notification)
    reference_doctype="Sales Invoice",
    reference_docname=invoice.name,
)

# 2. Make the call
try:
    response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    req.handle_success(response.json())     # status="Completed", output=<response JSON>
except Exception as e:
    req.handle_failure({"error": str(e)})   # status="Failed",    error=<error JSON>
    raise
```

Statuses: `Queued` → `Authorized` → `Completed` / `Failed` / `Cancelled`. Use `req.update_status(params, status)` to merge new params into `data` and bump status.

- **`reference_doctype` + `reference_docname` are mandatory** — they connect the log to the business record (so you can find "what did we send to the payment gateway for SI-00001?").
- **Auto-cleanup**: rows older than 30 days are deleted by the scheduled `clear_old_logs` job. Don't depend on Integration Request as long-term storage; copy critical fields onto the reference doc if you need them retained.
- **Retry pattern**: a retry button on the reference doc re-reads `req.data`, re-POSTs, and creates a fresh Integration Request (don't mutate the failed one — keep the audit trail).
- **Inbound webhooks**: log them too — store the raw payload + signature verification result. If the provider replays, you have proof.

## Database Operations

```python
doc = frappe.get_doc("DocType", name)
docs = frappe.get_all("DocType", filters={"status": "Open"}, fields=["name"])
value = frappe.db.get_value("DocType", name, "field")
frappe.db.set_value("DocType", name, "field", value)
doc.db_set("field", value)
frappe.db.exists("DocType", name)

# Tuple filter operators
frappe.db.get_value("DocType", {"status": ("!=", "Cancelled")}, ["name"], as_dict=True)
frappe.get_all("DocType", filters={"date": ["between", [start, end]]})
```

### `get_list` vs `get_all`

| Method | User Permissions | Permission Query Hook | Use for |
|--------|------------------|------------------------|---------|
| `frappe.get_list()` | Applied | Applied | User-facing queries |
| `frappe.get_all()` | Ignored | Ignored | System/background queries |

Use `get_list()` for anything returned to a user. `get_all()` bypasses ALL permission filtering — fine for jobs, dangerous in whitelisted endpoints.

### Query Builder (`frappe.qb`)

Preferred over `frappe.db.sql()` for new code — parameterized by default.

```python
Task = frappe.qb.DocType("Task")
Customer = frappe.qb.DocType("Customer")
from frappe.query_builder.functions import Count, Sum

(frappe.qb.from_(Task)
    .inner_join(Customer).on(Task.customer == Customer.name)
    .select(Task.status, Count(Task.name).as_("n"))
    .where((Task.status == "Open") | (Task.priority == "High"))  # OR uses `|`, not `or`
    .groupby(Task.status)
).run(as_dict=True)

# Inspect SQL without executing
query.get_sql()       # SQL string
query.walk()          # (SQL, params)
```

### SQL safety

```python
frappe.db.sql("SELECT ... WHERE name = %(name)s", {"name": user_input})  # safe
where = f"`tabCustomer`.owner = {frappe.db.escape(user)}"                # escape dynamic fragments
```

Never f-string user input into raw SQL.

## Client Scripts (Desk)

```javascript
frappe.ui.form.on("DocType", {
    refresh(frm) {
        frm.add_custom_button(__("Action"), () => {
            frappe.call({ method: "app.module.api", args: { name: frm.doc.name },
                freeze: true, callback: r => frm.reload_doc() });
        }, __("Actions"));
    },
    field_name(frm) {
        frm.set_value("other_field", frm.doc.field_name * 2);
    }
});

// Child table events
frappe.ui.form.on("Child DocType", {
    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "amount", row.qty * row.rate);
    }
});
```

### Client-script gotchas

- **`onload` doesn't always fire on hard reload** — lazy-fetch inside `refresh` instead.
- **`add_custom_button` is NOT idempotent** — `frm.remove_custom_button(label, group)` first if the handler can fire multiple times (refresh + field-change both trigger).
- **`frappe.call` ignores the `error:` callback** — that key is silently dropped. Use `always:` for success-or-failure cleanup.
- **`__()` inside JS template literals is invisible to `bench get-untranslated`** — extract to a const first: `const label = __("Label")` then `` `<th>${label}</th>` ``.
- **`frm.set_value(...).then(...)`** — only returns a Promise on v15+; v14 returns `undefined` and `.then()` silently never runs.

## hooks.py

```python
after_install = "myapp.install.after_install"
after_migrate = "myapp.install.after_migrate"

doctype_js = { "Sales Invoice": "public/js/sales_invoice.js" }
doc_events = { "Sales Invoice": { "validate": "myapp.mymodule.custom.sales_invoice.validate" } }
scheduler_events = {
    "hourly": ["myapp.tasks.hourly_task"],
    "cron": { "0 9 * * *": ["myapp.tasks.morning_task"] },
}
override_doctype_class = { "Sales Invoice": "myapp.overrides.CustomSalesInvoice" }
```

---

# Permissions

Five layers: Role → User Permission → Perm Level → `has_permission` hook → Data Masking (v16+).

### Check permission

```python
frappe.has_permission("Sales Order", "write", doc=doc, throw=True)
doc.has_permission("write")              # bool
doc.check_permission("write")            # raises frappe.PermissionError

# Debug evaluation steps
frappe.has_permission("Sales Order", "read", debug=True)
print(frappe.local.permission_debug_log)
```

### `has_permission` hook — deny-only

Can only deny; returning `True` does NOT grant. Return `None` to let standard checks proceed.

```python
# hooks.py
has_permission = { "Sales Order": "myapp.permissions.check_order" }

def check_order(doc, ptype, user):
    if ptype == "write" and doc.docstatus == 2:
        if "Sales Manager" not in frappe.get_roles(user):
            return False
    return None
```

### `permission_query_conditions` — row-level filter

Affects `frappe.get_list()` only. Returns a SQL WHERE fragment. **Always `frappe.db.escape()`** user input.

```python
permission_query_conditions = { "Customer": "myapp.permissions.customer_query" }

def customer_query(user):
    user = user or frappe.session.user
    if "Sales Manager" in frappe.get_roles(user):
        return ""
    return f"`tabCustomer`.owner = {frappe.db.escape(user)}"
```

### Bypass — last resort

```python
doc.flags.ignore_permissions = True   # always comment WHY
```

Built-in roles: `Guest` (anonymous), `All` (any auth user), `Administrator` (always passes).

---

# Background Jobs & Scheduler

### `scheduler_events` vs `frappe.enqueue`

| | `scheduler_events` (hooks.py) | `frappe.enqueue()` |
|--|------------------------------|---------------------|
| Triggered by | Time/interval | Code |
| Arguments | NONE (parameterless) | Any serializable |
| Queue control | `*_long` event suffix | `queue=` parameter |

Run `bench migrate` after editing `scheduler_events` in `hooks.py`.

### Scheduler event keys

| Key | Queue | For |
|-----|-------|-----|
| `all` | short (NEVER >60s) | Every tick |
| `hourly` / `daily` / `weekly` / `monthly` | short | Tasks <5 min |
| `hourly_long` / `daily_long` / … | long | Tasks 5-25 min |
| `cron: { "0 9 * * *": [...] }` | short | Custom schedule |

### `frappe.enqueue` pattern

```python
from frappe.utils.background_jobs import is_job_enqueued

@frappe.whitelist()
def process(doctype, filters):
    job_id = f"process_{doctype}_{frappe.session.user}"
    if is_job_enqueued(job_id):
        return {"message": "Already in progress"}
    frappe.enqueue("myapp.tasks.process_batch",
        queue="long",                # ALWAYS explicit
        timeout=1800,
        job_id=job_id,
        enqueue_after_commit=True,   # wait until current txn commits
        doctype=doctype, filters=filters)
```

Queue defaults: `short` 300s · `default` 300s · `long` 1500s.

```bash
bench --site <site> execute myapp.tasks.daily_cleanup   # run direct
bench --site <site> show-pending-jobs
bench --site <site> doctor
```

---

# Caching

```python
# Document cache — DO NOT mutate the returned doc (shared reference)
settings = frappe.get_cached_doc("System Settings")
frappe.clear_document_cache("Item", "ITEM-001")

# Redis (auto-prefixed with site name)
frappe.cache.set_value("key", data, expires_in_sec=300)
frappe.cache.delete_keys("item_price*")
frappe.cache.hset("user|perms", "u@x.com", perms)   # also hget/hdel/hgetall

# Function memoization
from frappe.utils.caching import redis_cache
@redis_cache(ttl=300)
def get_rate(from_ccy, to_ccy): ...
get_rate.clear_cache()
# Rules: args must be hashable (no dicts/lists); never decorate side-effecting fns.

# Per-request memo — plain dict, lives one HTTP request
if "user_settings" not in frappe.local.cache:
    frappe.local.cache["user_settings"] = frappe.get_doc("User Settings", frappe.session.user)
```

---

# Print Formats & Jinja Templates

Two production traps live here — the `frappe.utils.X` sandbox namespace trap (silent `None` resolution in Jinja) and the Print Format JSON-to-DB sync-skip. Full reference with fixes: [references/jinja-and-print-formats.md](references/jinja-and-print-formats.md)

---

# Custom App Development Patterns

## Recommended structure

```
myapp/
├── myapp/
│   ├── hooks.py
│   ├── install.py                  # custom fields, master data
│   ├── mymodule/
│   │   ├── setup.py                # alternate: module-local custom fields
│   │   ├── custom/                 # hook handlers for OTHER apps' DocTypes
│   │   │   └── sales_invoice.py
│   │   └── doctype/                # this app's own DocTypes
│   ├── shared/                     # cross-module utilities
│   └── public/js/
│       ├── sales_invoice.js        # client scripts for existing DocTypes
│       └── customer.js
└── pyproject.toml
```

## install.py for custom fields

Define fields in a single `get_custom_fields()` dict, wire into BOTH `after_install` and `after_migrate` for idempotency:

```python
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    create_custom_fields(get_custom_fields())
    setup_master_data()

def after_migrate():
    create_custom_fields(get_custom_fields())

def get_custom_fields():
    return {
        "Customer": [
            {"fieldname": "my_field", "label": "My Field", "fieldtype": "Data",
             "insert_after": "customer_name"},
        ],
        "Sales Invoice": [...],
    }
```

For multi-module apps, prefer **module-level `setup.py`** with one `make_custom_fields()` per module, then list them all in `after_migrate`:

```python
after_migrate = [
    "myapp.module1.setup.make_custom_fields",
    "myapp.module2.setup.make_custom_fields",
]
```

**Ownership rule:** an app only creates, reads, and writes its OWN custom fields. Never manage (or delete) custom fields that belong to another app — that's how two apps end up fighting over a field on every migrate.

## `custom/` folder for doc events

One file per DocType you're hooking. Handler functions take `(doc, method=None)`. Register paths in `hooks.py` `doc_events`.

```python
# mymodule/custom/sales_invoice.py
def validate(doc, method=None): ...
def on_submit(doc, method=None): ...
```

## Client scripts for existing DocTypes

- One file per DocType, named after it in lowercase: `public/js/customer.js`, `public/js/sales_invoice.js`. **Never** put two doctypes' `frappe.ui.form.on(...)` in one file — it kills grep-by-doctype-name.
- Register via `doctype_js` in `hooks.py`.

### Sharing client scripts across DocTypes

`doctype_js` accepts **a list of files per doctype** — Frappe concatenates them into the form's `__js` only when that form opens (smaller blast radius than `app_include_js`):

```python
doctype_js = {
    "Customer": ["public/js/shared_helpers.js", "public/js/customer.js"],
    "Supplier": ["public/js/shared_helpers.js", "public/js/supplier.js"],
}
```

List helpers first (they register a namespace), doctype-specific file last (it uses the namespace).

| Approach | Loads on | Use when |
|----------|----------|----------|
| `app_include_js = "myapp.bundle.js"` | **Every desk page** | Helpers used app-wide (ERPNext pattern) |
| `doctype_js: [helpers, doctype]` | **Only that form** | Helpers shared by a small set of related doctypes |

---

## Best Practices Summary

1. **Custom fields**: `install.py` `get_custom_fields()`, wired into BOTH `after_install` and `after_migrate`.
2. **Hook handlers**: in `custom/` folder, one file per DocType.
3. **Client scripts**: one file per DocType in `public/js/`, named after the DocType. Register via `doctype_js`.
4. **Shared client scripts**: `doctype_js: ["helpers.js", "doctype.js"]` (per-doctype). Use `app_include_js` only for truly cross-cutting helpers.
5. **Shared server code**: `shared/` folder.
6. **Permissions**: `frappe.has_permission(..., throw=True)` in whitelisted methods. `get_list` (not `get_all`) for user-facing data.
7. **Validations live server-side**: enforce rules in the controller (`validate`) or field metadata (reqd, options, depends_on) — client-side checks are UX hints only, never the enforcement layer.
8. **i18n**: `_()` / `__()` on all user-facing strings; extract from JS template literals first.
9. **Logging**: `frappe.log_error()`, never `print()`.
10. **Errors**: `frappe.throw()` for user errors; try/except + `log_error()` for system errors.
11. **Queries**: `frappe.qb` over `frappe.db.sql()`. Parameterize / `frappe.db.escape()` when raw SQL is unavoidable.
12. **Background jobs**: always explicit `queue=`; `enqueue_after_commit=True` when the job depends on data the request is writing.
13. **Caching**: never mutate a `get_cached_doc()` result (shared ref); invalidate via `doc_events` or `.clear_cache()`.
14. **Outbound HTTP**: every third-party call (and inbound webhook receipt) goes through `frappe.integrations.utils.create_request_log` → `handle_success`/`handle_failure`. Set `reference_doctype` + `reference_docname` so the log links back to the business record.
15. **No raw-SQL workarounds**: when something seems impossible through the ORM, there is almost always a proper Frappe API for it — find it before reaching for `frappe.db.sql` writes.
16. **No throwaway scripts inside `apps/`**: use `bench execute` or `bench console` for one-off diagnostics; ad-hoc `.py` files in app folders end up committed.

## Common Commands

```bash
bench --site <site> run-tests --app app_name
bench --site <site> migrate
bench --site <site> console
bench --site <site> clear-cache
bench build --app app_name
bench --site <site> execute myapp.install.after_install
```

## Utilities

```python
from frappe.utils import (
    nowdate, nowtime, now_datetime, getdate, get_datetime,
    flt, cint, cstr, fmt_money, get_link_to_form,
)
```
