---
name: swiftui-architecture
description: Building iOS/macOS apps with SwiftUI
---



# SwiftUI Architecture Patterns

**Use this skill when:**
- Building iOS/macOS apps with SwiftUI
- Implementing MVVM architecture patterns
- Managing state with @Observable, @State, @Binding
- Organizing SwiftUI views and view models
- Designing clean separation of concerns in SwiftUI apps

## Core Architecture: MVVM with Observation Framework

SwiftUI apps use Model-View-ViewModel (MVVM) architecture with Swift's Observation framework for reactive state management.

### The Three Layers

```swift
// MODEL: Pure data and business logic
struct User: Codable, Identifiable {
    let id: UUID
    var name: String
    var email: String
}

// VIEW MODEL: Observable state container
@Observable
final class UserProfileViewModel {
    var user: User?
    var isLoading = false
    var errorMessage: String?

    private let userService: UserService

    init(userService: UserService = .shared) {
        self.userService = userService
    }

    func loadUser(id: UUID) async {
        isLoading = true
        errorMessage = nil

        do {
            user = try await userService.fetchUser(id: id)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func updateName(_ newName: String) async throws {
        guard var user else { return }
        user.name = newName

        let updatedUser = try await userService.updateUser(user)
        self.user = updatedUser
    }
}

// VIEW: UI presentation
struct UserProfileView: View {
    @State private var viewModel = UserProfileViewModel()
    let userId: UUID

    var body: some View {
        Group {
            if viewModel.isLoading {
                ProgressView()
            } else if let user = viewModel.user {
                UserDetailView(user: user, viewModel: viewModel)
            } else if let error = viewModel.errorMessage {
                ErrorView(message: error)
            }
        }
        .task {
            await viewModel.loadUser(id: userId)
        }
    }
}
```

## State Management Patterns

### @Observable: Primary State Container

Use `@Observable` macro for view models (Swift 5.9+):

```swift
@Observable
final class DashboardViewModel {
    var items: [Item] = []
    var searchQuery = ""
    var selectedFilter: FilterType = .all

    // Computed properties automatically trigger view updates
    var filteredItems: [Item] {
        items.filter { item in
            (searchQuery.isEmpty || item.title.contains(searchQuery)) &&
            (selectedFilter == .all || item.category == selectedFilter)
        }
    }

    func loadItems() async throws {
        items = try await ItemService.shared.fetchItems()
    }
}

struct DashboardView: View {
    @State private var viewModel = DashboardViewModel()

    var body: some View {
        List(viewModel.filteredItems) { item in
            ItemRow(item: item)
        }
        .searchable(text: $viewModel.searchQuery)
        .task {
            try? await viewModel.loadItems()
        }
    }
}
```

### @State: View-Local State

Use `@State` for simple view-local state:

```swift
struct ToggleView: View {
    @State private var isExpanded = false
    @State private var selectedTab = 0

    var body: some View {
        VStack {
            Picker("Tab", selection: $selectedTab) {
                Text("First").tag(0)
                Text("Second").tag(1)
            }

            if isExpanded {
                DetailContentView()
            }

            Button(isExpanded ? "Collapse" : "Expand") {
                withAnimation {
                    isExpanded.toggle()
                }
            }
        }
    }
}
```

### @Binding: Two-Way Data Flow

Use `@Binding` to pass mutable state to child views:

```swift
struct SettingsForm: View {
    @Binding var settings: AppSettings

    var body: some View {
        Form {
            Toggle("Enable Notifications", isOn: $settings.notificationsEnabled)
            Picker("Theme", selection: $settings.theme) {
                Text("Light").tag(Theme.light)
                Text("Dark").tag(Theme.dark)
                Text("Auto").tag(Theme.auto)
            }
        }
    }
}

struct SettingsView: View {
    @State private var settings = AppSettings()

    var body: some View {
        SettingsForm(settings: $settings)
            .onChange(of: settings) { oldValue, newValue in
                saveSettings(newValue)
            }
    }
}
```

### @Environment: Dependency Injection

Use `@Environment` for cross-cutting concerns:

```swift
// Define environment key
private struct UserServiceKey: EnvironmentKey {
    static let defaultValue: UserService = .shared
}

extension EnvironmentValues {
    var userService: UserService {
        get { self[UserServiceKey.self] }
        set { self[UserServiceKey.self] = newValue }
    }
}

// Inject in view
struct ContentView: View {
    @Environment(\.userService) private var userService

    var body: some View {
        Text("Using userService")
    }
}

// Provide at app level
@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.userService, UserService.shared)
        }
    }
}
```

## View Composition Patterns

### Extract Subviews for Reusability

Break complex views into focused components:

```swift
struct ProductListView: View {
    @State private var viewModel = ProductListViewModel()

    var body: some View {
        List {
            SearchBarSection(query: $viewModel.searchQuery)

            FilterSection(
                selectedFilter: $viewModel.selectedFilter,
                availableFilters: viewModel.availableFilters
            )

            ProductsSection(
                products: viewModel.filteredProducts,
                onSelect: viewModel.selectProduct
            )
        }
    }
}

private struct SearchBarSection: View {
    @Binding var query: String

    var body: some View {
        Section {
            TextField("Search products", text: $query)
                .textFieldStyle(.roundedBorder)
        }
    }
}

private struct ProductsSection: View {
    let products: [Product]
    let onSelect: (Product) -> Void

    var body: some View {
        Section {
            ForEach(products) { product in
                ProductRow(product: product)
                    .onTapGesture {
                        onSelect(product)
                    }
            }
        }
    }
}
```

### ViewBuilder for Conditional Content

Use `@ViewBuilder` for flexible content composition:

```swift
struct Card<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)

            content()
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(radius: 2)
    }
}

// Usage
Card(title: "User Info") {
    Text("Name: \(user.name)")
    Text("Email: \(user.email)")
}

Card(title: "Stats") {
    HStack {
        StatView(label: "Posts", value: stats.posts)
        StatView(label: "Followers", value: stats.followers)
    }
}
```

## Dependency Management

### Constructor Injection

Pass dependencies through initializers:

```swift
@Observable
final class OrderViewModel {
    var orders: [Order] = []

    private let orderService: OrderService
    private let analyticsService: AnalyticsService

    init(
        orderService: OrderService,
        analyticsService: AnalyticsService = .shared
    ) {
        self.orderService = orderService
        self.analyticsService = analyticsService
    }

    func loadOrders() async throws {
        orders = try await orderService.fetchOrders()
        analyticsService.track("orders_loaded", count: orders.count)
    }
}

struct OrderListView: View {
    @State private var viewModel: OrderViewModel

    init(orderService: OrderService = .shared) {
        _viewModel = State(initialValue: OrderViewModel(orderService: orderService))
    }

    var body: some View {
        List(viewModel.orders) { order in
            OrderRow(order: order)
        }
        .task {
            try? await viewModel.loadOrders()
        }
    }
}
```

### Protocol-Based Dependencies

Use protocols for testability:

```swift
protocol AuthServiceProtocol {
    func login(email: String, password: String) async throws -> User
    func logout() async throws
    var currentUser: User? { get }
}

@Observable
final class AuthViewModel {
    var currentUser: User?
    var isLoading = false
    var errorMessage: String?

    private let authService: AuthServiceProtocol

    init(authService: AuthServiceProtocol) {
        self.authService = authService
        self.currentUser = authService.currentUser
    }

    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            currentUser = try await authService.login(email: email, password: password)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}
```

## Loading, Error, and Empty States

Always handle all UI states explicitly:

```swift
@Observable
final class ContentViewModel {
    enum LoadingState {
        case idle
        case loading
        case loaded([Item])
        case error(Error)
    }

    var state: LoadingState = .idle

    func load() async {
        state = .loading

        do {
            let items = try await fetchItems()
            state = items.isEmpty ? .loaded([]) : .loaded(items)
        } catch {
            state = .error(error)
        }
    }
}

struct ContentView: View {
    @State private var viewModel = ContentViewModel()

    var body: some View {
        Group {
            switch viewModel.state {
            case .idle:
                Color.clear
                    .onAppear {
                        Task { await viewModel.load() }
                    }

            case .loading:
                ProgressView("Loading...")

            case .loaded(let items) where items.isEmpty:
                EmptyStateView(
                    title: "No Items",
                    message: "Add your first item to get started",
                    action: { viewModel.showAddItem() }
                )

            case .loaded(let items):
                ItemListView(items: items)

            case .error(let error):
                ErrorView(
                    error: error,
                    retry: { Task { await viewModel.load() } }
                )
            }
        }
        .animation(.default, value: viewModel.state)
    }
}
```

## Testing View Models

Structure view models for testability:

```swift
// Production service
actor ProductService: ProductServiceProtocol {
    func fetchProducts() async throws -> [Product] {
        // Network call
    }
}

// Test mock
final class MockProductService: ProductServiceProtocol {
    var productsToReturn: [Product] = []
    var shouldThrowError = false

    func fetchProducts() async throws -> [Product] {
        if shouldThrowError {
            throw NSError(domain: "test", code: -1)
        }
        return productsToReturn
    }
}

// Test
@Test
func testProductLoadingSuccess() async throws {
    let mockService = MockProductService()
    mockService.productsToReturn = [
        Product(id: 1, name: "Test Product")
    ]

    let viewModel = ProductViewModel(service: mockService)
    await viewModel.loadProducts()

    #expect(viewModel.products.count == 1)
    #expect(viewModel.errorMessage == nil)
}
```

## Anti-Patterns to Avoid

**DON'T put business logic in views:**
```swift
// ❌ BAD
struct UserView: View {
    @State private var user: User?

    var body: some View {
        Text(user?.name ?? "")
            .task {
                // Business logic in view!
                let url = URL(string: "https://api.example.com/user")!
                let (data, _) = try await URLSession.shared.data(from: url)
                user = try JSONDecoder().decode(User.self, from: data)
            }
    }
}

// ✅ GOOD
struct UserView: View {
    @State private var viewModel = UserViewModel()

    var body: some View {
        Text(viewModel.user?.name ?? "")
            .task {
                await viewModel.loadUser()
            }
    }
}
```

**DON'T use @StateObject or @ObservedObject with @Observable:**
```swift
// ❌ BAD - @Observable doesn't need @StateObject
@StateObject private var viewModel = MyViewModel()

// ✅ GOOD
@State private var viewModel = MyViewModel()
```

**DON'T make view models reference views:**
```swift
// ❌ BAD - Creates retain cycles
@Observable
final class BadViewModel {
    weak var view: SomeView?
}

// ✅ GOOD - Use callbacks or published state
@Observable
final class GoodViewModel {
    var onComplete: (() -> Void)?
    var shouldDismiss = false
}
```

## Related Skills

- **swift-concurrency.md** - async/await patterns, actors, Swift 6 concurrency
- **swiftdata-persistence.md** - Persisting view model state
- **swiftui-navigation.md** - Passing view models through navigation
- **ios-networking.md** - Network layer for view models
- **ios-testing.md** - Testing SwiftUI views and view models
