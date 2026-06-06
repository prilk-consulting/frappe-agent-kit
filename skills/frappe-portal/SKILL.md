---
name: frappe-portal
description: Frappe/ERPNext portal and website development. Use for exposing DocTypes on the portal (WebsiteGenerator vs portal list patterns), website_route_rules, portal menu items, has_website_permission, detail page templates, and upgrade-safe extension of existing portal pages. Not for React/Vue SPAs mounted inside a Frappe app — use frappe-frontend.
---

# Portal & Website Development

## Usage

Use this skill when:

- Exposing a DocType on the customer/supplier portal (list + detail pages)
- Choosing between WebsiteGenerator and the portal-list pattern
- Portal access control (`has_website_permission`, `portal_users`)
- Extending existing ERPNext portal pages without forking templates
- Debugging "portal page shows nothing" or PDF-generation hangs

## Two patterns for exposing DocTypes

| Pattern | When | Setup |
|---------|------|-------|
| **A: WebsiteGenerator** | Publishable content (Blog Post, Web Page) | `has_web_view=1`, controller extends `WebsiteGenerator`, requires `route` field |
| **B: Portal List** *(recommended for transactions)* | Sales Order, Invoice, any user-owned document | `get_list_context()` in controller module; no `has_web_view` |

### Pattern A: WebsiteGenerator

- Set `has_web_view = 1` on the DocType, controller extends `WebsiteGenerator`
- Requires a `route` field; each document gets its own URL
- Template file named after the doctype (`.html`) inside the doctype folder's `templates` directory
- Override `get_context(context)` for template variables

### Pattern B: Portal List (recommended for transaction documents)

```python
# In the DocType controller module (my_doctype.py)
def get_list_context(context=None):
    return {
        "show_sidebar": True,
        "show_search": True,
        "no_breadcrumbs": True,
        "title": _("My Documents"),
        "get_list": get_filtered_list,
        "row_template": "templates/includes/my_app/my_row.html",
        "list_template": "templates/includes/list/list.html",
    }

def get_filtered_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
    """Filter list to only show current user's documents."""
    return frappe.get_all(
        doctype,
        filters={"user": frappe.session.user},
        fields=["name", "status", "creation"],
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by=order_by or "modified desc",
    )

def has_website_permission(doc, ptype, user=None, verbose=False):
    """Only allow users to see their own documents."""
    return doc.user == (user or frappe.session.user)
```

```python
# hooks.py
website_route_rules = [
    # List page — maps to DocType with get_list_context
    {"from_route": "/my-docs", "to_route": "My DocType"},
    # Detail page — maps to a template
    {
        "from_route": "/my-docs/<path:name>",
        "to_route": "my-doc-detail",
        "defaults": {
            "doctype": "My DocType",
            "parents": [{"label": "My Docs", "route": "my-docs"}],
        },
    },
]

standard_portal_menu_items = [
    {"title": "My Docs", "route": "/my-docs", "reference_doctype": "My DocType", "role": "My Role"},
]

has_website_permission = {
    "My DocType": "my_app.module.doctype.my_doctype.my_doctype.has_website_permission",
}
```

### Detail page template

```python
# templates/pages/my-doc-detail.py
import frappe
from frappe import _

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
    context.parents = frappe.form_dict.parents
    context.title = context.doc.name
    if not frappe.has_website_permission(context.doc):
        frappe.throw(_("Not Permitted"), frappe.PermissionError)
```

```html
{# templates/pages/my-doc-detail.html #}
{% extends "templates/web.html" %}
{% block title %}{{ doc.name }}{% endblock %}
{% block breadcrumbs %}{% include "templates/includes/breadcrumbs.html" %}{% endblock %}
{% block page_content %}
    <h3>{{ doc.name }}</h3>
    <p>Status: {{ doc.status }}</p>
{% endblock %}
```

### Row template for the list

```html
{# templates/includes/my_app/my_row.html #}
<div class="row py-3 border-bottom">
    <div class="col-sm-4">
        <a href="/my-docs/{{ doc.name }}"><strong>{{ doc.name }}</strong></a>
    </div>
    <div class="col-sm-4">
        <span class="indicator-pill {{ 'green' if doc.status == 'Active' else 'orange' }}">
            {{ doc.status }}
        </span>
    </div>
    <div class="col-sm-4 text-right text-muted small">
        {{ frappe.utils.format_date(doc.creation, 'medium') }}
    </div>
</div>
```

## Extending existing portal pages WITHOUT template overrides

The upgrade-safe way — no ERPNext template gets forked:

```python
# hooks.py
web_include_js = "my_portal.bundle.js"          # JS on all portal pages
web_include_css = "my_portal.bundle.css"        # CSS on all portal pages
update_website_context = ["my_app.portal.context.update_website_context"]
```

```python
# portal/context.py
def update_website_context(context):
    if frappe.session.user == "Guest":
        return
    if "My Role" not in frappe.get_roles():
        return
    context.my_custom_flag = True
```

```javascript
// public/js/my_portal.bundle.js
(function() {
    document.addEventListener("DOMContentLoaded", function() {
        const path = window.location.pathname;
        if (path.match(/^\/orders\/.+/)) {
            // inject custom UI into the order detail page
        }
    });
})();
```

`update_website_context` runs on **every** portal page — keep it lightweight.

## Portal access control (ERPNext pattern)

ERPNext scopes portal transactions through the Customer/Supplier `portal_users` child table:

```python
# website_list_for_contact.py pattern
def get_transaction_list(doctype, ...):
    # 1. Find which customers belong to this portal user
    customers = get_parents_for_user("Customer")
    # 2. Filter transactions by those customers
    return frappe.get_all(doctype, filters={"customer": ["in", customers]}, ...)
```

Portal users need BOTH:
1. The appropriate role (Customer, Supplier, or a custom role)
2. Their email in the Customer/Supplier `portal_users` table

Missing either one produces an empty portal list with no error — the most common "portal shows nothing" cause.

## Portal gotchas

- `bench serve --nothreading` deadlocks when wkhtmltopdf loads CSS from the same server (PDF generation hangs forever in single-threaded dev).
- `frm.call()` sends form values to the server — Password fields get overwritten on the round-trip. Use `frappe.xcall()` for methods that set Password fields.
- Template resolution: last installed app wins. Use `{% extends "appname/path" %}` prefix to pin a specific app's template.
- `standard_portal_menu_items` only sync on `bench migrate` (or Portal Settings save) — adding an entry to hooks.py does nothing until you migrate.
- `website_route_rules` changes need `bench --site <site> clear-website-cache`.
