/**
 * Automerge CRDT Example
 *
 * Demonstrates using Automerge for conflict-free JSON document collaboration.
 * Automerge provides a JSON-like API with automatic conflict resolution.
 *
 * Installation:
 *   npm install @automerge/automerge
 *
 * Run:
 *   node automerge-example.js
 */

const Automerge = require('@automerge/automerge');

// =============================================================================
// Basic Document Collaboration
// =============================================================================

function exampleBasicDocument() {
  console.log('='.repeat(60));
  console.log('Example 1: Basic Document Collaboration');
  console.log('='.repeat(60));

  // Create initial document
  let doc1 = Automerge.from({
    title: 'My Document',
    content: 'Hello, World!',
    author: 'Alice'
  });

  console.log('\nInitial document:');
  console.log(JSON.stringify(doc1, null, 2));

  // Make changes
  doc1 = Automerge.change(doc1, (doc) => {
    doc.title = 'Updated Document';
    doc.content = 'Hello, Automerge!';
  });

  console.log('\nAfter changes:');
  console.log(JSON.stringify(doc1, null, 2));

  // Clone for second replica
  let doc2 = Automerge.clone(doc1);

  // Concurrent changes
  doc1 = Automerge.change(doc1, (doc) => {
    doc.author = 'Alice Smith';
  });

  doc2 = Automerge.change(doc2, (doc) => {
    doc.title = 'Collaborative Document';
  });

  console.log('\nBefore merge:');
  console.log('Doc 1:', JSON.stringify(doc1, null, 2));
  console.log('Doc 2:', JSON.stringify(doc2, null, 2));

  // Merge
  doc1 = Automerge.merge(doc1, doc2);
  doc2 = Automerge.merge(doc2, doc1);

  console.log('\nAfter merge:');
  console.log('Doc 1:', JSON.stringify(doc1, null, 2));
  console.log('Doc 2:', JSON.stringify(doc2, null, 2));

  console.log('\nBoth changes preserved!');
}

// =============================================================================
// Lists and Arrays
// =============================================================================

function exampleLists() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 2: Collaborative Lists');
  console.log('='.repeat(60));

  // Create document with list
  let doc1 = Automerge.from({
    tasks: ['Task 1', 'Task 2']
  });

  console.log('\nInitial list:');
  console.log(doc1.tasks);

  // Clone for second user
  let doc2 = Automerge.clone(doc1);

  // User 1 adds task
  doc1 = Automerge.change(doc1, (doc) => {
    doc.tasks.push('Task 3');
  });

  // User 2 adds task (concurrent)
  doc2 = Automerge.change(doc2, (doc) => {
    doc.tasks.push('Task 4');
  });

  console.log('\nBefore merge:');
  console.log('Doc 1:', doc1.tasks);
  console.log('Doc 2:', doc2.tasks);

  // Merge
  doc1 = Automerge.merge(doc1, doc2);
  doc2 = Automerge.merge(doc2, doc1);

  console.log('\nAfter merge:');
  console.log('Doc 1:', doc1.tasks);
  console.log('Doc 2:', doc2.tasks);

  console.log('\nBoth tasks added!');
}

// =============================================================================
// Text Editing
// =============================================================================

function exampleTextEditing() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 3: Collaborative Text Editing');
  console.log('='.repeat(60));

  // Create document with text
  let doc1 = Automerge.from({
    content: new Automerge.Text('The quick brown fox')
  });

  console.log('\nInitial text:', doc1.content.toString());

  // Clone for second editor
  let doc2 = Automerge.clone(doc1);

  // Editor 1 inserts at end
  doc1 = Automerge.change(doc1, (doc) => {
    doc.content.insertAt(doc.content.length, ' jumps over the lazy dog');
  });

  // Editor 2 inserts in middle (concurrent)
  doc2 = Automerge.change(doc2, (doc) => {
    doc.content.insertAt(10, 'very ');
  });

  console.log('\nBefore merge:');
  console.log('Doc 1:', doc1.content.toString());
  console.log('Doc 2:', doc2.content.toString());

  // Merge
  doc1 = Automerge.merge(doc1, doc2);
  doc2 = Automerge.merge(doc2, doc1);

  console.log('\nAfter merge:');
  console.log('Doc 1:', doc1.content.toString());
  console.log('Doc 2:', doc2.content.toString());

  console.log('\nBoth edits merged!');
}

// =============================================================================
// Nested Objects
// =============================================================================

function exampleNestedObjects() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 4: Nested Objects');
  console.log('='.repeat(60));

  // Create document with nested structure
  let doc1 = Automerge.from({
    user: {
      name: 'Alice',
      email: 'alice@example.com',
      settings: {
        theme: 'dark',
        notifications: true
      }
    }
  });

  console.log('\nInitial document:');
  console.log(JSON.stringify(doc1, null, 2));

  // Clone for second replica
  let doc2 = Automerge.clone(doc1);

  // Update different nested fields
  doc1 = Automerge.change(doc1, (doc) => {
    doc.user.name = 'Alice Smith';
  });

  doc2 = Automerge.change(doc2, (doc) => {
    doc.user.settings.theme = 'light';
  });

  console.log('\nBefore merge:');
  console.log('Doc 1:', JSON.stringify(doc1, null, 2));
  console.log('Doc 2:', JSON.stringify(doc2, null, 2));

  // Merge
  doc1 = Automerge.merge(doc1, doc2);
  doc2 = Automerge.merge(doc2, doc1);

  console.log('\nAfter merge:');
  console.log('Doc 1:', JSON.stringify(doc1, null, 2));
  console.log('Doc 2:', JSON.stringify(doc2, null, 2));

  console.log('\nAll nested changes merged!');
}

// =============================================================================
// History and Time Travel
// =============================================================================

function exampleHistory() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 5: History and Time Travel');
  console.log('='.repeat(60));

  // Create document
  let doc = Automerge.from({ counter: 0 });

  // Make several changes
  console.log('\nMaking changes:');

  doc = Automerge.change(doc, (d) => {
    d.counter = 1;
  });
  console.log('Step 1: counter =', doc.counter);

  doc = Automerge.change(doc, (d) => {
    d.counter = 2;
  });
  console.log('Step 2: counter =', doc.counter);

  doc = Automerge.change(doc, (d) => {
    d.counter = 3;
  });
  console.log('Step 3: counter =', doc.counter);

  // Get history
  const history = Automerge.getHistory(doc);

  console.log('\nHistory:');
  history.forEach((change, i) => {
    console.log(`  Change ${i + 1}:`, change.change.message || '(no message)');
  });

  console.log(`\nTotal changes: ${history.length}`);
  console.log(`Current counter: ${doc.counter}`);
}

// =============================================================================
// Conflict Resolution
// =============================================================================

function exampleConflictResolution() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 6: Conflict Resolution (Last-Write-Wins)');
  console.log('='.repeat(60));

  // Create document
  let doc1 = Automerge.from({ status: 'draft' });
  let doc2 = Automerge.clone(doc1);

  // Concurrent updates to same field
  console.log('\nConcurrent updates to "status":');

  doc1 = Automerge.change(doc1, (doc) => {
    doc.status = 'published';
  });
  console.log('Doc 1: status =', doc1.status);

  doc2 = Automerge.change(doc2, (doc) => {
    doc.status = 'archived';
  });
  console.log('Doc 2: status =', doc2.status);

  // Merge
  console.log('\nMerging...');
  doc1 = Automerge.merge(doc1, doc2);
  doc2 = Automerge.merge(doc2, doc1);

  console.log('\nAfter merge:');
  console.log('Doc 1: status =', doc1.status);
  console.log('Doc 2: status =', doc2.status);

  console.log('\nNote: Automerge uses deterministic resolution for conflicts');
}

// =============================================================================
// Todo List Application
// =============================================================================

function exampleTodoApp() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 7: Collaborative Todo List Application');
  console.log('='.repeat(60));

  // Create initial todo list
  let alice = Automerge.from({
    todos: [
      { id: '1', text: 'Buy groceries', done: false },
      { id: '2', text: 'Walk the dog', done: false }
    ]
  });

  console.log('\nAlice creates todos:');
  alice.todos.forEach((todo) => {
    console.log(`  [${todo.done ? '✓' : ' '}] ${todo.text}`);
  });

  // Bob gets a copy
  let bob = Automerge.clone(alice);

  // Alice marks first todo as done
  alice = Automerge.change(alice, (doc) => {
    doc.todos[0].done = true;
  });

  // Bob adds a new todo (concurrent)
  bob = Automerge.change(bob, (doc) => {
    doc.todos.push({ id: '3', text: 'Review code', done: false });
  });

  console.log('\nBefore sync:');
  console.log('Alice:');
  alice.todos.forEach((todo) => {
    console.log(`  [${todo.done ? '✓' : ' '}] ${todo.text}`);
  });

  console.log('Bob:');
  bob.todos.forEach((todo) => {
    console.log(`  [${todo.done ? '✓' : ' '}] ${todo.text}`);
  });

  // Sync
  alice = Automerge.merge(alice, bob);
  bob = Automerge.merge(bob, alice);

  console.log('\nAfter sync:');
  console.log('Alice:');
  alice.todos.forEach((todo) => {
    console.log(`  [${todo.done ? '✓' : ' '}] ${todo.text}`);
  });

  console.log('Bob:');
  bob.todos.forEach((todo) => {
    console.log(`  [${todo.done ? '✓' : ' '}] ${todo.text}`);
  });

  console.log('\nAll changes synced!');
}

// =============================================================================
// Persistence
// =============================================================================

function examplePersistence() {
  console.log('\n' + '='.repeat(60));
  console.log('Example 8: Persistence (Save/Load)');
  console.log('='.repeat(60));

  // Create document
  let doc = Automerge.from({
    title: 'Persistent Document',
    content: 'This will be saved and restored',
    metadata: {
      created: new Date().toISOString(),
      version: 1
    }
  });

  console.log('\nOriginal document:');
  console.log(JSON.stringify(doc, null, 2));

  // Save to bytes
  const bytes = Automerge.save(doc);
  console.log(`\nSaved to ${bytes.length} bytes`);

  // Simulate: save to file, database, etc.
  // fs.writeFileSync('document.automerge', bytes);

  // Load from bytes
  const restored = Automerge.load(bytes);

  console.log('\nRestored document:');
  console.log(JSON.stringify(restored, null, 2));

  console.log('\nDocument perfectly restored!');
}

// =============================================================================
// Main
// =============================================================================

function main() {
  console.log('\nAutomerge CRDT Examples\n');

  exampleBasicDocument();
  exampleLists();
  exampleTextEditing();
  exampleNestedObjects();
  exampleHistory();
  exampleConflictResolution();
  exampleTodoApp();
  examplePersistence();

  console.log('\n' + '='.repeat(60));
  console.log('All examples complete!');
  console.log('='.repeat(60));
}

main();
