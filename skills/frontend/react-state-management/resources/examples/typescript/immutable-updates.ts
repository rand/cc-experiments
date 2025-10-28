/**
 * Immutable State Updates Example
 *
 * Demonstrates:
 * - Array immutable operations
 * - Object immutable operations
 * - Nested updates
 * - Using Immer
 * - Common patterns
 * - Performance considerations
 */

import { produce } from 'immer';

// ============================================================================
// Array Operations
// ============================================================================

type Todo = {
  id: string;
  text: string;
  completed: boolean;
};

// Adding items
export const arrayAddExamples = {
  // Bad: Mutates array
  bad: (todos: Todo[], newTodo: Todo) => {
    todos.push(newTodo); // ❌ Mutation!
    return todos;
  },

  // Good: Spread operator
  spreadEnd: (todos: Todo[], newTodo: Todo) => {
    return [...todos, newTodo]; // ✅ New array
  },

  // Good: concat
  concat: (todos: Todo[], newTodo: Todo) => {
    return todos.concat(newTodo); // ✅ New array
  },

  // Good: Add at beginning
  spreadStart: (todos: Todo[], newTodo: Todo) => {
    return [newTodo, ...todos]; // ✅ New array
  },

  // Good: Add at specific index
  insertAt: (todos: Todo[], newTodo: Todo, index: number) => {
    return [...todos.slice(0, index), newTodo, ...todos.slice(index)]; // ✅ New array
  },
};

// Removing items
export const arrayRemoveExamples = {
  // Bad: Mutates array
  bad: (todos: Todo[], index: number) => {
    todos.splice(index, 1); // ❌ Mutation!
    return todos;
  },

  // Good: Filter by index
  filterIndex: (todos: Todo[], index: number) => {
    return todos.filter((_, i) => i !== index); // ✅ New array
  },

  // Good: Filter by id
  filterId: (todos: Todo[], id: string) => {
    return todos.filter((todo) => todo.id !== id); // ✅ New array
  },

  // Good: Remove multiple
  filterMultiple: (todos: Todo[], idsToRemove: string[]) => {
    return todos.filter((todo) => !idsToRemove.includes(todo.id)); // ✅ New array
  },

  // Good: Remove at specific index using slice
  slice: (todos: Todo[], index: number) => {
    return [...todos.slice(0, index), ...todos.slice(index + 1)]; // ✅ New array
  },
};

// Updating items
export const arrayUpdateExamples = {
  // Bad: Mutates array
  bad: (todos: Todo[], index: number, updates: Partial<Todo>) => {
    todos[index] = { ...todos[index], ...updates }; // ❌ Mutation!
    return todos;
  },

  // Good: Map with index
  mapIndex: (todos: Todo[], index: number, updates: Partial<Todo>) => {
    return todos.map((todo, i) => (i === index ? { ...todo, ...updates } : todo)); // ✅ New array
  },

  // Good: Map with id
  mapId: (todos: Todo[], id: string, updates: Partial<Todo>) => {
    return todos.map((todo) => (todo.id === id ? { ...todo, ...updates } : todo)); // ✅ New array
  },

  // Good: Toggle boolean
  toggle: (todos: Todo[], id: string) => {
    return todos.map((todo) =>
      todo.id === id ? { ...todo, completed: !todo.completed } : todo
    ); // ✅ New array
  },

  // Good: Update multiple
  updateMultiple: (todos: Todo[], updates: Array<{ id: string; changes: Partial<Todo> }>) => {
    return todos.map((todo) => {
      const update = updates.find((u) => u.id === todo.id);
      return update ? { ...todo, ...update.changes } : todo;
    }); // ✅ New array
  },
};

// Sorting and filtering
export const arrayTransformExamples = {
  // Bad: Mutates array
  badSort: (todos: Todo[]) => {
    todos.sort((a, b) => a.text.localeCompare(b.text)); // ❌ Mutation!
    return todos;
  },

  // Good: Sort with spread
  sort: (todos: Todo[]) => {
    return [...todos].sort((a, b) => a.text.localeCompare(b.text)); // ✅ New array
  },

  // Good: Reverse
  reverse: (todos: Todo[]) => {
    return [...todos].reverse(); // ✅ New array
  },

  // Good: Filter
  filter: (todos: Todo[]) => {
    return todos.filter((todo) => !todo.completed); // ✅ New array
  },

  // Good: Map and filter (chain)
  mapAndFilter: (todos: Todo[]) => {
    return todos
      .filter((todo) => !todo.completed)
      .map((todo) => ({ ...todo, text: todo.text.toUpperCase() })); // ✅ New array
  },
};

// ============================================================================
// Object Operations
// ============================================================================

type User = {
  id: string;
  name: string;
  email: string;
  settings: {
    theme: 'light' | 'dark';
    notifications: boolean;
    privacy: {
      showEmail: boolean;
      showProfile: boolean;
    };
  };
};

// Shallow updates
export const objectUpdateExamples = {
  // Bad: Mutates object
  bad: (user: User, name: string) => {
    user.name = name; // ❌ Mutation!
    return user;
  },

  // Good: Spread operator
  spread: (user: User, name: string) => {
    return { ...user, name }; // ✅ New object
  },

  // Good: Multiple properties
  multipleProps: (user: User, updates: Partial<User>) => {
    return { ...user, ...updates }; // ✅ New object
  },

  // Good: Computed property names
  computed: (user: User, key: keyof User, value: any) => {
    return { ...user, [key]: value }; // ✅ New object
  },
};

// Nested updates
export const nestedUpdateExamples = {
  // Bad: Deep mutation
  bad: (user: User, theme: 'light' | 'dark') => {
    user.settings.theme = theme; // ❌ Mutation!
    return user;
  },

  // Good: Spread all levels
  spreadAll: (user: User, theme: 'light' | 'dark') => {
    return {
      ...user,
      settings: {
        ...user.settings,
        theme,
      },
    }; // ✅ New object
  },

  // Good: Deeply nested
  deeplyNested: (user: User, showEmail: boolean) => {
    return {
      ...user,
      settings: {
        ...user.settings,
        privacy: {
          ...user.settings.privacy,
          showEmail,
        },
      },
    }; // ✅ New object
  },

  // Good: Multiple nested updates
  multipleNested: (user: User, theme: 'light' | 'dark', notifications: boolean) => {
    return {
      ...user,
      settings: {
        ...user.settings,
        theme,
        notifications,
      },
    }; // ✅ New object
  },
};

// ============================================================================
// Complex State Operations
// ============================================================================

type AppState = {
  users: { [id: string]: User };
  todos: Todo[];
  currentUser: string | null;
  filters: {
    search: string;
    status: 'all' | 'active' | 'completed';
  };
};

export const complexStateExamples = {
  // Add user to dictionary
  addUser: (state: AppState, user: User) => {
    return {
      ...state,
      users: {
        ...state.users,
        [user.id]: user,
      },
    };
  },

  // Remove user from dictionary
  removeUser: (state: AppState, userId: string) => {
    const { [userId]: removed, ...rest } = state.users;
    return {
      ...state,
      users: rest,
    };
  },

  // Update user in dictionary
  updateUser: (state: AppState, userId: string, updates: Partial<User>) => {
    return {
      ...state,
      users: {
        ...state.users,
        [userId]: {
          ...state.users[userId],
          ...updates,
        },
      },
    };
  },

  // Update multiple parts of state
  multipleUpdates: (state: AppState, userId: string, newTodo: Todo, search: string) => {
    return {
      ...state,
      users: {
        ...state.users,
        [userId]: {
          ...state.users[userId],
          name: 'Updated Name',
        },
      },
      todos: [...state.todos, newTodo],
      filters: {
        ...state.filters,
        search,
      },
    };
  },
};

// ============================================================================
// Using Immer for Complex Updates
// ============================================================================

export const immerExamples = {
  // Simple update
  simpleUpdate: (state: AppState, userId: string, name: string) => {
    return produce(state, (draft) => {
      draft.users[userId].name = name;
    });
  },

  // Nested update
  nestedUpdate: (state: AppState, userId: string, theme: 'light' | 'dark') => {
    return produce(state, (draft) => {
      draft.users[userId].settings.theme = theme;
      draft.users[userId].settings.privacy.showEmail = true;
    });
  },

  // Array operations
  arrayOps: (state: AppState, newTodo: Todo) => {
    return produce(state, (draft) => {
      draft.todos.push(newTodo);
      draft.todos[0].completed = true;
      draft.todos.sort((a, b) => a.text.localeCompare(b.text));
    });
  },

  // Complex operations
  complex: (state: AppState, userId: string, todoId: string) => {
    return produce(state, (draft) => {
      // Find and update todo
      const todo = draft.todos.find((t) => t.id === todoId);
      if (todo) {
        todo.completed = !todo.completed;
      }

      // Update user
      if (draft.users[userId]) {
        draft.users[userId].name = 'New Name';
        draft.users[userId].settings.notifications = false;
      }

      // Update filters
      draft.filters.status = 'active';
    });
  },

  // Conditional updates
  conditional: (state: AppState, userId: string) => {
    return produce(state, (draft) => {
      const user = draft.users[userId];
      if (user) {
        if (user.settings.theme === 'light') {
          user.settings.theme = 'dark';
        } else {
          user.settings.theme = 'light';
        }

        // Remove completed todos
        draft.todos = draft.todos.filter((t) => !t.completed);
      }
    });
  },
};

// ============================================================================
// Performance Considerations
// ============================================================================

export const performanceExamples = {
  // Bad: Creating new objects on every render
  badMemo: (users: User[]) => {
    // This creates a new array on every call
    return users.filter((u) => u.name.startsWith('A'));
  },

  // Good: Memoize expensive operations
  goodMemo: (() => {
    let cache: { users: User[]; result: User[] } | null = null;

    return (users: User[]) => {
      if (cache && cache.users === users) {
        return cache.result;
      }

      const result = users.filter((u) => u.name.startsWith('A'));
      cache = { users, result };
      return result;
    };
  })(),

  // Bad: Unnecessary spreading
  unnecessarySpread: (user: User) => {
    return { ...user }; // No changes, but creates new object
  },

  // Good: Return same reference if unchanged
  conditionalSpread: (user: User, name: string) => {
    if (user.name === name) {
      return user; // No changes, return same reference
    }
    return { ...user, name };
  },
};

// ============================================================================
// Common Patterns
// ============================================================================

export const commonPatterns = {
  // Toggle boolean in object
  toggleBoolean: (state: { enabled: boolean }) => {
    return { ...state, enabled: !state.enabled };
  },

  // Increment counter
  increment: (state: { count: number }) => {
    return { ...state, count: state.count + 1 };
  },

  // Add to set (using array)
  addToSet: (state: { items: string[] }, item: string) => {
    if (state.items.includes(item)) {
      return state;
    }
    return { ...state, items: [...state.items, item] };
  },

  // Remove from set
  removeFromSet: (state: { items: string[] }, item: string) => {
    return { ...state, items: state.items.filter((i) => i !== item) };
  },

  // Toggle in set
  toggleInSet: (state: { items: string[] }, item: string) => {
    if (state.items.includes(item)) {
      return { ...state, items: state.items.filter((i) => i !== item) };
    }
    return { ...state, items: [...state.items, item] };
  },

  // Replace entire array
  replaceArray: (state: { items: string[] }, newItems: string[]) => {
    return { ...state, items: newItems };
  },

  // Clear array
  clearArray: (state: { items: string[] }) => {
    return { ...state, items: [] };
  },

  // Merge objects
  mergeObjects: (state: { data: Record<string, any> }, updates: Record<string, any>) => {
    return {
      ...state,
      data: { ...state.data, ...updates },
    };
  },

  // Reset to initial state
  reset: (state: any, initialState: any) => {
    return initialState;
  },
};

// ============================================================================
// React Hooks Integration
// ============================================================================

import { useState } from 'react';

export function useImmutableState<T>(initialState: T) {
  const [state, setState] = useState(initialState);

  const updateState = (updates: Partial<T> | ((prev: T) => T)) => {
    setState((prev) => {
      if (typeof updates === 'function') {
        return updates(prev);
      }
      return { ...prev, ...updates };
    });
  };

  const updateNested = (path: string[], value: any) => {
    setState((prev) => {
      return produce(prev, (draft: any) => {
        let current = draft;
        for (let i = 0; i < path.length - 1; i++) {
          current = current[path[i]];
        }
        current[path[path.length - 1]] = value;
      });
    });
  };

  return { state, updateState, updateNested, setState };
}

// ============================================================================
// Best Practices Summary
// ============================================================================

/*
DO:
✅ Use spread operator for shallow updates
✅ Spread all levels for nested updates
✅ Use array methods that return new arrays (map, filter, concat)
✅ Use Immer for complex nested updates
✅ Return same reference if state unchanged
✅ Memoize expensive operations
✅ Use structural sharing when possible

DON'T:
❌ Mutate state directly
❌ Use array methods that mutate (push, pop, splice, sort without copying)
❌ Modify nested objects directly
❌ Create unnecessary copies
❌ Forget to copy all levels in nested updates
❌ Use Object.assign on state (use spread instead)
❌ Rely on deep cloning (JSON.parse/stringify) - it's slow

PATTERNS:
- Add: [...array, item]
- Remove: array.filter(i => i !== item)
- Update: array.map(i => i.id === id ? {...i, ...updates} : i)
- Sort: [...array].sort()
- Nested: { ...obj, nested: { ...obj.nested, prop: value } }
- Immer: produce(state, draft => { draft.prop = value })
*/
