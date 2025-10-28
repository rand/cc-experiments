/**
 * React Context Provider Example
 *
 * Demonstrates:
 * - Basic Context pattern
 * - Optimized Context (split state/dispatch)
 * - Multiple contexts
 * - Context with useReducer
 * - Context composition
 * - Performance optimization
 */

import React, { createContext, useContext, useReducer, useState, ReactNode, useMemo } from 'react';

// ============================================================================
// Basic Context Pattern
// ============================================================================

type Theme = 'light' | 'dark';

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const value = { theme, setTheme, toggleTheme };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

// ============================================================================
// Optimized Context (Separate State and Dispatch)
// ============================================================================

type User = {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
};

type AuthState = {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
};

type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: User }
  | { type: 'LOGIN_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_USER'; payload: Partial<User> };

const AuthStateContext = createContext<AuthState | undefined>(undefined);
const AuthDispatchContext = createContext<React.Dispatch<AuthAction> | undefined>(undefined);

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return { ...state, isLoading: true, error: null };
    case 'LOGIN_SUCCESS':
      return {
        user: action.payload,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        isLoading: false,
        error: action.payload,
      };
    case 'LOGOUT':
      return {
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    case 'UPDATE_USER':
      return {
        ...state,
        user: state.user ? { ...state.user, ...action.payload } : null,
      };
    default:
      return state;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  });

  return (
    <AuthStateContext.Provider value={state}>
      <AuthDispatchContext.Provider value={dispatch}>
        {children}
      </AuthDispatchContext.Provider>
    </AuthStateContext.Provider>
  );
}

// Hook for reading state (components re-render on state changes)
export function useAuthState() {
  const context = useContext(AuthStateContext);
  if (!context) {
    throw new Error('useAuthState must be used within AuthProvider');
  }
  return context;
}

// Hook for dispatching actions (components DON'T re-render on state changes)
export function useAuthDispatch() {
  const context = useContext(AuthDispatchContext);
  if (!context) {
    throw new Error('useAuthDispatch must be used within AuthProvider');
  }
  return context;
}

// Combined hook for convenience
export function useAuth() {
  return {
    state: useAuthState(),
    dispatch: useAuthDispatch(),
  };
}

// ============================================================================
// Context with Actions (Higher-level API)
// ============================================================================

type TodoItem = {
  id: string;
  text: string;
  completed: boolean;
  createdAt: Date;
};

type TodoState = {
  todos: TodoItem[];
  filter: 'all' | 'active' | 'completed';
};

type TodoActions = {
  addTodo: (text: string) => void;
  toggleTodo: (id: string) => void;
  deleteTodo: (id: string) => void;
  setFilter: (filter: TodoState['filter']) => void;
  clearCompleted: () => void;
};

type TodoContextValue = TodoState & TodoActions;

const TodoContext = createContext<TodoContextValue | undefined>(undefined);

export function TodoProvider({ children }: { children: ReactNode }) {
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [filter, setFilter] = useState<TodoState['filter']>('all');

  const actions: TodoActions = useMemo(
    () => ({
      addTodo: (text: string) => {
        setTodos((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            text,
            completed: false,
            createdAt: new Date(),
          },
        ]);
      },

      toggleTodo: (id: string) => {
        setTodos((prev) =>
          prev.map((todo) =>
            todo.id === id ? { ...todo, completed: !todo.completed } : todo
          )
        );
      },

      deleteTodo: (id: string) => {
        setTodos((prev) => prev.filter((todo) => todo.id !== id));
      },

      setFilter: (newFilter: TodoState['filter']) => {
        setFilter(newFilter);
      },

      clearCompleted: () => {
        setTodos((prev) => prev.filter((todo) => !todo.completed));
      },
    }),
    []
  );

  const value: TodoContextValue = useMemo(
    () => ({
      todos,
      filter,
      ...actions,
    }),
    [todos, filter, actions]
  );

  return <TodoContext.Provider value={value}>{children}</TodoContext.Provider>;
}

export function useTodos() {
  const context = useContext(TodoContext);
  if (!context) {
    throw new Error('useTodos must be used within TodoProvider');
  }
  return context;
}

// ============================================================================
// Composed Providers
// ============================================================================

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <TodoProvider>{children}</TodoProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

// ============================================================================
// Context with Selector Pattern (Manual Implementation)
// ============================================================================

type AppState = {
  user: User | null;
  theme: Theme;
  notifications: Array<{ id: string; message: string }>;
  settings: {
    language: string;
    timezone: string;
  };
};

type Listener<T> = (value: T) => void;

class Store<T> {
  private state: T;
  private listeners = new Set<Listener<T>>();

  constructor(initialState: T) {
    this.state = initialState;
  }

  getState = () => {
    return this.state;
  };

  setState = (updater: Partial<T> | ((prev: T) => T)) => {
    const newState =
      typeof updater === 'function'
        ? updater(this.state)
        : { ...this.state, ...updater };

    this.state = newState;
    this.listeners.forEach((listener) => listener(newState));
  };

  subscribe = (listener: Listener<T>) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };
}

const appStore = new Store<AppState>({
  user: null,
  theme: 'light',
  notifications: [],
  settings: {
    language: 'en',
    timezone: 'UTC',
  },
});

const AppStateContext = createContext<Store<AppState> | undefined>(undefined);

export function AppStateProvider({ children }: { children: ReactNode }) {
  return <AppStateContext.Provider value={appStore}>{children}</AppStateContext.Provider>;
}

// Selector hook - only re-renders when selected value changes
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useContext(AppStateContext);
  if (!store) {
    throw new Error('useAppState must be used within AppStateProvider');
  }

  const [value, setValue] = useState(() => selector(store.getState()));

  React.useEffect(() => {
    const checkForUpdates = (state: AppState) => {
      const newValue = selector(state);
      setValue((prev) => {
        // Only update if value changed
        if (prev !== newValue) {
          return newValue;
        }
        return prev;
      });
    };

    const unsubscribe = store.subscribe(checkForUpdates);
    return unsubscribe;
  }, [store, selector]);

  return value;
}

// ============================================================================
// Usage Examples
// ============================================================================

/*
// Basic Theme Context
function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button onClick={toggleTheme}>
      Current: {theme}
    </button>
  );
}

// Optimized Auth Context (components only dispatch, don't re-render)
function LoginButton() {
  const dispatch = useAuthDispatch(); // ✅ Doesn't re-render on auth state changes

  const handleLogin = async () => {
    dispatch({ type: 'LOGIN_START' });
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: 'user@example.com', password: 'password' }),
      });
      const user = await response.json();
      dispatch({ type: 'LOGIN_SUCCESS', payload: user });
    } catch (error) {
      dispatch({ type: 'LOGIN_FAILURE', payload: error.message });
    }
  };

  return <button onClick={handleLogin}>Login</button>;
}

// Read auth state
function UserProfile() {
  const { user, isLoading } = useAuthState(); // ✅ Re-renders when auth state changes

  if (isLoading) return <div>Loading...</div>;
  if (!user) return <div>Not logged in</div>;

  return <div>Welcome, {user.name}</div>;
}

// Todo Context with actions
function TodoList() {
  const { todos, filter, toggleTodo, deleteTodo } = useTodos();

  const filteredTodos = todos.filter((todo) => {
    if (filter === 'active') return !todo.completed;
    if (filter === 'completed') return todo.completed;
    return true;
  });

  return (
    <ul>
      {filteredTodos.map((todo) => (
        <li key={todo.id}>
          <input
            type="checkbox"
            checked={todo.completed}
            onChange={() => toggleTodo(todo.id)}
          />
          <span>{todo.text}</span>
          <button onClick={() => deleteTodo(todo.id)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}

// Selector-based context (only re-renders when selected value changes)
function UserName() {
  const userName = useAppState((state) => state.user?.name); // ✅ Only re-renders when user name changes

  return <div>{userName}</div>;
}

function ThemeDisplay() {
  const theme = useAppState((state) => state.theme); // ✅ Only re-renders when theme changes

  return <div>Theme: {theme}</div>;
}

// App setup
function App() {
  return (
    <AppProviders>
      <div>
        <UserProfile />
        <ThemeToggle />
        <TodoList />
      </div>
    </AppProviders>
  );
}
*/

// ============================================================================
// Performance Tips
// ============================================================================

/*
DO:
- Split contexts by concern (auth, theme, notifications separate)
- Separate state and dispatch contexts
- Use useMemo for context values
- Use useCallback for context actions
- Implement selector pattern for granular subscriptions
- Keep context values stable between renders

DON'T:
- Put all app state in one context
- Create new objects/arrays in context value on every render
- Use context for frequently changing values
- Nest too many providers (consider composition)
- Access multiple contexts if only one is needed
*/
