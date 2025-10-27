---
name: frontend-react-state-management
description: Choosing state management solution
---



# React State Management

**Scope**: Context, Zustand, Jotai, Redux Toolkit, when to use each, state patterns
**Lines**: ~300
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Choosing state management solution
- Managing global application state
- Sharing state across components
- Optimizing state updates and re-renders
- Migrating between state libraries
- Debugging state management issues

## Core Concepts

### State Types

**Local State** - Component-specific
```tsx
const [count, setCount] = useState(0);
```

**Shared State** - Multiple components
```tsx
const theme = useContext(ThemeContext);
```

**Global State** - Application-wide
```tsx
const user = useStore(state => state.user);
```

**Server State** - Data from API
```tsx
const { data: posts } = useSWR('/api/posts');
```

---

## When to Use Each Solution

### Decision Tree

```
State needed by single component? → useState
  ↓
State needed by 2-3 nearby components? → Lift state up or useContext
  ↓
State needed across app (5+ components)? → Zustand or Jotai
  ↓
Complex state logic (reducers, middleware)? → Redux Toolkit
  ↓
Server data (API, caching, revalidation)? → SWR or React Query
```

### Comparison Matrix

| Library | Complexity | Bundle Size | DevTools | Best For |
|---------|-----------|-------------|----------|----------|
| **Context** | Low | 0kb (built-in) | No | Small apps, theming |
| **Zustand** | Low | 1.2kb | Yes | Most apps, simple global state |
| **Jotai** | Medium | 3kb | Yes | Atomic state, derived values |
| **Redux Toolkit** | High | 8kb | Excellent | Large apps, complex logic |

---

## React Context

### Basic Context Pattern

```tsx
// contexts/ThemeContext.tsx
import { createContext, useContext, useState } from 'react';

type Theme = 'light' | 'dark';

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
} | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
}

// Usage
function App() {
  return (
    <ThemeProvider>
      <Header />
      <Main />
    </ThemeProvider>
  );
}

function Header() {
  const { theme, setTheme } = useTheme();
  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      Toggle: {theme}
    </button>
  );
}
```

### Context Performance Optimization

```tsx
// Split context to prevent unnecessary re-renders
const UserContext = createContext<User | null>(null);
const UserActionsContext = createContext<{
  login: (email: string, password: string) => void;
  logout: () => void;
} | null>(null);

function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  // Memoize actions to prevent re-renders
  const actions = useMemo(() => ({
    login: async (email: string, password: string) => {
      const user = await loginAPI(email, password);
      setUser(user);
    },
    logout: () => setUser(null),
  }), []);

  return (
    <UserContext.Provider value={user}>
      <UserActionsContext.Provider value={actions}>
        {children}
      </UserActionsContext.Provider>
    </UserContext.Provider>
  );
}

// Components only re-render when user changes (not actions)
function UserProfile() {
  const user = useContext(UserContext);
  return <div>{user?.name}</div>;
}

// Components using actions don't re-render when user changes
function LogoutButton() {
  const { logout } = useContext(UserActionsContext)!;
  return <button onClick={logout}>Logout</button>;
}
```

**When to use Context**:
- Simple state (theme, locale, auth user)
- 2-5 consumers
- Infrequent updates
- Small apps

**When NOT to use Context**:
- Frequent updates (causes re-renders)
- Many consumers (performance issues)
- Complex state logic

---

## Zustand

### Basic Store

```tsx
// stores/useStore.ts
import { create } from 'zustand';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

interface TodoStore {
  todos: Todo[];
  addTodo: (title: string) => void;
  toggleTodo: (id: string) => void;
  deleteTodo: (id: string) => void;
}

export const useTodoStore = create<TodoStore>((set) => ({
  todos: [],

  addTodo: (title) =>
    set((state) => ({
      todos: [...state.todos, { id: crypto.randomUUID(), title, completed: false }],
    })),

  toggleTodo: (id) =>
    set((state) => ({
      todos: state.todos.map((todo) =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      ),
    })),

  deleteTodo: (id) =>
    set((state) => ({
      todos: state.todos.filter((todo) => todo.id !== id),
    })),
}));

// Usage
function TodoList() {
  const todos = useTodoStore((state) => state.todos);
  const toggleTodo = useTodoStore((state) => state.toggleTodo);

  return (
    <div>
      {todos.map((todo) => (
        <div key={todo.id} onClick={() => toggleTodo(todo.id)}>
          {todo.title} - {todo.completed ? '✓' : '○'}
        </div>
      ))}
    </div>
  );
}

function AddTodo() {
  const addTodo = useTodoStore((state) => state.addTodo);

  return (
    <button onClick={() => addTodo('New Todo')}>
      Add Todo
    </button>
  );
}
```

**Selector optimization** - Component only re-renders when selected value changes:
```tsx
// ❌ Re-renders on any store change
const store = useTodoStore();

// ✅ Only re-renders when todos change
const todos = useTodoStore((state) => state.todos);
```

### Zustand with Immer (Immutability)

```tsx
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface Store {
  nested: {
    deeply: {
      value: number;
    };
  };
  increment: () => void;
}

const useStore = create<Store>()(
  immer((set) => ({
    nested: { deeply: { value: 0 } },

    // Immer allows "mutation" syntax
    increment: () =>
      set((state) => {
        state.nested.deeply.value += 1;
      }),
  }))
);
```

### Zustand with Persistence

```tsx
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthStore {
  user: User | null;
  login: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      login: (user) => set({ user }),
      logout: () => set({ user: null }),
    }),
    {
      name: 'auth-storage', // localStorage key
    }
  )
);
```

**When to use Zustand**:
- Most applications
- Simple global state
- Good performance (fine-grained subscriptions)
- Minimal boilerplate

---

## Jotai

### Atoms (Atomic State)

```tsx
// stores/atoms.ts
import { atom } from 'jotai';

// Primitive atoms
export const countAtom = atom(0);
export const userAtom = atom<User | null>(null);

// Derived atoms (computed)
export const doubleCountAtom = atom((get) => get(countAtom) * 2);

// Writable derived atoms
export const incrementCountAtom = atom(
  (get) => get(countAtom),
  (get, set) => set(countAtom, get(countAtom) + 1)
);

// Async atoms
export const postsAtom = atom(async () => {
  const res = await fetch('/api/posts');
  return res.json();
});

// Usage
function Counter() {
  const [count, setCount] = useAtom(countAtom);
  const doubleCount = useAtomValue(doubleCountAtom);

  return (
    <div>
      <p>Count: {count}</p>
      <p>Double: {doubleCount}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
```

### Atom Families (Dynamic Atoms)

```tsx
import { atomFamily } from 'jotai/utils';

// Create atoms dynamically by ID
const todoAtomFamily = atomFamily((id: string) =>
  atom<Todo>({ id, title: '', completed: false })
);

function TodoItem({ id }: { id: string }) {
  const [todo, setTodo] = useAtom(todoAtomFamily(id));

  return (
    <div>
      <input
        value={todo.title}
        onChange={(e) => setTodo({ ...todo, title: e.target.value })}
      />
    </div>
  );
}
```

### Jotai with Storage

```tsx
import { atomWithStorage } from 'jotai/utils';

export const themeAtom = atomWithStorage<'light' | 'dark'>('theme', 'light');
```

**When to use Jotai**:
- Bottom-up state (compose small pieces)
- Derived/computed state
- Atomic updates (fine-grained reactivity)
- TypeScript-first

---

## Redux Toolkit

### Store Setup

```tsx
// store/store.ts
import { configureStore } from '@reduxjs/toolkit';
import todosReducer from './todosSlice';
import userReducer from './userSlice';

export const store = configureStore({
  reducer: {
    todos: todosReducer,
    user: userReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### Slice Definition

```tsx
// store/todosSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

interface TodosState {
  items: Todo[];
  loading: boolean;
}

const initialState: TodosState = {
  items: [],
  loading: false,
};

const todosSlice = createSlice({
  name: 'todos',
  initialState,
  reducers: {
    addTodo: (state, action: PayloadAction<string>) => {
      state.items.push({
        id: crypto.randomUUID(),
        title: action.payload,
        completed: false,
      });
    },
    toggleTodo: (state, action: PayloadAction<string>) => {
      const todo = state.items.find((t) => t.id === action.payload);
      if (todo) todo.completed = !todo.completed;
    },
    deleteTodo: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter((t) => t.id !== action.payload);
    },
  },
});

export const { addTodo, toggleTodo, deleteTodo } = todosSlice.actions;
export default todosSlice.reducer;
```

### Async Thunks

```tsx
// store/userSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchUser = createAsyncThunk('user/fetch', async (userId: string) => {
  const res = await fetch(`/api/users/${userId}`);
  return res.json();
});

interface UserState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

const userSlice = createSlice({
  name: 'user',
  initialState: { user: null, loading: false, error: null } as UserState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
      })
      .addCase(fetchUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch user';
      });
  },
});

export default userSlice.reducer;
```

### Hooks

```tsx
// hooks/redux.ts
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from '../store/store';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Usage
function TodoList() {
  const todos = useAppSelector((state) => state.todos.items);
  const dispatch = useAppDispatch();

  return (
    <div>
      {todos.map((todo) => (
        <div key={todo.id} onClick={() => dispatch(toggleTodo(todo.id))}>
          {todo.title}
        </div>
      ))}
      <button onClick={() => dispatch(addTodo('New Todo'))}>Add</button>
    </div>
  );
}
```

**When to use Redux Toolkit**:
- Large, complex applications
- Time-travel debugging needed
- Team familiar with Redux
- Extensive middleware needed
- Strict state management patterns

---

## State Patterns

### Optimistic Updates

```tsx
// Zustand
const useStore = create<Store>((set) => ({
  todos: [],

  toggleTodo: async (id: string) => {
    // Optimistic update
    set((state) => ({
      todos: state.todos.map((todo) =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      ),
    }));

    try {
      await fetch(`/api/todos/${id}/toggle`, { method: 'POST' });
    } catch (error) {
      // Revert on error
      set((state) => ({
        todos: state.todos.map((todo) =>
          todo.id === id ? { ...todo, completed: !todo.completed } : todo
        ),
      }));
    }
  },
}));
```

### Loading States

```tsx
interface Store {
  data: Data[];
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

const useStore = create<Store>((set) => ({
  data: [],
  loading: false,
  error: null,

  fetch: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch('/api/data');
      const data = await res.json();
      set({ data, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
}));
```

### Derived State

```tsx
// Jotai - automatic memoization
const todosAtom = atom<Todo[]>([]);
const completedTodosAtom = atom((get) =>
  get(todosAtom).filter((todo) => todo.completed)
);
const activeTodosAtom = atom((get) =>
  get(todosAtom).filter((todo) => !todo.completed)
);
const statsAtom = atom((get) => {
  const todos = get(todosAtom);
  return {
    total: todos.length,
    completed: get(completedTodosAtom).length,
    active: get(activeTodosAtom).length,
  };
});

// Zustand - manual memoization
const useStore = create<Store>((set) => ({
  todos: [],
  get completedTodos() {
    return this.todos.filter((todo) => todo.completed);
  },
}));
```

---

## Migration Patterns

### Context → Zustand

```tsx
// Before (Context)
const TodoContext = createContext<{
  todos: Todo[];
  addTodo: (title: string) => void;
} | null>(null);

function TodoProvider({ children }) {
  const [todos, setTodos] = useState<Todo[]>([]);
  const addTodo = (title: string) => setTodos([...todos, { title }]);
  return <TodoContext.Provider value={{ todos, addTodo }}>{children}</TodoContext.Provider>;
}

// After (Zustand)
const useTodoStore = create<Store>((set) => ({
  todos: [],
  addTodo: (title) => set((state) => ({ todos: [...state.todos, { title }] })),
}));

// Replace useContext with store hook
const todos = useTodoStore((state) => state.todos);
const addTodo = useTodoStore((state) => state.addTodo);
```

---

## Quick Reference

### Choosing State Management

```
Local component state → useState
2-3 components nearby → Lift state or Context
App-wide, simple → Zustand
Atomic, derived state → Jotai
Complex, large app → Redux Toolkit
Server data → SWR/React Query
```

### Performance Tips

```tsx
// ❌ Bad: Entire store subscription
const store = useStore();

// ✅ Good: Selective subscription
const todos = useStore((state) => state.todos);

// ✅ Good: Multiple selectors
const addTodo = useStore((state) => state.addTodo);
const deleteTodo = useStore((state) => state.deleteTodo);

// ✅ Good: Memoized selector
const completedCount = useStore(
  (state) => state.todos.filter((t) => t.completed).length
);
```

---

## Common Anti-Patterns

❌ **Storing server state in global store**: Use SWR/React Query instead
✅ Keep server state separate from client state

❌ **Too much global state**: Most state should be local
✅ Only globalize what needs to be shared

❌ **Not splitting context**: One context causes all consumers to re-render
✅ Split into multiple contexts (data + actions)

❌ **Derived state not memoized**: Recalculates on every render
✅ Use useMemo, Jotai derived atoms, or Zustand getters

---

## Level 3: Resources

### Comprehensive Reference
- **REFERENCE.md**: Complete React state management guide (900+ lines)
  - All state categories (local, shared, server, URL, form)
  - React built-in hooks (useState, useReducer, useContext)
  - External libraries (Zustand, Jotai, Redux Toolkit, MobX, Recoil)
  - Server state (TanStack Query, SWR)
  - URL state management
  - Form state (React Hook Form, Formik)
  - Decision trees and comparison matrices
  - Performance optimization patterns
  - State colocation strategies
  - Immutability patterns
  - Common patterns and anti-patterns

### Executable Scripts
Located in `resources/scripts/`:

1. **analyze_state.py** - Analyze React component state patterns
   - Detects state management approaches (useState, useReducer, Context)
   - Identifies prop drilling issues
   - Finds stale closure risks
   - Detects unnecessary derived state
   - Suggests optimization opportunities
   - Reports state complexity metrics
   ```bash
   ./analyze_state.py ./src
   ./analyze_state.py ./src --json
   ```

2. **benchmark_renders.js** - Benchmark render performance
   - Simulates component trees with different state patterns
   - Measures render count and timing
   - Compares useState, Context, Zustand, Jotai
   - Reports performance metrics
   ```bash
   ./benchmark_renders.js
   ./benchmark_renders.js --depth 20 --updates 500
   ./benchmark_renders.js --json
   ```

3. **detect_unnecessary_renders.js** - Detect unnecessary re-renders
   - Identifies components that should use React.memo
   - Finds props that change on every render (object/array literals)
   - Detects missing dependencies in useMemo/useCallback
   - Finds unstable callback props
   - Reports context overuse
   ```bash
   ./detect_unnecessary_renders.js ./src
   ./detect_unnecessary_renders.js ./components --json
   ```

### TypeScript Examples
Located in `resources/examples/typescript/`:

1. **zustand-store.ts** - Complete Zustand patterns
   - Basic store with actions
   - Async operations
   - Slices pattern for large stores
   - Middleware (persist, immer)
   - Selectors and performance

2. **tanstack-query-hooks.ts** - TanStack Query (React Query) patterns
   - Basic queries and mutations
   - Optimistic updates
   - Pagination and infinite queries
   - Dependent and parallel queries
   - Query invalidation
   - Cache management

3. **context-provider.tsx** - React Context patterns
   - Basic Context
   - Optimized Context (split state/dispatch)
   - Context with useReducer
   - Context composition
   - Selector pattern
   - Performance optimization

4. **react-hook-form-example.tsx** - Form state management
   - Basic forms with Zod validation
   - Complex nested fields
   - Field arrays (dynamic forms)
   - Controlled components
   - Custom validation
   - Async validation

5. **immutable-updates.ts** - Immutable state patterns
   - Array operations (add, remove, update, sort)
   - Object operations (shallow, nested)
   - Complex state operations
   - Using Immer for complex updates
   - Performance considerations
   - Common patterns

---

## Related Skills

- `react-component-patterns.md` - useState, useContext, custom hooks
- `react-data-fetching.md` - SWR, React Query for server state
- `nextjs-app-router.md` - Server Components (minimal client state)
- `frontend-performance.md` - Re-render optimization

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
