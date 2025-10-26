---
name: swiftdata-persistence
description: Building iOS/macOS apps with local persistence
---



# SwiftData Persistence Patterns

**Use this skill when:**
- Building iOS/macOS apps with local persistence
- Migrating from Core Data to SwiftData
- Implementing data models with relationships
- Querying and filtering persisted data
- Managing model versions and migrations

## Model Definition

### Basic Model Class

Define models with `@Model` macro:

```swift
import SwiftData

@Model
final class Task {
    var title: String
    var isCompleted: Bool
    var createdAt: Date
    var dueDate: Date?

    init(title: String, isCompleted: Bool = false, dueDate: Date? = nil) {
        self.title = title
        self.isCompleted = isCompleted
        self.createdAt = Date()
        self.dueDate = dueDate
    }
}
```

### Relationships

Define one-to-many and many-to-many relationships:

```swift
@Model
final class Project {
    var name: String
    var createdAt: Date

    // One-to-many: one project has many tasks
    @Relationship(deleteRule: .cascade, inverse: \Task.project)
    var tasks: [Task] = []

    init(name: String) {
        self.name = name
        self.createdAt = Date()
    }
}

@Model
final class Task {
    var title: String
    var isCompleted: Bool

    // Many-to-one: many tasks belong to one project
    var project: Project?

    // Many-to-many: task can have multiple tags
    var tags: [Tag] = []

    init(title: String, project: Project? = nil) {
        self.title = title
        self.isCompleted = false
        self.project = project
    }
}

@Model
final class Tag {
    @Attribute(.unique) var name: String
    var tasks: [Task] = []

    init(name: String) {
        self.name = name
    }
}
```

### Attributes and Constraints

Use `@Attribute` for special properties:

```swift
@Model
final class User {
    // Unique constraint
    @Attribute(.unique) var email: String

    // Spotlight indexing
    @Attribute(.spotlight) var name: String

    // Prevent from being saved
    @Transient var temporaryToken: String?

    // Custom transformation
    @Attribute(.transformable) var metadata: [String: Any]?

    // Original property name for migration
    @Attribute(originalName: "userName") var displayName: String

    init(email: String, name: String, displayName: String) {
        self.email = email
        self.name = name
        self.displayName = displayName
    }
}
```

## Container Setup

### App-Level Configuration

Configure SwiftData container in your app:

```swift
import SwiftUI
import SwiftData

@main
struct TaskApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [Task.self, Project.self, Tag.self])
    }
}

// With configuration
@main
struct TaskApp: App {
    var container: ModelContainer

    init() {
        let schema = Schema([Task.self, Project.self, Tag.self])
        let configuration = ModelConfiguration(
            schema: schema,
            isStoredInMemoryOnly: false,
            allowsSave: true
        )

        do {
            container = try ModelContainer(
                for: schema,
                configurations: configuration
            )
        } catch {
            fatalError("Failed to create container: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(container)
    }
}
```

### Multiple Containers

Use separate containers for different data sets:

```swift
@main
struct MultiContainerApp: App {
    let userContainer: ModelContainer
    let cacheContainer: ModelContainer

    init() {
        do {
            // Persistent user data
            userContainer = try ModelContainer(
                for: User.self,
                configurations: ModelConfiguration(
                    isStoredInMemoryOnly: false
                )
            )

            // In-memory cache
            cacheContainer = try ModelContainer(
                for: CachedItem.self,
                configurations: ModelConfiguration(
                    isStoredInMemoryOnly: true
                )
            )
        } catch {
            fatalError("Container creation failed: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .modelContainer(userContainer)
                .modelContainer(cacheContainer)
        }
    }
}
```

## Querying Data

### Using @Query in Views

Fetch data directly in SwiftUI views:

```swift
struct TaskListView: View {
    // Fetch all tasks
    @Query private var tasks: [Task]

    var body: some View {
        List(tasks) { task in
            TaskRow(task: task)
        }
    }
}

// With sorting
struct SortedTasksView: View {
    @Query(sort: \Task.createdAt, order: .reverse)
    private var tasks: [Task]

    var body: some View {
        List(tasks) { task in
            TaskRow(task: task)
        }
    }
}

// With filter
struct FilteredTasksView: View {
    @Query(filter: #Predicate<Task> { task in
        task.isCompleted == false
    })
    private var incompleteTasks: [Task]

    var body: some View {
        List(incompleteTasks) { task in
            TaskRow(task: task)
        }
    }
}
```

### Dynamic Predicates

Use predicates for complex filtering:

```swift
struct ProjectTasksView: View {
    let project: Project

    @Query private var tasks: [Task]

    init(project: Project) {
        self.project = project

        // Filter tasks by project
        let projectId = project.persistentModelID
        _tasks = Query(filter: #Predicate<Task> { task in
            task.project?.persistentModelID == projectId
        })
    }

    var body: some View {
        List(tasks) { task in
            TaskRow(task: task)
        }
    }
}

// Search functionality
struct SearchableTasksView: View {
    @State private var searchText = ""

    @Query private var allTasks: [Task]

    var filteredTasks: [Task] {
        if searchText.isEmpty {
            return allTasks
        }

        return allTasks.filter { task in
            task.title.localizedStandardContains(searchText)
        }
    }

    var body: some View {
        List(filteredTasks) { task in
            TaskRow(task: task)
        }
        .searchable(text: $searchText)
    }
}
```

### FetchDescriptor for Programmatic Queries

Use `FetchDescriptor` in view models:

```swift
@Observable
final class TaskViewModel {
    var tasks: [Task] = []
    var errorMessage: String?

    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func loadTasks(filter: TaskFilter) async {
        let predicate = switch filter {
        case .all:
            #Predicate<Task> { _ in true }
        case .completed:
            #Predicate<Task> { $0.isCompleted == true }
        case .incomplete:
            #Predicate<Task> { $0.isCompleted == false }
        case .overdue:
            #Predicate<Task> {
                $0.dueDate != nil && $0.dueDate! < Date() && !$0.isCompleted
            }
        }

        var descriptor = FetchDescriptor<Task>(
            predicate: predicate,
            sortBy: [SortDescriptor(\.createdAt, order: .reverse)]
        )

        // Limit results
        descriptor.fetchLimit = 100

        do {
            tasks = try modelContext.fetch(descriptor)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func searchTasks(query: String) async {
        let descriptor = FetchDescriptor<Task>(
            predicate: #Predicate<Task> {
                $0.title.localizedStandardContains(query)
            }
        )

        do {
            tasks = try modelContext.fetch(descriptor)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
```

## Creating, Updating, Deleting

### CRUD Operations

Perform basic operations with `ModelContext`:

```swift
struct TaskEditorView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var title = ""

    var body: some View {
        Form {
            TextField("Task title", text: $title)

            Button("Create Task") {
                createTask()
            }
        }
    }

    private func createTask() {
        let task = Task(title: title)
        modelContext.insert(task)

        // Changes are auto-saved
        // Or explicitly save:
        do {
            try modelContext.save()
        } catch {
            print("Failed to save: \(error)")
        }
    }
}

// Update
struct TaskDetailView: View {
    @Bindable var task: Task

    var body: some View {
        Form {
            TextField("Title", text: $task.title)
            Toggle("Completed", isOn: $task.isCompleted)
        }
        // Changes auto-saved when view disappears
    }
}

// Delete
struct TaskListView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var tasks: [Task]

    var body: some View {
        List {
            ForEach(tasks) { task in
                TaskRow(task: task)
            }
            .onDelete(perform: deleteTasks)
        }
    }

    private func deleteTasks(at offsets: IndexSet) {
        for index in offsets {
            modelContext.delete(tasks[index])
        }
    }
}
```

### Batch Operations

Perform operations on multiple objects:

```swift
@Observable
final class TaskManager {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func completeAll(in project: Project) {
        for task in project.tasks {
            task.isCompleted = true
        }

        do {
            try modelContext.save()
        } catch {
            print("Failed to save: \(error)")
        }
    }

    func deleteCompleted() {
        let descriptor = FetchDescriptor<Task>(
            predicate: #Predicate { $0.isCompleted == true }
        )

        do {
            let completed = try modelContext.fetch(descriptor)
            for task in completed {
                modelContext.delete(task)
            }
            try modelContext.save()
        } catch {
            print("Failed to delete: \(error)")
        }
    }

    func archiveOldProjects() {
        let cutoffDate = Calendar.current.date(
            byAdding: .month,
            value: -6,
            to: Date()
        )!

        let descriptor = FetchDescriptor<Project>(
            predicate: #Predicate { $0.createdAt < cutoffDate }
        )

        do {
            let oldProjects = try modelContext.fetch(descriptor)
            for project in oldProjects {
                project.isArchived = true
            }
            try modelContext.save()
        } catch {
            print("Failed to archive: \(error)")
        }
    }
}
```

## Relationships and Cascading

### Working with Relationships

Manage related objects:

```swift
@Observable
final class ProjectManager {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func createProjectWithTasks(name: String, taskTitles: [String]) {
        let project = Project(name: name)
        modelContext.insert(project)

        for title in taskTitles {
            let task = Task(title: title, project: project)
            modelContext.insert(task)
            // Relationship automatically maintained
        }

        do {
            try modelContext.save()
        } catch {
            print("Failed to save: \(error)")
        }
    }

    func moveTask(_ task: Task, to project: Project) {
        task.project = project
        // SwiftData handles relationship updates
    }

    func addTag(_ tag: Tag, to task: Task) {
        if !task.tags.contains(where: { $0.name == tag.name }) {
            task.tags.append(tag)
        }
    }
}
```

### Delete Rules

Understand cascade deletion:

```swift
@Model
final class Project {
    var name: String

    // Cascade: deleting project deletes all tasks
    @Relationship(deleteRule: .cascade)
    var tasks: [Task] = []

    // Nullify: deleting project sets task.project to nil
    @Relationship(deleteRule: .nullify)
    var owner: User?

    // Deny: cannot delete project if it has tasks
    @Relationship(deleteRule: .deny)
    var criticalDependencies: [Dependency] = []

    init(name: String) {
        self.name = name
    }
}
```

## Model Versioning and Migration

### Schema Versions

Handle model changes:

```swift
// Version 1
@Model
final class Task {
    var title: String
    var isCompleted: Bool

    init(title: String) {
        self.title = title
        self.isCompleted = false
    }
}

// Version 2 - Added priority
@Model
final class Task {
    var title: String
    var isCompleted: Bool
    var priority: Int  // New property

    init(title: String, priority: Int = 0) {
        self.title = title
        self.isCompleted = false
        self.priority = priority
    }
}

// SwiftData handles lightweight migrations automatically
// For complex changes, define custom migration:

enum TaskMigrationPlan: SchemaMigrationPlan {
    static var schemas: [VersionedSchema.Type] {
        [TaskSchemaV1.self, TaskSchemaV2.self]
    }

    static var stages: [MigrationStage] {
        [migrateV1toV2]
    }

    static let migrateV1toV2 = MigrationStage.custom(
        fromVersion: TaskSchemaV1.self,
        toVersion: TaskSchemaV2.self,
        willMigrate: { context in
            // Pre-migration setup
        },
        didMigrate: { context in
            // Set default priority for existing tasks
            let descriptor = FetchDescriptor<Task>()
            let tasks = try context.fetch(descriptor)
            for task in tasks {
                task.priority = 0
            }
            try context.save()
        }
    )
}
```

## Background Operations

### Background Context

Perform heavy operations off the main thread:

```swift
actor DataImporter {
    private let modelContainer: ModelContainer

    init(modelContainer: ModelContainer) {
        self.modelContainer = modelContainer
    }

    func importTasks(from url: URL) async throws {
        // Create background context
        let context = ModelContext(modelContainer)

        // Parse CSV or JSON
        let taskData = try parseFile(at: url)

        // Insert in batches
        for batch in taskData.chunked(into: 100) {
            for data in batch {
                let task = Task(
                    title: data.title,
                    isCompleted: data.isCompleted
                )
                context.insert(task)
            }

            try context.save()
        }
    }

    func exportTasks() async throws -> Data {
        let context = ModelContext(modelContainer)

        let descriptor = FetchDescriptor<Task>(
            sortBy: [SortDescriptor(\.createdAt)]
        )

        let tasks = try context.fetch(descriptor)

        // Convert to exportable format
        return try JSONEncoder().encode(tasks.map { task in
            TaskExportData(
                title: task.title,
                isCompleted: task.isCompleted,
                createdAt: task.createdAt
            )
        })
    }
}
```

## Testing with SwiftData

### In-Memory Container for Tests

Use in-memory storage for tests:

```swift
import Testing
import SwiftData

@Test
func testTaskCreation() async throws {
    // Create in-memory container
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try ModelContainer(
        for: Task.self,
        configurations: config
    )

    let context = ModelContext(container)

    // Test operations
    let task = Task(title: "Test Task")
    context.insert(task)
    try context.save()

    let descriptor = FetchDescriptor<Task>()
    let tasks = try context.fetch(descriptor)

    #expect(tasks.count == 1)
    #expect(tasks.first?.title == "Test Task")
}

@Test
func testTaskCompletion() async throws {
    let container = try ModelContainer(
        for: Task.self,
        configurations: ModelConfiguration(isStoredInMemoryOnly: true)
    )

    let context = ModelContext(container)

    let task = Task(title: "Test")
    context.insert(task)

    task.isCompleted = true
    try context.save()

    #expect(task.isCompleted == true)
}
```

## Anti-Patterns to Avoid

**DON'T fetch in loops:**
```swift
// ❌ BAD - Multiple fetches
for projectId in projectIds {
    let descriptor = FetchDescriptor<Project>(
        predicate: #Predicate { $0.id == projectId }
    )
    let project = try context.fetch(descriptor).first
}

// ✅ GOOD - Single fetch
let descriptor = FetchDescriptor<Project>(
    predicate: #Predicate { projectIds.contains($0.id) }
)
let projects = try context.fetch(descriptor)
```

**DON'T ignore relationship delete rules:**
```swift
// ❌ BAD - Manual deletion
for task in project.tasks {
    context.delete(task)
}
context.delete(project)

// ✅ GOOD - Use cascade
@Relationship(deleteRule: .cascade)
var tasks: [Task] = []

// Then just:
context.delete(project)  // Tasks deleted automatically
```

**DON'T use main context for heavy operations:**
```swift
// ❌ BAD - Blocks UI
func importData() {
    for item in largeDataset {
        let task = Task(title: item.title)
        modelContext.insert(task)
    }
}

// ✅ GOOD - Background context
func importData() async {
    let context = ModelContext(modelContainer)
    for item in largeDataset {
        let task = Task(title: item.title)
        context.insert(task)
    }
    try? context.save()
}
```

## Related Skills

- **swiftui-architecture.md** - Using SwiftData in view models
- **swift-concurrency.md** - Async operations with SwiftData
- **ios-testing.md** - Testing SwiftData models
- **swiftui-navigation.md** - Passing models through navigation
