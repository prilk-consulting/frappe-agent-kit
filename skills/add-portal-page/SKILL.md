---
name: add-portal-page
description: Step-by-step workflow to expose a DocType on the Frappe/ERPNext portal as a list + detail page with access control. Use when the user asks to show documents on the portal, customer portal page, or "let customers see their X". For pattern background and gotchas, see frappe-portal.
---

# Add a Portal Page for a DocType

End-to-end workflow. Uses the portal-list pattern (right for transaction/user-owned documents — the common case). If the content is *publishable* (blog-like, public URLs per document), stop and use the WebsiteGenerator pattern from the frappe-portal skill instead.

## Usage

Use this skill when:

- "Customers should see their orders / invoices / certificates on the portal"
- Adding a portal list + detail view with per-user access control
- Wiring a new entry into the portal sidebar menu

## Steps

### 1. Decide the access rule first

Who may see which documents? The answer becomes `has_website_permission` and the list filter. Common shapes:

| Rule | Filter |
|------|--------|
| Owner only | `{"owner": frappe.session.user}` or a `user` Link field |
| Customer's documents | via `portal_users` lookup (ERPNext pattern) |
| Role-gated, all docs | role check only — rare, double-check with the user |

### 2. Controller module — list context + permission

In the DocType's `.py` module (module level, NOT inside the class):

```python
def get_list_context(context=None):
    return {
        "show_sidebar": True,
        "title": _("My Documents"),
        "get_list": get_filtered_list,
        "row_template": "templates/includes/<app>/<doctype>_row.html",
        "list_template": "templates/includes/list/list.html",
    }

def get_filtered_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
    return frappe.get_all(doctype,
        filters={"user": frappe.session.user},          # ← step-1 rule
        fields=["name", "status", "creation"],
        limit_start=limit_start, limit_page_length=limit_page_length,
        order_by=order_by or "modified desc")

def has_website_permission(doc, ptype, user=None, verbose=False):
    return doc.user == (user or frappe.session.user)    # ← step-1 rule
```

### 3. hooks.py — three entries

```python
website_route_rules = [
    {"from_route": "/<route>", "to_route": "<DocType Name>"},
    {"from_route": "/<route>/<path:name>", "to_route": "<route>-detail",
     "defaults": {"doctype": "<DocType Name>",
                  "parents": [{"label": "<Title>", "route": "<route>"}]}},
]
standard_portal_menu_items = [
    {"title": "<Title>", "route": "/<route>", "reference_doctype": "<DocType Name>", "role": "<Role>"},
]
has_website_permission = {
    "<DocType Name>": "<app>.<module>.doctype.<scrubbed>.<scrubbed>.has_website_permission",
}
```

Use an existing role (Customer, Supplier) — don't invent one unless genuinely new.

### 4. Templates — row + detail

- Row template: create a row HTML file named after the doctype inside the app's `templates/includes` folder (name link + status pill — copy the shape from the frappe-portal skill)
- Detail page: create a page module + template named after the detail route inside `templates/pages`; the Python module MUST call `frappe.has_website_permission(doc)` and throw `frappe.PermissionError` — the route rule alone protects nothing.

### 5. Apply & verify

```bash
bench --site <site> migrate            # syncs portal menu items
bench --site <site> clear-website-cache
```

Then verify as a real portal user (not Administrator — it bypasses everything):
1. Log in as a user with the role → `/<route>` lists ONLY their documents
2. Open a document they own → detail renders
3. Manually request a document they do NOT own → must get 403, not the document
4. Check the sidebar shows the new menu item

If the list is empty for a legitimate user: they're missing either the role or the `portal_users` entry on the Customer/Supplier — the classic silent failure.

## Rules

- Access control lives in `has_website_permission` + the list filter — never trust the route.
- Step 5.3 (negative test) is mandatory. A portal page that leaks across users is a Critical finding in any audit.
- Deeper patterns, ERPNext `portal_users` plumbing, and gotchas: frappe-portal skill.
