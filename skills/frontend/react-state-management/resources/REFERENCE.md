# React State Management Reference

> **Purpose**: Comprehensive guide to state management patterns, libraries, and best practices in React applications.

## Table of Contents
1. [State Categories](#state-categories)
2. [React Built-in State](#react-built-in-state)
3. [External State Libraries](#external-state-libraries)
4. [Server State Management](#server-state-management)
5. [URL State Management](#url-state-management)
6. [Form State Management](#form-state-management)
7. [Decision Tree](#decision-tree)
8. [Performance Optimization](#performance-optimization)
9. [State Colocation](#state-colocation)
10. [Immutability Patterns](#immutability-patterns)
11. [Common Patterns](#common-patterns)
12. [Anti-Patterns](#anti-patterns)

---

## State Categories

### Types of State in React Applications

1. **Local Component State**
   - Belongs to single component
   - Not shared with siblings
   - Examples: form inputs, toggles, modals

2. **Shared Application State**
   - Shared across multiple components
   - Global or contextual scope
   - Examples: user session, theme, language

3. **Server State**
   - Data from external sources
   - Cached and synchronized
   - Examples: API responses, database records

4. **URL State**
   - Encoded in URL parameters
   - Shareable and bookmarkable
   - Examples: filters, search queries, pagination

5. **Form State**
   - Specialized for form handling
   - Validation and submission
   - Examples: input values, errors, touched fields

6. **Ephemeral/UI State**
   - Temporary UI concerns
   - Not persisted
   - Examples: loading states, tooltips, animations

---

## React Built-in State

### useState

**When to Use**:
- Simple local component state
- Independent state updates
- Primitive or simple object state

**Basic Usage**:
```typescript
const [count, setCount] = useState(0);
const [user, setUser] = useState<User | null>(null);
const [items, setItems] = useState<Item[]>([]);
```

**Functional Updates**:
```typescript
// Bad: May cause stale state issues
setCount(count + 1);

// Good: Uses previous state
setCount(prev => prev + 1);
```

**Lazy Initialization**:
```typescript
// Bad: Expensive computation runs every render
const [data, setData] = useState(expensiveComputation());

// Good: Runs only on mount
const [data, setData] = useState(() => expensiveComputation());
```

**Multiple State Variables**:
```typescript
// Option 1: Separate state
const [firstName, setFirstName] = useState('');
const [lastName, setLastName] = useState('');

// Option 2: Single object (prefer separate for independent updates)
const [form, setForm] = useState({ firstName: '', lastName: '' });
```

---

### useReducer

**When to Use**:
- Complex state logic
- Multiple sub-values
- Next state depends on previous
- State transitions follow patterns

**Basic Usage**:
```typescript
type State = {
  count: number;
  step: number;
};

type Action =
  | { type: 'increment' }
  | { type: 'decrement' }
  | { type: 'setStep'; payload: number }
  | { type: 'reset' };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'increment':
      return { ...state, count: state.count + state.step };
    case 'decrement':
      return { ...state, count: state.count - state.step };
    case 'setStep':
      return { ...state, step: action.payload };
    case 'reset':
      return { count: 0, step: 1 };
    default:
      return state;
  }
}

function Counter() {
  const [state, dispatch] = useReducer(reducer, { count: 0, step: 1 });

  return (
    <div>
      <p>Count: {state.count}</p>
      <button onClick={() => dispatch({ type: 'increment' })}>+</button>
      <button onClick={() => dispatch({ type: 'decrement' })}>-</button>
    </div>
  );
}
```

**With Immer for Immutability**:
```typescript
import { useImmerReducer } from 'use-immer';

type Todo = {
  id: string;
  text: string;
  completed: boolean;
};

type State = {
  todos: Todo[];
};

type Action =
  | { type: 'add'; payload: { text: string } }
  | { type: 'toggle'; payload: { id: string } }
  | { type: 'delete'; payload: { id: string } };

function reducer(draft: State, action: Action) {
  switch (action.type) {
    case 'add':
      draft.todos.push({
        id: crypto.randomUUID(),
        text: action.payload.text,
        completed: false,
      });
      break;
    case 'toggle':
      const todo = draft.todos.find(t => t.id === action.payload.id);
      if (todo) todo.completed = !todo.completed;
      break;
    case 'delete':
      draft.todos = draft.todos.filter(t => t.id !== action.payload.id);
      break;
  }
}
```

---

### useContext

**When to Use**:
- Share state across component tree
- Avoid prop drilling
- Theme, auth, language context

**Basic Usage**:
```typescript
type Theme = 'light' | 'dark';

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

// Usage
function Button() {
  const { theme, setTheme } = useTheme();
  return <button>{theme}</button>;
}
```

**Performance Considerations**:
```typescript
// Bad: Every context consumer re-renders on any state change
type AppContextValue = {
  user: User;
  theme: Theme;
  setUser: (user: User) => void;
  setTheme: (theme: Theme) => void;
};

// Good: Split contexts by concern
type UserContextValue = {
  user: User;
  setUser: (user: User) => void;
};

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};
```

**Optimized Context Pattern**:
```typescript
// Separate state and dispatch contexts
const StateContext = createContext<State | undefined>(undefined);
const DispatchContext = createContext<Dispatch<Action> | undefined>(undefined);

function Provider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </StateContext.Provider>
  );
}

// Components that only dispatch don't re-render on state changes
function useDispatch() {
  const context = useContext(DispatchContext);
  if (!context) throw new Error('useDispatch outside Provider');
  return context;
}
```

---

## External State Libraries

### Zustand

**When to Use**:
- Simple global state
- No boilerplate needed
- TypeScript-first
- No providers required

**Basic Store**:
```typescript
import { create } from 'zustand';

type State = {
  count: number;
  increment: () => void;
  decrement: () => void;
  reset: () => void;
};

const useStore = create<State>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
  reset: () => set({ count: 0 }),
}));

// Usage
function Counter() {
  const count = useStore((state) => state.count);
  const increment = useStore((state) => state.increment);

  return <button onClick={increment}>{count}</button>;
}
```

**Async Actions**:
```typescript
type State = {
  users: User[];
  loading: boolean;
  error: string | null;
  fetchUsers: () => Promise<void>;
};

const useUserStore = create<State>((set) => ({
  users: [],
  loading: false,
  error: null,
  fetchUsers: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('/api/users');
      const users = await response.json();
      set({ users, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
}));
```

**Slices Pattern**:
```typescript
type UserSlice = {
  user: User | null;
  setUser: (user: User) => void;
};

type ThemeSlice = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

const createUserSlice = (set: SetState<State>): UserSlice => ({
  user: null,
  setUser: (user) => set({ user }),
});

const createThemeSlice = (set: SetState<State>): ThemeSlice => ({
  theme: 'light',
  setTheme: (theme) => set({ theme }),
});

const useStore = create<UserSlice & ThemeSlice>((set) => ({
  ...createUserSlice(set),
  ...createThemeSlice(set),
}));
```

**Middleware**:
```typescript
import { persist } from 'zustand/middleware';

const useStore = create(
  persist<State>(
    (set) => ({
      count: 0,
      increment: () => set((state) => ({ count: state.count + 1 })),
    }),
    {
      name: 'count-storage',
    }
  )
);
```

**Selectors**:
```typescript
// Bad: Re-renders on any state change
const state = useStore();

// Good: Re-renders only when count changes
const count = useStore((state) => state.count);

// Good: Derived state with selector
const doubleCount = useStore((state) => state.count * 2);

// With shallow equality
import { shallow } from 'zustand/shallow';

const { count, step } = useStore(
  (state) => ({ count: state.count, step: state.step }),
  shallow
);
```

---

### Jotai

**When to Use**:
- Atomic state management
- Bottom-up approach
- Derived state computation
- Minimal boilerplate

**Basic Atoms**:
```typescript
import { atom, useAtom } from 'jotai';

const countAtom = atom(0);
const userAtom = atom<User | null>(null);

function Counter() {
  const [count, setCount] = useAtom(countAtom);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

**Derived Atoms**:
```typescript
const firstNameAtom = atom('');
const lastNameAtom = atom('');

// Read-only derived atom
const fullNameAtom = atom((get) => {
  const firstName = get(firstNameAtom);
  const lastName = get(lastNameAtom);
  return `${firstName} ${lastName}`;
});

// Read-write derived atom
const upperCaseNameAtom = atom(
  (get) => get(fullNameAtom).toUpperCase(),
  (get, set, newValue: string) => {
    const [first, last] = newValue.split(' ');
    set(firstNameAtom, first);
    set(lastNameAtom, last);
  }
);
```

**Async Atoms**:
```typescript
const userIdAtom = atom<string | null>(null);

const userAtom = atom(async (get) => {
  const userId = get(userIdAtom);
  if (!userId) return null;

  const response = await fetch(`/api/users/${userId}`);
  return response.json();
});

// Usage with Suspense
function User() {
  const [user] = useAtom(userAtom);
  return <div>{user?.name}</div>;
}

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <User />
    </Suspense>
  );
}
```

**Write-only Atoms**:
```typescript
const todosAtom = atom<Todo[]>([]);

const addTodoAtom = atom(
  null,
  (get, set, text: string) => {
    const todos = get(todosAtom);
    set(todosAtom, [
      ...todos,
      { id: crypto.randomUUID(), text, completed: false },
    ]);
  }
);

function AddTodo() {
  const [, addTodo] = useAtom(addTodoAtom);
  return <button onClick={() => addTodo('New todo')}>Add</button>;
}
```

**Atom Families**:
```typescript
import { atomFamily } from 'jotai/utils';

const todoAtomFamily = atomFamily((id: string) =>
  atom<Todo>({ id, text: '', completed: false })
);

function TodoItem({ id }: { id: string }) {
  const [todo, setTodo] = useAtom(todoAtomFamily(id));
  return <div>{todo.text}</div>;
}
```

---

### Redux Toolkit

**When to Use**:
- Large applications
- Complex state logic
- Time-travel debugging
- Established patterns

**Store Setup**:
```typescript
import { configureStore, createSlice, PayloadAction } from '@reduxjs/toolkit';

type TodoState = {
  todos: Todo[];
  filter: 'all' | 'active' | 'completed';
};

const initialState: TodoState = {
  todos: [],
  filter: 'all',
};

const todoSlice = createSlice({
  name: 'todos',
  initialState,
  reducers: {
    addTodo: (state, action: PayloadAction<string>) => {
      state.todos.push({
        id: crypto.randomUUID(),
        text: action.payload,
        completed: false,
      });
    },
    toggleTodo: (state, action: PayloadAction<string>) => {
      const todo = state.todos.find(t => t.id === action.payload);
      if (todo) todo.completed = !todo.completed;
    },
    setFilter: (state, action: PayloadAction<TodoState['filter']>) => {
      state.filter = action.payload;
    },
  },
});

export const { addTodo, toggleTodo, setFilter } = todoSlice.actions;

const store = configureStore({
  reducer: {
    todos: todoSlice.reducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

**Typed Hooks**:
```typescript
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

**Usage**:
```typescript
function TodoList() {
  const dispatch = useAppDispatch();
  const todos = useAppSelector((state) => state.todos.todos);
  const filter = useAppSelector((state) => state.todos.filter);

  const filteredTodos = todos.filter(todo => {
    if (filter === 'active') return !todo.completed;
    if (filter === 'completed') return todo.completed;
    return true;
  });

  return (
    <div>
      {filteredTodos.map(todo => (
        <div key={todo.id} onClick={() => dispatch(toggleTodo(todo.id))}>
          {todo.text}
        </div>
      ))}
    </div>
  );
}
```

**Async Thunks**:
```typescript
import { createAsyncThunk } from '@reduxjs/toolkit';

const fetchUsers = createAsyncThunk(
  'users/fetch',
  async (userId: string, thunkAPI) => {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
  }
);

const userSlice = createSlice({
  name: 'users',
  initialState: {
    users: [] as User[],
    loading: false,
    error: null as string | null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchUsers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUsers.fulfilled, (state, action) => {
        state.loading = false;
        state.users.push(action.payload);
      })
      .addCase(fetchUsers.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? 'Failed to fetch';
      });
  },
});
```

---

### MobX

**When to Use**:
- OOP-style state management
- Observable patterns
- Automatic reactivity
- Computed values

**Store Class**:
```typescript
import { makeAutoObservable } from 'mobx';

class TodoStore {
  todos: Todo[] = [];
  filter: 'all' | 'active' | 'completed' = 'all';

  constructor() {
    makeAutoObservable(this);
  }

  addTodo(text: string) {
    this.todos.push({
      id: crypto.randomUUID(),
      text,
      completed: false,
    });
  }

  toggleTodo(id: string) {
    const todo = this.todos.find(t => t.id === id);
    if (todo) todo.completed = !todo.completed;
  }

  setFilter(filter: 'all' | 'active' | 'completed') {
    this.filter = filter;
  }

  get filteredTodos() {
    switch (this.filter) {
      case 'active':
        return this.todos.filter(t => !t.completed);
      case 'completed':
        return this.todos.filter(t => t.completed);
      default:
        return this.todos;
    }
  }

  get completedCount() {
    return this.todos.filter(t => t.completed).length;
  }
}

const todoStore = new TodoStore();
export default todoStore;
```

**React Integration**:
```typescript
import { observer } from 'mobx-react-lite';

const TodoList = observer(() => {
  return (
    <div>
      {todoStore.filteredTodos.map(todo => (
        <div key={todo.id} onClick={() => todoStore.toggleTodo(todo.id)}>
          {todo.text}
        </div>
      ))}
      <p>Completed: {todoStore.completedCount}</p>
    </div>
  );
});
```

---

### Recoil

**When to Use**:
- Facebook's state library
- Atom-based like Jotai
- Complex async dependencies
- React Concurrent Mode

**Atoms**:
```typescript
import { atom, selector, useRecoilState, useRecoilValue } from 'recoil';

const textState = atom({
  key: 'textState',
  default: '',
});

const todoListState = atom<Todo[]>({
  key: 'todoListState',
  default: [],
});

function TextInput() {
  const [text, setText] = useRecoilState(textState);
  return <input value={text} onChange={(e) => setText(e.target.value)} />;
}
```

**Selectors**:
```typescript
const charCountState = selector({
  key: 'charCountState',
  get: ({ get }) => {
    const text = get(textState);
    return text.length;
  },
});

const filteredTodoListState = selector({
  key: 'filteredTodoListState',
  get: ({ get }) => {
    const filter = get(todoListFilterState);
    const list = get(todoListState);

    switch (filter) {
      case 'Show Completed':
        return list.filter(item => item.isComplete);
      case 'Show Uncompleted':
        return list.filter(item => !item.isComplete);
      default:
        return list;
    }
  },
});
```

**Async Selectors**:
```typescript
const currentUserIDState = atom({
  key: 'CurrentUserID',
  default: null,
});

const currentUserNameQuery = selector({
  key: 'CurrentUserName',
  get: async ({ get }) => {
    const userId = get(currentUserIDState);
    if (!userId) return null;

    const response = await fetch(`/api/users/${userId}`);
    return response.json();
  },
});
```

---

## Server State Management

### TanStack Query (React Query)

**When to Use**:
- Fetching server data
- Caching and synchronization
- Background updates
- Optimistic updates

**Basic Query**:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

function Users() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await fetch('/api/users');
      return response.json();
    },
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {data.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

**Parameterized Query**:
```typescript
function User({ userId }: { userId: string }) {
  const { data: user } = useQuery({
    queryKey: ['user', userId],
    queryFn: async () => {
      const response = await fetch(`/api/users/${userId}`);
      return response.json();
    },
    enabled: !!userId, // Only run if userId exists
  });

  return <div>{user?.name}</div>;
}
```

**Mutations**:
```typescript
function CreateUser() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (newUser: { name: string }) => {
      const response = await fetch('/api/users', {
        method: 'POST',
        body: JSON.stringify(newUser),
      });
      return response.json();
    },
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return (
    <button onClick={() => mutation.mutate({ name: 'New User' })}>
      Create User
    </button>
  );
}
```

**Optimistic Updates**:
```typescript
const mutation = useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['todos'] });

    // Snapshot previous value
    const previousTodos = queryClient.getQueryData(['todos']);

    // Optimistically update
    queryClient.setQueryData(['todos'], (old: Todo[]) => {
      return old.map(todo =>
        todo.id === newTodo.id ? newTodo : todo
      );
    });

    return { previousTodos };
  },
  onError: (err, newTodo, context) => {
    // Rollback on error
    queryClient.setQueryData(['todos'], context.previousTodos);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['todos'] });
  },
});
```

**Pagination**:
```typescript
function Projects() {
  const [page, setPage] = useState(0);

  const { data, isPreviousData } = useQuery({
    queryKey: ['projects', page],
    queryFn: () => fetchProjects(page),
    keepPreviousData: true,
  });

  return (
    <div>
      {data.projects.map(project => (
        <p key={project.id}>{project.name}</p>
      ))}
      <button
        onClick={() => setPage(old => Math.max(old - 1, 0))}
        disabled={page === 0}
      >
        Previous
      </button>
      <button
        onClick={() => setPage(old => old + 1)}
        disabled={isPreviousData || !data.hasMore}
      >
        Next
      </button>
    </div>
  );
}
```

**Infinite Queries**:
```typescript
function Projects() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['projects'],
    queryFn: ({ pageParam = 0 }) => fetchProjects(pageParam),
    getNextPageParam: (lastPage, pages) => lastPage.nextCursor,
  });

  return (
    <div>
      {data.pages.map((page, i) => (
        <React.Fragment key={i}>
          {page.projects.map(project => (
            <p key={project.id}>{project.name}</p>
          ))}
        </React.Fragment>
      ))}
      <button
        onClick={() => fetchNextPage()}
        disabled={!hasNextPage || isFetchingNextPage}
      >
        Load More
      </button>
    </div>
  );
}
```

---

### SWR

**When to Use**:
- Alternative to React Query
- Simpler API
- Built-in features for revalidation

**Basic Usage**:
```typescript
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(r => r.json());

function Profile() {
  const { data, error, isLoading } = useSWR('/api/user', fetcher);

  if (error) return <div>Failed to load</div>;
  if (isLoading) return <div>Loading...</div>;
  return <div>Hello {data.name}!</div>;
}
```

**Revalidation**:
```typescript
const { data, mutate } = useSWR('/api/user', fetcher, {
  refreshInterval: 3000, // Poll every 3s
  revalidateOnFocus: true,
  revalidateOnReconnect: true,
});

// Manually trigger revalidation
mutate();
```

**Optimistic UI**:
```typescript
const { mutate } = useSWR('/api/user', fetcher);

async function updateUser(newData) {
  // Update local data immediately
  mutate(newData, false);

  // Send request to update source
  await fetch('/api/user', {
    method: 'POST',
    body: JSON.stringify(newData),
  });

  // Trigger revalidation
  mutate();
}
```

---

## URL State Management

### TanStack Router

**When to Use**:
- Type-safe routing
- URL as single source of truth
- Search params for filters

**Route Definition**:
```typescript
import { createFileRoute } from '@tanstack/react-router';
import { z } from 'zod';

const searchSchema = z.object({
  page: z.number().default(1),
  sort: z.enum(['name', 'date']).default('name'),
  filter: z.string().optional(),
});

export const Route = createFileRoute('/users')({
  validateSearch: searchSchema,
  component: Users,
});

function Users() {
  const { page, sort, filter } = Route.useSearch();
  const navigate = Route.useNavigate();

  const setPage = (newPage: number) => {
    navigate({ search: (prev) => ({ ...prev, page: newPage }) });
  };

  return <div>Page: {page}</div>;
}
```

---

### Next.js Router

**App Router (Next.js 13+)**:
```typescript
'use client';

import { useSearchParams, useRouter, usePathname } from 'next/navigation';

export default function SearchPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const page = searchParams.get('page') ?? '1';
  const query = searchParams.get('q') ?? '';

  const updateParams = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set(key, value);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div>
      <input
        value={query}
        onChange={(e) => updateParams('q', e.target.value)}
      />
      <p>Page: {page}</p>
    </div>
  );
}
```

**Pages Router**:
```typescript
import { useRouter } from 'next/router';

export default function SearchPage() {
  const router = useRouter();
  const { page = '1', q = '' } = router.query;

  const updateQuery = (updates: Record<string, string>) => {
    router.push({
      pathname: router.pathname,
      query: { ...router.query, ...updates },
    });
  };

  return (
    <div>
      <input
        value={q}
        onChange={(e) => updateQuery({ q: e.target.value })}
      />
    </div>
  );
}
```

---

## Form State Management

### React Hook Form

**When to Use**:
- Complex forms
- Performance critical
- Validation requirements
- Minimal re-renders

**Basic Form**:
```typescript
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  age: z.number().min(18),
});

type FormData = z.infer<typeof schema>;

function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await fetch('/api/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}

      <input type="password" {...register('password')} />
      {errors.password && <span>{errors.password.message}</span>}

      <input type="number" {...register('age', { valueAsNumber: true })} />
      {errors.age && <span>{errors.age.message}</span>}

      <button disabled={isSubmitting}>Submit</button>
    </form>
  );
}
```

**Controlled Components**:
```typescript
import { Controller } from 'react-hook-form';

function Form() {
  const { control } = useForm();

  return (
    <Controller
      name="dateOfBirth"
      control={control}
      render={({ field }) => (
        <DatePicker
          selected={field.value}
          onChange={field.onChange}
        />
      )}
    />
  );
}
```

**Field Arrays**:
```typescript
import { useFieldArray } from 'react-hook-form';

function TodoForm() {
  const { control, register } = useForm({
    defaultValues: {
      todos: [{ text: '' }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'todos',
  });

  return (
    <div>
      {fields.map((field, index) => (
        <div key={field.id}>
          <input {...register(`todos.${index}.text`)} />
          <button onClick={() => remove(index)}>Remove</button>
        </div>
      ))}
      <button onClick={() => append({ text: '' })}>Add Todo</button>
    </div>
  );
}
```

---

### Formik

**When to Use**:
- Mature form library
- Existing Formik codebase
- Integration with Yup validation

**Basic Form**:
```typescript
import { Formik, Form, Field, ErrorMessage } from 'formik';
import * as Yup from 'yup';

const schema = Yup.object({
  email: Yup.string().email().required(),
  password: Yup.string().min(8).required(),
});

function LoginForm() {
  return (
    <Formik
      initialValues={{ email: '', password: '' }}
      validationSchema={schema}
      onSubmit={async (values) => {
        await fetch('/api/login', {
          method: 'POST',
          body: JSON.stringify(values),
        });
      }}
    >
      {({ isSubmitting }) => (
        <Form>
          <Field name="email" type="email" />
          <ErrorMessage name="email" component="div" />

          <Field name="password" type="password" />
          <ErrorMessage name="password" component="div" />

          <button type="submit" disabled={isSubmitting}>
            Submit
          </button>
        </Form>
      )}
    </Formik>
  );
}
```

---

## Decision Tree

```
What kind of state?
├─ Local component state
│  ├─ Simple value → useState
│  └─ Complex logic → useReducer
│
├─ Shared across components
│  ├─ Small app, few components → useContext
│  ├─ Medium app → Zustand
│  ├─ Large app, complex logic → Redux Toolkit
│  └─ Atomic approach → Jotai/Recoil
│
├─ Server data
│  ├─ REST API → TanStack Query
│  ├─ GraphQL → Apollo Client
│  └─ Simple polling → SWR
│
├─ URL state
│  ├─ Type-safe routing → TanStack Router
│  └─ Next.js app → Next.js Router
│
└─ Form state
   ├─ Performance critical → React Hook Form
   └─ Existing Formik → Formik
```

---

## Performance Optimization

### React.memo

**Memoize Component**:
```typescript
const ExpensiveComponent = React.memo(({ data }: { data: Data }) => {
  // Only re-renders if data changes
  return <div>{data.value}</div>;
});

// Custom comparison
const Component = React.memo(
  ({ data }) => <div>{data.value}</div>,
  (prevProps, nextProps) => {
    return prevProps.data.id === nextProps.data.id;
  }
);
```

---

### useMemo

**Memoize Expensive Computations**:
```typescript
function TodoList({ todos, filter }: Props) {
  // Bad: Computes every render
  const filteredTodos = todos.filter(todo => {
    // expensive filtering logic
    return todo.status === filter;
  });

  // Good: Computes only when dependencies change
  const filteredTodos = useMemo(
    () => todos.filter(todo => todo.status === filter),
    [todos, filter]
  );

  return <div>{filteredTodos.length}</div>;
}
```

**When to Use**:
- Expensive computations
- Referential equality matters
- Child component requires stable reference

**When NOT to Use**:
- Simple computations
- Premature optimization
- Everything (measure first!)

---

### useCallback

**Memoize Functions**:
```typescript
function Parent() {
  const [count, setCount] = useState(0);

  // Bad: New function every render
  const handleClick = () => {
    setCount(c => c + 1);
  };

  // Good: Stable function reference
  const handleClick = useCallback(() => {
    setCount(c => c + 1);
  }, []);

  return <ExpensiveChild onClick={handleClick} />;
}

const ExpensiveChild = React.memo(({ onClick }: { onClick: () => void }) => {
  // Only re-renders if onClick reference changes
  return <button onClick={onClick}>Click</button>;
});
```

**Common Pattern**:
```typescript
function SearchInput() {
  const [query, setQuery] = useState('');

  const debouncedSearch = useCallback(
    debounce((value: string) => {
      // API call
      fetch(`/api/search?q=${value}`);
    }, 300),
    []
  );

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    debouncedSearch(e.target.value);
  };

  return <input value={query} onChange={handleChange} />;
}
```

---

### Context Optimization

**Split Contexts**:
```typescript
// Bad: Single context for everything
const AppContext = createContext({
  user: null,
  theme: 'light',
  notifications: [],
  settings: {},
});

// Good: Separate contexts
const UserContext = createContext(null);
const ThemeContext = createContext('light');
const NotificationsContext = createContext([]);
const SettingsContext = createContext({});
```

**Separate State and Dispatch**:
```typescript
const StateContext = createContext(null);
const DispatchContext = createContext(null);

function Provider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </StateContext.Provider>
  );
}

// Components that only dispatch don't re-render on state changes
function ActionButton() {
  const dispatch = useContext(DispatchContext);
  return <button onClick={() => dispatch({ type: 'ACTION' })}>Action</button>;
}
```

**Context Selector Pattern**:
```typescript
import { createContext, useContextSelector } from 'use-context-selector';

const AppContext = createContext(null);

function Component() {
  // Only re-renders when user.name changes
  const userName = useContextSelector(AppContext, state => state.user.name);
  return <div>{userName}</div>;
}
```

---

## State Colocation

**Principle**: Keep state as close as possible to where it's used.

**Bad: Lifting State Too High**:
```typescript
function App() {
  const [modalOpen, setModalOpen] = useState(false); // ❌ Used only in Modal
  const [inputValue, setInputValue] = useState(''); // ❌ Used only in Input

  return (
    <div>
      <Header />
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} />
      <Input value={inputValue} onChange={setInputValue} />
    </div>
  );
}
```

**Good: Colocated State**:
```typescript
function App() {
  return (
    <div>
      <Header />
      <Modal />
      <Input />
    </div>
  );
}

function Modal() {
  const [open, setOpen] = useState(false); // ✅ Local to Modal
  return <dialog open={open}>...</dialog>;
}

function Input() {
  const [value, setValue] = useState(''); // ✅ Local to Input
  return <input value={value} onChange={e => setValue(e.target.value)} />;
}
```

**When to Lift State**:
- Multiple components need same state
- State needs to be synchronized
- Parent needs to coordinate children

**When NOT to Lift State**:
- Only one component uses it
- No coordination needed
- Increases unnecessary re-renders

---

## Immutability Patterns

### Array Operations

**Adding Items**:
```typescript
// Bad: Mutates array
state.items.push(newItem);

// Good: Creates new array
setState({ items: [...state.items, newItem] });
setState({ items: state.items.concat(newItem) });
```

**Removing Items**:
```typescript
// Bad: Mutates array
state.items.splice(index, 1);

// Good: Creates new array
setState({ items: state.items.filter((_, i) => i !== index) });
setState({ items: state.items.filter(item => item.id !== id) });
```

**Updating Items**:
```typescript
// Bad: Mutates array
state.items[index] = newValue;

// Good: Creates new array
setState({
  items: state.items.map((item, i) =>
    i === index ? newValue : item
  )
});

setState({
  items: state.items.map(item =>
    item.id === id ? { ...item, ...updates } : item
  )
});
```

---

### Object Operations

**Updating Properties**:
```typescript
// Bad: Mutates object
state.user.name = 'New Name';

// Good: Creates new object
setState({ user: { ...state.user, name: 'New Name' } });
```

**Nested Updates**:
```typescript
// Bad: Deep mutation
state.user.address.city = 'New York';

// Good: Spread all levels
setState({
  user: {
    ...state.user,
    address: {
      ...state.user.address,
      city: 'New York',
    },
  },
});
```

**Using Immer**:
```typescript
import { produce } from 'immer';

// Simple, readable updates
setState(
  produce(draft => {
    draft.user.address.city = 'New York';
    draft.items.push(newItem);
    draft.settings.theme = 'dark';
  })
);
```

---

## Common Patterns

### Loading States

```typescript
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };

function useAsyncData<T>(fetcher: () => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' });

  useEffect(() => {
    setState({ status: 'loading' });
    fetcher()
      .then(data => setState({ status: 'success', data }))
      .catch(error => setState({ status: 'error', error: error.message }));
  }, []);

  return state;
}

// Usage
function Component() {
  const state = useAsyncData(fetchUsers);

  switch (state.status) {
    case 'idle':
    case 'loading':
      return <div>Loading...</div>;
    case 'error':
      return <div>Error: {state.error}</div>;
    case 'success':
      return <div>{state.data.length} users</div>;
  }
}
```

---

### Optimistic Updates

```typescript
function useTodoMutation() {
  const [todos, setTodos] = useState<Todo[]>([]);

  const addTodo = async (text: string) => {
    const tempId = `temp-${Date.now()}`;
    const optimisticTodo = { id: tempId, text, completed: false };

    // Add optimistically
    setTodos(prev => [...prev, optimisticTodo]);

    try {
      const newTodo = await api.addTodo(text);
      // Replace with server response
      setTodos(prev =>
        prev.map(todo => (todo.id === tempId ? newTodo : todo))
      );
    } catch (error) {
      // Rollback on error
      setTodos(prev => prev.filter(todo => todo.id !== tempId));
      throw error;
    }
  };

  return { todos, addTodo };
}
```

---

### Undo/Redo

```typescript
function useHistory<T>(initialState: T) {
  const [history, setHistory] = useState<T[]>([initialState]);
  const [index, setIndex] = useState(0);

  const state = history[index];

  const setState = (newState: T) => {
    const newHistory = history.slice(0, index + 1);
    setHistory([...newHistory, newState]);
    setIndex(newHistory.length);
  };

  const undo = () => {
    if (index > 0) setIndex(index - 1);
  };

  const redo = () => {
    if (index < history.length - 1) setIndex(index + 1);
  };

  const canUndo = index > 0;
  const canRedo = index < history.length - 1;

  return { state, setState, undo, redo, canUndo, canRedo };
}
```

---

## Anti-Patterns

### 1. Props Drilling

**Bad**:
```typescript
function App() {
  const [user, setUser] = useState(null);
  return <Page user={user} setUser={setUser} />;
}

function Page({ user, setUser }) {
  return <Section user={user} setUser={setUser} />;
}

function Section({ user, setUser }) {
  return <Component user={user} setUser={setUser} />;
}

function Component({ user, setUser }) {
  return <div>{user.name}</div>;
}
```

**Good**:
```typescript
const UserContext = createContext(null);

function App() {
  const [user, setUser] = useState(null);
  return (
    <UserContext.Provider value={{ user, setUser }}>
      <Page />
    </UserContext.Provider>
  );
}

function Component() {
  const { user } = useContext(UserContext);
  return <div>{user.name}</div>;
}
```

---

### 2. Stale Closures

**Bad**:
```typescript
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCount(count + 1); // ❌ Always references initial count
    }, 1000);
    return () => clearInterval(interval);
  }, []); // Empty deps

  return <div>{count}</div>;
}
```

**Good**:
```typescript
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCount(c => c + 1); // ✅ Uses function form
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return <div>{count}</div>;
}
```

---

### 3. Derived State

**Bad**:
```typescript
function SearchList({ items, query }) {
  const [filteredItems, setFilteredItems] = useState(items);

  useEffect(() => {
    setFilteredItems(items.filter(item => item.name.includes(query)));
  }, [items, query]);

  return <ul>{filteredItems.map(...)}</ul>;
}
```

**Good**:
```typescript
function SearchList({ items, query }) {
  const filteredItems = useMemo(
    () => items.filter(item => item.name.includes(query)),
    [items, query]
  );

  return <ul>{filteredItems.map(...)}</ul>;
}
```

---

### 4. Unnecessary Context

**Bad**:
```typescript
const ThemeContext = createContext('light');

function Button() {
  const theme = useContext(ThemeContext);
  return <button className={theme}>Click</button>;
}

function App() {
  const [theme] = useState('light'); // ❌ Never changes
  return (
    <ThemeContext.Provider value={theme}>
      <Button />
    </ThemeContext.Provider>
  );
}
```

**Good**:
```typescript
// Just use props for static values
function Button({ theme }: { theme: string }) {
  return <button className={theme}>Click</button>;
}

function App() {
  return <Button theme="light" />;
}
```

---

### 5. Over-optimization

**Bad**:
```typescript
function Component() {
  // ❌ Unnecessary memo for simple computation
  const doubled = useMemo(() => count * 2, [count]);

  // ❌ Unnecessary callback for inline handler
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);

  // ❌ Memo everything
  const Component1 = useMemo(() => <div>1</div>, []);
  const Component2 = useMemo(() => <div>2</div>, []);

  return <div>{doubled}</div>;
}
```

**Good**:
```typescript
function Component() {
  // ✅ Simple computation, no memo needed
  const doubled = count * 2;

  // ✅ Inline handler is fine
  return <button onClick={() => console.log('clicked')}>Click</button>;
}
```

---

## Conclusion

State management in React is about choosing the right tool for the job:

1. **Start simple**: Use `useState` and `useReducer`
2. **Avoid prop drilling**: Use Context or state library
3. **Server state is different**: Use TanStack Query or SWR
4. **URL is state**: Use router for shareable state
5. **Forms are special**: Use React Hook Form or Formik
6. **Optimize strategically**: Measure before optimizing
7. **Keep state close**: Colocate when possible
8. **Stay immutable**: Never mutate state directly

**Decision Framework**:
- Local state → `useState`/`useReducer`
- Shared state → Context → Zustand → Redux Toolkit
- Server state → TanStack Query
- URL state → TanStack Router / Next.js Router
- Form state → React Hook Form

Choose based on:
- Application size
- Team experience
- Performance requirements
- Type safety needs
- Ecosystem compatibility
