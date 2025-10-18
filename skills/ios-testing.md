---
name: ios-testing
description: Writing unit tests for iOS/macOS apps
---



# iOS Testing with Swift Testing Framework

**Use this skill when:**
- Writing unit tests for iOS/macOS apps
- Testing async/await code
- Testing SwiftUI views and view models
- Using Swift Testing framework (swift-testing)
- Migrating from XCTest to Swift Testing

## Swift Testing Basics

### Writing Tests

Use `@Test` attribute for test functions:

```swift
import Testing

@Test
func addition() {
    let result = 2 + 2
    #expect(result == 4)
}

@Test("Multiplication works correctly")
func multiplication() {
    #expect(3 * 4 == 12)
}

// Test with custom display name
@Test("String concatenation", .tags(.stringTests))
func stringConcat() {
    let result = "Hello" + " " + "World"
    #expect(result == "Hello World")
}
```

### Expectations

Use `#expect` for assertions:

```swift
@Test
func expectations() {
    // Boolean expectation
    #expect(true)
    #expect(!false)

    // Equality
    #expect(42 == 42)
    #expect("hello" == "hello")

    // Optional unwrapping
    let value: Int? = 42
    #expect(value != nil)

    // Throwing expectation
    #expect(throws: DivisionError.self) {
        try divide(10, by: 0)
    }

    // Non-throwing expectation
    #expect {
        try parseJSON(validData)
    } throws: { error in
        false  // Expect no error
    }
}
```

### Parameterized Tests

Test with multiple inputs:

```swift
@Test(arguments: [1, 2, 3, 4, 5])
func testSquare(number: Int) {
    let result = number * number
    #expect(result == number * number)
}

@Test(arguments: [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("Swift", "SWIFT")
])
func testUppercase(input: String, expected: String) {
    #expect(input.uppercased() == expected)
}

// Multiple parameter sets
@Test(arguments: [1, 2, 3], [10, 20, 30])
func testAddition(a: Int, b: Int) {
    let result = a + b
    #expect(result == a + b)
}
```

## Testing Async Code

### Basic Async Tests

Test async functions:

```swift
@Test
func testAsyncFetch() async throws {
    let service = UserService()
    let user = try await service.fetchUser(id: testUserId)

    #expect(user.name == "Test User")
    #expect(user.email.contains("@"))
}

@Test
func testParallelFetch() async throws {
    let service = UserService()

    async let user1 = service.fetchUser(id: id1)
    async let user2 = service.fetchUser(id: id2)

    let users = try await [user1, user2]

    #expect(users.count == 2)
    #expect(users[0].id != users[1].id)
}
```

### Testing Actors

Test actor state and isolation:

```swift
@Test
func testActorState() async {
    let cache = UserCache()

    await cache.setUser(testUser)
    let retrieved = await cache.getUser(id: testUser.id)

    #expect(retrieved?.id == testUser.id)
    #expect(retrieved?.name == testUser.name)

    await cache.clear()
    let afterClear = await cache.getUser(id: testUser.id)
    #expect(afterClear == nil)
}

@Test
func testConcurrentAccess() async {
    let counter = Counter()

    await withTaskGroup(of: Void.self) { group in
        for _ in 0..<100 {
            group.addTask {
                await counter.increment()
            }
        }
    }

    let final = await counter.value
    #expect(final == 100)
}
```

### Testing with Timeouts

Test time-sensitive code:

```swift
@Test(.timeLimit(.seconds(5)))
func testWithTimeout() async throws {
    let result = try await longRunningOperation()
    #expect(result != nil)
}

@Test
func testOperationCompletes() async throws {
    let start = Date()

    try await Task.sleep(for: .milliseconds(100))

    let elapsed = Date().timeIntervalSince(start)
    #expect(elapsed >= 0.1)
    #expect(elapsed < 0.2)
}
```

## Testing View Models

### Observable View Models

Test SwiftUI view models:

```swift
@Test
func testViewModelLoading() async {
    let mockService = MockUserService()
    mockService.userToReturn = User(id: UUID(), name: "Test")

    let viewModel = UserViewModel(service: mockService)

    #expect(viewModel.user == nil)
    #expect(viewModel.isLoading == false)

    await viewModel.loadUser()

    #expect(viewModel.user != nil)
    #expect(viewModel.user?.name == "Test")
    #expect(viewModel.isLoading == false)
}

@Test
func testViewModelError() async {
    let mockService = MockUserService()
    mockService.shouldThrowError = true

    let viewModel = UserViewModel(service: mockService)

    await viewModel.loadUser()

    #expect(viewModel.user == nil)
    #expect(viewModel.errorMessage != nil)
}
```

### Testing State Changes

Verify state transitions:

```swift
@Observable
final class TaskViewModel {
    enum State {
        case idle
        case loading
        case loaded([Task])
        case error(Error)
    }

    var state: State = .idle

    func load() async {
        state = .loading

        do {
            let tasks = try await fetchTasks()
            state = .loaded(tasks)
        } catch {
            state = .error(error)
        }
    }
}

@Test
func testStateTransitions() async {
    let viewModel = TaskViewModel()

    // Initial state
    if case .idle = viewModel.state {
        // Pass
    } else {
        Issue.record("Expected idle state")
    }

    // Start loading
    Task {
        await viewModel.load()
    }

    // Eventually reaches loaded state
    try await Task.sleep(for: .milliseconds(100))

    if case .loaded(let tasks) = viewModel.state {
        #expect(!tasks.isEmpty)
    } else {
        Issue.record("Expected loaded state")
    }
}
```

## Testing SwiftUI Views

### Snapshot Testing Concept

Test view structure (conceptual, requires snapshot library):

```swift
@Test
func testUserProfileView() {
    let user = User(id: UUID(), name: "Test User", email: "test@example.com")
    let view = UserProfileView(user: user)

    // With snapshot testing library:
    // assertSnapshot(matching: view, as: .image)
}
```

### Testing View Logic

Test extracted view logic:

```swift
struct TaskListView: View {
    let tasks: [Task]

    // Extract filtering logic
    func filteredTasks(searchText: String) -> [Task] {
        guard !searchText.isEmpty else { return tasks }

        return tasks.filter { task in
            task.title.localizedStandardContains(searchText)
        }
    }

    var body: some View {
        List(tasks) { task in
            Text(task.title)
        }
    }
}

@Test
func testTaskFiltering() {
    let tasks = [
        Task(title: "Buy milk"),
        Task(title: "Write code"),
        Task(title: "Buy groceries")
    ]

    let view = TaskListView(tasks: tasks)

    let filtered = view.filteredTasks(searchText: "buy")
    #expect(filtered.count == 2)
    #expect(filtered.allSatisfy { $0.title.lowercased().contains("buy") })
}
```

## Testing Network Code

### Mock Network Service

Create testable network layer:

```swift
protocol NetworkServiceProtocol {
    func fetch<T: Decodable>(url: URL, as type: T.Type) async throws -> T
}

final class MockNetworkService: NetworkServiceProtocol {
    var dataToReturn: Data?
    var errorToThrow: Error?

    func fetch<T: Decodable>(url: URL, as type: T.Type) async throws -> T {
        if let error = errorToThrow {
            throw error
        }

        guard let data = dataToReturn else {
            throw NetworkError.noData
        }

        return try JSONDecoder().decode(T.self, from: data)
    }
}

@Test
func testNetworkSuccess() async throws {
    let mockService = MockNetworkService()
    let userData = """
    {"id": "123", "name": "Test User", "email": "test@example.com"}
    """.data(using: .utf8)!

    mockService.dataToReturn = userData

    let user = try await mockService.fetch(
        url: URL(string: "https://api.example.com/user")!,
        as: User.self
    )

    #expect(user.name == "Test User")
}

@Test
func testNetworkError() async {
    let mockService = MockNetworkService()
    mockService.errorToThrow = NetworkError.serverError

    await #expect(throws: NetworkError.self) {
        try await mockService.fetch(
            url: URL(string: "https://api.example.com/user")!,
            as: User.self
        )
    }
}
```

### Testing with Mock Data

Use mock responses:

```swift
struct MockData {
    static let validUser = """
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test User",
        "email": "test@example.com",
        "createdAt": "2024-01-01T00:00:00Z"
    }
    """.data(using: .utf8)!

    static let usersList = """
    {
        "users": [
            {"id": "550e8400-e29b-41d4-a716-446655440000", "name": "User 1", "email": "user1@example.com"},
            {"id": "550e8400-e29b-41d4-a716-446655440001", "name": "User 2", "email": "user2@example.com"}
        ],
        "total": 2
    }
    """.data(using: .utf8)!

    static let errorResponse = """
    {
        "error": "Not found",
        "code": 404
    }
    """.data(using: .utf8)!
}

@Test
func testUserDecoding() throws {
    let user = try JSONDecoder().decode(User.self, from: MockData.validUser)

    #expect(user.name == "Test User")
    #expect(user.email == "test@example.com")
}
```

## Testing SwiftData Models

### In-Memory Persistence

Test models with in-memory store:

```swift
@Test
func testModelPersistence() async throws {
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try ModelContainer(
        for: Task.self,
        configurations: config
    )

    let context = ModelContext(container)

    // Create
    let task = Task(title: "Test Task")
    context.insert(task)
    try context.save()

    // Fetch
    let descriptor = FetchDescriptor<Task>()
    let tasks = try context.fetch(descriptor)

    #expect(tasks.count == 1)
    #expect(tasks.first?.title == "Test Task")

    // Update
    task.isCompleted = true
    try context.save()

    #expect(task.isCompleted == true)

    // Delete
    context.delete(task)
    try context.save()

    let afterDelete = try context.fetch(descriptor)
    #expect(afterDelete.isEmpty)
}

@Test
func testModelRelationships() throws {
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try ModelContainer(
        for: [Project.self, Task.self],
        configurations: config
    )

    let context = ModelContext(container)

    let project = Project(name: "Test Project")
    context.insert(project)

    let task1 = Task(title: "Task 1", project: project)
    let task2 = Task(title: "Task 2", project: project)

    context.insert(task1)
    context.insert(task2)

    try context.save()

    #expect(project.tasks.count == 2)
    #expect(task1.project?.name == "Test Project")
}
```

## Test Organization

### Test Suites

Group related tests:

```swift
@Suite("User Management Tests")
struct UserTests {
    @Test("Create user")
    func createUser() async throws {
        // Test implementation
    }

    @Test("Update user")
    func updateUser() async throws {
        // Test implementation
    }

    @Test("Delete user")
    func deleteUser() async throws {
        // Test implementation
    }
}

@Suite("Authentication Tests", .tags(.auth))
struct AuthTests {
    @Test
    func login() async throws {
        // Test implementation
    }

    @Test
    func logout() async throws {
        // Test implementation
    }
}
```

### Tags for Organization

Use tags to categorize tests:

```swift
extension Tag {
    @Tag static var unit: Self
    @Tag static var integration: Self
    @Tag static var ui: Self
    @Tag static var network: Self
    @Tag static var slow: Self
}

@Test(.tags(.unit, .network))
func testAPIClient() async throws {
    // Network unit test
}

@Test(.tags(.integration, .slow))
func testFullUserFlow() async throws {
    // Integration test
}
```

### Setup and Teardown

Initialize test state:

```swift
@Suite("Database Tests")
struct DatabaseTests {
    var container: ModelContainer

    init() throws {
        let config = ModelConfiguration(isStoredInMemoryOnly: true)
        container = try ModelContainer(
            for: Task.self,
            configurations: config
        )
    }

    @Test
    func testOperation1() throws {
        let context = ModelContext(container)
        // Test using context
    }

    @Test
    func testOperation2() throws {
        let context = ModelContext(container)
        // Test using context
    }
}
```

## Testing Best Practices

### AAA Pattern

Use Arrange-Act-Assert:

```swift
@Test
func testUserCreation() async throws {
    // Arrange
    let mockService = MockUserService()
    let viewModel = UserViewModel(service: mockService)

    // Act
    await viewModel.createUser(name: "Test", email: "test@example.com")

    // Assert
    #expect(viewModel.user?.name == "Test")
    #expect(viewModel.user?.email == "test@example.com")
}
```

### Test Isolation

Keep tests independent:

```swift
@Suite
struct IsolatedTests {
    @Test
    func test1() async throws {
        // Create own test data
        let data = TestData()
        // Test with data
    }

    @Test
    func test2() async throws {
        // Create own test data (don't reuse from test1)
        let data = TestData()
        // Test with data
    }
}
```

### Descriptive Test Names

Write clear test names:

```swift
// ❌ BAD
@Test func test1() { }
@Test func testUser() { }

// ✅ GOOD
@Test("User is created with valid email")
func userCreationWithValidEmail() { }

@Test("Login fails with invalid credentials")
func loginFailureWithInvalidCredentials() { }
```

## Anti-Patterns to Avoid

**DON'T test implementation details:**
```swift
// ❌ BAD - Testing private implementation
@Test
func testInternalCache() {
    // Don't test internal caching mechanism
}

// ✅ GOOD - Test public behavior
@Test
func testDataFetchingReturnsCorrectData() async throws {
    let data = try await service.fetchData()
    #expect(data.count > 0)
}
```

**DON'T write dependent tests:**
```swift
// ❌ BAD - Test depends on order
var sharedState: User?

@Test
func test1() {
    sharedState = User(name: "Test")
}

@Test
func test2() {
    #expect(sharedState?.name == "Test")  // Fragile!
}

// ✅ GOOD - Independent tests
@Test
func test1() {
    let user = User(name: "Test")
    #expect(user.name == "Test")
}

@Test
func test2() {
    let user = User(name: "Another")
    #expect(user.name == "Another")
}
```

**DON'T ignore async context:**
```swift
// ❌ BAD - Not awaiting async work
@Test
func badAsyncTest() {
    Task {
        let user = try await fetchUser()
        #expect(user != nil)  // May not execute!
    }
}

// ✅ GOOD
@Test
func goodAsyncTest() async throws {
    let user = try await fetchUser()
    #expect(user != nil)
}
```

## Related Skills

- **swiftui-architecture.md** - Testing view models
- **swift-concurrency.md** - Testing actors and async code
- **swiftdata-persistence.md** - Testing data models
- **ios-networking.md** - Mocking network services
- **swiftui-navigation.md** - Testing navigation flows
