# Monorepo Dependency Management

Comprehensive guide to managing dependencies in monorepo architectures using workspaces.

## Overview

Monorepos require careful dependency management to:
- Share common dependencies across packages
- Maintain version consistency
- Optimize install time and disk space
- Enable efficient builds and tests

## npm Workspaces

### Setup

```json
// package.json (root)
{
  "name": "my-monorepo",
  "version": "1.0.0",
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*"
  ],
  "scripts": {
    "install:all": "npm install",
    "build": "npm run build --workspaces",
    "test": "npm run test --workspaces",
    "lint": "npm run lint --workspaces"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0"
  }
}
```

### Package Structure

```
my-monorepo/
├── package.json
├── package-lock.json
├── packages/
│   ├── ui-components/
│   │   └── package.json
│   ├── utils/
│   │   └── package.json
│   └── api-client/
│       └── package.json
└── apps/
    ├── web/
    │   └── package.json
    └── mobile/
        └── package.json
```

### Package Configuration

```json
// packages/ui-components/package.json
{
  "name": "@myorg/ui-components",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "@myorg/utils": "^1.0.0"
  },
  "peerDependencies": {
    "react": "^18.0.0"
  }
}
```

```json
// apps/web/package.json
{
  "name": "@myorg/web",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "@myorg/ui-components": "^1.0.0",
    "@myorg/api-client": "^1.0.0"
  }
}
```

### Commands

```bash
# Install all dependencies
npm install

# Add dependency to specific workspace
npm install lodash -w @myorg/utils

# Add dev dependency to root
npm install -D jest --workspace-root

# Run script in specific workspace
npm run build -w @myorg/ui-components

# Run script in all workspaces
npm run test --workspaces

# Run script in workspaces if present
npm run build --workspaces --if-present
```

## pnpm Workspaces

### Setup

```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
  - 'apps/*'
  - '!**/test/**'
```

```json
// package.json (root)
{
  "name": "my-monorepo",
  "private": true,
  "scripts": {
    "build": "pnpm -r run build",
    "test": "pnpm -r run test",
    "dev": "pnpm -r --parallel run dev"
  }
}
```

### .npmrc Configuration

```ini
# .npmrc
# Hoist all dependencies to root
hoist=true

# Or use specific hoist patterns
hoist-pattern[]=*react*
hoist-pattern[]=*@types/*

# Strict peer dependencies
strict-peer-dependencies=true

# Save exact versions
save-exact=true

# Shamefully hoist (if needed for compatibility)
shamefully-hoist=false
```

### Commands

```bash
# Install all dependencies
pnpm install

# Add dependency to specific workspace
pnpm add lodash --filter @myorg/utils

# Add dependency to multiple workspaces
pnpm add react --filter "./packages/**"

# Run script in specific workspace
pnpm --filter @myorg/ui-components build

# Run script in all workspaces
pnpm -r run test

# Run script in parallel
pnpm -r --parallel run dev

# Update dependencies
pnpm -r update

# List all packages
pnpm ls -r --depth 0
```

## Yarn Workspaces

### Setup

```json
// package.json (root)
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*"
  ],
  "scripts": {
    "build": "yarn workspaces run build",
    "test": "yarn workspaces run test"
  }
}
```

### Commands

```bash
# Install all dependencies
yarn install

# Add dependency to workspace
yarn workspace @myorg/utils add lodash

# Add dependency to all workspaces
yarn workspaces foreach add react

# Run script in workspace
yarn workspace @myorg/ui-components build

# Run script in all workspaces
yarn workspaces run test

# Info about workspace
yarn workspace @myorg/utils info
```

## Dependency Version Management

### Version Pinning Strategy

```json
// package.json (root)
{
  "resolutions": {
    "react": "18.2.0",
    "lodash": "4.17.21",
    "**/@types/node": "18.0.0"
  }
}
```

### Workspace Protocol (pnpm)

```json
// packages/ui-components/package.json
{
  "dependencies": {
    "@myorg/utils": "workspace:*"
  }
}
```

### Version Ranges

```json
{
  "dependencies": {
    "@myorg/utils": "workspace:^1.0.0",  // SemVer range
    "@myorg/core": "workspace:~",         // Same version as package
    "@myorg/shared": "workspace:*"        // Any version
  }
}
```

## Dependency Hoisting

### npm/Yarn Hoisting

Dependencies are hoisted to root `node_modules` by default:

```
node_modules/
├── react/              # Hoisted
├── lodash/             # Hoisted
└── @myorg/
    ├── ui-components/
    └── utils/
```

### pnpm Hoisting

pnpm uses symlinks and isolated node_modules:

```
node_modules/
├── .pnpm/
│   ├── react@18.2.0/
│   └── lodash@4.17.21/
└── @myorg/
    ├── ui-components -> .pnpm/@myorg+ui-components@1.0.0/
    └── utils -> .pnpm/@myorg+utils@1.0.0/
```

## Shared Configuration

### TypeScript

```json
// tsconfig.base.json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "incremental": true,
    "isolatedModules": true,
    "lib": ["ES2020"],
    "module": "commonjs",
    "moduleResolution": "node",
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "preserveWatchOutput": true,
    "skipLibCheck": true,
    "strict": true,
    "target": "ES2020"
  },
  "exclude": ["node_modules"]
}
```

```json
// packages/ui-components/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "references": [
    { "path": "../utils" }
  ]
}
```

### ESLint

```javascript
// .eslintrc.js (root)
module.exports = {
  root: true,
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module'
  },
  env: {
    node: true,
    es6: true
  }
};
```

## Build Orchestration

### Nx

```json
// nx.json
{
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx/tasks-runners/default",
      "options": {
        "cacheableOperations": ["build", "test", "lint"]
      }
    }
  },
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"]
    }
  }
}
```

```json
// packages/ui-components/project.json
{
  "name": "ui-components",
  "targets": {
    "build": {
      "executor": "@nrwl/js:tsc",
      "outputs": ["{projectRoot}/dist"],
      "options": {
        "outputPath": "dist/packages/ui-components",
        "main": "packages/ui-components/src/index.ts",
        "tsConfig": "packages/ui-components/tsconfig.lib.json"
      }
    }
  }
}
```

### Turborepo

```json
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"]
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": []
    },
    "lint": {
      "outputs": []
    },
    "dev": {
      "cache": false
    }
  }
}
```

```bash
# Run builds with Turborepo
turbo run build

# Run with caching
turbo run build --cache-dir=.turbo

# Force rebuild
turbo run build --force
```

## Dependency Update Strategy

### Automated Updates

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Root dependencies
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      dev-dependencies:
        dependency-type: "development"

  # Workspace packages
  - package-ecosystem: "npm"
    directory: "/packages/ui-components"
    schedule:
      interval: "weekly"

  - package-ecosystem: "npm"
    directory: "/packages/utils"
    schedule:
      interval: "weekly"

  - package-ecosystem: "npm"
    directory: "/apps/web"
    schedule:
      interval: "weekly"
```

### Batch Updates

```bash
#!/bin/bash
# update-all-workspaces.sh

echo "Updating all workspace dependencies..."

# npm
npm update --workspaces

# pnpm
pnpm -r update

# yarn
yarn workspaces foreach run upgrade

echo "Running tests..."
npm run test --workspaces

if [ $? -eq 0 ]; then
  echo "✅ All tests passed"
  git add .
  git commit -m "chore: update dependencies"
else
  echo "❌ Tests failed, rolling back"
  git checkout .
fi
```

## Selective Dependency Installation

### Production Only

```bash
# npm
npm ci --workspaces --production

# pnpm
pnpm install --prod --filter @myorg/web

# yarn
yarn workspaces focus --production
```

### Specific Workspaces

```bash
# npm
npm ci -w @myorg/web -w @myorg/api-client

# pnpm
pnpm install --filter @myorg/web --filter @myorg/api-client

# yarn
yarn workspaces focus @myorg/web @myorg/api-client
```

## CI/CD Optimization

### Caching Strategy

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Get pnpm store directory
        id: pnpm-cache
        run: echo "pnpm_cache_dir=$(pnpm store path)" >> $GITHUB_OUTPUT

      - name: Setup pnpm cache
        uses: actions/cache@v3
        with:
          path: ${{ steps.pnpm-cache.outputs.pnpm_cache_dir }}
          key: ${{ runner.os }}-pnpm-store-${{ hashFiles('**/pnpm-lock.yaml') }}
          restore-keys: |
            ${{ runner.os }}-pnpm-store-

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build all packages
        run: pnpm -r run build

      - name: Test all packages
        run: pnpm -r run test

      - name: Lint all packages
        run: pnpm -r run lint
```

### Incremental Builds

```yaml
# Using Turborepo
- name: Build changed packages
  run: |
    turbo run build --filter=[HEAD^1]

# Using Nx
- name: Build affected packages
  run: |
    npx nx affected --target=build --base=origin/main
```

## Troubleshooting

### Phantom Dependencies

Problem: Package imports dependency not declared in package.json

```bash
# Fix with pnpm (strict mode)
pnpm install

# Error: "Cannot find module 'lodash'"
# Solution: Add lodash to package.json
pnpm add lodash --filter @myorg/utils
```

### Version Conflicts

```bash
# Check for duplicate versions
pnpm ls lodash

# Deduplicate
npm dedupe

# Or use resolutions
{
  "resolutions": {
    "lodash": "4.17.21"
  }
}
```

### Broken Symlinks

```bash
# Recreate symlinks (⚠️ WARNING: Deletes all node_modules)
rm -rf node_modules
pnpm install

# Or
npm install --force
```

## Best Practices

1. **Use workspace protocol**: `workspace:*` for internal dependencies
2. **Hoist common dependencies**: Share React, TypeScript, etc.
3. **Separate dev dependencies**: Keep tooling at root
4. **Use dependency constraints**: Enforce version consistency
5. **Enable strict peer dependencies**: Catch version mismatches
6. **Cache aggressively**: Speed up CI/CD
7. **Update atomically**: All workspaces together
8. **Test comprehensively**: All workspaces after updates
9. **Document structure**: Explain workspace organization
10. **Monitor bundle size**: Track impact of dependencies
