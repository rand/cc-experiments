---
name: frontend-react-component-patterns
description: Designing component architecture
---



# React Component Patterns

**Scope**: Composition patterns, custom hooks, memoization, code splitting, component organization
**Lines**: ~320
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Designing component architecture
- Optimizing component re-renders
- Creating reusable component patterns
- Building custom hooks
- Implementing code splitting
- Refactoring large components
- Managing component state and props

## Core Concepts

### Component Types

**Presentation Components** (Dumb/Stateless):
- Display UI based on props
- No business logic
- No state management
- Easy to test and reuse

**Container Components** (Smart/Stateful):
- Handle business logic
- Manage state
- Connect to data sources
- Pass data to presentation components

---

## Composition Patterns

### Children Prop Pattern

```tsx
// Layout component using children
function Card({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <div className="card-body">{children}</div>
    </div>
  );
}

// Usage
<Card title="User Profile">
  <UserAvatar />
  <UserInfo />
</Card>
```

**Good for**:
- Layout components
- Wrappers (modals, tooltips)
- Generic containers

### Render Props Pattern

```tsx
// Data fetcher using render prop
function DataFetcher<T>({
  url,
  render
}: {
  url: string;
  render: (data: T | null, loading: boolean, error: Error | null) => React.ReactNode;
}) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [url]);

  return <>{render(data, loading, error)}</>;
}

// Usage
<DataFetcher<User>
  url="/api/users/42"
  render={(user, loading, error) => {
    if (loading) return <Spinner />;
    if (error) return <Error message={error.message} />;
    if (!user) return null;
    return <UserProfile user={user} />;
  }}
/>
```

**Good for**:
- Sharing logic with different UI
- Data fetching patterns
- Animation wrappers

**Modern alternative**: Custom hooks (preferred in most cases)

### Compound Component Pattern

```tsx
// Tabs compound component
const TabsContext = createContext<{
  activeTab: string;
  setActiveTab: (tab: string) => void;
} | null>(null);

function Tabs({ children, defaultTab }: { children: React.ReactNode; defaultTab: string }) {
  const [activeTab, setActiveTab] = useState(defaultTab);

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className="tabs">{children}</div>
    </TabsContext.Provider>
  );
}

function TabList({ children }: { children: React.ReactNode }) {
  return <div className="tab-list">{children}</div>;
}

function Tab({ id, children }: { id: string; children: React.ReactNode }) {
  const context = useContext(TabsContext);
  if (!context) throw new Error('Tab must be used within Tabs');

  const { activeTab, setActiveTab } = context;
  const isActive = activeTab === id;

  return (
    <button
      className={isActive ? 'tab active' : 'tab'}
      onClick={() => setActiveTab(id)}
    >
      {children}
    </button>
  );
}

function TabPanel({ id, children }: { id: string; children: React.ReactNode }) {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabPanel must be used within Tabs');

  const { activeTab } = context;
  if (activeTab !== id) return null;

  return <div className="tab-panel">{children}</div>;
}

// Export as namespace
export const TabsComponent = Object.assign(Tabs, {
  List: TabList,
  Tab,
  Panel: TabPanel
});

// Usage
<TabsComponent defaultTab="profile">
  <TabsComponent.List>
    <TabsComponent.Tab id="profile">Profile</TabsComponent.Tab>
    <TabsComponent.Tab id="settings">Settings</TabsComponent.Tab>
  </TabsComponent.List>

  <TabsComponent.Panel id="profile">
    <UserProfile />
  </TabsComponent.Panel>
  <TabsComponent.Panel id="settings">
    <UserSettings />
  </TabsComponent.Panel>
</TabsComponent>
```

**Good for**:
- Complex UI components (tabs, accordions, dropdowns)
- Component APIs that need tight coupling
- Flexible component composition

### Higher-Order Component (HOC) Pattern

```tsx
// withAuth HOC
function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading } = useAuth();

    if (loading) return <Spinner />;
    if (!user) return <Navigate to="/login" />;

    return <Component {...props} />;
  };
}

// Usage
const ProtectedPage = withAuth(DashboardPage);
```

**Good for**:
- Cross-cutting concerns (auth, logging, analytics)
- Legacy codebases

**Modern alternative**: Custom hooks (preferred)

---

## Custom Hooks Patterns

### Data Fetching Hook

```tsx
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (!cancelled) setData(data);
      })
      .catch(err => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [url]);

  return { data, loading, error };
}

// Usage
function UserProfile({ userId }: { userId: string }) {
  const { data: user, loading, error } = useFetch<User>(`/api/users/${userId}`);

  if (loading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  if (!user) return null;

  return <div>{user.name}</div>;
}
```

### Local Storage Hook

```tsx
function useLocalStorage<T>(key: string, initialValue: T) {
  // State to store value
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(error);
      return initialValue;
    }
  });

  // Return wrapped version of useState's setter function
  const setValue = (value: T | ((val: T) => T)) => {
    try {
      // Allow value to be function (same API as useState)
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(error);
    }
  };

  return [storedValue, setValue] as const;
}

// Usage
function ThemeToggle() {
  const [theme, setTheme] = useLocalStorage('theme', 'light');

  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
}
```

### Debounce Hook

```tsx
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Usage
function SearchInput() {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  useEffect(() => {
    if (debouncedSearchTerm) {
      // API call only happens after 300ms of no typing
      fetch(`/api/search?q=${debouncedSearchTerm}`);
    }
  }, [debouncedSearchTerm]);

  return (
    <input
      type="text"
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
    />
  );
}
```

---

## Memoization Patterns

### React.memo for Component Optimization

```tsx
// Expensive component that re-renders unnecessarily
function ExpensiveComponent({ data }: { data: string[] }) {
  // Heavy computation
  const processedData = data.map(item => /* expensive operation */ item);

  return <div>{processedData.join(', ')}</div>;
}

// Memoized version - only re-renders when data changes
const MemoizedExpensiveComponent = React.memo(ExpensiveComponent);

// With custom comparison function
const MemoizedExpensiveComponent = React.memo(
  ExpensiveComponent,
  (prevProps, nextProps) => {
    // Return true if props are equal (skip re-render)
    return prevProps.data.length === nextProps.data.length;
  }
);
```

**When to use**:
- Component renders often with same props
- Component is expensive to render
- Parent re-renders frequently

**When NOT to use**:
- Component always renders with new props
- Cheap rendering cost
- Premature optimization

### useMemo for Expensive Calculations

```tsx
function ProductList({ products, filter }: { products: Product[]; filter: string }) {
  // Expensive filtering only runs when products or filter changes
  const filteredProducts = useMemo(() => {
    return products.filter(product =>
      product.name.toLowerCase().includes(filter.toLowerCase())
    );
  }, [products, filter]);

  return (
    <div>
      {filteredProducts.map(product => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
```

**When to use**:
- Expensive calculations
- Creating objects/arrays passed to child components
- Filtering/sorting large datasets

**When NOT to use**:
- Simple calculations (memoization overhead > calculation cost)
- Premature optimization

### useCallback for Function Stability

```tsx
function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([]);

  // Without useCallback: new function every render
  const handleToggle = (id: string) => {
    setTodos(todos.map(todo =>
      todo.id === id ? { ...todo, completed: !todo.completed } : todo
    ));
  };

  // With useCallback: same function reference across renders
  const handleToggle = useCallback((id: string) => {
    setTodos(todos => todos.map(todo =>
      todo.id === id ? { ...todo, completed: !todo.completed } : todo
    ));
  }, []); // Empty deps because we use functional update

  return (
    <div>
      {todos.map(todo => (
        <TodoItem key={todo.id} todo={todo} onToggle={handleToggle} />
      ))}
    </div>
  );
}

// Child component is memoized
const TodoItem = React.memo(({ todo, onToggle }: {
  todo: Todo;
  onToggle: (id: string) => void;
}) => {
  return (
    <div onClick={() => onToggle(todo.id)}>
      {todo.title}
    </div>
  );
});
```

**When to use**:
- Passing callbacks to memoized child components
- Dependency in useEffect/useMemo
- Stable function reference needed

**When NOT to use**:
- Not passing to memoized children
- Premature optimization

---

## Code Splitting Patterns

### Route-Based Code Splitting

```tsx
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// Lazy load route components
const Home = lazy(() => import('./pages/Home'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Profile = lazy(() => import('./pages/Profile'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
```

### Component-Based Code Splitting

```tsx
// Heavy component loaded on demand
const HeavyChart = lazy(() => import('./components/HeavyChart'));

function Dashboard() {
  const [showChart, setShowChart] = useState(false);

  return (
    <div>
      <button onClick={() => setShowChart(true)}>Show Chart</button>

      {showChart && (
        <Suspense fallback={<div>Loading chart...</div>}>
          <HeavyChart />
        </Suspense>
      )}
    </div>
  );
}
```

### Named Export Code Splitting

```tsx
// utils.ts
export function heavyFunction() { /* ... */ }
export function lightFunction() { /* ... */ }

// App.tsx - only load heavyFunction when needed
const loadHeavyFunction = () => import('./utils').then(mod => mod.heavyFunction);

function Component() {
  const handleClick = async () => {
    const heavyFn = await loadHeavyFunction();
    heavyFn();
  };

  return <button onClick={handleClick}>Run Heavy Task</button>;
}
```

---

## Component Organization Patterns

### Feature-Based Structure

```
src/
  features/
    auth/
      components/
        LoginForm.tsx
        RegisterForm.tsx
      hooks/
        useAuth.ts
      api/
        authApi.ts
      types.ts
      index.ts
    todos/
      components/
        TodoList.tsx
        TodoItem.tsx
      hooks/
        useTodos.ts
      api/
        todosApi.ts
      types.ts
      index.ts
  shared/
    components/
      Button.tsx
      Input.tsx
    hooks/
      useLocalStorage.ts
    utils/
      formatDate.ts
```

### Colocation Pattern

```tsx
// UserProfile.tsx
import { useState } from 'react';
import { UserAvatar } from './UserAvatar';
import { useUserData } from './useUserData';
import type { User } from './types';
import './UserProfile.css';

// Keep related files together
// - UserProfile.tsx (component)
// - UserAvatar.tsx (sub-component)
// - useUserData.ts (hook)
// - types.ts (types)
// - UserProfile.css (styles)
// - UserProfile.test.tsx (tests)
```

---

## Anti-Patterns to Avoid

### 1. Prop Drilling

```tsx
// ❌ Bad: Passing props through many levels
function App() {
  const [user, setUser] = useState<User | null>(null);
  return <Layout user={user} setUser={setUser} />;
}

function Layout({ user, setUser }) {
  return <Sidebar user={user} setUser={setUser} />;
}

function Sidebar({ user, setUser }) {
  return <UserMenu user={user} setUser={setUser} />;
}

// ✅ Good: Use Context
const UserContext = createContext<{
  user: User | null;
  setUser: (user: User | null) => void;
} | null>(null);

function App() {
  const [user, setUser] = useState<User | null>(null);
  return (
    <UserContext.Provider value={{ user, setUser }}>
      <Layout />
    </UserContext.Provider>
  );
}

function UserMenu() {
  const { user, setUser } = useContext(UserContext)!;
  // Use directly without prop drilling
}
```

### 2. Large Components

```tsx
// ❌ Bad: 500-line component doing everything
function Dashboard() {
  // 50 lines of state
  // 100 lines of effects
  // 200 lines of handlers
  // 150 lines of JSX
  return <div>...</div>;
}

// ✅ Good: Extract logical pieces
function Dashboard() {
  return (
    <div>
      <DashboardHeader />
      <DashboardStats />
      <DashboardCharts />
      <DashboardTables />
    </div>
  );
}
```

### 3. Premature Memoization

```tsx
// ❌ Bad: Memoizing everything
const Component = React.memo(() => {
  const value = useMemo(() => 1 + 1, []);
  const handler = useCallback(() => console.log('click'), []);
  return <button onClick={handler}>{value}</button>;
});

// ✅ Good: Only memoize when needed (profiling shows performance issue)
function Component() {
  return <button onClick={() => console.log('click')}>2</button>;
}
```

---

## Quick Reference

### When to Use Each Pattern

```
Composition:
- Children prop → Layouts, wrappers
- Render props → Logic sharing with different UI (rare)
- Compound components → Complex UI with tight coupling
- HOC → Legacy code, cross-cutting concerns

Custom Hooks:
- Data fetching → useFetch, useQuery
- Side effects → useDebounce, useLocalStorage
- Logic reuse → useAuth, useForm

Memoization:
- React.memo → Expensive components with stable props
- useMemo → Expensive calculations
- useCallback → Stable function refs for memoized children

Code Splitting:
- Route-based → Always for routes
- Component-based → Heavy components, modals, charts
- Function-based → Rarely needed
```

---

## Related Skills

- `nextjs-app-router.md` - Server vs Client Components, App Router patterns
- `react-state-management.md` - Context, Zustand, Jotai patterns
- `react-data-fetching.md` - SWR, React Query for data fetching
- `frontend-performance.md` - Bundle optimization, Core Web Vitals
- `web-accessibility.md` - ARIA patterns, keyboard navigation

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
