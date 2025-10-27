#!/usr/bin/env ts-node
/**
 * GraphQL Client Example using Apollo Client
 *
 * Demonstrates client-side best practices:
 * - Type-safe queries with TypeScript
 * - Fragment composition
 * - Cache management
 * - Error handling
 * - Pagination
 * - Optimistic updates
 */

import {
  ApolloClient,
  InMemoryCache,
  gql,
  NormalizedCacheObject,
  ApolloQueryResult,
} from '@apollo/client';

// Generated types (from generate_types.py)
interface User {
  id: string;
  username: string;
  email: string;
  displayName: string;
}

interface Post {
  id: string;
  title: string;
  content: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  author: User;
}

interface PostEdge {
  cursor: string;
  node: Post;
}

interface PageInfo {
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  startCursor: string | null;
  endCursor: string | null;
}

interface PostConnection {
  edges: PostEdge[];
  pageInfo: PageInfo;
  totalCount: number;
}

// Fragments
const USER_FRAGMENT = gql`
  fragment UserFields on User {
    id
    username
    displayName
  }
`;

const POST_FRAGMENT = gql`
  fragment PostFields on Post {
    id
    title
    content
    status
    author {
      ...UserFields
    }
  }
  ${USER_FRAGMENT}
`;

// Queries
const GET_VIEWER = gql`
  query GetViewer {
    viewer {
      ...UserFields
    }
  }
  ${USER_FRAGMENT}
`;

const GET_POSTS = gql`
  query GetPosts($first: Int!, $after: String, $status: PostStatus) {
    posts(first: $first, after: $after, status: $status) {
      edges {
        cursor
        node {
          ...PostFields
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
      totalCount
    }
  }
  ${POST_FRAGMENT}
`;

const GET_POST = gql`
  query GetPost($id: ID!) {
    post(id: $id) {
      ...PostFields
    }
  }
  ${POST_FRAGMENT}
`;

// Mutations
const CREATE_POST = gql`
  mutation CreatePost($input: CreatePostInput!) {
    createPost(input: $input) {
      success
      errors {
        message
        code
      }
      post {
        ...PostFields
      }
    }
  }
  ${POST_FRAGMENT}
`;

const UPDATE_POST = gql`
  mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
    updatePost(id: $id, input: $input) {
      success
      errors {
        message
        code
      }
      post {
        ...PostFields
      }
    }
  }
  ${POST_FRAGMENT}
`;

class GraphQLClient {
  private client: ApolloClient<NormalizedCacheObject>;

  constructor(uri: string = 'http://localhost:4000/graphql') {
    this.client = new ApolloClient({
      uri,
      cache: new InMemoryCache({
        typePolicies: {
          Query: {
            fields: {
              posts: {
                // Merge strategy for pagination
                keyArgs: ['status'],
                merge(existing, incoming, { args }) {
                  if (!existing) return incoming;

                  // Append new edges
                  const edges = existing.edges ? [...existing.edges] : [];

                  if (incoming.edges) {
                    incoming.edges.forEach((edge: PostEdge) => {
                      if (!edges.some((e) => e.cursor === edge.cursor)) {
                        edges.push(edge);
                      }
                    });
                  }

                  return {
                    ...incoming,
                    edges,
                  };
                },
              },
            },
          },
        },
      }),
    });
  }

  /**
   * Get current user
   */
  async getViewer(): Promise<User | null> {
    const result = await this.client.query({
      query: GET_VIEWER,
    });

    return result.data.viewer;
  }

  /**
   * Get posts with pagination
   */
  async getPosts(
    first: number = 10,
    after?: string,
    status?: string
  ): Promise<PostConnection> {
    const result = await this.client.query({
      query: GET_POSTS,
      variables: { first, after, status },
    });

    return result.data.posts;
  }

  /**
   * Get all posts (paginate through all pages)
   */
  async getAllPosts(status?: string): Promise<Post[]> {
    const allPosts: Post[] = [];
    let after: string | null = null;
    let hasNextPage = true;

    while (hasNextPage) {
      const result = await this.getPosts(10, after || undefined, status);

      allPosts.push(...result.edges.map((edge) => edge.node));

      hasNextPage = result.pageInfo.hasNextPage;
      after = result.pageInfo.endCursor;
    }

    return allPosts;
  }

  /**
   * Get single post
   */
  async getPost(id: string): Promise<Post | null> {
    const result = await this.client.query({
      query: GET_POST,
      variables: { id },
    });

    return result.data.post;
  }

  /**
   * Create post with optimistic update
   */
  async createPost(
    title: string,
    content: string,
    status: string = 'DRAFT'
  ): Promise<{ success: boolean; errors: any[]; post: Post | null }> {
    const result = await this.client.mutate({
      mutation: CREATE_POST,
      variables: {
        input: { title, content, status },
      },
      optimisticResponse: {
        createPost: {
          __typename: 'CreatePostPayload',
          success: true,
          errors: [],
          post: {
            __typename: 'Post',
            id: `temp-${Date.now()}`,
            title,
            content,
            status,
            author: {
              __typename: 'User',
              id: '1',
              username: 'loading...',
              displayName: 'Loading...',
            },
          },
        },
      },
      update: (cache, { data }) => {
        if (data?.createPost.success && data.createPost.post) {
          // Update cache with new post
          cache.modify({
            fields: {
              posts(existing = { edges: [], pageInfo: {}, totalCount: 0 }) {
                const newEdge = {
                  __typename: 'PostEdge',
                  cursor: `temp-${Date.now()}`,
                  node: data.createPost.post,
                };

                return {
                  ...existing,
                  edges: [newEdge, ...existing.edges],
                  totalCount: existing.totalCount + 1,
                };
              },
            },
          });
        }
      },
    });

    return result.data.createPost;
  }

  /**
   * Update post with optimistic update
   */
  async updatePost(
    id: string,
    input: { title?: string; content?: string; status?: string }
  ): Promise<{ success: boolean; errors: any[]; post: Post | null }> {
    const result = await this.client.mutate({
      mutation: UPDATE_POST,
      variables: { id, input },
      optimisticResponse: {
        updatePost: {
          __typename: 'UpdatePostPayload',
          success: true,
          errors: [],
          post: {
            __typename: 'Post',
            id,
            ...input,
          },
        },
      },
    });

    return result.data.updatePost;
  }

  /**
   * Watch query for real-time updates
   */
  watchPosts(
    callback: (posts: PostConnection) => void,
    first: number = 10,
    status?: string
  ) {
    const observable = this.client.watchQuery({
      query: GET_POSTS,
      variables: { first, status },
      pollInterval: 5000, // Poll every 5 seconds
    });

    return observable.subscribe({
      next: (result) => callback(result.data.posts),
      error: (error) => console.error('Watch error:', error),
    });
  }

  /**
   * Clear cache
   */
  async clearCache() {
    await this.client.clearStore();
  }

  /**
   * Refetch all active queries
   */
  async refetchQueries() {
    await this.client.refetchQueries({ include: 'active' });
  }
}

// Example usage
async function main() {
  const client = new GraphQLClient('http://localhost:4000/graphql');

  console.log('GraphQL Client Example\n');

  try {
    // Get viewer
    console.log('1. Getting current user...');
    const viewer = await client.getViewer();
    console.log('Viewer:', viewer);
    console.log();

    // Get posts
    console.log('2. Getting posts (first page)...');
    const postsPage1 = await client.getPosts(2);
    console.log(`Found ${postsPage1.totalCount} total posts`);
    console.log('Posts:', postsPage1.edges.map((e) => e.node.title));
    console.log();

    // Get all posts
    console.log('3. Getting all posts (paginated)...');
    const allPosts = await client.getAllPosts();
    console.log(`Retrieved ${allPosts.length} posts`);
    console.log();

    // Create post
    console.log('4. Creating new post...');
    const createResult = await client.createPost(
      'New Post from Client',
      'This post was created via Apollo Client',
      'PUBLISHED'
    );

    if (createResult.success) {
      console.log('Created post:', createResult.post?.title);
    } else {
      console.log('Errors:', createResult.errors);
    }
    console.log();

    // Update post
    if (createResult.post) {
      console.log('5. Updating post...');
      const updateResult = await client.updatePost(createResult.post.id, {
        title: 'Updated Title',
      });

      if (updateResult.success) {
        console.log('Updated post:', updateResult.post?.title);
      } else {
        console.log('Errors:', updateResult.errors);
      }
      console.log();
    }

    // Watch posts for updates
    console.log('6. Watching posts for updates (5 seconds)...');
    const subscription = client.watchPosts(
      (posts) => {
        console.log(`  Update: ${posts.edges.length} posts in cache`);
      },
      10
    );

    await new Promise((resolve) => setTimeout(resolve, 5000));
    subscription.unsubscribe();
    console.log('Stopped watching');
    console.log();

    console.log('✓ All examples completed successfully');
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { GraphQLClient, GET_VIEWER, GET_POSTS, CREATE_POST, UPDATE_POST };
