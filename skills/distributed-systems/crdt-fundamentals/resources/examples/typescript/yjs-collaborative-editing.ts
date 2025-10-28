/**
 * Yjs Collaborative Editing Example
 *
 * Demonstrates using Yjs for real-time collaborative text editing.
 * Yjs is a high-performance CRDT library optimized for collaborative apps.
 *
 * Installation:
 *   npm install yjs
 *
 * Run:
 *   npx ts-node yjs-collaborative-editing.ts
 */

import * as Y from 'yjs';

// =============================================================================
// Basic Text Collaboration
// =============================================================================

function exampleBasicText() {
  console.log('='.repeat(60));
  console.log('Example 1: Basic Text Collaboration');
  console.log('='.repeat(60));

  // Create two documents (simulating two users)
  const doc1 = new Y.Doc();
  const doc2 = new Y.Doc();

  // Get shared text types
  const text1 = doc1.getText('mytext');
  const text2 = doc2.getText('mytext');

  // Setup sync between documents
  doc1.on('update', (update: Uint8Array) => {
    Y.applyUpdate(doc2, update);
  });

  doc2.on('update', (update: Uint8Array) => {
    Y.applyUpdate(doc1, update);
  });

  // User 1 types
  console.log('\nUser 1 types "Hello"');
  text1.insert(0, 'Hello');
  console.log(`Doc 1: "${text1.toString()}"`);
  console.log(`Doc 2: "${text2.toString()}"`);

  // User 2 types
  console.log('\nUser 2 types " World"');
  text2.insert(text2.length, ' World');
  console.log(`Doc 1: "${text1.toString()}"`);
  console.log(`Doc 2: "${text2.toString()}"`);

  console.log('\nBoth documents converged!');
}

// =============================================================================
// Concurrent Editing
// =============================================================================

function exampleConcurrentEditing() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 2: Concurrent Editing (Offline Simulation)');
  console.log('='.repeat(60));

  const doc1 = new Y.Doc();
  const doc2 = new Y.Doc();

  const text1 = doc1.getText('content');
  const text2 = doc2.getText('content');

  // Initial state
  text1.insert(0, 'The quick brown fox');
  Y.applyUpdate(doc2, Y.encodeStateAsUpdate(doc1));

  console.log(`Initial: "${text1.toString()}"`);

  // Disconnect (simulate offline)
  console.log('\nUsers go offline...');

  // User 1 edits offline
  console.log('User 1 (offline): inserts " jumps" at end');
  text1.insert(text1.length, ' jumps');
  console.log(`  Doc 1: "${text1.toString()}"`);

  // User 2 edits offline
  console.log('User 2 (offline): inserts " very" after "The"');
  text2.insert(3, ' very');
  console.log(`  Doc 2: "${text2.toString()}"`);

  // Reconnect and sync
  console.log('\nUsers come back online and sync...');
  Y.applyUpdate(doc1, Y.encodeStateAsUpdate(doc2));
  Y.applyUpdate(doc2, Y.encodeStateAsUpdate(doc1));

  console.log(`\nDoc 1: "${text1.toString()}"`);
  console.log(`Doc 2: "${text2.toString()}"`);
  console.log('\nBoth edits preserved and merged!');
}

// =============================================================================
// Shared Data Types
// =============================================================================

function exampleSharedDataTypes() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 3: Shared Data Types (Map, Array)');
  console.log('='.repeat(60));

  const doc1 = new Y.Doc();
  const doc2 = new Y.Doc();

  // Setup sync
  doc1.on('update', (update: Uint8Array) => {
    Y.applyUpdate(doc2, update);
  });

  doc2.on('update', (update: Uint8Array) => {
    Y.applyUpdate(doc1, update);
  });

  // Shared Map (like a dictionary)
  const map1 = doc1.getMap('config');
  const map2 = doc2.getMap('config');

  console.log('\nShared Map:');
  map1.set('timeout', 30);
  map1.set('retries', 3);
  console.log(`  Doc 1: ${JSON.stringify(map1.toJSON())}`);
  console.log(`  Doc 2: ${JSON.stringify(map2.toJSON())}`);

  // Shared Array
  const array1 = doc1.getArray('tasks');
  const array2 = doc2.getArray('tasks');

  console.log('\nShared Array:');
  array1.push(['Buy milk', 'Write code']);
  array2.push(['Review PR']);
  console.log(`  Doc 1: ${JSON.stringify(array1.toJSON())}`);
  console.log(`  Doc 2: ${JSON.stringify(array2.toJSON())}`);

  console.log('\nAll changes synced!');
}

// =============================================================================
// Collaborative Todo List
// =============================================================================

interface Todo {
  text: string;
  done: boolean;
  id: string;
}

function exampleCollaborativeTodoList() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 4: Collaborative Todo List');
  console.log('='.repeat(60));

  // Two users
  const aliceDoc = new Y.Doc();
  const bobDoc = new Y.Doc();

  // Setup sync
  aliceDoc.on('update', (update: Uint8Array) => {
    Y.applyUpdate(bobDoc, update);
  });

  bobDoc.on('update', (update: Uint8Array) => {
    Y.applyUpdate(aliceDoc, update);
  });

  // Shared todos array
  const aliceTodos = aliceDoc.getArray<Y.Map<any>>('todos');
  const bobTodos = bobDoc.getArray<Y.Map<any>>('todos');

  // Alice adds todos
  console.log('\nAlice adds todos:');
  const todo1 = new Y.Map();
  todo1.set('id', '1');
  todo1.set('text', 'Buy groceries');
  todo1.set('done', false);
  aliceTodos.push([todo1]);

  const todo2 = new Y.Map();
  todo2.set('id', '2');
  todo2.set('text', 'Walk the dog');
  todo2.set('done', false);
  aliceTodos.push([todo2]);

  printTodos('Alice', aliceTodos);
  printTodos('Bob', bobTodos);

  // Bob marks todo as done
  console.log('\nBob marks "Buy groceries" as done:');
  bobTodos.get(0).set('done', true);

  printTodos('Alice', aliceTodos);
  printTodos('Bob', bobTodos);

  // Alice adds another todo
  console.log('\nAlice adds another todo:');
  const todo3 = new Y.Map();
  todo3.set('id', '3');
  todo3.set('text', 'Review code');
  todo3.set('done', false);
  aliceTodos.push([todo3]);

  printTodos('Alice', aliceTodos);
  printTodos('Bob', bobTodos);

  console.log('\nAll changes synced in real-time!');
}

function printTodos(user: string, todos: Y.Array<Y.Map<any>>) {
  console.log(`  ${user}'s todos:`);
  todos.forEach((todo, i) => {
    const text = todo.get('text');
    const done = todo.get('done');
    const status = done ? '✓' : ' ';
    console.log(`    [${status}] ${text}`);
  });
}

// =============================================================================
// Undo/Redo
// =============================================================================

function exampleUndoRedo() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 5: Undo/Redo');
  console.log('='.repeat(60));

  const doc = new Y.Doc();
  const text = doc.getText('content');

  // Create undo manager
  const undoManager = new Y.UndoManager(text);

  // Make changes
  console.log('\nMaking changes:');
  text.insert(0, 'Hello');
  console.log(`  After insert: "${text.toString()}"`);

  text.insert(5, ' World');
  console.log(`  After insert: "${text.toString()}"`);

  text.insert(11, '!');
  console.log(`  After insert: "${text.toString()}"`);

  // Undo
  console.log('\nUndo:');
  undoManager.undo();
  console.log(`  After undo: "${text.toString()}"`);

  undoManager.undo();
  console.log(`  After undo: "${text.toString()}"`);

  // Redo
  console.log('\nRedo:');
  undoManager.redo();
  console.log(`  After redo: "${text.toString()}"`);

  undoManager.redo();
  console.log(`  After redo: "${text.toString()}"`);
}

// =============================================================================
// Persistence
// =============================================================================

function examplePersistence() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 6: Persistence (Serialization)');
  console.log('='.repeat(60));

  // Create and populate document
  const doc1 = new Y.Doc();
  const text1 = doc1.getText('content');
  text1.insert(0, 'This is persistent data');

  const map1 = doc1.getMap('metadata');
  map1.set('author', 'Alice');
  map1.set('created', Date.now());

  console.log('\nOriginal document:');
  console.log(`  Text: "${text1.toString()}"`);
  console.log(`  Metadata: ${JSON.stringify(map1.toJSON())}`);

  // Serialize to bytes
  const state = Y.encodeStateAsUpdate(doc1);
  console.log(`\nSerialized to ${state.length} bytes`);

  // Simulate: save to database, send over network, etc.
  // const base64 = Buffer.from(state).toString('base64');

  // Restore from bytes
  const doc2 = new Y.Doc();
  Y.applyUpdate(doc2, state);

  const text2 = doc2.getText('content');
  const map2 = doc2.getMap('metadata');

  console.log('\nRestored document:');
  console.log(`  Text: "${text2.toString()}"`);
  console.log(`  Metadata: ${JSON.stringify(map2.toJSON())}`);

  console.log('\nData perfectly restored!');
}

// =============================================================================
// Observing Changes
// =============================================================================

function exampleObservers() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 7: Observing Changes');
  console.log('='.repeat(60));

  const doc = new Y.Doc();
  const text = doc.getText('content');

  // Observer for text changes
  text.observe((event) => {
    console.log('\nText changed:');
    event.changes.delta.forEach((change) => {
      if (change.insert) {
        console.log(`  Inserted: "${change.insert}"`);
      } else if (change.delete) {
        console.log(`  Deleted: ${change.delete} characters`);
      } else if (change.retain) {
        console.log(`  Retained: ${change.retain} characters`);
      }
    });
  });

  // Make changes
  console.log('\nInserting "Hello":');
  text.insert(0, 'Hello');

  console.log('\nInserting " World":');
  text.insert(5, ' World');

  console.log('\nDeleting 6 characters:');
  text.delete(0, 6);

  console.log(`\nFinal text: "${text.toString()}"`);
}

// =============================================================================
// Main
// =============================================================================

function main() {
  console.log('\nYjs Collaborative Editing Examples\n');

  exampleBasicText();
  exampleConcurrentEditing();
  exampleSharedDataTypes();
  exampleCollaborativeTodoList();
  exampleUndoRedo();
  examplePersistence();
  exampleObservers();

  console.log('\n' + '='.repeat(60));
  console.log('All examples complete!');
  console.log('='.repeat(60));
}

main();
