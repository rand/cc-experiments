/**
 * Zustand Store Example
 *
 * Demonstrates:
 * - Type-safe Zustand store
 * - Actions and state
 * - Async operations
 * - Slices pattern
 * - Middleware (persist)
 * - Selectors
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// ============================================================================
// Basic Store Example
// ============================================================================

type Todo = {
  id: string;
  text: string;
  completed: boolean;
  createdAt: Date;
};

type TodoStore = {
  todos: Todo[];
  filter: 'all' | 'active' | 'completed';

  // Actions
  addTodo: (text: string) => void;
  toggleTodo: (id: string) => void;
  deleteTodo: (id: string) => void;
  setFilter: (filter: TodoStore['filter']) => void;
  clearCompleted: () => void;

  // Derived state
  filteredTodos: () => Todo[];
  stats: () => { total: number; active: number; completed: number };
};

export const useTodoStore = create<TodoStore>((set, get) => ({
  todos: [],
  filter: 'all',

  addTodo: (text) =>
    set((state) => ({
      todos: [
        ...state.todos,
        {
          id: crypto.randomUUID(),
          text,
          completed: false,
          createdAt: new Date(),
        },
      ],
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

  setFilter: (filter) => set({ filter }),

  clearCompleted: () =>
    set((state) => ({
      todos: state.todos.filter((todo) => !todo.completed),
    })),

  filteredTodos: () => {
    const { todos, filter } = get();
    switch (filter) {
      case 'active':
        return todos.filter((todo) => !todo.completed);
      case 'completed':
        return todos.filter((todo) => todo.completed);
      default:
        return todos;
    }
  },

  stats: () => {
    const todos = get().todos;
    return {
      total: todos.length,
      active: todos.filter((t) => !t.completed).length,
      completed: todos.filter((t) => t.completed).length,
    };
  },
}));

// ============================================================================
// Store with Async Actions
// ============================================================================

type User = {
  id: string;
  name: string;
  email: string;
};

type UserStore = {
  users: User[];
  currentUser: User | null;
  loading: boolean;
  error: string | null;

  fetchUsers: () => Promise<void>;
  fetchUser: (id: string) => Promise<void>;
  updateUser: (id: string, updates: Partial<User>) => Promise<void>;
  deleteUser: (id: string) => Promise<void>;
  setCurrentUser: (user: User | null) => void;
};

export const useUserStore = create<UserStore>((set, get) => ({
  users: [],
  currentUser: null,
  loading: false,
  error: null,

  fetchUsers: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('/api/users');
      if (!response.ok) throw new Error('Failed to fetch users');
      const users = await response.json();
      set({ users, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', loading: false });
    }
  },

  fetchUser: async (id) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`/api/users/${id}`);
      if (!response.ok) throw new Error('Failed to fetch user');
      const user = await response.json();
      set({ currentUser: user, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', loading: false });
    }
  },

  updateUser: async (id, updates) => {
    try {
      const response = await fetch(`/api/users/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update user');
      const updatedUser = await response.json();

      set((state) => ({
        users: state.users.map((u) => (u.id === id ? updatedUser : u)),
        currentUser: state.currentUser?.id === id ? updatedUser : state.currentUser,
      }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error' });
      throw error;
    }
  },

  deleteUser: async (id) => {
    try {
      const response = await fetch(`/api/users/${id}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete user');

      set((state) => ({
        users: state.users.filter((u) => u.id !== id),
        currentUser: state.currentUser?.id === id ? null : state.currentUser,
      }));
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error' });
      throw error;
    }
  },

  setCurrentUser: (user) => set({ currentUser: user }),
}));

// ============================================================================
// Slices Pattern for Large Stores
// ============================================================================

type AuthSlice = {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

type ThemeSlice = {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
};

type NotificationSlice = {
  notifications: Array<{ id: string; message: string; type: 'info' | 'success' | 'error' }>;
  addNotification: (message: string, type: NotificationSlice['notifications'][0]['type']) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
};

const createAuthSlice = (set: any, get: any): AuthSlice => ({
  user: null,
  token: null,
  isAuthenticated: false,

  login: async (email, password) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const { user, token } = await response.json();
    set({ user, token, isAuthenticated: true });
  },

  logout: () => {
    set({ user: null, token: null, isAuthenticated: false });
  },
});

const createThemeSlice = (set: any): ThemeSlice => ({
  theme: 'light',
  toggleTheme: () => set((state: ThemeSlice) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  setTheme: (theme) => set({ theme }),
});

const createNotificationSlice = (set: any): NotificationSlice => ({
  notifications: [],

  addNotification: (message, type) =>
    set((state: NotificationSlice) => ({
      notifications: [
        ...state.notifications,
        { id: crypto.randomUUID(), message, type },
      ],
    })),

  removeNotification: (id) =>
    set((state: NotificationSlice) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () => set({ notifications: [] }),
});

export const useAppStore = create<AuthSlice & ThemeSlice & NotificationSlice>()(
  (set, get) => ({
    ...createAuthSlice(set, get),
    ...createThemeSlice(set),
    ...createNotificationSlice(set),
  })
);

// ============================================================================
// Store with Persist Middleware
// ============================================================================

type SettingsStore = {
  language: string;
  notifications: boolean;
  autoSave: boolean;
  setLanguage: (lang: string) => void;
  toggleNotifications: () => void;
  toggleAutoSave: () => void;
};

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      language: 'en',
      notifications: true,
      autoSave: true,

      setLanguage: (language) => set({ language }),
      toggleNotifications: () => set((state) => ({ notifications: !state.notifications })),
      toggleAutoSave: () => set((state) => ({ autoSave: !state.autoSave })),
    }),
    {
      name: 'app-settings',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// ============================================================================
// Store with Immer Middleware for Complex State
// ============================================================================

type NestedState = {
  data: {
    users: {
      [id: string]: {
        profile: {
          name: string;
          settings: {
            theme: string;
            notifications: boolean;
          };
        };
      };
    };
  };
  updateUserTheme: (userId: string, theme: string) => void;
  updateUserName: (userId: string, name: string) => void;
};

export const useNestedStore = create<NestedState>()(
  immer((set) => ({
    data: {
      users: {},
    },

    updateUserTheme: (userId, theme) =>
      set((state) => {
        if (state.data.users[userId]) {
          state.data.users[userId].profile.settings.theme = theme;
        }
      }),

    updateUserName: (userId, name) =>
      set((state) => {
        if (state.data.users[userId]) {
          state.data.users[userId].profile.name = name;
        }
      }),
  }))
);

// ============================================================================
// Usage Examples in Components
// ============================================================================

/*
// Basic usage - re-renders only when specific slice changes
function TodoList() {
  const todos = useTodoStore((state) => state.filteredTodos());
  const toggleTodo = useTodoStore((state) => state.toggleTodo);

  return (
    <ul>
      {todos.map((todo) => (
        <li key={todo.id} onClick={() => toggleTodo(todo.id)}>
          {todo.text}
        </li>
      ))}
    </ul>
  );
}

// Multiple selectors
function TodoStats() {
  const stats = useTodoStore((state) => state.stats());
  const filter = useTodoStore((state) => state.filter);

  return (
    <div>
      <p>Total: {stats.total}</p>
      <p>Active: {stats.active}</p>
      <p>Completed: {stats.completed}</p>
      <p>Filter: {filter}</p>
    </div>
  );
}

// Async actions
function UserList() {
  const { users, loading, error, fetchUsers } = useUserStore();

  React.useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <ul>
      {users.map((user) => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}

// Using slices
function Header() {
  const { user, logout } = useAppStore((state) => ({
    user: state.user,
    logout: state.logout,
  }));
  const theme = useAppStore((state) => state.theme);
  const toggleTheme = useAppStore((state) => state.toggleTheme);

  return (
    <header>
      <p>Welcome, {user?.name}</p>
      <button onClick={logout}>Logout</button>
      <button onClick={toggleTheme}>Toggle {theme}</button>
    </header>
  );
}

// Transient updates (don't persist to store)
const useTemporaryStore = create(() => ({ temp: 0 }));

function Component() {
  // This doesn't trigger re-renders
  useTemporaryStore.setState({ temp: 1 });
}
*/
