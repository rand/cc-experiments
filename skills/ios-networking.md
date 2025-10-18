---
name: ios-networking
description: Building network layers for iOS/macOS apps
---



# iOS Networking Patterns

**Use this skill when:**
- Building network layers for iOS/macOS apps
- Implementing RESTful API clients
- Managing async URLSession operations
- Handling authentication and token refresh
- Implementing retry logic and error handling

## NetworkService Actor Pattern

### Basic Network Service

Build a thread-safe network service with actor:

```swift
actor NetworkService {
    static let shared = NetworkService()

    private let session: URLSession
    private let baseURL: URL

    init(
        baseURL: URL = URL(string: "https://api.example.com")!,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.session = session
    }

    func request<T: Decodable>(
        _ endpoint: Endpoint,
        as type: T.Type
    ) async throws -> T {
        let request = try buildRequest(for: endpoint)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        return try decoder.decode(T.self, from: data)
    }

    private func buildRequest(for endpoint: Endpoint) throws -> URLRequest {
        let url = baseURL.appendingPathComponent(endpoint.path)

        var urlComponents = URLComponents(url: url, resolvingAgainstBaseURL: true)
        urlComponents?.queryItems = endpoint.queryItems

        guard let finalURL = urlComponents?.url else {
            throw NetworkError.invalidURL
        }

        var request = URLRequest(url: finalURL)
        request.httpMethod = endpoint.method.rawValue
        request.allHTTPHeaderFields = endpoint.headers

        if let body = endpoint.body {
            request.httpBody = try JSONEncoder().encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        return request
    }
}

enum NetworkError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError(let error):
            return "Decoding failed: \(error.localizedDescription)"
        }
    }
}
```

## Endpoint Definition

### Type-Safe Endpoints

Define endpoints with type safety:

```swift
protocol Endpoint {
    var path: String { get }
    var method: HTTPMethod { get }
    var headers: [String: String]? { get }
    var queryItems: [URLQueryItem]? { get }
    var body: Encodable? { get }
}

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
    case patch = "PATCH"
}

enum UserEndpoint: Endpoint {
    case getUser(id: UUID)
    case listUsers(page: Int, limit: Int)
    case createUser(UserCreateRequest)
    case updateUser(id: UUID, UserUpdateRequest)
    case deleteUser(id: UUID)

    var path: String {
        switch self {
        case .getUser(let id):
            return "/users/\(id)"
        case .listUsers:
            return "/users"
        case .createUser:
            return "/users"
        case .updateUser(let id, _):
            return "/users/\(id)"
        case .deleteUser(let id):
            return "/users/\(id)"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .getUser, .listUsers:
            return .get
        case .createUser:
            return .post
        case .updateUser:
            return .put
        case .deleteUser:
            return .delete
        }
    }

    var headers: [String : String]? {
        ["Accept": "application/json"]
    }

    var queryItems: [URLQueryItem]? {
        switch self {
        case .listUsers(let page, let limit):
            return [
                URLQueryItem(name: "page", value: "\(page)"),
                URLQueryItem(name: "limit", value: "\(limit)")
            ]
        default:
            return nil
        }
    }

    var body: Encodable? {
        switch self {
        case .createUser(let request):
            return request
        case .updateUser(_, let request):
            return request
        default:
            return nil
        }
    }
}

// Request/Response models
struct UserCreateRequest: Encodable {
    let name: String
    let email: String
}

struct UserUpdateRequest: Encodable {
    let name: String?
    let email: String?
}

struct UserResponse: Decodable {
    let id: UUID
    let name: String
    let email: String
    let createdAt: Date
}
```

## Authentication

### Token-Based Authentication

Implement JWT token management:

```swift
actor AuthenticationService {
    static let shared = AuthenticationService()

    private var accessToken: String?
    private var refreshToken: String?
    private var tokenExpirationDate: Date?

    func setTokens(access: String, refresh: String, expiresIn: TimeInterval) {
        self.accessToken = access
        self.refreshToken = refresh
        self.tokenExpirationDate = Date().addingTimeInterval(expiresIn)
        saveTokensToKeychain()
    }

    func getValidAccessToken() async throws -> String {
        // Check if token exists and is valid
        if let token = accessToken,
           let expiration = tokenExpirationDate,
           expiration > Date().addingTimeInterval(60) {  // 60s buffer
            return token
        }

        // Try to refresh token
        if let refresh = refreshToken {
            return try await refreshAccessToken(using: refresh)
        }

        throw AuthError.notAuthenticated
    }

    private func refreshAccessToken(using refreshToken: String) async throws -> String {
        let url = URL(string: "https://api.example.com/auth/refresh")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(refreshToken)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw AuthError.refreshFailed
        }

        let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)

        setTokens(
            access: tokenResponse.accessToken,
            refresh: tokenResponse.refreshToken,
            expiresIn: tokenResponse.expiresIn
        )

        return tokenResponse.accessToken
    }

    func logout() {
        accessToken = nil
        refreshToken = nil
        tokenExpirationDate = nil
        clearTokensFromKeychain()
    }

    private func saveTokensToKeychain() {
        // Keychain implementation
    }

    private func clearTokensFromKeychain() {
        // Keychain implementation
    }
}

struct TokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: TimeInterval
}

enum AuthError: LocalizedError {
    case notAuthenticated
    case refreshFailed

    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "Not authenticated"
        case .refreshFailed:
            return "Failed to refresh token"
        }
    }
}
```

### Authenticated Requests

Add authentication to network service:

```swift
extension NetworkService {
    func authenticatedRequest<T: Decodable>(
        _ endpoint: Endpoint,
        as type: T.Type
    ) async throws -> T {
        let token = try await AuthenticationService.shared.getValidAccessToken()

        var request = try buildRequest(for: endpoint)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        // Handle 401 - token might be invalid
        if httpResponse.statusCode == 401 {
            await AuthenticationService.shared.logout()
            throw AuthError.notAuthenticated
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.httpError(httpResponse.statusCode)
        }

        return try JSONDecoder().decode(T.self, from: data)
    }
}
```

## Retry Logic and Error Handling

### Automatic Retry

Implement exponential backoff:

```swift
extension NetworkService {
    func requestWithRetry<T: Decodable>(
        _ endpoint: Endpoint,
        as type: T.Type,
        maxRetries: Int = 3
    ) async throws -> T {
        var lastError: Error?

        for attempt in 0..<maxRetries {
            do {
                return try await request(endpoint, as: type)
            } catch {
                lastError = error

                // Don't retry client errors (4xx)
                if case NetworkError.httpError(let code) = error,
                   (400...499).contains(code) {
                    throw error
                }

                // Wait before retrying (exponential backoff)
                if attempt < maxRetries - 1 {
                    let delay = pow(2.0, Double(attempt))
                    try await Task.sleep(for: .seconds(delay))
                }
            }
        }

        throw lastError ?? NetworkError.invalidResponse
    }
}
```

### Error Mapping

Map network errors to domain errors:

```swift
enum DomainError: LocalizedError {
    case network(NetworkError)
    case validation(String)
    case notFound
    case unauthorized
    case serverError

    init(from networkError: NetworkError) {
        switch networkError {
        case .httpError(let code):
            switch code {
            case 401:
                self = .unauthorized
            case 404:
                self = .notFound
            case 422:
                self = .validation("Invalid input")
            case 500...599:
                self = .serverError
            default:
                self = .network(networkError)
            }
        default:
            self = .network(networkError)
        }
    }

    var errorDescription: String? {
        switch self {
        case .network(let error):
            return error.localizedDescription
        case .validation(let message):
            return message
        case .notFound:
            return "Resource not found"
        case .unauthorized:
            return "Unauthorized access"
        case .serverError:
            return "Server error occurred"
        }
    }
}
```

## API Client Pattern

### Domain-Specific API Client

Build focused API clients:

```swift
actor UserAPIClient {
    private let networkService: NetworkService

    init(networkService: NetworkService = .shared) {
        self.networkService = networkService
    }

    func getUser(id: UUID) async throws -> User {
        let response = try await networkService.authenticatedRequest(
            UserEndpoint.getUser(id: id),
            as: UserResponse.self
        )

        return User(from: response)
    }

    func listUsers(page: Int = 1, limit: Int = 20) async throws -> [User] {
        let response = try await networkService.authenticatedRequest(
            UserEndpoint.listUsers(page: page, limit: limit),
            as: UsersListResponse.self
        )

        return response.users.map { User(from: $0) }
    }

    func createUser(name: String, email: String) async throws -> User {
        let request = UserCreateRequest(name: name, email: email)
        let response = try await networkService.authenticatedRequest(
            UserEndpoint.createUser(request),
            as: UserResponse.self
        )

        return User(from: response)
    }

    func updateUser(id: UUID, name: String?, email: String?) async throws -> User {
        let request = UserUpdateRequest(name: name, email: email)
        let response = try await networkService.authenticatedRequest(
            UserEndpoint.updateUser(id: id, request),
            as: UserResponse.self
        )

        return User(from: response)
    }

    func deleteUser(id: UUID) async throws {
        _ = try await networkService.authenticatedRequest(
            UserEndpoint.deleteUser(id: id),
            as: EmptyResponse.self
        )
    }
}

struct UsersListResponse: Decodable {
    let users: [UserResponse]
    let total: Int
    let page: Int
}

struct EmptyResponse: Decodable {}

// Domain model
struct User: Identifiable {
    let id: UUID
    let name: String
    let email: String
    let createdAt: Date

    init(from response: UserResponse) {
        self.id = response.id
        self.name = response.name
        self.email = response.email
        self.createdAt = response.createdAt
    }
}
```

## Uploading and Downloading

### File Upload

Upload files with progress:

```swift
extension NetworkService {
    func upload(
        _ endpoint: Endpoint,
        file: URL,
        progressHandler: @escaping (Double) -> Void
    ) async throws -> Data {
        var request = try buildRequest(for: endpoint)

        let token = try await AuthenticationService.shared.getValidAccessToken()
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let uploadTask = session.uploadTask(with: request, fromFile: file)

        // Monitor progress
        for await progress in uploadTask.progress.values {
            progressHandler(progress.fractionCompleted)
        }

        return try await uploadTask.value.0
    }
}

// Usage
@Observable
final class UploadViewModel {
    var uploadProgress: Double = 0

    func uploadFile(url: URL) async throws {
        let endpoint = FileEndpoint.upload

        let data = try await NetworkService.shared.upload(
            endpoint,
            file: url,
            progressHandler: { progress in
                Task { @MainActor in
                    self.uploadProgress = progress
                }
            }
        )

        // Handle response
    }
}
```

### File Download

Download large files:

```swift
extension NetworkService {
    func download(
        from url: URL,
        to destination: URL,
        progressHandler: @escaping (Double) -> Void
    ) async throws {
        let downloadTask = session.downloadTask(with: url)

        // Monitor progress
        Task {
            for await progress in downloadTask.progress.values {
                progressHandler(progress.fractionCompleted)
            }
        }

        let (localURL, _) = try await downloadTask.value

        // Move to final destination
        try FileManager.default.moveItem(at: localURL, to: destination)
    }
}
```

## Caching

### Response Caching

Implement simple cache:

```swift
actor ResponseCache {
    private var cache: [URL: CachedResponse] = [:]
    private let maxAge: TimeInterval = 300  // 5 minutes

    struct CachedResponse {
        let data: Data
        let timestamp: Date

        var isExpired: Bool {
            Date().timeIntervalSince(timestamp) > 300
        }
    }

    func get(for url: URL) -> Data? {
        guard let cached = cache[url], !cached.isExpired else {
            return nil
        }
        return cached.data
    }

    func set(_ data: Data, for url: URL) {
        cache[url] = CachedResponse(data: data, timestamp: Date())
    }

    func clear() {
        cache.removeAll()
    }

    func removeExpired() {
        cache = cache.filter { !$0.value.isExpired }
    }
}

extension NetworkService {
    func requestWithCache<T: Decodable>(
        _ endpoint: Endpoint,
        as type: T.Type,
        cache: ResponseCache
    ) async throws -> T {
        let request = try buildRequest(for: endpoint)

        // Check cache
        if let cachedData = await cache.get(for: request.url!) {
            return try JSONDecoder().decode(T.self, from: cachedData)
        }

        // Fetch from network
        let (data, _) = try await session.data(for: request)

        // Update cache
        await cache.set(data, for: request.url!)

        return try JSONDecoder().decode(T.self, from: data)
    }
}
```

## Testing Network Code

### Mock Network Service

Create testable network layer:

```swift
protocol NetworkServiceProtocol {
    func request<T: Decodable>(_ endpoint: Endpoint, as type: T.Type) async throws -> T
}

extension NetworkService: NetworkServiceProtocol {}

final class MockNetworkService: NetworkServiceProtocol {
    var responseToReturn: Any?
    var errorToThrow: Error?

    func request<T: Decodable>(_ endpoint: Endpoint, as type: T.Type) async throws -> T {
        if let error = errorToThrow {
            throw error
        }

        guard let response = responseToReturn as? T else {
            throw NetworkError.invalidResponse
        }

        return response
    }
}

// Test
@Test
func testUserFetch() async throws {
    let mockService = MockNetworkService()
    mockService.responseToReturn = UserResponse(
        id: UUID(),
        name: "Test User",
        email: "test@example.com",
        createdAt: Date()
    )

    let client = UserAPIClient(networkService: mockService as! NetworkService)
    let user = try await client.getUser(id: UUID())

    #expect(user.name == "Test User")
}
```

## Anti-Patterns to Avoid

**DON'T make synchronous network calls:**
```swift
// ❌ BAD - Blocks thread
let data = try Data(contentsOf: url)

// ✅ GOOD
let (data, _) = try await URLSession.shared.data(from: url)
```

**DON'T ignore error responses:**
```swift
// ❌ BAD
let (data, _) = try await session.data(for: request)
return try JSONDecoder().decode(T.self, from: data)

// ✅ GOOD
let (data, response) = try await session.data(for: request)
guard let httpResponse = response as? HTTPURLResponse,
      (200...299).contains(httpResponse.statusCode) else {
    throw NetworkError.httpError((response as? HTTPURLResponse)?.statusCode ?? 0)
}
return try JSONDecoder().decode(T.self, from: data)
```

**DON'T hardcode URLs:**
```swift
// ❌ BAD
let url = URL(string: "https://api.example.com/users/\(id)")!

// ✅ GOOD
enum UserEndpoint: Endpoint {
    case getUser(id: UUID)
    var path: String { "/users/\(id)" }
}
```

## Related Skills

- **swift-concurrency.md** - Actor patterns, async/await
- **swiftui-architecture.md** - Network services in view models
- **ios-testing.md** - Testing network code
- **swiftdata-persistence.md** - Persisting fetched data
