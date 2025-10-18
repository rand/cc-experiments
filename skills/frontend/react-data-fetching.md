---
name: frontend-react-data-fetching
description: Fetching data from APIs
---



# React Data Fetching

**Scope**: SWR, React Query, Server Actions, caching strategies, optimistic updates
**Lines**: ~310
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Fetching data from APIs
- Implementing caching strategies
- Handling loading and error states
- Optimistic UI updates
- Infinite scrolling/pagination
- Real-time data synchronization
- Choosing between SWR and React Query

## Core Concepts

### Client vs Server Data

**Client State** - UI state, form inputs, modals
```tsx
const [isOpen, setIsOpen] = useState(false);
```

**Server State** - Data from API, database
```tsx
const { data: posts } = useSWR('/api/posts');
```

**Key differences**:
- Server state is async, remote, shared
- Server state can be stale
- Server state needs caching, revalidation
- Server state is owned by server

---

## SWR (Stale-While-Revalidate)

### Basic Usage

```tsx
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(res => res.json());

function Profile() {
  const { data, error, isLoading } = useSWR('/api/user', fetcher);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Failed to load</div>;

  return <div>Hello {data.name}!</div>;
}
```

### Global Configuration

```tsx
// app/layout.tsx or _app.tsx
import { SWRConfig } from 'swr';

const fetcher = (url: string) => fetch(url).then(res => {
  if (!res.ok) throw new Error('API error');
  return res.json();
});

export default function App({ children }) {
  return (
    <SWRConfig value={{
      fetcher,
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 2000,
    }}>
      {children}
    </SWRConfig>
  );
}
```

### Mutations

```tsx
function UpdateProfile() {
  const { data: user, mutate } = useSWR('/api/user', fetcher);

  const updateName = async (newName: string) => {
    // Optimistic update
    mutate({ ...user, name: newName }, false);

    // API call
    await fetch('/api/user', {
      method: 'PATCH',
      body: JSON.stringify({ name: newName }),
    });

    // Revalidate
    mutate();
  };

  return (
    <input
      value={user?.name}
      onChange={(e) => updateName(e.target.value)}
    />
  );
}
```

### Dependent Queries

```tsx
function UserPosts({ userId }: { userId: string }) {
  // First fetch user
  const { data: user } = useSWR(`/api/users/${userId}`, fetcher);

  // Then fetch user's posts (only when user is loaded)
  const { data: posts } = useSWR(
    user ? `/api/users/${user.id}/posts` : null,
    fetcher
  );

  if (!user) return <div>Loading user...</div>;
  if (!posts) return <div>Loading posts...</div>;

  return <div>{posts.map(post => <div key={post.id}>{post.title}</div>)}</div>;
}
```

### Pagination

```tsx
function PostList() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useSWR(
    `/api/posts?page=${page}&limit=10`,
    fetcher
  );

  return (
    <div>
      {data?.posts.map(post => <div key={post.id}>{post.title}</div>)}

      <button onClick={() => setPage(page - 1)} disabled={page === 1}>
        Previous
      </button>
      <button onClick={() => setPage(page + 1)}>
        Next
      </button>
    </div>
  );
}
```

### Infinite Scroll

```tsx
import useSWRInfinite from 'swr/infinite';

function InfinitePostList() {
  const getKey = (pageIndex: number, previousPageData: any) => {
    // Reached the end
    if (previousPageData && !previousPageData.posts.length) return null;

    // First page
    return `/api/posts?page=${pageIndex + 1}&limit=10`;
  };

  const { data, size, setSize, isLoading } = useSWRInfinite(getKey, fetcher);

  const posts = data ? data.flatMap(page => page.posts) : [];
  const isLoadingMore = isLoading || (size > 0 && data && typeof data[size - 1] === 'undefined');
  const isEmpty = data?.[0]?.posts.length === 0;
  const isReachingEnd = isEmpty || (data && data[data.length - 1]?.posts.length < 10);

  return (
    <div>
      {posts.map(post => <div key={post.id}>{post.title}</div>)}

      {!isReachingEnd && (
        <button onClick={() => setSize(size + 1)} disabled={isLoadingMore}>
          {isLoadingMore ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
}
```

---

## React Query (TanStack Query)

### Basic Usage

```tsx
import { useQuery } from '@tanstack/react-query';

function Posts() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['posts'],
    queryFn: async () => {
      const res = await fetch('/api/posts');
      if (!res.ok) throw new Error('Failed to fetch');
      return res.json();
    },
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data.map((post: Post) => (
        <div key={post.id}>{post.title}</div>
      ))}
    </div>
  );
}
```

### Query Client Setup

```tsx
// app/providers.tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Mutations

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';

function CreatePost() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (newPost: { title: string; content: string }) => {
      const res = await fetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPost),
      });
      if (!res.ok) throw new Error('Failed to create');
      return res.json();
    },
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });

  return (
    <button
      onClick={() => mutation.mutate({ title: 'New Post', content: 'Content' })}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? 'Creating...' : 'Create Post'}
    </button>
  );
}
```

### Optimistic Updates

```tsx
function UpdatePost({ post }: { post: Post }) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (updatedPost: Post) => {
      const res = await fetch(`/api/posts/${post.id}`, {
        method: 'PUT',
        body: JSON.stringify(updatedPost),
      });
      return res.json();
    },

    // Optimistic update
    onMutate: async (updatedPost) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['posts', post.id] });

      // Snapshot previous value
      const previousPost = queryClient.getQueryData(['posts', post.id]);

      // Optimistically update cache
      queryClient.setQueryData(['posts', post.id], updatedPost);

      // Return context with snapshot
      return { previousPost };
    },

    // Rollback on error
    onError: (err, updatedPost, context) => {
      queryClient.setQueryData(['posts', post.id], context?.previousPost);
    },

    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['posts', post.id] });
    },
  });

  return (
    <button onClick={() => mutation.mutate({ ...post, title: 'Updated' })}>
      Update
    </button>
  );
}
```

### Pagination

```tsx
function PaginatedPosts() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isPlaceholderData } = useQuery({
    queryKey: ['posts', page],
    queryFn: async () => {
      const res = await fetch(`/api/posts?page=${page}&limit=10`);
      return res.json();
    },
    placeholderData: (previousData) => previousData, // Keep previous data while fetching
  });

  return (
    <div>
      {data?.posts.map((post: Post) => (
        <div key={post.id}>{post.title}</div>
      ))}

      <button
        onClick={() => setPage(page - 1)}
        disabled={page === 1}
      >
        Previous
      </button>
      <button
        onClick={() => setPage(page + 1)}
        disabled={isPlaceholderData || !data?.hasMore}
      >
        Next
      </button>
    </div>
  );
}
```

### Infinite Queries

```tsx
import { useInfiniteQuery } from '@tanstack/react-query';

function InfinitePosts() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['posts'],
    queryFn: async ({ pageParam = 1 }) => {
      const res = await fetch(`/api/posts?page=${pageParam}&limit=10`);
      return res.json();
    },
    getNextPageParam: (lastPage, pages) => {
      return lastPage.hasMore ? pages.length + 1 : undefined;
    },
    initialPageParam: 1,
  });

  const posts = data?.pages.flatMap(page => page.posts) ?? [];

  return (
    <div>
      {posts.map((post: Post) => (
        <div key={post.id}>{post.title}</div>
      ))}

      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
}
```

---

## Next.js Server Actions

### Basic Server Action

```tsx
// app/actions.ts
'use server';

import { revalidatePath } from 'next/cache';

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;

  await prisma.post.create({
    data: { title, content }
  });

  revalidatePath('/posts');
}

// app/posts/new/page.tsx
import { createPost } from '@/app/actions';

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <textarea name="content" required />
      <button type="submit">Create</button>
    </form>
  );
}
```

### Client-Side with useFormStatus

```tsx
// app/components/SubmitButton.tsx
'use client';

import { useFormStatus } from 'react-dom';

export function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Creating...' : 'Create Post'}
    </button>
  );
}

// app/posts/new/page.tsx
import { createPost } from '@/app/actions';
import { SubmitButton } from '@/app/components/SubmitButton';

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <textarea name="content" required />
      <SubmitButton />
    </form>
  );
}
```

### useFormState for Validation

```tsx
// app/actions.ts
'use server';

export async function createPost(prevState: any, formData: FormData) {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;

  // Validation
  if (!title || title.length < 3) {
    return { error: 'Title must be at least 3 characters' };
  }

  await prisma.post.create({ data: { title, content } });

  return { success: true };
}

// app/components/PostForm.tsx
'use client';

import { useFormState } from 'react-dom';
import { createPost } from '@/app/actions';

export function PostForm() {
  const [state, formAction] = useFormState(createPost, null);

  return (
    <form action={formAction}>
      <input name="title" required />
      {state?.error && <p className="error">{state.error}</p>}
      <textarea name="content" required />
      <button type="submit">Create</button>
    </form>
  );
}
```

---

## Caching Strategies

### Stale-While-Revalidate (SWR Pattern)

```tsx
// Return stale data immediately, revalidate in background
const { data } = useSWR('/api/posts', fetcher, {
  revalidateOnFocus: true,    // Revalidate when window regains focus
  revalidateOnReconnect: true, // Revalidate when network reconnects
  dedupingInterval: 2000,      // Dedupe requests within 2 seconds
});
```

### Cache and Network (React Query)

```tsx
const { data } = useQuery({
  queryKey: ['posts'],
  queryFn: fetchPosts,
  staleTime: 5 * 60 * 1000,    // 5 minutes before stale
  cacheTime: 10 * 60 * 1000,   // 10 minutes in cache
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
});
```

### Time-Based Revalidation (Next.js)

```tsx
// app/posts/page.tsx
export const revalidate = 60; // Revalidate every 60 seconds

async function getPosts() {
  const res = await fetch('https://api.example.com/posts', {
    next: { revalidate: 60 }
  });
  return res.json();
}

export default async function PostsPage() {
  const posts = await getPosts();
  return <div>{posts.map(post => <div key={post.id}>{post.title}</div>)}</div>;
}
```

### On-Demand Revalidation (Next.js)

```tsx
// app/actions.ts
'use server';

import { revalidatePath, revalidateTag } from 'next/cache';

export async function createPost(data: any) {
  await prisma.post.create({ data });

  // Revalidate specific paths
  revalidatePath('/posts');
  revalidatePath('/');

  // Or revalidate by tag
  revalidateTag('posts');
}

// Fetch with tag
async function getPosts() {
  const res = await fetch('https://api.example.com/posts', {
    next: { tags: ['posts'] }
  });
  return res.json();
}
```

---

## SWR vs React Query

### Comparison

| Feature | SWR | React Query |
|---------|-----|-------------|
| **Bundle Size** | 4.3kb | 12.9kb |
| **Complexity** | Simple | More features |
| **DevTools** | No | Yes |
| **Mutations** | Manual | Built-in |
| **TypeScript** | Good | Excellent |
| **Best For** | Simple apps, Next.js | Complex apps, large teams |

### When to Use SWR

```
✅ Next.js projects (official Vercel library)
✅ Simple data fetching needs
✅ Small bundle size priority
✅ Straightforward caching
✅ Quick setup
```

### When to Use React Query

```
✅ Complex mutations
✅ Optimistic updates
✅ DevTools needed
✅ Pagination/infinite scroll
✅ Large apps with many queries
✅ Advanced caching strategies
```

---

## Quick Reference

### SWR Basic Pattern

```tsx
const { data, error, isLoading, mutate } = useSWR(key, fetcher, options);

// Mutate
mutate(newData, false); // Optimistic
mutate();               // Revalidate
```

### React Query Basic Pattern

```tsx
const { data, error, isLoading } = useQuery({
  queryKey: ['key'],
  queryFn: fetchFn,
});

const mutation = useMutation({
  mutationFn: createFn,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['key'] }),
});
```

### Server Actions Pattern

```tsx
'use server';
export async function action(formData: FormData) {
  // Mutation
  revalidatePath('/path');
}

// Client
<form action={action}>...</form>
```

---

## Common Anti-Patterns

❌ **Fetching in useEffect**: Use SWR/React Query instead
✅ Dedicated data fetching library

❌ **Global state for server data**: Server state !== client state
✅ Keep server data in SWR/React Query cache

❌ **No loading/error states**: Poor UX
✅ Always handle loading, error, empty states

❌ **Not caching**: Unnecessary refetches
✅ Use staleTime, cacheTime appropriately

---

## Related Skills

- `react-state-management.md` - Client state (Zustand, Context)
- `nextjs-app-router.md` - Server Components, Server Actions
- `frontend-performance.md` - Request deduplication, prefetching
- `react-form-handling.md` - Form validation, submission

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
