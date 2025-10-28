/**
 * TanStack Query (React Query) Hooks Example
 *
 * Demonstrates:
 * - Basic queries
 * - Mutations
 * - Optimistic updates
 * - Pagination
 * - Infinite queries
 * - Dependent queries
 * - Parallel queries
 * - Query invalidation
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
  useQueries,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';
import { ReactNode } from 'react';

// ============================================================================
// Types
// ============================================================================

type User = {
  id: string;
  name: string;
  email: string;
  avatar?: string;
};

type Post = {
  id: string;
  title: string;
  body: string;
  authorId: string;
  createdAt: string;
};

type Comment = {
  id: string;
  postId: string;
  userId: string;
  text: string;
  createdAt: string;
};

type PaginatedResponse<T> = {
  data: T[];
  page: number;
  pageSize: number;
  total: number;
  hasMore: boolean;
};

// ============================================================================
// Query Client Setup
// ============================================================================

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes (formerly cacheTime)
      retry: 3,
      refetchOnWindowFocus: false,
    },
  },
});

export function QueryProvider({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchUsers(): Promise<User[]> {
  const response = await fetch('/api/users');
  if (!response.ok) throw new Error('Failed to fetch users');
  return response.json();
}

async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) throw new Error('Failed to fetch user');
  return response.json();
}

async function fetchPosts(page: number, pageSize: number): Promise<PaginatedResponse<Post>> {
  const response = await fetch(`/api/posts?page=${page}&pageSize=${pageSize}`);
  if (!response.ok) throw new Error('Failed to fetch posts');
  return response.json();
}

async function fetchPost(id: string): Promise<Post> {
  const response = await fetch(`/api/posts/${id}`);
  if (!response.ok) throw new Error('Failed to fetch post');
  return response.json();
}

async function fetchComments(postId: string): Promise<Comment[]> {
  const response = await fetch(`/api/posts/${postId}/comments`);
  if (!response.ok) throw new Error('Failed to fetch comments');
  return response.json();
}

async function createPost(data: Omit<Post, 'id' | 'createdAt'>): Promise<Post> {
  const response = await fetch('/api/posts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create post');
  return response.json();
}

async function updatePost(id: string, data: Partial<Post>): Promise<Post> {
  const response = await fetch(`/api/posts/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update post');
  return response.json();
}

async function deletePost(id: string): Promise<void> {
  const response = await fetch(`/api/posts/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete post');
}

// ============================================================================
// Basic Query Hooks
// ============================================================================

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });
}

export function useUser(userId: string) {
  return useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
    enabled: !!userId, // Only run if userId exists
  });
}

export function usePost(postId: string) {
  return useQuery({
    queryKey: ['post', postId],
    queryFn: () => fetchPost(postId),
    staleTime: 1000 * 60 * 10, // 10 minutes for individual posts
  });
}

// ============================================================================
// Dependent Queries
// ============================================================================

export function usePostWithAuthor(postId: string) {
  // First, fetch the post
  const { data: post, ...postQuery } = usePost(postId);

  // Then, fetch the author (only runs if post exists)
  const { data: author, ...authorQuery } = useUser(post?.authorId || '');

  return {
    post,
    author,
    isLoading: postQuery.isLoading || authorQuery.isLoading,
    isError: postQuery.isError || authorQuery.isError,
    error: postQuery.error || authorQuery.error,
  };
}

export function usePostWithComments(postId: string) {
  const postQuery = useQuery({
    queryKey: ['post', postId],
    queryFn: () => fetchPost(postId),
  });

  const commentsQuery = useQuery({
    queryKey: ['comments', postId],
    queryFn: () => fetchComments(postId),
    enabled: !!postQuery.data, // Only fetch comments if post exists
  });

  return {
    post: postQuery.data,
    comments: commentsQuery.data,
    isLoading: postQuery.isLoading || commentsQuery.isLoading,
    isError: postQuery.isError || commentsQuery.isError,
  };
}

// ============================================================================
// Parallel Queries
// ============================================================================

export function useMultipleUsers(userIds: string[]) {
  return useQueries({
    queries: userIds.map((id) => ({
      queryKey: ['user', id],
      queryFn: () => fetchUser(id),
    })),
  });
}

export function useDashboardData() {
  const usersQuery = useUsers();
  const postsQuery = useQuery({
    queryKey: ['posts', 1, 10],
    queryFn: () => fetchPosts(1, 10),
  });

  return {
    users: usersQuery.data,
    posts: postsQuery.data?.data,
    isLoading: usersQuery.isLoading || postsQuery.isLoading,
    isError: usersQuery.isError || postsQuery.isError,
  };
}

// ============================================================================
// Pagination
// ============================================================================

export function usePaginatedPosts(page: number, pageSize: number = 10) {
  return useQuery({
    queryKey: ['posts', page, pageSize],
    queryFn: () => fetchPosts(page, pageSize),
    placeholderData: (previousData) => previousData, // Keep previous data while loading
  });
}

// ============================================================================
// Infinite Queries
// ============================================================================

export function useInfinitePosts() {
  return useInfiniteQuery({
    queryKey: ['posts', 'infinite'],
    queryFn: ({ pageParam = 1 }) => fetchPosts(pageParam, 10),
    getNextPageParam: (lastPage) => (lastPage.hasMore ? lastPage.page + 1 : undefined),
    initialPageParam: 1,
  });
}

// ============================================================================
// Mutations
// ============================================================================

export function useCreatePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPost,
    onSuccess: (newPost) => {
      // Invalidate and refetch posts
      queryClient.invalidateQueries({ queryKey: ['posts'] });

      // Or add to existing cache
      queryClient.setQueryData(['post', newPost.id], newPost);
    },
  });
}

export function useUpdatePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Post> }) => updatePost(id, data),
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['post', id] });

      // Snapshot previous value
      const previousPost = queryClient.getQueryData<Post>(['post', id]);

      // Optimistically update
      if (previousPost) {
        queryClient.setQueryData(['post', id], { ...previousPost, ...data });
      }

      return { previousPost };
    },
    onError: (err, { id }, context) => {
      // Rollback on error
      if (context?.previousPost) {
        queryClient.setQueryData(['post', id], context.previousPost);
      }
    },
    onSettled: (data, error, { id }) => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: ['post', id] });
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });
}

export function useDeletePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deletePost,
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['posts'] });

      const previousPosts = queryClient.getQueryData(['posts']);

      // Optimistically remove from cache
      queryClient.setQueriesData<PaginatedResponse<Post>>(
        { queryKey: ['posts'] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.filter((post) => post.id !== id),
          };
        }
      );

      return { previousPosts };
    },
    onError: (err, id, context) => {
      if (context?.previousPosts) {
        queryClient.setQueryData(['posts'], context.previousPosts);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });
}

// ============================================================================
// Advanced: Optimistic Updates with Multiple Caches
// ============================================================================

export function useOptimisticUpdatePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Post> }) => updatePost(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: ['post', id] });
      await queryClient.cancelQueries({ queryKey: ['posts'] });

      // Snapshot
      const previousPost = queryClient.getQueryData<Post>(['post', id]);
      const previousPosts = queryClient.getQueryData(['posts']);

      // Update individual post
      if (previousPost) {
        queryClient.setQueryData(['post', id], { ...previousPost, ...data });
      }

      // Update posts list
      queryClient.setQueriesData<PaginatedResponse<Post>>(
        { queryKey: ['posts'] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.map((post) =>
              post.id === id ? { ...post, ...data } : post
            ),
          };
        }
      );

      return { previousPost, previousPosts };
    },
    onError: (err, { id }, context) => {
      if (context?.previousPost) {
        queryClient.setQueryData(['post', id], context.previousPost);
      }
      if (context?.previousPosts) {
        queryClient.setQueryData(['posts'], context.previousPosts);
      }
    },
    onSettled: (data, error, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['post', id] });
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });
}

// ============================================================================
// Manual Cache Updates
// ============================================================================

export function useCacheManagement() {
  const queryClient = useQueryClient();

  return {
    // Prefetch data
    prefetchPost: (id: string) => {
      return queryClient.prefetchQuery({
        queryKey: ['post', id],
        queryFn: () => fetchPost(id),
      });
    },

    // Get cached data
    getCachedPost: (id: string) => {
      return queryClient.getQueryData<Post>(['post', id]);
    },

    // Set cached data
    setCachedPost: (post: Post) => {
      queryClient.setQueryData(['post', post.id], post);
    },

    // Invalidate queries
    invalidatePosts: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },

    // Remove query from cache
    removePost: (id: string) => {
      queryClient.removeQueries({ queryKey: ['post', id] });
    },

    // Reset all queries
    resetQueries: () => {
      queryClient.resetQueries();
    },
  };
}

// ============================================================================
// Usage Examples in Components
// ============================================================================

/*
// Basic query
function UserList() {
  const { data: users, isLoading, error } = useUsers();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {users?.map((user) => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}

// Mutation
function CreatePostForm() {
  const createPost = useCreatePost();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createPost.mutate({
      title: formData.get('title') as string,
      body: formData.get('body') as string,
      authorId: 'current-user-id',
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="title" required />
      <textarea name="body" required />
      <button disabled={createPost.isPending}>
        {createPost.isPending ? 'Creating...' : 'Create'}
      </button>
      {createPost.isError && <div>Error: {createPost.error.message}</div>}
    </form>
  );
}

// Pagination
function PaginatedPosts() {
  const [page, setPage] = React.useState(1);
  const { data, isLoading, isPlaceholderData } = usePaginatedPosts(page);

  return (
    <div>
      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <ul>
          {data?.data.map((post) => (
            <li key={post.id}>{post.title}</li>
          ))}
        </ul>
      )}

      <button
        onClick={() => setPage((p) => Math.max(1, p - 1))}
        disabled={page === 1}
      >
        Previous
      </button>
      <button
        onClick={() => setPage((p) => p + 1)}
        disabled={isPlaceholderData || !data?.hasMore}
      >
        Next
      </button>
    </div>
  );
}

// Infinite scroll
function InfinitePosts() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfinitePosts();

  return (
    <div>
      {data?.pages.map((page, i) => (
        <React.Fragment key={i}>
          {page.data.map((post) => (
            <div key={post.id}>{post.title}</div>
          ))}
        </React.Fragment>
      ))}

      <button
        onClick={() => fetchNextPage()}
        disabled={!hasNextPage || isFetchingNextPage}
      >
        {isFetchingNextPage
          ? 'Loading...'
          : hasNextPage
          ? 'Load More'
          : 'No more posts'}
      </button>
    </div>
  );
}
*/
