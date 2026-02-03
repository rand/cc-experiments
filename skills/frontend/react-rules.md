---
name: frontend-react-rules
description: 40+ opinionated React rules for Server Components, performance, state management, and component design. High-density best practices, not a tutorial.
---

# React Rules

Opinionated, high-density rules for modern React (v19+, Next.js App Router). These are prescriptive — follow them unless you have a specific, articulated reason not to. Not a tutorial; assumes working React knowledge.

---

## Server Components

**1. Default to Server Components.**
Every component is a Server Component unless it needs interactivity, browser APIs, or state. Never add `'use client'` preemptively.

**2. Push client boundaries down, not up.**
Wrap only the interactive leaf in `'use client'`. Never mark a layout or page as client just because one child needs `onClick`.

```tsx
// Bad: entire page is client
'use client'
export default function Page() {
  return <div><StaticContent /><LikeButton /></div>
}

// Good: only the interactive part is client
export default function Page() {
  return <div><StaticContent /><LikeButton /></div>
}
// LikeButton.tsx
'use client'
export function LikeButton() { /* ... */ }
```

**3. Never import server-only code into client components.**
Use the `server-only` package to poison imports. If a module touches DB or secrets, add `import 'server-only'` at the top.

**4. Fetch data in Server Components, not in useEffect.**
Server Components can be `async`. Use that. Client-side fetching creates waterfalls and loading spinners.

```tsx
// Bad
'use client'
function UserProfile({ id }) {
  const [user, setUser] = useState(null)
  useEffect(() => { fetch(`/api/users/${id}`).then(/* ... */) }, [id])
}

// Good
async function UserProfile({ id }) {
  const user = await getUser(id)
  return <Profile user={user} />
}
```

**5. Pass serializable props across the server/client boundary.**
No functions, classes, Dates, Maps, or Sets as props to client components. Serialize first.

**6. Use `cache()` for request-level deduplication.**
When multiple Server Components need the same data in one request, wrap the fetch with React `cache()`. Don't prop-drill to avoid re-fetching.

```tsx
import { cache } from 'react'
export const getUser = cache(async (id: string) => {
  return db.user.findUnique({ where: { id } })
})
```

**7. Colocate data fetching with the component that uses it.**
Don't hoist fetches to the page level and thread data down. Let each Server Component fetch its own data — `cache()` deduplicates.

**8. Use `<Suspense>` to stream Server Components.**
Wrap slow Server Components in Suspense so the rest of the page renders immediately. Don't block the whole page on one slow query.

---

## Performance

**9. Avoid waterfall fetches — parallelize with `Promise.all`.**
Sequential `await`s in Server Components create waterfalls. Fetch independent data in parallel.

```tsx
// Bad: sequential
const user = await getUser(id)
const posts = await getPosts(id)

// Good: parallel
const [user, posts] = await Promise.all([getUser(id), getPosts(id)])
```

**10. Use `<Suspense>` boundaries strategically.**
Each Suspense boundary is an independent streaming unit. Place them around independently-loading sections, not around every component.

**11. Minimize client JavaScript.**
Every `'use client'` component ships JS to the browser. Audit your client components — if it doesn't use hooks or event handlers, it shouldn't be client.

**12. Use `React.lazy` for heavy client components.**
Code-split large interactive components (editors, charts, modals) behind lazy boundaries.

```tsx
const HeavyEditor = lazy(() => import('./HeavyEditor'))
```

**13. Use `React.memo` at expensive render boundaries, not everywhere.**
`memo` is not free. Use it where profiling shows wasted renders — large lists, complex trees re-rendering from context changes.

**14. Use `useMemo`/`useCallback` for referential stability, not premature optimization.**
Use them when a value is passed as a prop to a memoized child or as a dependency in another hook. Don't sprinkle them "just in case."

**15. Avoid layout thrashing — batch DOM reads and writes.**
If you must measure DOM in client components, use `useLayoutEffect` for synchronous measurement, `useEffect` for everything else.

**16. Use the `key` prop to reset component state intentionally.**
Changing `key` unmounts and remounts. Use this to reset forms or animation states instead of complex useEffect cleanup.

```tsx
// Reset form when user changes
<UserForm key={userId} userId={userId} />
```

---

## State Management

**17. Derive state — never duplicate it.**
If a value can be computed from existing state or props, compute it during render. Never `useState` + `useEffect` to sync.

```tsx
// Bad
const [items, setItems] = useState([])
const [count, setCount] = useState(0)
useEffect(() => setCount(items.length), [items])

// Good
const [items, setItems] = useState([])
const count = items.length
```

**18. Use URL state for shareable UI.**
Filters, tabs, pagination, search queries — put them in the URL via `useSearchParams`. Users can bookmark and share. Browser back button works.

**19. Distinguish server state from client state.**
Server state (data from API) belongs in the server or a cache (React Query, SWR). Client state (UI toggles, form input) belongs in `useState` or `useReducer`.

**20. Use `useReducer` when state transitions are complex.**
If your `useState` setter needs to reference previous state in multiple places, or state updates depend on each other, switch to `useReducer`.

**21. Lift state to the lowest common ancestor, no higher.**
If two siblings share state, lift to their parent. Don't lift to a global store just because prop-drilling feels tedious — use composition first.

**22. Use context for dependency injection, not global state.**
Context is ideal for themes, locale, auth tokens — things that change rarely. For frequently-changing state, context causes full subtree re-renders.

---

## Components

**23. One component, one responsibility.**
If you're passing `mode` or `variant` props that fundamentally change behavior, split into separate components.

**24. Prefer composition over configuration.**
Instead of a `<Card>` with 15 props, use `<Card>`, `<Card.Header>`, `<Card.Body>`. Compound components are more flexible and readable.

```tsx
// Bad
<Card title="Hello" subtitle="World" showFooter footerAction={fn} />

// Good
<Card>
  <Card.Header title="Hello" subtitle="World" />
  <Card.Body>{children}</Card.Body>
  <Card.Footer><Button onClick={fn}>Action</Button></Card.Footer>
</Card>
```

**25. Accept `children` over render config.**
Prefer `children` for content injection. Use render props only when the child needs data from the parent.

**26. Use explicit prop types — never `any`.**
Define interfaces for props. Use discriminated unions for variant props.

```tsx
type ButtonProps =
  | { variant: 'link'; href: string }
  | { variant: 'button'; onClick: () => void }
```

**27. Colocate styles, types, and tests with the component.**
`Button/Button.tsx`, `Button/Button.test.tsx`, `Button/Button.module.css`. Don't scatter files across distant directories.

**28. Avoid premature abstraction.**
Duplicate code twice before abstracting. A wrong abstraction is worse than duplication.

**29. Name event handler props `onX`, handlers `handleX`.**
Props: `onClick`, `onSubmit`, `onChange`. Internal handlers: `handleClick`, `handleSubmit`. Be consistent.

**30. Forward refs for reusable UI primitives.**
Any component that wraps a native element (input, button, div) should forward its ref.

```tsx
const Input = forwardRef<HTMLInputElement, InputProps>((props, ref) => (
  <input ref={ref} {...props} />
))
```

---

## Forms

**31. Use Server Actions for form submissions.**
`<form action={serverAction}>` works without JavaScript. Progressive enhancement for free.

```tsx
async function createPost(formData: FormData) {
  'use server'
  const title = formData.get('title')
  await db.post.create({ data: { title } })
  revalidatePath('/posts')
}
```

**32. Use `useActionState` for form state and validation.**
It handles pending states, error display, and works with Server Actions. Don't build your own form state machine.

```tsx
const [state, action, pending] = useActionState(createPost, initialState)
```

**33. Validate on the server, always.**
Client validation is UX. Server validation is security. Never trust `formData` without server-side validation (Zod, etc.).

**34. Show pending states during submission.**
Use `useFormStatus` or the `pending` return from `useActionState` to disable buttons and show spinners. Never let users double-submit.

**35. Use hidden inputs for non-interactive data.**
Pass IDs, tokens, and other data via `<input type="hidden">` rather than closures over Server Action arguments.

---

## Patterns

**36. Always wrap routes in Error Boundaries.**
Use Next.js `error.tsx` or manual `<ErrorBoundary>`. Uncaught errors should show a recoverable UI, not a blank screen.

**37. Provide meaningful loading states.**
Use `loading.tsx` / Suspense fallbacks that match the layout shape (skeletons, not spinners). Avoid layout shift.

**38. Use optimistic updates for perceived speed.**
Use `useOptimistic` to update UI immediately on mutation. Roll back if the server rejects.

```tsx
const [optimisticLikes, addOptimisticLike] = useOptimistic(likes)
```

**39. Colocate `loading.tsx`, `error.tsx`, and `not-found.tsx` with each route.**
Every route segment should handle its own loading, error, and 404 states.

**40. Use `notFound()` for missing resources, not conditional rendering.**
Call `notFound()` in Server Components to trigger the nearest `not-found.tsx`. Don't render empty states for missing data.

```tsx
const post = await getPost(id)
if (!post) notFound()
```

**41. Use `redirect()` for server-side navigation.**
In Server Components and Server Actions, use `redirect()` from `next/navigation`. Don't return redirect instructions to the client.

**42. Prefer `<Link>` over `router.push` for navigation.**
`<Link>` prefetches, works without JS, and is accessible. Use `router.push` only for programmatic navigation after an action.

**43. Use `revalidatePath` / `revalidateTag` after mutations.**
After a Server Action modifies data, tell Next.js what to revalidate. Don't force full page reloads.
