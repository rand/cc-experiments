---
name: swift-concurrency
description: Working with async/await in Swift
---



# Swift Concurrency Patterns

**Use this skill when:**
- Working with async/await in Swift
- Implementing actors for thread-safe state
- Managing concurrent tasks and task groups
- Migrating to Swift 6 strict concurrency checking
- Building concurrent iOS/macOS applications

## Async/Await Fundamentals

### Basic Async Functions

Define async functions with `async` keyword:

```swift
// Simple async function
func fetchUser(id: UUID) async throws -> User {
    let url = URL(string: "https://api.example.com/users/\(id)")!
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(User.self, from: data)
}

// Calling async functions
func loadUserData() async {
    do {
        let user = try await fetchUser(id: currentUserId)
        print("Loaded user: \(user.name)")
    } catch {
        print("Failed to load user: \(error)")
    }
}
```

### Parallel Async Operations

Use `async let` for concurrent execution:

```swift
func loadDashboardData() async throws -> DashboardData {
    // All three requests start simultaneously
    async let user = fetchUser(id: currentUserId)
    async let posts = fetchPosts(userId: currentUserId)
    async let notifications = fetchNotifications()

    // Wait for all to complete
    return try await DashboardData(
        user: user,
        posts: posts,
        notifications: notifications
    )
}
```

### Sequential vs Parallel Execution

Understand the difference:

```swift
// Sequential - takes 6 seconds total
func sequential() async throws {
    let user1 = try await fetchUser(id: id1)      // 2 seconds
    let user2 = try await fetchUser(id: id2)      // 2 seconds
    let user3 = try await fetchUser(id: id3)      // 2 seconds
}

// Parallel - takes 2 seconds total
func parallel() async throws {
    async let user1 = fetchUser(id: id1)
    async let user2 = fetchUser(id: id2)
    async let user3 = fetchUser(id: id3)

    let users = try await [user1, user2, user3]
}
```

## Actors: Thread-Safe State Management

### Basic Actor Usage

Use actors for mutable state accessed from multiple contexts:

```swift
actor UserCache {
    private var cache: [UUID: User] = [:]

    func getUser(id: UUID) -> User? {
        cache[id]
    }

    func setUser(_ user: User) {
        cache[user.id] = user
    }

    func clear() {
        cache.removeAll()
    }
}

// Usage
let cache = UserCache()

// All access is automatically serialized
await cache.setUser(user)
let cachedUser = await cache.getUser(id: userId)
```

### Actor Isolation

Understand actor isolation rules:

```swift
actor DatabaseManager {
    private var connection: DatabaseConnection?

    // Synchronous - can access actor state directly
    private func isConnected() -> Bool {
        connection != nil
    }

    // Async - can be called from outside actor
    func connect() async throws {
        guard !isConnected() else { return }
        connection = try await DatabaseConnection.establish()
    }

    func executeQuery(_ query: String) async throws -> [Row] {
        guard isConnected() else {
            throw DatabaseError.notConnected
        }
        return try await connection!.execute(query)
    }
}
```

### Nonisolated Functions

Use `nonisolated` for functions that don't need actor isolation:

```swift
actor AnalyticsService {
    private var events: [Event] = []

    func track(_ event: Event) {
        events.append(event)
    }

    // No await needed to call this
    nonisolated func generateEventId() -> UUID {
        UUID()
    }

    // Computed property can be nonisolated
    nonisolated var serviceVersion: String {
        "1.0.0"
    }
}

// Usage
let analytics = AnalyticsService()
let id = analytics.generateEventId()  // No await needed
```

### @MainActor for UI Updates

Use `@MainActor` to ensure UI updates on main thread:

```swift
@MainActor
final class UserProfileViewModel: ObservableObject {
    @Published var user: User?
    @Published var isLoading = false

    // All methods run on main actor by default
    func loadUser(id: UUID) async {
        isLoading = true

        do {
            // This async call runs on background
            user = try await UserService.shared.fetchUser(id: id)
        } catch {
            // Error handling still on main actor
            showError(error)
        }

        isLoading = false
    }

    private func showError(_ error: Error) {
        // UI update - guaranteed on main thread
    }
}
```

### Mixing MainActor and Background Work

Explicitly switch execution contexts:

```swift
@MainActor
final class ImageProcessor {
    var processedImage: UIImage?

    func processImage(_ image: UIImage) async {
        // Start on MainActor
        processedImage = nil

        // Switch to background for heavy work
        let processed = await Task.detached {
            // Expensive image processing
            return self.applyFilters(to: image)
        }.value

        // Back on MainActor for UI update
        processedImage = processed
    }

    nonisolated private func applyFilters(to image: UIImage) -> UIImage {
        // CPU-intensive work
        // Not on MainActor
        return image
    }
}
```

## Task Management

### Creating Tasks

Use `Task` for unstructured concurrency:

```swift
// Fire-and-forget task
Task {
    await performBackgroundWork()
}

// Task with priority
Task(priority: .background) {
    await syncData()
}

// Task with value
let task = Task { () -> String in
    try await fetchData()
    return "Complete"
}
let result = await task.value
```

### Task Cancellation

Check for cancellation in long-running tasks:

```swift
func processLargeDataset(_ items: [Item]) async throws {
    for item in items {
        // Check if task was cancelled
        try Task.checkCancellation()

        await process(item)
    }
}

// Alternative using isCancelled
func continuousPolling() async {
    while !Task.isCancelled {
        await fetchUpdates()
        try? await Task.sleep(for: .seconds(5))
    }
}

// Cancel a task
let task = Task {
    await longRunningOperation()
}

// Later...
task.cancel()
```

### Task Groups for Dynamic Concurrency

Use task groups for variable number of concurrent operations:

```swift
func fetchAllUsers(ids: [UUID]) async throws -> [User] {
    try await withThrowingTaskGroup(of: User.self) { group in
        // Add a task for each user ID
        for id in ids {
            group.addTask {
                try await fetchUser(id: id)
            }
        }

        // Collect results as they complete
        var users: [User] = []
        for try await user in group {
            users.append(user)
        }

        return users
    }
}

// Non-throwing variant
func fetchImages(urls: [URL]) async -> [UIImage?] {
    await withTaskGroup(of: UIImage?.self) { group in
        for url in urls {
            group.addTask {
                try? await downloadImage(from: url)
            }
        }

        var images: [UIImage?] = []
        for await image in group {
            images.append(image)
        }

        return images
    }
}
```

### Task Group with Cancellation

Cancel remaining tasks when one succeeds:

```swift
func fetchFromFastestMirror(mirrors: [URL]) async throws -> Data {
    try await withThrowingTaskGroup(of: Data.self) { group in
        for mirror in mirrors {
            group.addTask {
                try await URLSession.shared.data(from: mirror).0
            }
        }

        // Get first successful result
        guard let data = try await group.next() else {
            throw NetworkError.noMirrors
        }

        // Cancel remaining tasks
        group.cancelAll()

        return data
    }
}
```

## Swift 6 Concurrency Safety

### Sendable Types

Mark types as `Sendable` to allow safe cross-actor passing:

```swift
// Value types are implicitly Sendable
struct User: Sendable {
    let id: UUID
    let name: String
}

// Reference types need explicit conformance
final class NetworkClient: Sendable {
    let baseURL: URL
    let session: URLSession  // URLSession is Sendable

    init(baseURL: URL) {
        self.baseURL = baseURL
        self.session = URLSession.shared
    }
}

// Use @unchecked Sendable carefully
final class LegacyCache: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [String: Any] = [:]

    func get(_ key: String) -> Any? {
        lock.lock()
        defer { lock.unlock() }
        return storage[key]
    }

    func set(_ key: String, value: Any) {
        lock.lock()
        defer { lock.unlock() }
        storage[key] = value
    }
}
```

### Avoiding Data Races

Eliminate data races with proper isolation:

```swift
// ❌ BAD - Data race possible
class BadCounter {
    var count = 0

    func increment() {
        count += 1  // Not thread-safe!
    }
}

// ✅ GOOD - Actor ensures safety
actor GoodCounter {
    var count = 0

    func increment() {
        count += 1  // Thread-safe
    }

    func getCount() -> Int {
        count
    }
}

// ✅ ALSO GOOD - Immutable value type
struct CounterState: Sendable {
    let count: Int

    func incremented() -> CounterState {
        CounterState(count: count + 1)
    }
}
```

### Global Actor Isolation

Create custom global actors for domain-specific isolation:

```swift
@globalActor
actor DatabaseActor {
    static let shared = DatabaseActor()
}

@DatabaseActor
func executeQuery(_ sql: String) async throws -> [Row] {
    // All calls to this function are serialized
    return try await database.execute(sql)
}

@DatabaseActor
final class DatabaseService {
    // All methods isolated to DatabaseActor
    private var connection: Connection?

    func connect() async throws {
        connection = try await Connection.establish()
    }

    func query(_ sql: String) async throws -> [Row] {
        try await connection!.execute(sql)
    }
}
```

## Common Patterns

### Network Service Actor

Build thread-safe network services:

```swift
actor NetworkService {
    private let session: URLSession
    private var cache: [URL: CachedResponse] = [:]

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetch<T: Decodable>(_ url: URL) async throws -> T {
        // Check cache
        if let cached = cache[url], !cached.isExpired {
            if let data = cached.data as? T {
                return data
            }
        }

        // Fetch from network
        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.invalidResponse
        }

        let decoded = try JSONDecoder().decode(T.self, from: data)

        // Update cache
        cache[url] = CachedResponse(data: decoded, timestamp: Date())

        return decoded
    }

    func clearCache() {
        cache.removeAll()
    }
}
```

### Async Sequence Processing

Work with `AsyncSequence` for streaming data:

```swift
func processNotifications() async {
    let stream = NotificationCenter.default.notifications(
        named: .dataUpdated
    )

    for await notification in stream {
        await handleUpdate(notification)

        if Task.isCancelled {
            break
        }
    }
}

// Custom async sequence
struct NumberSequence: AsyncSequence {
    typealias Element = Int
    let range: Range<Int>

    struct AsyncIterator: AsyncIteratorProtocol {
        var current: Int
        let end: Int

        mutating func next() async -> Int? {
            guard current < end else { return nil }

            try? await Task.sleep(for: .milliseconds(100))

            defer { current += 1 }
            return current
        }
    }

    func makeAsyncIterator() -> AsyncIterator {
        AsyncIterator(current: range.lowerBound, end: range.upperBound)
    }
}

// Usage
for await number in NumberSequence(range: 0..<10) {
    print(number)
}
```

### Combining Multiple Async Sequences

Merge multiple streams:

```swift
func monitorAllSources() async {
    await withTaskGroup(of: Void.self) { group in
        group.addTask {
            for await event in source1.events {
                await handle(event)
            }
        }

        group.addTask {
            for await event in source2.events {
                await handle(event)
            }
        }

        group.addTask {
            for await event in source3.events {
                await handle(event)
            }
        }
    }
}
```

## Testing Async Code

### Testing Async Functions

Use async test functions:

```swift
import Testing

@Test
func testUserFetch() async throws {
    let service = UserService()
    let user = try await service.fetchUser(id: testUserId)

    #expect(user.name == "Test User")
}

@Test
func testConcurrentFetch() async throws {
    let service = UserService()

    // Test parallel execution
    async let user1 = service.fetchUser(id: id1)
    async let user2 = service.fetchUser(id: id2)

    let users = try await [user1, user2]
    #expect(users.count == 2)
}
```

### Testing Actors

Test actor state changes:

```swift
@Test
func testCacheActor() async {
    let cache = UserCache()

    await cache.setUser(testUser)
    let retrieved = await cache.getUser(id: testUser.id)

    #expect(retrieved?.id == testUser.id)

    await cache.clear()
    let afterClear = await cache.getUser(id: testUser.id)
    #expect(afterClear == nil)
}
```

## Anti-Patterns to Avoid

**DON'T block async code:**
```swift
// ❌ BAD - Blocking async context
func bad() async {
    Thread.sleep(forTimeInterval: 2)  // Blocks thread!
}

// ✅ GOOD
func good() async throws {
    try await Task.sleep(for: .seconds(2))
}
```

**DON'T use DispatchQueue.main.async in async contexts:**
```swift
// ❌ BAD
func updateUI() async {
    DispatchQueue.main.async {
        self.label.text = "Updated"
    }
}

// ✅ GOOD
@MainActor
func updateUI() {
    label.text = "Updated"
}
```

**DON'T create detached tasks unnecessarily:**
```swift
// ❌ BAD - Loses task hierarchy
Task.detached {
    await someWork()
}

// ✅ GOOD - Inherits priority and cancellation
Task {
    await someWork()
}
```

**DON'T ignore task cancellation:**
```swift
// ❌ BAD - Keeps running after cancellation
func processItems(_ items: [Item]) async {
    for item in items {
        await process(item)  // Never checks cancellation
    }
}

// ✅ GOOD
func processItems(_ items: [Item]) async throws {
    for item in items {
        try Task.checkCancellation()
        await process(item)
    }
}
```

## Related Skills

- **swiftui-architecture.md** - Using actors and async in view models
- **ios-networking.md** - Network service actors, async URLSession
- **swiftdata-persistence.md** - Async database operations
- **ios-testing.md** - Testing async code and actors
- **swiftui-navigation.md** - Async navigation flows
