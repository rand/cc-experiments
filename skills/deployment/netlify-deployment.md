---
name: deployment-netlify-deployment
description: Deploying static sites, JAMstack apps, or frontend frameworks to Netlify
---



# Netlify Deployment

**Scope**: Netlify site deployment, build settings, continuous deployment, and configuration
**Lines**: ~320
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Deploying static sites, JAMstack apps, or frontend frameworks to Netlify
- Setting up continuous deployment from Git repositories (GitHub, GitLab, Bitbucket)
- Configuring build settings, environment variables, and deploy contexts
- Managing branch deploys, deploy previews, and production deployments
- Setting up redirects, rewrites, and custom headers
- Working with monorepo deployments or multiple sites
- Troubleshooting build failures or deployment issues

## Core Concepts

### Deployment Workflow

**Git-based deployment**:
- Push to Git → Netlify detects change → Build triggered → Site deployed
- Automatic deploys for production branch (main/master)
- Deploy previews for pull requests
- Branch deploys for feature branches

**Deploy contexts**:
- **Production**: Main branch deploys
- **Deploy previews**: Pull request deploys
- **Branch deploys**: Other branches (optional)
- Each context can have different build commands and env vars

### Build Configuration

**Three ways to configure**:
1. **netlify.toml** (recommended): Version-controlled config file
2. **Netlify UI**: Web dashboard settings
3. **Netlify CLI**: Command-line configuration

**Build settings hierarchy**:
- netlify.toml overrides UI settings
- Environment variables from UI merge with file config
- Deploy context settings override base settings

### Site Configuration

**Required settings**:
- **Base directory**: Root of your project (monorepos)
- **Build command**: Command to build your site
- **Publish directory**: Where build outputs files
- **Functions directory**: Serverless functions location (optional)

**Framework detection**:
- Netlify auto-detects popular frameworks (Next.js, Astro, SvelteKit, etc.)
- Suggests default build commands and publish directories
- Can override with custom settings

---

## Patterns

### Pattern 1: Basic netlify.toml Configuration

```toml
# netlify.toml - Basic configuration
[build]
  # Base directory for monorepos
  base = "apps/web"

  # Build command
  command = "npm run build"

  # Publish directory (relative to base)
  publish = "dist"

  # Functions directory
  functions = "netlify/functions"

# Environment variables (non-sensitive only)
[build.environment]
  NODE_VERSION = "20"
  NPM_FLAGS = "--legacy-peer-deps"

# Production context
[context.production]
  command = "npm run build:prod"

[context.production.environment]
  NEXT_PUBLIC_API_URL = "https://api.example.com"

# Deploy preview context (PRs)
[context.deploy-preview]
  command = "npm run build:preview"

[context.deploy-preview.environment]
  NEXT_PUBLIC_API_URL = "https://preview-api.example.com"

# Branch deploy context
[context.branch-deploy]
  command = "npm run build:dev"
```

**When to use**:
- All production deployments (version control config)
- Need different settings per deploy context
- Monorepo projects with base directory

### Pattern 2: Framework-Specific Configurations

```toml
# Next.js App Router
[build]
  command = "npm run build"
  publish = ".next"

[build.environment]
  NODE_VERSION = "20"
  NEXT_PRIVATE_TARGET = "server"

# Astro
[build]
  command = "npm run build"
  publish = "dist"

# SvelteKit
[build]
  command = "npm run build"
  publish = "build"

[build.environment]
  NODE_VERSION = "20"

# Vite + React
[build]
  command = "npm run build"
  publish = "dist"

# Nuxt 3
[build]
  command = "npm run build"
  publish = ".output/public"
```

**Framework-specific gotchas**:
- Next.js: Use `.next` for publish dir, Netlify handles server rendering
- Astro: Ensure `output: 'static'` or `'hybrid'` in astro.config
- SvelteKit: Use `@sveltejs/adapter-netlify`
- Nuxt: Use `nuxt build` with Nitro preset

### Pattern 3: Redirects and Rewrites

```toml
# netlify.toml redirects
[[redirects]]
  from = "/old-path/*"
  to = "/new-path/:splat"
  status = 301
  force = true

[[redirects]]
  from = "/api/*"
  to = "https://api.example.com/:splat"
  status = 200
  force = true

[[redirects]]
  from = "/blog/:slug"
  to = "/articles/:slug"
  status = 301

# SPA fallback (catch-all)
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

# Redirect with query params
[[redirects]]
  from = "/search"
  to = "/search-results?q=:query"
  query = {query = ":query"}
  status = 301

# Proxy API requests (no CORS)
[[redirects]]
  from = "/api-proxy/*"
  to = "https://external-api.com/:splat"
  status = 200
  headers = {X-Custom-Header = "value"}
```

**Alternative: _redirects file**:
```
# public/_redirects
/old-path/* /new-path/:splat 301
/api/* https://api.example.com/:splat 200
/* /index.html 200
```

**When to use**:
- Migrating old URLs (301 redirects)
- SPA routing (200 rewrite to index.html)
- Proxying external APIs (avoid CORS)
- Redirect based on conditions

### Pattern 4: Custom Headers

```toml
# netlify.toml headers
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Permissions-Policy = "camera=(), microphone=(), geolocation=()"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.js"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.css"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/api/*"
  [headers.values]
    Access-Control-Allow-Origin = "https://example.com"
    Access-Control-Allow-Methods = "GET, POST, PUT, DELETE"
    Access-Control-Allow-Headers = "Content-Type, Authorization"

[[headers]]
  for = "/index.html"
  [headers.values]
    Cache-Control = "public, max-age=0, must-revalidate"
```

**When to use**:
- Security headers (all production sites)
- Cache control for assets
- CORS headers for API routes
- CSP (Content Security Policy)

### Pattern 5: Netlify CLI Deployment

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Initialize new site
netlify init

# Link existing site
netlify link

# Deploy to draft URL (preview)
netlify deploy

# Deploy to production
netlify deploy --prod

# Deploy specific directory
netlify deploy --dir=dist --prod

# Open site in browser
netlify open

# View deployment status
netlify status

# Stream build logs
netlify watch

# Run dev server with Netlify features
netlify dev
```

**When to use**:
- Manual deployments (not Git-based)
- Testing before production deploy
- Local development with Netlify features
- CI/CD pipeline deployments

### Pattern 6: Environment Variables

```bash
# Set via CLI
netlify env:set API_KEY "secret-key"
netlify env:set API_URL "https://api.example.com" --context production
netlify env:set DEBUG_MODE "true" --context deploy-preview

# List environment variables
netlify env:list

# Import from .env file
netlify env:import .env.production

# Remove environment variable
netlify env:unset API_KEY
```

**In netlify.toml** (non-sensitive only):
```toml
[build.environment]
  NODE_VERSION = "20"
  NEXT_PUBLIC_APP_NAME = "My App"

[context.production.environment]
  NEXT_PUBLIC_API_URL = "https://api.example.com"

[context.deploy-preview.environment]
  NEXT_PUBLIC_API_URL = "https://preview-api.example.com"
```

**Best practices**:
- Never commit sensitive keys to netlify.toml
- Use Netlify UI or CLI for secrets
- Prefix public vars with `NEXT_PUBLIC_`, `VITE_`, `PUBLIC_` (framework-specific)
- Use different values per deploy context

### Pattern 7: Monorepo Deployment

```toml
# netlify.toml in repo root
[build]
  base = "apps/marketing"
  command = "npm run build"
  publish = "dist"

# Ignore builds if app didn't change
ignore = "git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF apps/marketing"
```

**Multiple sites from one repo**:
```toml
# Site 1: apps/marketing/netlify.toml
[build]
  base = "apps/marketing"
  command = "npm run build"
  publish = "dist"

# Site 2: apps/docs/netlify.toml
[build]
  base = "apps/docs"
  command = "npm run build"
  publish = "dist"
```

**When to use**:
- Monorepo with multiple deployable apps
- Need selective builds (only build changed apps)
- Sharing common packages

---

## Quick Reference

### Common Build Commands

```
Framework       | Build Command           | Publish Directory
----------------|-------------------------|------------------
Next.js         | npm run build          | .next
Astro           | npm run build          | dist
SvelteKit       | npm run build          | build
Vite            | npm run build          | dist
Nuxt 3          | npm run build          | .output/public
Gatsby          | npm run build          | public
Remix           | npm run build          | build/client
Eleventy        | npx @11ty/eleventy     | _site
Hugo            | hugo                   | public
Jekyll          | jekyll build           | _site
```

### Deploy Contexts

```
Context          | Trigger                | Use Case
-----------------|------------------------|---------------------------
production       | Push to main branch    | Live site
deploy-preview   | Open pull request      | PR previews
branch-deploy    | Push to other branch   | Feature branch testing
```

### Critical Files

```
File               | Purpose
-------------------|------------------------------------------
netlify.toml       | Build config, redirects, headers
_redirects         | Redirects (alternative to toml)
_headers           | Headers (alternative to toml)
.nvmrc             | Node version specification
package.json       | Dependencies, build scripts
```

### Deployment Checklist

```
✅ Build command configured
✅ Publish directory set correctly
✅ Environment variables added (production + preview)
✅ Redirects configured (especially SPA fallback)
✅ Security headers added
✅ Cache headers for static assets
✅ Node version specified (.nvmrc or netlify.toml)
✅ Git LFS configured (if using large files)
✅ Custom domain configured (if applicable)
✅ HTTPS enforced
```

---

## Anti-Patterns

❌ **Wrong publish directory**: Build succeeds but site shows 404
✅ Check framework's output directory (`.next`, `dist`, `build`, etc.)

❌ **Missing SPA fallback redirect**: Direct routes 404 in SPAs
✅ Add `/* /index.html 200` redirect for client-side routing

❌ **Hardcoded environment variables**: API URLs in source code
✅ Use environment variables, different per deploy context

❌ **No cache headers**: Static assets re-downloaded on every visit
✅ Set `Cache-Control: public, max-age=31536000, immutable` for hashed assets

❌ **Sensitive keys in netlify.toml**: API secrets committed to Git
✅ Use Netlify UI or CLI for sensitive environment variables

❌ **Build command missing dependencies**: Build fails after npm install
✅ Ensure all dependencies in package.json, test locally with `netlify dev`

❌ **Deploying build artifacts**: Committing `dist/` or `.next/` to Git
✅ Add to .gitignore, let Netlify build on deploy

❌ **No base directory in monorepo**: Builds entire repo
✅ Set `base = "apps/your-app"` in netlify.toml

---

## Related Skills

- `netlify-functions.md` - Serverless functions, Edge Functions, API endpoints
- `netlify-optimization.md` - Performance, caching, build optimization
- `nextjs-app-router.md` - Next.js specific deployment patterns
- `astro-deployment.md` - Astro SSR and hybrid deployment
- `github-actions-workflows.md` - Custom CI/CD before Netlify deploy
- `cloudflare-workers.md` - Alternative edge deployment platform

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
