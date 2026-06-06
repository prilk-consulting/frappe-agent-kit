---
name: frappe-frontend
description: Modern SPA frontends for Frappe apps. Use for React with frappe-react-sdk, Vue 3 with frappe-ui, frappe-js-sdk, Vite build configuration, the dev/prod boot dance, Socket.io realtime, and asset-path pitfalls that 404 in production. Not for desk form scripts (use frappe-dev) or server-rendered portal pages (use frappe-portal).
---

# Modern Frontend Development for Frappe

## Usage

Use this skill when:

- Building a React or Vue SPA inside a Frappe app (Raven/CRM-style)
- Wiring Vite builds into `bench build` and Frappe routing
- Debugging prod asset 404s, dev boot failures, or silent realtime listeners
- Choosing between frappe-react-sdk, frappe-ui, and frappe-js-sdk

## Stack options

| Stack | Libraries | Reference apps |
|-------|-----------|----------------|
| **React** | frappe-react-sdk, SWR, Tailwind, Radix/shadcn | Raven |
| **Vue 3** | frappe-ui, Pinia, Tailwind | CRM, Helpdesk |

## frappe-js-sdk (any framework)

```typescript
import { FrappeApp } from 'frappe-js-sdk'
const frappe = new FrappeApp('https://site.example.com')
await frappe.auth.loginWithUsernamePassword({ username, password })
await frappe.db.getDoc('Customer', 'X')
await frappe.db.getDocList('Customer', { fields: ['name'], filters: [['disabled', '=', 0]], limit: 20 })
await frappe.call.post('module.method', { param: 'value' })
await frappe.file.uploadFile(file, { doctype: 'Customer', docname: 'X' })
```

## frappe-react-sdk (React)

```tsx
<FrappeProvider socketPort={import.meta.env.VITE_SOCKET_PORT || '9000'}>
  <App />
</FrappeProvider>

// SWR-backed hooks — call mutate() to refetch after writes
const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: Row[] }>(
    'myapp.api.get_list', { status: 'Open', limit: 50 })
const rows = data?.message ?? []

const { data: doc, mutate } = useFrappeGetDoc<Shape>(doctype, name)
const { data: list } = useFrappeGetDocList<Shape>('Customer', {
    fields: ['name'], filters: [['disabled', '=', 0]],
    orderBy: { field: 'modified', order: 'desc' }, limit: 50 })

const { updateDoc } = useFrappeUpdateDoc()
await updateDoc('Customer', name, { territory: 'US' }); await mutate()

useFrappeEventListener('myapp_progress', d => setProgress(d.percent))
useFrappeDocumentEventListener(doctype, name, () => mutate())
```

Error helper — every server error has `{ exception, exc_type, _server_messages, message }`:

```tsx
const msg = err?.exception || err?.message || 'Unexpected error'
```

### React app scaffold (canonical)

```
apps/myapp/frontend/
├── index.html               # Jinja: {{ csrf_token }}, {{ boot }}
├── package.json             # dev / build / copy-html-entry scripts
├── vite.config.ts           # base, proxyOptions, manualChunks
├── proxyOptions.ts          # reads common_site_config.json
└── src/
    ├── main.tsx             # dev/prod boot dance + FrappeProvider mount
    ├── App.tsx              # BrowserRouter basename="/myroute"
    └── components/ui/       # shadcn/ui wrappers (Radix + tailwind-merge)
```

### The dev/prod boot dance

In prod, Frappe injects boot into `window.frappe.boot` via the Jinja template. In dev, the template literally contains `{{ boot }}` — you must fetch it before mounting:

```html
<!-- index.html -->
<script>
  window.csrf_token = '{{ csrf_token }}'
  if (!window.frappe) window.frappe = {}
  frappe.boot = JSON.parse({{ boot }})
</script>
```

```tsx
// src/main.tsx
const mount = () => createRoot(document.getElementById('root')!).render(
    <FrappeProvider socketPort={import.meta.env.VITE_SOCKET_PORT || '9000'}>
        <App />
    </FrappeProvider>)

if (import.meta.env.DEV) {
    fetch('/api/method/myapp.www.myroute.get_context_for_dev', { method: 'POST' })
        .then(r => r.json()).then(v => { window.frappe.boot = JSON.parse(v.message); mount() })
        .catch(() => { window.location.href = '/login?redirect-to=/myroute' })
} else { mount() }
```

```python
# myapp/www/myroute.py
@frappe.whitelist()
def get_context_for_dev():
    return json.dumps(frappe.sessions.get())
```

### Build chain — three paths MUST agree

`--base=/assets/<app>/<name>/` in the build script · `BrowserRouter basename="/<route>"` · `website_route_rules` `from_route`. Any drift → assets 404 in prod.

```json
// package.json
"scripts": {
  "dev": "vite",
  "build": "vite build --base=/assets/myapp/myname/ && yarn copy-html-entry",
  "copy-html-entry": "cp ../myapp/public/myname/index.html ../myapp/www/myroute.html"
}
```

```python
# hooks.py
website_route_rules = [{"from_route": "/myroute/<path:app_path>", "to_route": "myroute"}]
add_to_apps_screen = [{"name": "myapp", "logo": "/assets/myapp/images/logo.svg",
                        "title": "My App", "route": "/myroute"}]
```

The `<path:app_path>` catch-all gives client-side routing the whole subtree.

### Vite config (canonical)

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: { port: 8080, proxy: proxyOptions },
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: {
    outDir: '../myapp/public/myname',
    emptyOutDir: true, target: 'es2015',
    rollupOptions: { output: { manualChunks: {
      vendor: ['react', 'react-dom', 'react-router-dom'],
      frappe: ['frappe-react-sdk'],
    }}},
  },
})
```

```typescript
// proxyOptions.ts — derives upstream port from bench config; multi-site safe
const config = JSON.parse(fs.readFileSync('../../../sites/common_site_config.json', 'utf-8'))
const port = config.webserver_port || 8000
export default {
  '^/(app|api|assets|files|private)': {
    target: `http://127.0.0.1:${port}`,
    ws: true, changeOrigin: true,
    router: (req: any) => `http://${req.headers.host?.split(':')[0]}:${port}`,
  },
}
```

## frappe-ui (Vue 3)

```typescript
import frappeui from 'frappe-ui/vite'
export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: { indexHtmlPath: '../myapp/www/app.html', emptyOutDir: true },
    }),
    vue(),
  ],
})
```

```javascript
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui'
setConfig('resourceFetcher', frappeRequest)
app.use(FrappeUI).use(pinia)
const data = await frappeRequest({ method: 'frappe.client.get_list', body: { doctype, fields: ['name'] } })
```

## Wiring the build into bench

Add a root `package.json` build script so `bench build` regenerates the bundle, then **gitignore** the build output (`public/<bundle>/` and `www/<route>.html`):

```json
// apps/myapp/package.json (root)
{ "scripts": { "build": "cd frontend && yarn install && yarn build" } }
```

Only commit built assets when the app has no root build wiring (and then document why).

## Frontend gotchas

- **Base path mismatch** — `--base` / `basename` / `website_route_rules` drift → `/assets/*.js` 404 in prod.
- **Dev boot timing** — In dev, `window.frappe.boot` is undefined until the `get_context_for_dev` fetch resolves; mount AFTER it resolves.
- **Socket port mismatch** — `FrappeProvider socketPort` must match the bench's `socketio_port`. Mismatch fails silently — handlers never fire.
- **Proxy site routing** — `proxyOptions.ts` must derive the host from request headers. Hardcoding `localhost:8000` breaks multi-site dev.
- **`copy-html-entry` is mandatory** — Vite writes to `public/`; Frappe serves the entry from `www/<route>.html`. Skip the copy → route 404 after build.
- **`mutate()` after writes, not refetch hooks** — the SDK is SWR-backed; call `mutate()` to revalidate one query, `globalMutate(matcher)` to invalidate many.
- **Realtime needs `user=`** — `frappe.publish_realtime(event, data, user=target)` to target one user; `useFrappeEventListener` only fires for events bound to `frappe.session.user`.
- **CSRF token** — `frappe-react-sdk` reads `window.csrf_token` automatically. Don't pass it manually.
- **Validation stays server-side** — SPA-side checks are UX hints; every rule must also exist in the DocType controller, because the REST API bypasses your React forms entirely.
