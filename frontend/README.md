# Sampark Frontend

React 18 single-page application for the Sampark AI Decision Intelligence Platform.

## Actual Stack

| Component | Technology |
| :--- | :--- |
| **Framework** | React 18 (Vite) |
| **Styling** | Glassmorphism CSS — custom theme (see `theme.md`) |
| **Fonts** | Google Fonts (Outfit, Plus Jakarta Sans) |
| **Icons** | Lucide React |
| **Charts** | Recharts |
| **Speech** | Browser Web Speech API |
| **Auth** | JWT (built-in, no Firebase) |
| **API** | Custom `ApiClient` class in `api.js` |

> **Note:** This project does NOT use React Router, TanStack Query, Tailwind CSS, or Firebase Authentication.
> Routing is handled by a simple `activeTab` state pattern.
> API calls use a lightweight custom client with JWT token management.

## Design System

See [`theme.md`](./theme.md) for the complete design system documentation including:
- Color palette (dark theme + indigo/cyan gradients)
- Typography scale (Outfit font)
- Glassmorphism component library
- Responsive breakpoints
- Icon catalog
- Animation tokens

## Development

```bash
npm install
npm run dev        # Starts on http://localhost:5173
```

## Production Build

```bash
npm run build      # Outputs to dist/
```

The production build is served by nginx in the unified Docker container (see root `Dockerfile`).

## Key Files

| File | Purpose |
| :--- | :--- |
| `src/App.jsx` | Main SPA with login, report, dashboard, and KB tabs |
| `src/api.js` | API client with JWT auth, SSE streaming support |
| `src/index.css` | Full custom CSS design system (~500 lines) |
| `theme.md` | Design system documentation |
| `nginx.conf` | nginx config for SPA serving + caching |
| `Dockerfile` | (deprecated — use root `Dockerfile` for unified build)
