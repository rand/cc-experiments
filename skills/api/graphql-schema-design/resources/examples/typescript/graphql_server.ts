#!/usr/bin/env ts-node
/**
 * GraphQL Server Example using Apollo Server
 *
 * Demonstrates best practices for GraphQL schema design including:
 * - Type-safe resolvers with TypeScript
 * - Connection-based pagination
 * - Error handling with unions
 * - DataLoader for N+1 prevention
 * - Authentication and authorization
 */

import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import DataLoader from 'dataloader';

// Type Definitions
const typeDefs = `#graphql
  scalar DateTime

  # Interfaces
  interface Node {
    id: ID!
  }

  interface Error {
    message: String!
    code: String!
  }

  # Enums
  enum UserRole {
    ADMIN
    USER
    GUEST
  }

  enum PostStatus {
    DRAFT
    PUBLISHED
    ARCHIVED
  }

  # Types
  type User implements Node {
    id: ID!
    username: String!
    email: String!
    displayName: String!
    role: UserRole!
    createdAt: DateTime!
    posts(status: PostStatus): [Post!]!
  }

  type Post implements Node {
    id: ID!
    title: String!
    content: String!
    status: PostStatus!
    author: User!
    createdAt: DateTime!
  }

  # Pagination
  type PageInfo {
    hasNextPage: Boolean!
    hasPreviousPage: Boolean!
    startCursor: String
    endCursor: String
  }

  type PostEdge {
    cursor: String!
    node: Post!
  }

  type PostConnection {
    edges: [PostEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }

  # Input Types
  input CreatePostInput {
    title: String!
    content: String!
    status: PostStatus = DRAFT
  }

  input UpdatePostInput {
    title: String
    content: String
    status: PostStatus
  }

  # Error Types
  type ValidationError implements Error {
    message: String!
    code: String!
    field: String!
  }

  type NotFoundError implements Error {
    message: String!
    code: String!
    entityType: String!
    entityId: ID!
  }

  type AuthError implements Error {
    message: String!
    code: String!
  }

  # Payload Types
  type CreatePostPayload {
    success: Boolean!
    errors: [Error!]!
    post: Post
  }

  type UpdatePostPayload {
    success: Boolean!
    errors: [Error!]!
    post: Post
  }

  # Root Types
  type Query {
    viewer: User
    user(id: ID!): User
    users(role: UserRole): [User!]!
    post(id: ID!): Post
    posts(
      first: Int = 10
      after: String
      status: PostStatus
    ): PostConnection!
  }

  type Mutation {
    createPost(input: CreatePostInput!): CreatePostPayload!
    updatePost(id: ID!, input: UpdatePostInput!): UpdatePostPayload!
  }
`;

// Domain Models
interface UserModel {
  id: string;
  username: string;
  email: string;
  displayName: string;
  role: 'ADMIN' | 'USER' | 'GUEST';
  createdAt: Date;
}

interface PostModel {
  id: string;
  title: string;
  content: string;
  authorId: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  createdAt: Date;
}

// In-memory database
const USERS: UserModel[] = [
  {
    id: '1',
    username: 'alice',
    email: 'alice@example.com',
    displayName: 'Alice Smith',
    role: 'ADMIN',
    createdAt: new Date('2024-01-01'),
  },
  {
    id: '2',
    username: 'bob',
    email: 'bob@example.com',
    displayName: 'Bob Jones',
    role: 'USER',
    createdAt: new Date('2024-01-15'),
  },
];

const POSTS: PostModel[] = [
  {
    id: '1',
    title: 'First Post',
    content: 'Hello, GraphQL!',
    authorId: '1',
    status: 'PUBLISHED',
    createdAt: new Date('2024-02-01'),
  },
  {
    id: '2',
    title: 'Draft Post',
    content: 'Work in progress...',
    authorId: '1',
    status: 'DRAFT',
    createdAt: new Date('2024-02-05'),
  },
];

// Context
interface Context {
  currentUser: UserModel | null;
  loaders: {
    user: DataLoader<string, UserModel | null>;
  };
}

// DataLoader functions
function createUserLoader(): DataLoader<string, UserModel | null> {
  return new DataLoader(async (userIds: readonly string[]) => {
    console.log('Batch loading users:', userIds);
    // Simulate database query
    await new Promise((resolve) => setTimeout(resolve, 10));

    return userIds.map((id) => USERS.find((u) => u.id === id) || null);
  });
}

// Resolvers
const resolvers = {
  DateTime: {
    serialize: (value: Date) => value.toISOString(),
    parseValue: (value: string) => new Date(value),
  },

  Node: {
    __resolveType(obj: any) {
      if ('username' in obj) return 'User';
      if ('title' in obj) return 'Post';
      return null;
    },
  },

  Error: {
    __resolveType(obj: any) {
      if ('field' in obj) return 'ValidationError';
      if ('entityType' in obj) return 'NotFoundError';
      if (obj.code === 'UNAUTHORIZED' || obj.code === 'FORBIDDEN') {
        return 'AuthError';
      }
      return null;
    },
  },

  Query: {
    viewer: (_: any, __: any, context: Context) => {
      return context.currentUser;
    },

    user: async (_: any, { id }: { id: string }, context: Context) => {
      return context.loaders.user.load(id);
    },

    users: (_: any, { role }: { role?: string }) => {
      let users = USERS;
      if (role) {
        users = users.filter((u) => u.role === role);
      }
      return users;
    },

    post: (_: any, { id }: { id: string }) => {
      return POSTS.find((p) => p.id === id) || null;
    },

    posts: (
      _: any,
      {
        first = 10,
        after,
        status,
      }: { first?: number; after?: string; status?: string }
    ) => {
      let posts = POSTS;

      // Filter by status
      if (status) {
        posts = posts.filter((p) => p.status === status);
      }

      // Cursor pagination
      let startIndex = 0;
      if (after) {
        try {
          startIndex = parseInt(after, 10) + 1;
        } catch {
          // Invalid cursor, start from beginning
        }
      }

      const endIndex = startIndex + first;
      const pagePosts = posts.slice(startIndex, endIndex);

      const edges = pagePosts.map((post, i) => ({
        cursor: String(startIndex + i),
        node: post,
      }));

      return {
        edges,
        pageInfo: {
          hasNextPage: endIndex < posts.length,
          hasPreviousPage: startIndex > 0,
          startCursor: edges[0]?.cursor || null,
          endCursor: edges[edges.length - 1]?.cursor || null,
        },
        totalCount: posts.length,
      };
    },
  },

  Mutation: {
    createPost: (
      _: any,
      { input }: { input: { title: string; content: string; status?: string } },
      context: Context
    ) => {
      // Validate
      if (!input.title.trim()) {
        return {
          success: false,
          errors: [
            {
              __typename: 'ValidationError',
              message: 'Title cannot be empty',
              code: 'VALIDATION_ERROR',
              field: 'title',
            },
          ],
          post: null,
        };
      }

      if (!context.currentUser) {
        return {
          success: false,
          errors: [
            {
              __typename: 'AuthError',
              message: 'Authentication required',
              code: 'UNAUTHORIZED',
            },
          ],
          post: null,
        };
      }

      // Create post
      const post: PostModel = {
        id: String(POSTS.length + 1),
        title: input.title,
        content: input.content,
        authorId: context.currentUser.id,
        status: (input.status as any) || 'DRAFT',
        createdAt: new Date(),
      };
      POSTS.push(post);

      return {
        success: true,
        errors: [],
        post,
      };
    },

    updatePost: (
      _: any,
      {
        id,
        input,
      }: {
        id: string;
        input: { title?: string; content?: string; status?: string };
      },
      context: Context
    ) => {
      // Find post
      const post = POSTS.find((p) => p.id === id);

      if (!post) {
        return {
          success: false,
          errors: [
            {
              __typename: 'NotFoundError',
              message: `Post not found: ${id}`,
              code: 'NOT_FOUND',
              entityType: 'Post',
              entityId: id,
            },
          ],
          post: null,
        };
      }

      // Check authorization
      if (context.currentUser?.id !== post.authorId) {
        return {
          success: false,
          errors: [
            {
              __typename: 'AuthError',
              message: 'Not authorized',
              code: 'FORBIDDEN',
            },
          ],
          post: null,
        };
      }

      // Update fields
      if (input.title !== undefined) post.title = input.title;
      if (input.content !== undefined) post.content = input.content;
      if (input.status !== undefined) post.status = input.status as any;

      return {
        success: true,
        errors: [],
        post,
      };
    },
  },

  User: {
    posts: (
      user: UserModel,
      { status }: { status?: string }
    ) => {
      let posts = POSTS.filter((p) => p.authorId === user.id);
      if (status) {
        posts = posts.filter((p) => p.status === status);
      }
      return posts;
    },
  },

  Post: {
    author: (post: PostModel, _: any, context: Context) => {
      return context.loaders.user.load(post.authorId);
    },
  },
};

// Server
async function startServer() {
  const server = new ApolloServer({
    typeDefs,
    resolvers,
  });

  const { url } = await startStandaloneServer(server, {
    listen: { port: 4000 },
    context: async () => ({
      currentUser: USERS[0], // Simulate authenticated user
      loaders: {
        user: createUserLoader(),
      },
    }),
  });

  console.log(`🚀 GraphQL server ready at ${url}`);
  console.log('\nExample queries:');
  console.log('  { viewer { username } }');
  console.log('  { posts(first: 5) { edges { node { title author { username } } } } }');
}

if (require.main === module) {
  startServer();
}

export { typeDefs, resolvers, createUserLoader };
