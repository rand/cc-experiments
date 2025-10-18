---
name: swiftui-navigation
description: Implementing navigation in iOS 17+ apps
---



# SwiftUI Navigation Patterns

**Use this skill when:**
- Implementing navigation in iOS 17+ apps
- Building type-safe navigation flows
- Managing navigation state programmatically
- Creating deep linking and universal links
- Handling complex navigation hierarchies

## NavigationStack Fundamentals

### Basic Navigation

Use `NavigationStack` for hierarchical navigation:

```swift
struct RootView: View {
    var body: some View {
        NavigationStack {
            List {
                NavigationLink("Settings") {
                    SettingsView()
                }

                NavigationLink("Profile") {
                    ProfileView()
                }
            }
            .navigationTitle("Home")
        }
    }
}
```

### Programmatic Navigation

Control navigation with path binding:

```swift
@Observable
final class NavigationCoordinator {
    var path: NavigationPath = NavigationPath()

    func navigateToProfile() {
        path.append(Route.profile)
    }

    func navigateToSettings() {
        path.append(Route.settings)
    }

    func popToRoot() {
        path.removeLast(path.count)
    }

    func goBack() {
        if !path.isEmpty {
            path.removeLast()
        }
    }
}

enum Route: Hashable {
    case profile
    case settings
    case userDetail(userId: UUID)
    case editTask(taskId: UUID)
}

struct ContentView: View {
    @State private var coordinator = NavigationCoordinator()

    var body: some View {
        NavigationStack(path: $coordinator.path) {
            HomeView()
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .profile:
                        ProfileView()
                    case .settings:
                        SettingsView()
                    case .userDetail(let userId):
                        UserDetailView(userId: userId)
                    case .editTask(let taskId):
                        TaskEditorView(taskId: taskId)
                    }
                }
        }
        .environment(coordinator)
    }
}

// Usage in child view
struct HomeView: View {
    @Environment(NavigationCoordinator.self) private var coordinator

    var body: some View {
        Button("Go to Profile") {
            coordinator.navigateToProfile()
        }
    }
}
```

## Type-Safe Navigation

### Value-Based Navigation

Navigate with type-safe routes:

```swift
// Define navigation routes
enum AppRoute: Hashable {
    case home
    case userList
    case userDetail(User)
    case taskList(projectId: UUID)
    case taskDetail(Task)
    case settings
}

@Observable
final class AppNavigator {
    var path: [AppRoute] = []

    func navigate(to route: AppRoute) {
        path.append(route)
    }

    func navigateToUser(_ user: User) {
        path.append(.userDetail(user))
    }

    func navigateToTask(_ task: Task) {
        path.append(.taskDetail(task))
    }

    func pop() {
        if !path.isEmpty {
            path.removeLast()
        }
    }

    func popToRoot() {
        path.removeAll()
    }

    func popTo(_ route: AppRoute) {
        guard let index = path.firstIndex(of: route) else { return }
        path.removeLast(path.count - index - 1)
    }
}

struct AppView: View {
    @State private var navigator = AppNavigator()

    var body: some View {
        NavigationStack(path: $navigator.path) {
            RootView()
                .navigationDestination(for: AppRoute.self) { route in
                    routeView(for: route)
                }
        }
        .environment(navigator)
    }

    @ViewBuilder
    private func routeView(for route: AppRoute) -> some View {
        switch route {
        case .home:
            HomeView()
        case .userList:
            UserListView()
        case .userDetail(let user):
            UserDetailView(user: user)
        case .taskList(let projectId):
            TaskListView(projectId: projectId)
        case .taskDetail(let task):
            TaskDetailView(task: task)
        case .settings:
            SettingsView()
        }
    }
}
```

### NavigationPath for Mixed Types

Handle heterogeneous navigation paths:

```swift
struct MixedNavigationView: View {
    @State private var path = NavigationPath()

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Button("Show String") {
                    path.append("Hello")
                }

                Button("Show Number") {
                    path.append(42)
                }

                Button("Show User") {
                    path.append(User.sample)
                }
            }
            .navigationDestination(for: String.self) { text in
                Text("String: \(text)")
            }
            .navigationDestination(for: Int.self) { number in
                Text("Number: \(number)")
            }
            .navigationDestination(for: User.self) { user in
                UserDetailView(user: user)
            }
        }
    }
}
```

## Deep Linking and URL Handling

### URL-Based Navigation

Handle deep links and universal links:

```swift
@Observable
final class DeepLinkHandler {
    var path: NavigationPath = NavigationPath()

    func handle(_ url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            return
        }

        // Parse URL: myapp://user/123
        let pathComponents = components.path.components(separatedBy: "/")

        switch pathComponents.first {
        case "user":
            if let userId = pathComponents.dropFirst().first,
               let uuid = UUID(uuidString: userId) {
                path.append(Route.userDetail(userId: uuid))
            }

        case "task":
            if let taskId = pathComponents.dropFirst().first,
               let uuid = UUID(uuidString: taskId) {
                path.append(Route.taskDetail(taskId: uuid))
            }

        case "settings":
            path.append(Route.settings)

        default:
            break
        }
    }
}

@main
struct MyApp: App {
    @State private var deepLinkHandler = DeepLinkHandler()

    var body: some Scene {
        WindowGroup {
            NavigationStack(path: $deepLinkHandler.path) {
                HomeView()
                    .navigationDestination(for: Route.self) { route in
                        routeView(for: route)
                    }
            }
            .onOpenURL { url in
                deepLinkHandler.handle(url)
            }
        }
    }

    @ViewBuilder
    private func routeView(for route: Route) -> some View {
        // Route implementation
    }
}
```

### Query Parameter Handling

Parse URL query parameters:

```swift
extension DeepLinkHandler {
    func handleWithQuery(_ url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            return
        }

        // Parse: myapp://search?q=swift&category=ios
        let queryItems = components.queryItems ?? []

        if components.path == "/search" {
            let query = queryItems.first { $0.name == "q" }?.value ?? ""
            let category = queryItems.first { $0.name == "category" }?.value

            path.append(Route.search(query: query, category: category))
        }
    }
}
```

## Tab-Based Navigation

### NavigationStack in Tabs

Combine tabs with navigation:

```swift
struct TabNavigationView: View {
    @State private var selectedTab = 0
    @State private var homePath = NavigationPath()
    @State private var searchPath = NavigationPath()
    @State private var profilePath = NavigationPath()

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack(path: $homePath) {
                HomeView()
                    .navigationDestination(for: Route.self) { route in
                        routeView(for: route)
                    }
            }
            .tabItem {
                Label("Home", systemImage: "house")
            }
            .tag(0)

            NavigationStack(path: $searchPath) {
                SearchView()
                    .navigationDestination(for: Route.self) { route in
                        routeView(for: route)
                    }
            }
            .tabItem {
                Label("Search", systemImage: "magnifyingglass")
            }
            .tag(1)

            NavigationStack(path: $profilePath) {
                ProfileView()
                    .navigationDestination(for: Route.self) { route in
                        routeView(for: route)
                    }
            }
            .tabItem {
                Label("Profile", systemImage: "person")
            }
            .tag(2)
        }
    }

    @ViewBuilder
    private func routeView(for route: Route) -> some View {
        // Shared route handling
    }
}
```

### Preserving Tab State

Maintain navigation state per tab:

```swift
@Observable
final class TabCoordinator {
    var selectedTab: Tab = .home
    var homePath: [Route] = []
    var searchPath: [Route] = []
    var profilePath: [Route] = []

    var currentPath: Binding<[Route]> {
        switch selectedTab {
        case .home:
            return Binding(
                get: { self.homePath },
                set: { self.homePath = $0 }
            )
        case .search:
            return Binding(
                get: { self.searchPath },
                set: { self.searchPath = $0 }
            )
        case .profile:
            return Binding(
                get: { self.profilePath },
                set: { self.profilePath = $0 }
            )
        }
    }

    func navigate(to route: Route) {
        switch selectedTab {
        case .home:
            homePath.append(route)
        case .search:
            searchPath.append(route)
        case .profile:
            profilePath.append(route)
        }
    }

    func popToRoot() {
        switch selectedTab {
        case .home:
            homePath.removeAll()
        case .search:
            searchPath.removeAll()
        case .profile:
            profilePath.removeAll()
        }
    }
}

enum Tab {
    case home, search, profile
}
```

## Modal Presentation

### Sheet Presentation

Present modal views:

```swift
struct ContentView: View {
    @State private var showSettings = false
    @State private var selectedUser: User?

    var body: some View {
        NavigationStack {
            List {
                Button("Show Settings") {
                    showSettings = true
                }

                ForEach(users) { user in
                    Button(user.name) {
                        selectedUser = user
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
            .sheet(item: $selectedUser) { user in
                UserDetailSheet(user: user)
            }
        }
    }
}

// Dismissable sheet
struct UserDetailSheet: View {
    @Environment(\.dismiss) private var dismiss
    let user: User

    var body: some View {
        NavigationStack {
            UserDetailView(user: user)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") {
                            dismiss()
                        }
                    }
                }
        }
    }
}
```

### Full Screen Cover

Present full-screen modals:

```swift
struct MainView: View {
    @State private var showOnboarding = false

    var body: some View {
        NavigationStack {
            ContentView()
        }
        .fullScreenCover(isPresented: $showOnboarding) {
            OnboardingView()
        }
        .onAppear {
            showOnboarding = !hasCompletedOnboarding
        }
    }
}
```

### Alert and Confirmation Dialog

Show simple dialogs:

```swift
struct ActionView: View {
    @State private var showDeleteAlert = false
    @State private var showOptions = false

    var body: some View {
        VStack {
            Button("Delete") {
                showDeleteAlert = true
            }
            .alert("Delete Item?", isPresented: $showDeleteAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Delete", role: .destructive) {
                    deleteItem()
                }
            } message: {
                Text("This action cannot be undone.")
            }

            Button("Options") {
                showOptions = true
            }
            .confirmationDialog("Choose Action", isPresented: $showOptions) {
                Button("Edit") { editItem() }
                Button("Share") { shareItem() }
                Button("Delete", role: .destructive) { deleteItem() }
                Button("Cancel", role: .cancel) { }
            }
        }
    }

    private func deleteItem() { }
    private func editItem() { }
    private func shareItem() { }
}
```

## State Restoration

### Preserving Navigation State

Save and restore navigation:

```swift
@Observable
final class NavigationState {
    var path: [Route] = []

    func save() {
        let encoder = JSONEncoder()
        if let data = try? encoder.encode(path) {
            UserDefaults.standard.set(data, forKey: "navigation_path")
        }
    }

    func restore() {
        guard let data = UserDefaults.standard.data(forKey: "navigation_path"),
              let restored = try? JSONDecoder().decode([Route].self, from: data) else {
            return
        }

        path = restored
    }
}

@main
struct MyApp: App {
    @State private var navigationState = NavigationState()

    var body: some Scene {
        WindowGroup {
            NavigationStack(path: $navigationState.path) {
                HomeView()
                    .navigationDestination(for: Route.self) { route in
                        routeView(for: route)
                    }
            }
            .onChange(of: navigationState.path) { oldPath, newPath in
                navigationState.save()
            }
            .onAppear {
                navigationState.restore()
            }
        }
    }

    @ViewBuilder
    private func routeView(for route: Route) -> some View {
        // Route implementation
    }
}
```

## Testing Navigation

### Testing Navigation Flows

Test navigation logic:

```swift
import Testing

@Test
func testNavigationToProfile() {
    let navigator = AppNavigator()

    navigator.navigateToProfile()

    #expect(navigator.path.count == 1)
    #expect(navigator.path.first == .profile)
}

@Test
func testPopToRoot() {
    let navigator = AppNavigator()

    navigator.navigate(to: .userList)
    navigator.navigate(to: .userDetail(User.sample))
    navigator.navigate(to: .settings)

    #expect(navigator.path.count == 3)

    navigator.popToRoot()

    #expect(navigator.path.isEmpty)
}

@Test
func testDeepLinkParsing() {
    let handler = DeepLinkHandler()
    let url = URL(string: "myapp://user/\(UUID().uuidString)")!

    handler.handle(url)

    #expect(handler.path.count == 1)
}
```

## Anti-Patterns to Avoid

**DON'T use NavigationView (deprecated):**
```swift
// ❌ BAD - Deprecated in iOS 16
NavigationView {
    List { }
}

// ✅ GOOD
NavigationStack {
    List { }
}
```

**DON'T manage multiple NavigationPath states manually:**
```swift
// ❌ BAD - Hard to maintain
@State private var path1 = NavigationPath()
@State private var path2 = NavigationPath()
@State private var path3 = NavigationPath()

// ✅ GOOD - Use coordinator
@State private var coordinator = TabCoordinator()
```

**DON'T ignore dismiss environment:**
```swift
// ❌ BAD - Custom dismissal logic
@State private var isPresented = false

Button("Close") {
    isPresented = false  // Parent must manage this
}

// ✅ GOOD
@Environment(\.dismiss) private var dismiss

Button("Close") {
    dismiss()  // Works anywhere in hierarchy
}
```

**DON'T mix navigation paradigms:**
```swift
// ❌ BAD - Mixing NavigationStack and NavigationLink value
NavigationStack(path: $path) {
    NavigationLink(value: route) {  // Good
        Text("Link 1")
    }

    NavigationLink(destination: DetailView()) {  // Bad - old style
        Text("Link 2")
    }
}

// ✅ GOOD - Consistent approach
NavigationStack(path: $path) {
    NavigationLink(value: route1) {
        Text("Link 1")
    }

    NavigationLink(value: route2) {
        Text("Link 2")
    }
}
```

## Related Skills

- **swiftui-architecture.md** - Navigation in MVVM architecture
- **swift-concurrency.md** - Async navigation flows
- **swiftdata-persistence.md** - Navigating with persisted models
- **ios-testing.md** - Testing navigation logic
