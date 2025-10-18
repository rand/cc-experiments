---
name: frontend-nextjs-app-router
description: Building Next.js 13+ applications
---



# Next.js App Router

**Scope**: App Router conventions, layouts, loading/error states, Server vs Client Components
**Lines**: ~310
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Building Next.js 13+ applications
- Working with App Router (app directory)
- Deciding between Server and Client Components
- Implementing layouts and nested routes
- Handling loading and error states
- Using Server Actions
- Optimizing data fetching

## Core Concepts

### App Router vs Pages Router

**Pages Router** (Legacy):
```
pages/
  index.tsx          # /
  about.tsx          # /about
  blog/
    [slug].tsx       # /blog/:slug
```

**App Router** (New, recommended):
```
app/
  page.tsx           # /
  about/
    page.tsx         # /about
  blog/
    [slug]/
      page.tsx       # /blog/:slug
```

**Key differences**:
- File-based routing with folders (not files)
- Server Components by default
- Built-in layouts, loading, error states
- Nested layouts and parallel routes
- Server Actions for mutations

---

## File Conventions

### Core Files

```
app/
  layout.tsx         # Root layout (required)
  page.tsx           # Route page
  loading.tsx        # Loading UI (Suspense boundary)
  error.tsx          # Error UI (Error boundary)
  not-found.tsx      # 404 UI
  template.tsx       # Re-rendered layout
  route.ts           # API route handler
```

### Root Layout (Required)

```tsx
// app/layout.tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

**Must include**:
- `<html>` and `<body>` tags
- Root layout wraps entire app
- Cannot be Client Component

### Page Component

```tsx
// app/page.tsx
export default function HomePage() {
  return <h1>Home Page</h1>;
}
```

**Each route requires `page.tsx`** to be accessible.

### Loading Component

```tsx
// app/dashboard/loading.tsx
export default function Loading() {
  return <div>Loading dashboard...</div>;
}
```

**Automatic Suspense boundary** - wraps page in `<Suspense>`.

### Error Component

```tsx
// app/dashboard/error.tsx
'use client'; // Must be Client Component

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

**Automatic Error boundary** - catches errors in page and nested segments.

---

## Server vs Client Components

### Server Components (Default)

```tsx
// app/page.tsx (Server Component by default)
import { prisma } from '@/lib/prisma';

export default async function HomePage() {
  // Fetch data directly in component
  const users = await prisma.user.findMany();

  return (
    <div>
      {users.map(user => (
        <div key={user.id}>{user.name}</div>
      ))}
    </div>
  );
}
```

**Benefits**:
- Zero JavaScript sent to client
- Direct database access
- Can use server-only code (Node.js APIs)
- Better performance (no hydration cost)

**Limitations**:
- Cannot use hooks (useState, useEffect)
- Cannot use browser APIs
- Cannot use event handlers directly

### Client Components

```tsx
// app/components/Counter.tsx
'use client'; // Opt-in to Client Component

import { useState } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
```

**When to use**:
- Need hooks (useState, useEffect, useContext)
- Need event handlers (onClick, onChange)
- Need browser APIs (localStorage, window)
- Need third-party libraries that use hooks

**Add `'use client'`** at top of file.

### Mixing Server and Client Components

```tsx
// app/page.tsx (Server Component)
import { prisma } from '@/lib/prisma';
import Counter from './components/Counter'; // Client Component

export default async function HomePage() {
  const users = await prisma.user.findMany();

  return (
    <div>
      <h1>Users: {users.length}</h1>
      {/* Server Component data passed to Client Component */}
      <Counter initialCount={users.length} />
    </div>
  );
}
```

**Rules**:
- Server Components can import Client Components
- Client Components cannot import Server Components directly
- Pass Server Component data as props to Client Components

### Composition Pattern (Server in Client)

```tsx
// app/components/ClientWrapper.tsx
'use client';

export default function ClientWrapper({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div>
      <button onClick={() => setIsOpen(!isOpen)}>Toggle</button>
      {isOpen && children}
    </div>
  );
}

// app/page.tsx (Server Component)
import ClientWrapper from './components/ClientWrapper';
import ServerData from './components/ServerData'; // Server Component

export default function Page() {
  return (
    <ClientWrapper>
      {/* ServerData rendered on server, passed as children */}
      <ServerData />
    </ClientWrapper>
  );
}
```

**Pass Server Components as children** to Client Components.

---

## Layouts and Templates

### Nested Layouts

```tsx
// app/layout.tsx (Root Layout)
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        <nav>Global Nav</nav>
        {children}
      </body>
    </html>
  );
}

// app/dashboard/layout.tsx (Dashboard Layout)
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <aside>Dashboard Sidebar</aside>
      <main>{children}</main>
    </div>
  );
}

// app/dashboard/page.tsx
export default function DashboardPage() {
  return <h1>Dashboard</h1>;
}
```

**Result**:
```
<html>
  <body>
    <nav>Global Nav</nav>
    <div>
      <aside>Dashboard Sidebar</aside>
      <main>
        <h1>Dashboard</h1>
      </main>
    </div>
  </body>
</html>
```

**Layouts persist across navigation** - no re-render when switching pages in same layout.

### Templates (Re-rendered on Navigation)

```tsx
// app/dashboard/template.tsx
export default function DashboardTemplate({ children }: { children: React.ReactNode }) {
  return (
    <div className="fade-in">
      {children}
    </div>
  );
}
```

**Difference from Layout**:
- Layout: Persists, state preserved
- Template: Re-rendered on navigation, state reset

**Use templates for**:
- Page transitions/animations
- Resetting state on navigation
- useEffect that should run on every page load

---

## Routing Patterns

### Dynamic Routes

```
app/
  blog/
    [slug]/
      page.tsx       # /blog/:slug
```

```tsx
// app/blog/[slug]/page.tsx
export default function BlogPost({ params }: { params: { slug: string } }) {
  return <h1>Post: {params.slug}</h1>;
}
```

### Catch-All Routes

```
app/
  docs/
    [...slug]/
      page.tsx       # /docs/a, /docs/a/b, /docs/a/b/c
```

```tsx
// app/docs/[...slug]/page.tsx
export default function DocsPage({ params }: { params: { slug: string[] } }) {
  // /docs/a/b/c -> params.slug = ['a', 'b', 'c']
  return <h1>Docs: {params.slug.join(' > ')}</h1>;
}
```

### Optional Catch-All Routes

```
app/
  shop/
    [[...slug]]/
      page.tsx       # /shop, /shop/a, /shop/a/b
```

### Route Groups (Organization)

```
app/
  (marketing)/       # Group, not in URL
    page.tsx         # /
    about/
      page.tsx       # /about
  (shop)/
    products/
      page.tsx       # /products
  (dashboard)/
    settings/
      page.tsx       # /settings
```

**Parentheses** exclude folder from URL path.

**Use for**:
- Organizing routes
- Different layouts for different sections
- Splitting app into logical segments

### Parallel Routes

```
app/
  @analytics/        # Parallel slot
    page.tsx
  @team/             # Parallel slot
    page.tsx
  layout.tsx
  page.tsx
```

```tsx
// app/layout.tsx
export default function Layout({
  children,
  analytics,
  team,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  team: React.ReactNode;
}) {
  return (
    <div>
      {children}
      <div className="grid grid-cols-2">
        {analytics}
        {team}
      </div>
    </div>
  );
}
```

**Use for**:
- Multiple sections loading independently
- Conditional rendering of sections
- Complex dashboard layouts

---

## Data Fetching

### Async Server Components

```tsx
// app/posts/page.tsx
async function getPosts() {
  const res = await fetch('https://api.example.com/posts', {
    next: { revalidate: 3600 } // Cache for 1 hour
  });
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
}

export default async function PostsPage() {
  const posts = await getPosts();

  return (
    <div>
      {posts.map((post: Post) => (
        <div key={post.id}>{post.title}</div>
      ))}
    </div>
  );
}
```

**Fetch options**:
```tsx
// Static (cached forever, revalidate on build)
fetch(url, { cache: 'force-cache' })

// Dynamic (no cache, fetch on every request)
fetch(url, { cache: 'no-store' })

// Revalidate (cache, revalidate after N seconds)
fetch(url, { next: { revalidate: 60 } })
```

### Streaming with Suspense

```tsx
// app/dashboard/page.tsx
import { Suspense } from 'react';

async function Analytics() {
  const data = await fetchAnalytics(); // Slow
  return <div>Analytics: {data.value}</div>;
}

async function RecentSales() {
  const sales = await fetchSales(); // Fast
  return <div>Sales: {sales.length}</div>;
}

export default function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>

      {/* RecentSales loads first, Analytics streams in */}
      <Suspense fallback={<div>Loading analytics...</div>}>
        <Analytics />
      </Suspense>

      <Suspense fallback={<div>Loading sales...</div>}>
        <RecentSales />
      </Suspense>
    </div>
  );
}
```

**Benefits**:
- Faster initial page load
- Progressive rendering
- Independent loading states

---

## Server Actions

### Form Actions

```tsx
// app/actions.ts
'use server';

import { revalidatePath } from 'next/cache';

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;

  // Database insert
  await prisma.post.create({
    data: { title, content }
  });

  // Revalidate cache
  revalidatePath('/posts');
}

// app/posts/new/page.tsx
import { createPost } from '@/app/actions';

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <textarea name="content" required />
      <button type="submit">Create Post</button>
    </form>
  );
}
```

**Progressive enhancement** - works without JavaScript.

### Client-Side Actions

```tsx
// app/components/PostForm.tsx
'use client';

import { useFormStatus } from 'react-dom';
import { createPost } from '@/app/actions';

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Creating...' : 'Create Post'}
    </button>
  );
}

export default function PostForm() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <textarea name="content" required />
      <SubmitButton />
    </form>
  );
}
```

### Revalidation

```tsx
'use server';

import { revalidatePath, revalidateTag } from 'next/cache';

export async function updatePost(id: string, data: any) {
  await prisma.post.update({ where: { id }, data });

  // Revalidate specific path
  revalidatePath('/posts');
  revalidatePath(`/posts/${id}`);

  // Or revalidate by tag
  revalidateTag('posts');
}
```

---

## Metadata and SEO

### Static Metadata

```tsx
// app/page.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Home Page',
  description: 'Welcome to our site',
  openGraph: {
    title: 'Home Page',
    description: 'Welcome to our site',
    images: ['/og-image.png'],
  },
};

export default function HomePage() {
  return <h1>Home</h1>;
}
```

### Dynamic Metadata

```tsx
// app/posts/[slug]/page.tsx
import type { Metadata } from 'next';

export async function generateMetadata(
  { params }: { params: { slug: string } }
): Promise<Metadata> {
  const post = await getPost(params.slug);

  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      images: [post.image],
    },
  };
}

export default function PostPage({ params }: { params: { slug: string } }) {
  return <div>Post</div>;
}
```

---

## Optimization Patterns

### Route Handlers (API Routes)

```tsx
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const users = await prisma.user.findMany();
  return NextResponse.json(users);
}

export async function POST(request: NextRequest) {
  const data = await request.json();
  const user = await prisma.user.create({ data });
  return NextResponse.json(user, { status: 201 });
}
```

### Middleware

```tsx
// middleware.ts
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token');

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/dashboard/:path*',
};
```

---

## Quick Reference

### File Conventions
```
page.tsx           # Route UI
layout.tsx         # Persistent layout
template.tsx       # Re-rendered layout
loading.tsx        # Loading UI (Suspense)
error.tsx          # Error UI (Error boundary)
not-found.tsx      # 404 UI
route.ts           # API endpoint
```

### Server vs Client Decision Tree
```
Need interactivity (state, events)? → Client Component
Need browser APIs? → Client Component
Need server-only code? → Server Component
Need data fetching? → Server Component (default)
Unsure? → Start with Server Component, convert if needed
```

### Fetch Caching
```tsx
// Static (build time)
fetch(url, { cache: 'force-cache' })

// Dynamic (every request)
fetch(url, { cache: 'no-store' })

// Revalidate (time-based)
fetch(url, { next: { revalidate: 60 } })

// Revalidate (tag-based)
fetch(url, { next: { tags: ['posts'] } })
```

---

## Related Skills

- `react-component-patterns.md` - Component composition, custom hooks
- `react-state-management.md` - Client-side state management
- `react-data-fetching.md` - SWR, React Query for Client Components
- `nextjs-seo.md` - Metadata API, structured data, sitemaps
- `frontend-performance.md` - Bundle optimization, image optimization

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
