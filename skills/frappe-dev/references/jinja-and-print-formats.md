# Print Formats & Jinja Templates

## The `frappe.utils.X` sandbox trap

In Jinja templates (print formats, web pages, email templates, server scripts), `frappe.utils` is **NOT** the actual `frappe.utils` package — it's a restricted namespace called `datautils`, populated only from symbols in `frappe/utils/data.py` per the `VALID_UTILS` allow-list at `frappe/utils/safe_exec.py`.

Helpers imported into `frappe/utils/__init__.py` from other submodules — `get_fullname`, `get_gravatar_url`, etc. — are NOT in that namespace. Calling them as `frappe.utils.get_fullname(...)` silently resolves to `None` first, then raises:

```
TypeError: 'NoneType' object is not callable
→ PrintFormatError: Error in print format on line N
```

The kicker: the same call short-circuited inside `if x else ''` will look fine until the day `x` is truthy.

## Fix: move it under `frappe.X`, not bare

These helpers live inside the `frappe=NamespaceDict(...)` block of `get_safe_globals()` — that is, they're reachable as `frappe.<name>` in Jinja, **not** as bare `<name>`. Replacing `frappe.utils.X` with bare `X` ALSO returns `None`.

```jinja
{# ❌ Broken — frappe.utils.get_fullname (datautils doesn't have get_fullname) #}
{% set name = frappe.utils.get_fullname(user) if user else '' %}

{# ❌ Also broken — get_fullname isn't a top-level Jinja global #}
{% set name = get_fullname(user) if user else '' %}

{# ✅ Works — get_fullname lives under the frappe namespace #}
{% set name = frappe.get_fullname(user) if user else '' %}
```

Common helpers under `frappe.X` (from the `frappe=NamespaceDict(...)` block in `safe_exec.py`): `frappe.get_fullname`, `frappe.get_gravatar`, `frappe.get_url`, `frappe.bold`, `frappe.format`, `frappe.format_value`, `frappe.format_date`, `frappe.get_doc`, `frappe.get_cached_doc`, `frappe.get_list`, `frappe.get_all`, `frappe.get_meta`, `frappe.render_template`, `frappe.msgprint`, `frappe.throw`, `frappe.sanitize_html`, `frappe.user`, `frappe.full_name`, `frappe.session`, `frappe.db.get_value`, `frappe.db.exists`, …

Truly bare top-level Jinja globals are a much shorter list: `frappe`, `json`, `orjson`, `dict`, `log`, `_dict`, `args`, `_` (translate), `get_toc`, `get_next_link`, `scrub`, `FrappeClient`, `style`, `dev_server`, `run_script`, `is_job_queued`, `get_visible_columns`.

## Rule of thumb

- `frappe.utils.X` works for **data-formatting helpers** in `VALID_UTILS` (`format_date`, `format_datetime`, `today`, `flt`, `cint`, `cstr`, `fmt_money`, `comma_and`, `nowdate`, …) — anything actually defined in `frappe/utils/data.py`.
- For everything else imported into `frappe/utils/__init__.py` (`get_fullname`, `get_gravatar_url`, etc.), use `frappe.<name>` — they live in the `frappe` NamespaceDict, not at top level.
- Grep `safe_exec.py:get_safe_globals` for the symbol — its position tells you whether to use bare, `frappe.X`, or `frappe.utils.X`.

## Print Format JSON ↔ DB sync gotcha

Editing a print format's `html` field in the JSON file **does not** propagate to the DB on `bench migrate` or `bench reload-doc <module> print_format <name>` unless the JSON's `modified` timestamp is newer than the DB's `modified`. Frappe compares timestamps and skips reload when they match. Symptom: you fix the template on disk, the bug persists in `/api/method/.../printview`, `grep` of the JSON looks clean but `frappe.db.get_value("Print Format", name, "html")` still shows the old bytes.

Two fixes:
1. **Patch the DB directly** — fastest. `frappe.db.set_value("Print Format", name, "html", new_html); frappe.db.commit(); frappe.clear_cache()`.
2. **Bump the JSON `modified` field** (e.g. `datetime.now()`), then run `bench --site <site> reload-doc <module> print_format <name>`. This is the right move when committing the fix back to source so future migrations don't drift.

Do both: fix the DB so users unblock, bump the JSON so the file-to-DB sync works the next time someone runs migrate on another bench.
