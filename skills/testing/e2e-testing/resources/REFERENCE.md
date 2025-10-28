# End-to-End Testing Reference

## Table of Contents
1. [E2E Testing Philosophy and Strategy](#e2e-testing-philosophy-and-strategy)
2. [The Testing Pyramid and E2E Position](#the-testing-pyramid-and-e2e-position)
3. [Choosing an E2E Framework](#choosing-an-e2e-framework)
4. [Page Object Model (POM)](#page-object-model-pom)
5. [Selector Strategies](#selector-strategies)
6. [Waiting Strategies](#waiting-strategies)
7. [Authentication and Session Management](#authentication-and-session-management)
8. [Test Data Management](#test-data-management)
9. [Network Interception and Mocking](#network-interception-and-mocking)
10. [Visual Regression Testing](#visual-regression-testing)
11. [Cross-Browser Testing](#cross-browser-testing)
12. [Handling Complex Interactions](#handling-complex-interactions)
13. [Test Organization and Structure](#test-organization-and-structure)
14. [Flakiness Reduction Techniques](#flakiness-reduction-techniques)
15. [Parallelization and Performance](#parallelization-and-performance)
16. [CI/CD Integration](#cicd-integration)
17. [Debugging Strategies](#debugging-strategies)
18. [Accessibility Testing](#accessibility-testing)
19. [Mobile and Responsive Testing](#mobile-and-responsive-testing)
20. [Common Anti-Patterns](#common-anti-patterns)
21. [Best Practices](#best-practices)
22. [Real-World Test Suites](#real-world-test-suites)

---

## E2E Testing Philosophy and Strategy

### What Are E2E Tests?

**End-to-End tests verify complete user workflows** from the user interface through all application layers to the database and back. They simulate real user behavior in a real browser environment.

**Characteristics**:
- **Highest confidence**: Tests the entire stack working together
- **Slowest execution**: Starts browser, loads pages, waits for interactions
- **Most brittle**: Breaks with UI changes, network issues, timing problems
- **Most expensive**: Complex to write and maintain

**E2E tests answer**: "Does this feature work for real users in a real browser?"

### When to Write E2E Tests

**DO write E2E tests for**:
- Critical user journeys (login, checkout, registration)
- Happy paths through multi-step workflows
- Features that must work across browsers
- Regulatory compliance requirements
- Revenue-critical features
- Complex user interactions (drag-drop, file uploads)

**DON'T write E2E tests for**:
- Business logic (use unit tests)
- API contracts (use integration tests)
- Edge cases and error handling (too many combinations)
- Browser-specific quirks (use focused tests)
- Everything (too slow, too brittle)

### The 10/20/70 Rule

A healthy test suite distribution:

```
10% E2E tests       - Critical user journeys
20% Integration     - API and service boundaries
70% Unit tests      - Business logic and components
```

**Why this ratio?**
- Unit tests: Fast feedback, pinpoint failures, cheap to maintain
- Integration tests: Verify components work together, moderate speed
- E2E tests: Highest confidence, but slowest and most brittle

### Cost-Benefit Analysis

**E2E Test Costs**:
- **Time**: 10-100x slower than unit tests (seconds vs milliseconds)
- **Complexity**: Browser setup, test data, state management
- **Brittleness**: UI changes break tests frequently
- **Debugging**: Hard to isolate failures in full stack
- **Infrastructure**: Requires browsers, servers, databases

**E2E Test Benefits**:
- **Confidence**: Proves features work end-to-end
- **Regression detection**: Catches integration failures
- **User perspective**: Tests real user workflows
- **Documentation**: Shows how features should work

**Break-even point**: E2E tests pay off for:
1. Features touched frequently (refactoring)
2. Critical paths (revenue, compliance)
3. Complex workflows (multi-step processes)
4. Cross-cutting concerns (authentication, navigation)

---

## The Testing Pyramid and E2E Position

### Classic Testing Pyramid

```
        /\
       /E2E\        Few (10%)    - Slow, brittle, high confidence
      /-----\
     / Integ \      Some (20%)   - Medium speed, verify boundaries
    /---------\
   /   Unit    \    Many (70%)   - Fast, focused, cheap
  /-------------\
```

### Testing Trophy (Alternative View)

```
        ___
       /   \
      / E2E \        Some        - Critical paths only
     /-------\
    /  Integ  \      Most        - Component + integration
   /-----------\
  /    Unit     \    Many        - Pure logic
 /      Static   \   Foundation  - TypeScript, linters
-------------------
```

**Trophy philosophy**: Integration tests provide best ROI for web apps.

### E2E Test Scope

**What E2E tests cover**:
```
User Browser
    ↓
Frontend (React/Vue/etc)
    ↓
HTTP Requests
    ↓
Backend API
    ↓
Business Logic
    ↓
Database
    ↓
Response back through stack
    ↓
UI Updates
```

**Every layer is real**: Real browser, real HTTP, real database.

### Deciding Test Level

**Use this decision tree**:

```
Can I test this with a unit test?
    YES → Write unit test (fastest feedback)
    NO ↓

Does it cross service boundaries?
    YES → Write integration test
    NO ↓

Does it require browser interaction?
    YES → Write E2E test
    NO → Reconsider if test is needed
```

---

## Choosing an E2E Framework

### Framework Comparison

| Feature | Playwright | Cypress | Selenium | Puppeteer | TestCafe |
|---------|-----------|---------|----------|-----------|----------|
| **Browsers** | Chrome, Firefox, Safari, Edge | Chrome, Firefox, Edge | All browsers | Chrome only | All browsers |
| **Languages** | JS/TS, Python, Java, .NET | JS/TS only | All languages | JS/TS only | JS/TS only |
| **Parallelization** | Native, efficient | Per-spec file | Manual setup | Manual setup | Native |
| **Auto-waiting** | Excellent | Excellent | Manual | Manual | Good |
| **Network mocking** | Full control | Full control | Limited | Full control | Limited |
| **Debugging** | Trace viewer, inspector | Time-travel, video | Basic | DevTools | Screenshots |
| **Speed** | Fast | Fast | Slower | Fast | Medium |
| **Multi-tab** | Yes | No | Yes | Yes | Yes |
| **Mobile emulation** | Native | Viewport only | WebDriver | Native | Viewport only |
| **Community** | Growing rapidly | Large | Huge | Large | Medium |
| **Maintenance** | Active (Microsoft) | Active (Cypress.io) | Active (Selenium) | Active (Google) | Active |

### Playwright (Recommended)

**Strengths**:
- True multi-browser support (Chromium, Firefox, WebKit)
- Excellent auto-waiting and retry mechanisms
- Native mobile emulation and device profiles
- Powerful network interception and mocking
- Multiple tabs and contexts in single test
- Trace viewer for debugging
- Fast and reliable
- Great TypeScript support

**Best for**:
- New projects starting E2E testing
- Multi-browser testing requirements
- Complex workflows needing multiple tabs
- Teams wanting modern tooling
- Mobile web testing

**Example**:
```typescript
import { test, expect } from '@playwright/test';

test('user can login', async ({ page }) => {
  await page.goto('https://example.com');
  await page.fill('#username', 'alice');
  await page.fill('#password', 'secret');
  await page.click('button[type="submit"]');
  await expect(page.locator('.welcome')).toContainText('Welcome, Alice');
});
```

### Cypress

**Strengths**:
- Excellent developer experience
- Time-travel debugging (see every step)
- Real-time reloads during development
- Built-in screenshot and video
- Simple, intuitive API
- Great documentation

**Limitations**:
- Chromium-based browsers only (limited Firefox, no Safari)
- Single tab limitation (can't test multiple windows)
- Runs in browser context (some limitations)

**Best for**:
- Teams prioritizing developer experience
- Chromium-only testing acceptable
- Single-tab workflows
- Projects already using Cypress

**Example**:
```typescript
describe('Login', () => {
  it('allows user to login', () => {
    cy.visit('https://example.com');
    cy.get('#username').type('alice');
    cy.get('#password').type('secret');
    cy.get('button[type="submit"]').click();
    cy.get('.welcome').should('contain', 'Welcome, Alice');
  });
});
```

### Selenium WebDriver

**Strengths**:
- Industry standard (most mature)
- Supports all browsers and platforms
- Available in all major languages
- Huge community and ecosystem
- Grid support for distributed testing

**Limitations**:
- Verbose API (lots of boilerplate)
- Manual waiting required
- Slower than modern alternatives
- Requires more maintenance

**Best for**:
- Large organizations with existing Selenium infrastructure
- Testing in languages other than JavaScript
- Legacy projects
- Teams with Selenium expertise

**Example** (Python):
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Chrome()
driver.get('https://example.com')

driver.find_element(By.ID, 'username').send_keys('alice')
driver.find_element(By.ID, 'password').send_keys('secret')
driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

WebDriverWait(driver, 10).until(
    EC.text_to_be_present_in_element((By.CLASS_NAME, 'welcome'), 'Welcome, Alice')
)

driver.quit()
```

### Puppeteer

**Strengths**:
- Chrome DevTools Protocol (low-level control)
- Excellent for scraping and automation
- Fast and lightweight
- Good for PDF generation and screenshots
- Maintained by Google Chrome team

**Limitations**:
- Chrome/Chromium only (no Firefox, Safari)
- More low-level (manual waiting often needed)
- Smaller community for testing use cases

**Best for**:
- Chrome-only testing
- PDF generation or scraping tasks
- Teams already using Puppeteer
- Low-level browser automation

### Framework Selection Guide

**Choose Playwright if**:
- Starting new E2E test suite
- Need multi-browser support
- Want modern, fast tooling
- Testing mobile web apps

**Choose Cypress if**:
- Developer experience is top priority
- Chromium-only testing is acceptable
- Team already uses Cypress
- Want excellent debugging tools

**Choose Selenium if**:
- Need non-JavaScript language (Java, Python, C#)
- Large existing Selenium infrastructure
- Testing very old browsers
- Grid-based distributed testing

**Choose Puppeteer if**:
- Chrome-only acceptable
- Need low-level browser control
- PDF generation or scraping
- Already using Puppeteer

---

## Page Object Model (POM)

### What is Page Object Model?

**Page Object Model** is a design pattern that:
- Encapsulates page structure in classes
- Separates test logic from page implementation
- Provides reusable page actions
- Makes tests maintainable when UI changes

**Without POM** (brittle, duplicated):
```typescript
test('user can login', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.fill('#username', 'alice');
  await page.fill('#password', 'secret');
  await page.click('button[type="submit"]');
  await expect(page.locator('.welcome-message')).toBeVisible();
});

test('admin can login', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.fill('#username', 'admin');  // Duplicated selectors
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await expect(page.locator('.welcome-message')).toBeVisible();
});
```

**With POM** (maintainable, reusable):
```typescript
class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('https://example.com/login');
  }

  async login(username: string, password: string) {
    await this.page.fill('#username', username);
    await this.page.fill('#password', password);
    await this.page.click('button[type="submit"]');
  }

  get welcomeMessage() {
    return this.page.locator('.welcome-message');
  }
}

test('user can login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('alice', 'secret');
  await expect(loginPage.welcomeMessage).toBeVisible();
});

test('admin can login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('admin', 'admin123');
  await expect(loginPage.welcomeMessage).toBeVisible();
});
```

### POM Benefits

**Maintainability**: Change selector once in page object, not in every test
```typescript
// Before: Selector change requires updating 50 tests
await page.fill('#username', 'alice');

// After: Change selector in one place
class LoginPage {
  private usernameInput = '#username'; // Change here only

  async enterUsername(username: string) {
    await this.page.fill(this.usernameInput, username);
  }
}
```

**Readability**: Tests read like user actions
```typescript
// Without POM (technical details)
await page.fill('#email', 'alice@example.com');
await page.fill('#card-number', '4242424242424242');
await page.fill('#cvv', '123');
await page.click('.submit-payment');

// With POM (business actions)
await checkoutPage.enterPaymentDetails({
  email: 'alice@example.com',
  cardNumber: '4242424242424242',
  cvv: '123'
});
await checkoutPage.submitPayment();
```

**Reusability**: Share page objects across tests
```typescript
// Multiple tests reuse same page objects
test.describe('Dashboard', () => {
  test('shows user stats', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    expect(await dashboard.getUserCount()).toBe('1,234');
  });

  test('allows navigation to settings', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await dashboard.navigateToSettings();
    expect(page.url()).toContain('/settings');
  });
});
```

### POM Structure Patterns

#### Basic Page Object

```typescript
// pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.locator('#username');
    this.passwordInput = page.locator('#password');
    this.submitButton = page.locator('button[type="submit"]');
    this.errorMessage = page.locator('.error-message');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(username: string, password: string) {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectError(message: string) {
    await expect(this.errorMessage).toHaveText(message);
  }
}
```

#### Page Object with Component Composition

```typescript
// components/Header.ts
export class Header {
  constructor(private page: Page) {}

  async logout() {
    await this.page.click('.user-menu');
    await this.page.click('.logout-button');
  }

  async navigateTo(section: string) {
    await this.page.click(`nav a:has-text("${section}")`);
  }

  async getUserName(): Promise<string> {
    return await this.page.locator('.user-name').textContent() || '';
  }
}

// pages/DashboardPage.ts
export class DashboardPage {
  readonly page: Page;
  readonly header: Header;

  constructor(page: Page) {
    this.page = page;
    this.header = new Header(page);
  }

  async goto() {
    await this.page.goto('/dashboard');
  }

  async getStatValue(statName: string): Promise<string> {
    const locator = this.page.locator(`.stat[data-name="${statName}"] .value`);
    return await locator.textContent() || '';
  }

  get statsGrid() {
    return this.page.locator('.stats-grid');
  }
}

// Test using composed page objects
test('dashboard workflow', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.goto();

  // Use dashboard methods
  const userCount = await dashboard.getStatValue('users');
  expect(userCount).toBe('1,234');

  // Use composed header component
  expect(await dashboard.header.getUserName()).toBe('Alice');
  await dashboard.header.logout();
});
```

#### Page Object with Fluent API

```typescript
export class ProductPage {
  constructor(private page: Page) {}

  async goto(productId: string) {
    await this.page.goto(`/products/${productId}`);
    return this;
  }

  async selectSize(size: string) {
    await this.page.click(`button[data-size="${size}"]`);
    return this;
  }

  async selectColor(color: string) {
    await this.page.click(`button[data-color="${color}"]`);
    return this;
  }

  async addToCart() {
    await this.page.click('.add-to-cart');
    return this;
  }

  async expectInCart() {
    await expect(this.page.locator('.cart-badge')).toBeVisible();
    return this;
  }
}

// Fluent test (chainable)
test('add product to cart', async ({ page }) => {
  await new ProductPage(page)
    .goto('123')
    .then(p => p.selectSize('M'))
    .then(p => p.selectColor('Blue'))
    .then(p => p.addToCart())
    .then(p => p.expectInCart());
});
```

#### Page Object Factory

```typescript
// pages/PageFactory.ts
export class PageFactory {
  constructor(private page: Page) {}

  loginPage() {
    return new LoginPage(this.page);
  }

  dashboardPage() {
    return new DashboardPage(this.page);
  }

  settingsPage() {
    return new SettingsPage(this.page);
  }

  productPage() {
    return new ProductPage(this.page);
  }
}

// Test using factory
test('complete user journey', async ({ page }) => {
  const pages = new PageFactory(page);

  await pages.loginPage()
    .goto()
    .then(p => p.login('alice', 'secret'));

  await pages.dashboardPage()
    .goto()
    .then(p => p.header.navigateTo('Products'));

  await pages.productPage()
    .goto('123')
    .then(p => p.addToCart());
});
```

### POM Best Practices

**1. One page class per page**:
```typescript
// ✅ Good: Separate classes
class LoginPage { }
class DashboardPage { }
class SettingsPage { }

// ❌ Bad: Mixed pages
class AllPages {
  async login() { }
  async viewDashboard() { }
  async updateSettings() { }
}
```

**2. Return page objects from navigation**:
```typescript
class LoginPage {
  async login(username: string, password: string): Promise<DashboardPage> {
    await this.page.fill('#username', username);
    await this.page.fill('#password', password);
    await this.page.click('button[type="submit"]');
    return new DashboardPage(this.page);
  }
}

// Test shows clear navigation
test('login navigates to dashboard', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();

  const dashboardPage = await loginPage.login('alice', 'secret');
  await expect(dashboardPage.welcomeMessage).toBeVisible();
});
```

**3. Use locators, not raw selectors**:
```typescript
// ✅ Good: Locator properties
class LoginPage {
  readonly usernameInput: Locator;

  constructor(page: Page) {
    this.usernameInput = page.locator('#username');
  }
}

// ❌ Bad: String selectors
class LoginPage {
  async enterUsername(username: string) {
    await this.page.fill('#username', username); // Duplicated selector
  }
}
```

**4. Keep assertions in tests, not page objects**:
```typescript
// ✅ Good: Assertions in test
class LoginPage {
  get errorMessage() {
    return this.page.locator('.error');
  }
}

test('shows error on invalid login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.login('invalid', 'wrong');
  await expect(loginPage.errorMessage).toContainText('Invalid credentials');
});

// ❌ Bad: Assertions in page object (couples test expectations to page)
class LoginPage {
  async expectError(message: string) {
    await expect(this.page.locator('.error')).toContainText(message);
  }
}
```

**5. Use descriptive method names**:
```typescript
// ✅ Good: Action-oriented names
class CheckoutPage {
  async enterShippingAddress(address: Address) { }
  async selectPaymentMethod(method: string) { }
  async applyDiscountCode(code: string) { }
  async completeOrder() { }
}

// ❌ Bad: Generic names
class CheckoutPage {
  async fill(data: any) { }
  async click(button: string) { }
  async submit() { }
}
```

---

## Selector Strategies

### Selector Hierarchy (Best to Worst)

**1. Data test IDs** (most stable):
```typescript
// ✅ Best: Explicit test attributes
<button data-testid="submit-button">Submit</button>
await page.click('[data-testid="submit-button"]');
```

**2. Accessible roles and labels** (semantic):
```typescript
// ✅ Good: ARIA roles and labels
<button aria-label="Submit form">Submit</button>
await page.click('button[aria-label="Submit form"]');
await page.getByRole('button', { name: 'Submit form' }).click();
```

**3. Text content** (fragile to copy changes):
```typescript
// ⚠️ Okay: Text content (breaks with copy changes)
await page.click('button:has-text("Submit")');
await page.getByText('Submit').click();
```

**4. CSS selectors** (fragile to style changes):
```typescript
// ⚠️ Fragile: Class names (breaks with CSS refactoring)
<button class="btn btn-primary submit-btn">Submit</button>
await page.click('.submit-btn');
```

**5. XPath** (most fragile):
```typescript
// ❌ Worst: XPath (breaks with DOM structure changes)
await page.click('//div[3]/form/button[1]');
```

### Playwright Locator API

**Recommended locators**:
```typescript
// Role-based (accessible, semantic)
page.getByRole('button', { name: 'Submit' })
page.getByRole('textbox', { name: 'Username' })
page.getByRole('link', { name: 'Home' })

// Label-based (forms)
page.getByLabel('Email address')
page.getByLabel('Password')

// Placeholder
page.getByPlaceholder('Enter your email')

// Text content
page.getByText('Welcome back')
page.getByText(/Sign in/i) // Case-insensitive regex

// Test ID (best for stability)
page.getByTestId('submit-button')
page.getByTestId('user-profile')

// Title
page.getByTitle('Close dialog')

// Alt text (images)
page.getByAltText('User avatar')
```

**CSS and XPath** (less preferred):
```typescript
// CSS selector
page.locator('.submit-button')
page.locator('#username')
page.locator('button[type="submit"]')

// XPath (avoid if possible)
page.locator('xpath=//button[text()="Submit"]')
```

### Selector Combinators

**Filtering locators**:
```typescript
// Filter by text
page.getByRole('button').filter({ hasText: 'Submit' })

// Filter by test ID
page.locator('.card').filter({ hasTestId: 'featured-card' })

// Filter by not having text
page.getByRole('button').filter({ hasNotText: 'Cancel' })

// First, last, nth
page.getByRole('listitem').first()
page.getByRole('listitem').last()
page.getByRole('listitem').nth(2)
```

**Chaining locators**:
```typescript
// Find within parent
page.locator('.user-card')
  .locator('.username')
  .click();

// Has locator (parent contains child)
page.locator('.card')
  .filter({ has: page.getByRole('button', { name: 'Delete' }) })
  .first();

// Has text
page.locator('.notification')
  .filter({ hasText: 'Success' })
  .click();
```

### Data Test IDs Strategy

**Add test IDs to components**:
```tsx
// React component with data-testid
function LoginForm() {
  return (
    <form data-testid="login-form">
      <input
        type="text"
        name="username"
        data-testid="login-username"
        placeholder="Username"
      />
      <input
        type="password"
        name="password"
        data-testid="login-password"
        placeholder="Password"
      />
      <button type="submit" data-testid="login-submit">
        Sign In
      </button>
    </form>
  );
}

// Test using stable test IDs
test('user can login', async ({ page }) => {
  await page.goto('/login');
  await page.getByTestId('login-username').fill('alice');
  await page.getByTestId('login-password').fill('secret');
  await page.getByTestId('login-submit').click();
  await expect(page).toHaveURL('/dashboard');
});
```

**Naming convention**:
```typescript
// ✅ Good: Component-action pattern
data-testid="login-username"
data-testid="login-password"
data-testid="login-submit"
data-testid="cart-add-button"
data-testid="product-price"

// ❌ Bad: Generic or unclear
data-testid="input1"
data-testid="button"
data-testid="thing"
```

### Accessibility-First Selectors

**Use ARIA roles**:
```typescript
// Standard HTML roles
await page.getByRole('heading', { name: 'Dashboard' })
await page.getByRole('button', { name: 'Save' })
await page.getByRole('link', { name: 'Home' })
await page.getByRole('textbox', { name: 'Email' })
await page.getByRole('checkbox', { name: 'Remember me' })
await page.getByRole('radio', { name: 'Credit Card' })
await page.getByRole('listitem')
await page.getByRole('row')
await page.getByRole('cell')

// Custom ARIA roles
<div role="dialog" aria-label="Confirmation">
  <h2>Confirm deletion</h2>
  <button>Delete</button>
</div>

await page.getByRole('dialog', { name: 'Confirmation' })
await page.getByRole('button', { name: 'Delete' })
```

**Benefits of accessibility-first selectors**:
1. **Stable**: Don't break with CSS changes
2. **Semantic**: Tests read like user actions
3. **Enforce accessibility**: If selector fails, UI might not be accessible
4. **Screen reader compatible**: What works for tests works for assistive tech

### Handling Dynamic Content

**Wait for content to load**:
```typescript
// Wait for element to appear
await page.waitForSelector('[data-testid="user-profile"]');

// Wait for specific text
await page.waitForSelector('text=Welcome, Alice');

// Wait for element count
await page.locator('.notification').count(); // Returns count when stable
```

**Select dynamic elements**:
```typescript
// Data attributes with dynamic IDs
<div data-testid="user-card" data-user-id="123">Alice</div>

await page.locator('[data-testid="user-card"][data-user-id="123"]').click();

// Partial text match
await page.locator('text=/User #\\d+/').click();

// Regex selector
await page.locator('[data-id^="user-"]').first().click();
```

### Selector Performance

**Efficient selectors**:
```typescript
// ✅ Fast: Direct ID or test ID
page.getByTestId('submit-button')
page.locator('#username')

// ⚠️ Slower: Deep traversal
page.locator('div > div > div > button')

// ❌ Slowest: Complex XPath
page.locator('//div[@class="container"]/descendant::button[contains(text(), "Submit")]')
```

**Best practices**:
- Use test IDs for critical elements
- Avoid deep CSS selectors
- Minimize XPath usage
- Cache locators in page objects

---

## Waiting Strategies

### Why Proper Waiting Matters

**The problem**: Web apps load asynchronously
- DOM elements appear/disappear dynamically
- AJAX requests load data
- Animations and transitions delay visibility
- Network latency varies

**Bad solution**: `sleep()` or `wait()`
```typescript
// ❌ NEVER: Fixed waits are flaky and slow
await page.click('button');
await page.waitForTimeout(2000); // Might be too short or too long
await expect(page.locator('.result')).toBeVisible();
```

**Good solution**: Smart waiting
```typescript
// ✅ Good: Wait for actual condition
await page.click('button');
await page.waitForSelector('.result', { state: 'visible' });
await expect(page.locator('.result')).toBeVisible();
```

### Playwright Auto-Waiting

**Playwright automatically waits** for elements to be:
1. **Attached** to DOM
2. **Visible** (not display: none, visibility: hidden, or opacity: 0)
3. **Stable** (not animating or moving)
4. **Enabled** (not disabled attribute)
5. **Receives events** (not obscured by other elements)

**Actions with auto-waiting**:
```typescript
// These automatically wait for element to be actionable
await page.click('button');        // Waits for button to be clickable
await page.fill('input', 'text');  // Waits for input to be editable
await page.check('checkbox');      // Waits for checkbox to be checkable
await page.selectOption('select', 'value'); // Waits for select to be enabled

// Assertions auto-wait too
await expect(page.locator('.message')).toBeVisible(); // Waits up to timeout
await expect(page.locator('.count')).toHaveText('5'); // Retries until text matches
```

**Configure timeout**:
```typescript
// Per-action timeout
await page.click('button', { timeout: 5000 });

// Per-test timeout
test('slow operation', async ({ page }) => {
  test.setTimeout(60000); // 60 seconds for this test
  await page.goto('/slow-page');
});

// Global timeout (playwright.config.ts)
export default defineConfig({
  timeout: 30000, // 30 seconds default
  expect: {
    timeout: 5000, // 5 seconds for assertions
  },
});
```

### Explicit Waits

**Wait for selector**:
```typescript
// Wait for element to exist in DOM
await page.waitForSelector('.dynamic-content');

// Wait for specific state
await page.waitForSelector('.modal', { state: 'visible' });
await page.waitForSelector('.loading', { state: 'hidden' });
await page.waitForSelector('.temp-element', { state: 'detached' });
```

**Wait for navigation**:
```typescript
// Wait for URL change
await page.click('a[href="/dashboard"]');
await page.waitForURL('/dashboard');

// Wait for URL pattern
await page.waitForURL('**/products/*');
await page.waitForURL(/\/product\/\d+/);

// Wait for load state
await page.goto('https://example.com');
await page.waitForLoadState('domcontentloaded'); // DOM ready
await page.waitForLoadState('load');             // All resources loaded
await page.waitForLoadState('networkidle');      // No network activity for 500ms
```

**Wait for network requests**:
```typescript
// Wait for specific API response
const responsePromise = page.waitForResponse('https://api.example.com/users');
await page.click('button');
const response = await responsePromise;
expect(response.status()).toBe(200);

// Wait for response matching condition
const responsePromise = page.waitForResponse(
  response => response.url().includes('/api/users') && response.status() === 200
);
await page.click('button');
await responsePromise;

// Wait for request
const requestPromise = page.waitForRequest('**/api/search?q=*');
await page.fill('input[name="search"]', 'laptop');
const request = await requestPromise;
expect(request.url()).toContain('q=laptop');
```

**Wait for function**:
```typescript
// Wait for custom condition
await page.waitForFunction(() => {
  return document.querySelectorAll('.item').length > 10;
});

// Wait for JS variable
await page.waitForFunction(() => window.appReady === true);

// Pass arguments to function
await page.waitForFunction(
  (minCount) => document.querySelectorAll('.item').length >= minCount,
  10 // minCount argument
);
```

**Wait for event**:
```typescript
// Wait for console message
const messagePromise = page.waitForEvent('console',
  msg => msg.type() === 'log' && msg.text().includes('Ready')
);
await page.click('button');
await messagePromise;

// Wait for dialog (alert, confirm, prompt)
const dialogPromise = page.waitForEvent('dialog');
await page.click('button');
const dialog = await dialogPromise;
expect(dialog.message()).toBe('Are you sure?');
await dialog.accept();

// Wait for download
const downloadPromise = page.waitForEvent('download');
await page.click('a[download]');
const download = await downloadPromise;
await download.saveAs('/path/to/save/file.pdf');
```

### Cypress Waiting

**Automatic retrying**:
```typescript
// Cypress automatically retries until assertion passes or timeout
cy.get('.result').should('be.visible');
cy.get('.count').should('have.text', '5');

// Configure timeout
cy.get('.slow-element', { timeout: 10000 }).should('exist');
```

**Explicit waits**:
```typescript
// Wait for element
cy.get('.loading').should('not.exist');

// Wait for URL
cy.url().should('include', '/dashboard');

// Wait for network request
cy.intercept('GET', '/api/users').as('getUsers');
cy.visit('/users');
cy.wait('@getUsers'); // Wait for API call

// Wait for multiple requests
cy.intercept('GET', '/api/users').as('getUsers');
cy.intercept('GET', '/api/posts').as('getPosts');
cy.visit('/dashboard');
cy.wait(['@getUsers', '@getPosts']); // Wait for both
```

### Selenium Explicit Waits

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Wait for element to be clickable
wait = WebDriverWait(driver, 10)
element = wait.until(EC.element_to_be_clickable((By.ID, 'submit-button')))
element.click()

# Wait for element to be visible
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'message')))

# Wait for text to be present
wait.until(EC.text_to_be_present_in_element((By.ID, 'status'), 'Complete'))

# Wait for URL to change
wait.until(EC.url_contains('/dashboard'))

# Custom condition
wait.until(lambda driver: len(driver.find_elements(By.CLASS_NAME, 'item')) > 5)
```

### Anti-Patterns: Bad Waiting

```typescript
// ❌ NEVER: Hard-coded sleep
await page.waitForTimeout(2000);
await sleep(2000);

// ❌ NEVER: Polling with fixed interval
while (true) {
  if (await page.locator('.result').isVisible()) break;
  await page.waitForTimeout(100);
}

// ❌ NEVER: Increasing timeouts without investigating
await page.click('button', { timeout: 60000 }); // Why so slow?

// ✅ DO: Investigate slow operations, optimize, then set reasonable timeout
await page.waitForResponse('**/api/slow-operation'); // Track what's slow
await page.click('button', { timeout: 10000 }); // Reasonable for this operation
```

---

## Authentication and Session Management

### Authentication Strategies

**1. Global Setup** (authenticate once, reuse state):

```typescript
// global-setup.ts
import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Login once
  await page.goto('https://example.com/login');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard');

  // Save authenticated state
  await page.context().storageState({ path: 'auth.json' });

  await browser.close();
}

export default globalSetup;
```

```typescript
// playwright.config.ts
export default defineConfig({
  globalSetup: require.resolve('./global-setup'),
  use: {
    storageState: 'auth.json', // All tests start authenticated
  },
});
```

```typescript
// Tests automatically start with auth state
test('access protected page', async ({ page }) => {
  await page.goto('/dashboard'); // Already logged in!
  await expect(page.locator('.welcome')).toBeVisible();
});
```

**2. Fixture-Based Authentication**:

```typescript
// fixtures/auth.ts
import { test as base } from '@playwright/test';

type AuthFixtures = {
  authenticatedPage: Page;
  adminPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Login as regular user
    await page.goto('/login');
    await page.fill('#username', 'user');
    await page.fill('#password', 'user123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');

    await use(page);
  },

  adminPage: async ({ page }, use) => {
    // Login as admin
    await page.goto('/login');
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin');

    await use(page);
  },
});

// Use in tests
test('user can view profile', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/profile');
  await expect(authenticatedPage.locator('h1')).toContainText('Profile');
});

test('admin can manage users', async ({ adminPage }) => {
  await adminPage.goto('/admin/users');
  await expect(adminPage.locator('.user-list')).toBeVisible();
});
```

**3. API-Based Authentication** (faster):

```typescript
// fixtures/api-auth.ts
export const test = base.extend({
  authenticatedPage: async ({ page, context }, use) => {
    // Get auth token via API (faster than UI login)
    const response = await context.request.post('https://api.example.com/login', {
      data: {
        username: 'user',
        password: 'user123',
      },
    });

    const { token } = await response.json();

    // Set auth token in cookies/localStorage
    await context.addCookies([{
      name: 'auth_token',
      value: token,
      domain: 'example.com',
      path: '/',
    }]);

    await use(page);
  },
});
```

**4. Helper Function**:

```typescript
// helpers/auth.ts
export async function login(
  page: Page,
  username: string,
  password: string
): Promise<void> {
  await page.goto('/login');
  await page.fill('#username', username);
  await page.fill('#password', password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard');
}

// Use in tests
test('user workflow', async ({ page }) => {
  await login(page, 'alice', 'secret');
  await page.goto('/profile');
  // ... rest of test
});
```

### Session Management

**Persist session across tests**:
```typescript
// Save session state
await page.context().storageState({ path: 'session.json' });

// Load session state in new test
const context = await browser.newContext({
  storageState: 'session.json',
});
const page = await context.newPage();
```

**Manage multiple sessions**:
```typescript
test('multi-user interaction', async ({ browser }) => {
  // User 1 context
  const user1Context = await browser.newContext({
    storageState: 'user1-session.json',
  });
  const user1Page = await user1Context.newPage();

  // User 2 context
  const user2Context = await browser.newContext({
    storageState: 'user2-session.json',
  });
  const user2Page = await user2Context.newPage();

  // Both users interact simultaneously
  await user1Page.goto('/chat/123');
  await user2Page.goto('/chat/123');

  await user1Page.fill('input', 'Hello from User 1');
  await user1Page.press('input', 'Enter');

  await expect(user2Page.locator('.message').last()).toContainText('Hello from User 1');
});
```

**Clear session**:
```typescript
// Clear cookies
await context.clearCookies();

// Clear localStorage/sessionStorage
await page.evaluate(() => {
  localStorage.clear();
  sessionStorage.clear();
});

// Start fresh context
await context.close();
const newContext = await browser.newContext();
```

### Handling Different Auth Types

**JWT Token**:
```typescript
// Store JWT in localStorage
await page.evaluate((token) => {
  localStorage.setItem('auth_token', token);
}, 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...');

// Or in cookie
await context.addCookies([{
  name: 'jwt',
  value: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
  domain: 'example.com',
  path: '/',
  httpOnly: true,
}]);
```

**OAuth/SSO**:
```typescript
// Mock OAuth provider
await page.route('https://oauth-provider.com/authorize', route => {
  route.fulfill({
    status: 302,
    headers: {
      'Location': 'https://example.com/callback?code=mock-auth-code',
    },
  });
});

await page.route('https://oauth-provider.com/token', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      access_token: 'mock-access-token',
      token_type: 'Bearer',
    }),
  });
});
```

**Basic Auth**:
```typescript
// Set basic auth credentials
const context = await browser.newContext({
  httpCredentials: {
    username: 'admin',
    password: 'admin123',
  },
});
```

### Cypress Authentication

```typescript
// Custom command (cypress/support/commands.ts)
Cypress.Commands.add('login', (username: string, password: string) => {
  cy.session([username, password], () => {
    cy.visit('/login');
    cy.get('#username').type(username);
    cy.get('#password').type(password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/dashboard');
  });
});

// Use in tests
describe('User workflows', () => {
  beforeEach(() => {
    cy.login('alice', 'secret'); // Cached per session
  });

  it('can view profile', () => {
    cy.visit('/profile');
    cy.contains('Profile').should('be.visible');
  });
});
```

**API-based login in Cypress**:
```typescript
Cypress.Commands.add('loginViaAPI', (username: string, password: string) => {
  cy.request('POST', '/api/login', { username, password })
    .then((response) => {
      window.localStorage.setItem('auth_token', response.body.token);
    });
});

// Faster than UI login
beforeEach(() => {
  cy.loginViaAPI('alice', 'secret');
  cy.visit('/dashboard');
});
```

---

## Test Data Management

### Test Data Strategies

**1. Fixtures** (static, predictable data):

```typescript
// fixtures/users.json
{
  "validUser": {
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecurePass123!"
  },
  "adminUser": {
    "username": "admin",
    "email": "admin@example.com",
    "password": "AdminPass123!"
  }
}
```

```typescript
// Use in tests
import users from './fixtures/users.json';

test('valid user can login', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#username', users.validUser.username);
  await page.fill('#password', users.validUser.password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/dashboard');
});
```

**2. Factories** (dynamic, randomized data):

```typescript
// factories/userFactory.ts
import { faker } from '@faker-js/faker';

export function createUser(overrides = {}) {
  return {
    id: faker.string.uuid(),
    username: faker.internet.userName(),
    email: faker.internet.email(),
    firstName: faker.person.firstName(),
    lastName: faker.person.lastName(),
    age: faker.number.int({ min: 18, max: 80 }),
    ...overrides,
  };
}

export function createAdmin() {
  return createUser({
    role: 'admin',
    permissions: ['read', 'write', 'delete'],
  });
}
```

```typescript
// Use in tests
import { createUser } from './factories/userFactory';

test('user registration', async ({ page }) => {
  const user = createUser();

  await page.goto('/register');
  await page.fill('#username', user.username);
  await page.fill('#email', user.email);
  await page.fill('#password', 'SecurePass123!');
  await page.click('button[type="submit"]');

  await expect(page.locator('.success')).toContainText(`Welcome, ${user.username}`);
});
```

**3. Database Seeding**:

```typescript
// helpers/database.ts
import { Pool } from 'pg';

export async function seedDatabase() {
  const pool = new Pool({ connectionString: process.env.TEST_DATABASE_URL });

  await pool.query(`
    INSERT INTO users (username, email, password_hash)
    VALUES
      ('alice', 'alice@example.com', '$2b$10$...'),
      ('bob', 'bob@example.com', '$2b$10$...')
  `);

  await pool.query(`
    INSERT INTO products (name, price, stock)
    VALUES
      ('Laptop', 999.99, 10),
      ('Mouse', 29.99, 50)
  `);

  await pool.end();
}

export async function cleanDatabase() {
  const pool = new Pool({ connectionString: process.env.TEST_DATABASE_URL });

  // Clean test database between test runs
  await pool.query('TRUNCATE users, products, orders CASCADE');

  await pool.end();
}
```

```typescript
// Use in tests
import { test } from '@playwright/test';
import { seedDatabase, cleanDatabase } from './helpers/database';

test.beforeEach(async () => {
  await cleanDatabase();
  await seedDatabase();
});

test('user can purchase product', async ({ page }) => {
  // Database already has users and products seeded
  await page.goto('/products');
  await page.click('text=Laptop');
  await page.click('button:has-text("Add to Cart")');
  // ... rest of test
});
```

**4. API-Based Setup**:

```typescript
// Setup test data via API (faster than UI)
test.beforeEach(async ({ request }) => {
  // Create user via API
  await request.post('/api/users', {
    data: {
      username: 'testuser',
      email: 'test@example.com',
      password: 'SecurePass123!',
    },
  });

  // Create products via API
  await request.post('/api/products', {
    data: {
      name: 'Test Product',
      price: 99.99,
      stock: 10,
    },
  });
});
```

### Data Cleanup

**Per-test cleanup**:
```typescript
test('user workflow', async ({ page, request }) => {
  // Test creates data
  const response = await request.post('/api/users', {
    data: { username: 'tempuser', email: 'temp@example.com' },
  });
  const userId = (await response.json()).id;

  // ... test logic

  // Cleanup
  await request.delete(`/api/users/${userId}`);
});
```

**After each cleanup**:
```typescript
test.afterEach(async ({ request }) => {
  // Clean up all test data
  await request.post('/api/test/cleanup');
});
```

**Database transactions** (rollback after test):
```typescript
import { test as base } from '@playwright/test';
import { Pool } from 'pg';

const test = base.extend({
  db: async ({}, use) => {
    const pool = new Pool({ connectionString: process.env.TEST_DATABASE_URL });
    const client = await pool.connect();

    await client.query('BEGIN'); // Start transaction

    await use(client);

    await client.query('ROLLBACK'); // Rollback all changes
    client.release();
    await pool.end();
  },
});

test('database test', async ({ db }) => {
  // Any database changes will be rolled back
  await db.query('INSERT INTO users (username) VALUES ($1)', ['testuser']);
  // ... test logic
}); // Automatic rollback
```

### Handling File Uploads

**Upload test files**:
```typescript
test('upload profile picture', async ({ page }) => {
  await page.goto('/profile');

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('path/to/test-image.png');

  await page.click('button:has-text("Upload")');
  await expect(page.locator('.success-message')).toBeVisible();
});
```

**Upload multiple files**:
```typescript
await fileInput.setInputFiles([
  'path/to/file1.pdf',
  'path/to/file2.pdf',
]);
```

**Generate file on-the-fly**:
```typescript
const buffer = Buffer.from('Test file content');
await fileInput.setInputFiles({
  name: 'test.txt',
  mimeType: 'text/plain',
  buffer: buffer,
});
```

### Test Data Patterns

**Builder Pattern**:
```typescript
class UserBuilder {
  private user: Partial<User> = {};

  withUsername(username: string) {
    this.user.username = username;
    return this;
  }

  withEmail(email: string) {
    this.user.email = email;
    return this;
  }

  asAdmin() {
    this.user.role = 'admin';
    return this;
  }

  build(): User {
    return {
      id: faker.string.uuid(),
      username: this.user.username || faker.internet.userName(),
      email: this.user.email || faker.internet.email(),
      role: this.user.role || 'user',
    };
  }
}

// Use in tests
const admin = new UserBuilder()
  .withUsername('admin')
  .asAdmin()
  .build();

const user = new UserBuilder().build(); // All defaults
```

---

## Network Interception and Mocking

### Why Mock Network Requests?

**Benefits**:
1. **Speed**: No real API calls, tests run faster
2. **Reliability**: No dependency on external services
3. **Control**: Test edge cases (errors, timeouts, specific responses)
4. **Isolation**: Test frontend independently from backend
5. **Offline testing**: Tests work without internet

**When to mock**:
- External APIs (payment, weather, maps)
- Slow endpoints (reports, analytics)
- Error scenarios (500 errors, timeouts)
- Rate-limited APIs
- Testing UI with specific data

**When NOT to mock**:
- Your own backend (use integration tests)
- Critical user paths (test real flow)
- Simple requests (mocking adds complexity)

### Playwright Network Interception

**Basic mocking**:
```typescript
test('displays users from API', async ({ page }) => {
  // Intercept and mock API response
  await page.route('**/api/users', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 1, name: 'Alice', email: 'alice@example.com' },
        { id: 2, name: 'Bob', email: 'bob@example.com' },
      ]),
    });
  });

  await page.goto('/users');

  await expect(page.locator('.user-item')).toHaveCount(2);
  await expect(page.locator('.user-item').first()).toContainText('Alice');
});
```

**Mock errors**:
```typescript
test('handles API errors gracefully', async ({ page }) => {
  await page.route('**/api/users', route => {
    route.fulfill({ status: 500, body: 'Internal Server Error' });
  });

  await page.goto('/users');
  await expect(page.locator('.error-message')).toBeVisible();
  await expect(page.locator('.error-message')).toContainText('Failed to load users');
});
```

**Conditional routing**:
```typescript
await page.route('**/api/users', route => {
  const url = new URL(route.request().url());
  const page = url.searchParams.get('page');

  if (page === '1') {
    route.fulfill({
      status: 200,
      body: JSON.stringify({ users: [...], hasMore: true }),
    });
  } else {
    route.fulfill({
      status: 200,
      body: JSON.stringify({ users: [], hasMore: false }),
    });
  }
});
```

**Verify request payload**:
```typescript
test('sends correct data to API', async ({ page }) => {
  let requestBody: any;

  await page.route('**/api/users', async route => {
    requestBody = route.request().postDataJSON();
    await route.fulfill({
      status: 201,
      body: JSON.stringify({ id: 123, ...requestBody }),
    });
  });

  await page.goto('/users/new');
  await page.fill('#name', 'Alice');
  await page.fill('#email', 'alice@example.com');
  await page.click('button[type="submit"]');

  expect(requestBody).toEqual({
    name: 'Alice',
    email: 'alice@example.com',
  });
});
```

**Pass through unmatched requests**:
```typescript
await page.route('**/*', route => {
  const url = route.request().url();

  if (url.includes('/api/mock-me')) {
    route.fulfill({ status: 200, body: '{"mocked": true}' });
  } else {
    route.continue(); // Let real request happen
  }
});
```

**Load response from file**:
```typescript
await page.route('**/api/users', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    path: 'fixtures/users-response.json',
  });
});
```

**Simulate network delays**:
```typescript
await page.route('**/api/slow-endpoint', async route => {
  await new Promise(resolve => setTimeout(resolve, 3000)); // 3s delay
  route.fulfill({ status: 200, body: '{"data": "slow"}' });
});

test('shows loading state during slow request', async ({ page }) => {
  const loadingPromise = page.waitForSelector('.loading-spinner');

  page.goto('/slow-page');

  await loadingPromise;
  await expect(page.locator('.loading-spinner')).toBeVisible();
  await expect(page.locator('.loading-spinner')).not.toBeVisible({ timeout: 5000 });
});
```

### Advanced Mocking Patterns

**Request counter**:
```typescript
test('retries failed requests', async ({ page }) => {
  let attemptCount = 0;

  await page.route('**/api/unstable', route => {
    attemptCount++;

    if (attemptCount < 3) {
      route.fulfill({ status: 500 }); // Fail first 2 attempts
    } else {
      route.fulfill({ status: 200, body: '{"success": true}' });
    }
  });

  await page.goto('/page-with-retry-logic');

  await expect(page.locator('.success-message')).toBeVisible();
  expect(attemptCount).toBe(3);
});
```

**Mock with HAR files** (recorded network traffic):
```typescript
// Record network traffic
await page.routeFromHAR('traffic.har', { update: true });
await page.goto('/users');
// Interactions recorded to traffic.har

// Replay from HAR
await page.routeFromHAR('traffic.har');
await page.goto('/users'); // Uses recorded responses
```

### Cypress Interception

```typescript
describe('Network mocking', () => {
  beforeEach(() => {
    // Intercept and alias request
    cy.intercept('GET', '/api/users', {
      statusCode: 200,
      body: [
        { id: 1, name: 'Alice' },
        { id: 2, name: 'Bob' },
      ],
    }).as('getUsers');
  });

  it('displays mocked users', () => {
    cy.visit('/users');

    // Wait for request
    cy.wait('@getUsers');

    cy.get('.user-item').should('have.length', 2);
    cy.get('.user-item').first().should('contain', 'Alice');
  });
});
```

**Mock from fixture**:
```typescript
cy.intercept('GET', '/api/users', { fixture: 'users.json' }).as('getUsers');
```

**Spy on requests** (don't modify):
```typescript
cy.intercept('POST', '/api/users').as('createUser');

cy.get('#name').type('Alice');
cy.get('button[type="submit"]').click();

cy.wait('@createUser').its('request.body').should('deep.equal', {
  name: 'Alice',
});
```

---

## Visual Regression Testing

### What is Visual Regression Testing?

**Visual regression testing** detects unintended visual changes by comparing screenshots.

**Use cases**:
- Detect CSS changes affecting layout
- Catch cross-browser rendering differences
- Verify responsive design
- Ensure UI consistency across features
- Prevent visual bugs in production

**How it works**:
1. **Baseline**: Capture screenshot of current "correct" state
2. **Test**: Run tests, capture new screenshots
3. **Compare**: Pixel-by-pixel comparison
4. **Review**: Approve or reject differences

### Playwright Visual Testing

**Basic screenshot comparison**:
```typescript
test('homepage visual regression', async ({ page }) => {
  await page.goto('/');

  // Compare against baseline
  await expect(page).toHaveScreenshot('homepage.png', {
    fullPage: true,
  });
});
```

**First run**: Creates `homepage.png` baseline in test artifacts.
**Subsequent runs**: Compares current screenshot to baseline, fails if different.

**Element-level screenshots**:
```typescript
test('button visual states', async ({ page }) => {
  await page.goto('/components');

  const button = page.locator('.primary-button');

  // Default state
  await expect(button).toHaveScreenshot('button-default.png');

  // Hover state
  await button.hover();
  await expect(button).toHaveScreenshot('button-hover.png');

  // Focus state
  await button.focus();
  await expect(button).toHaveScreenshot('button-focus.png');

  // Disabled state
  await page.evaluate(() => {
    document.querySelector('.primary-button').setAttribute('disabled', '');
  });
  await expect(button).toHaveScreenshot('button-disabled.png');
});
```

**Configure tolerance**:
```typescript
await expect(page).toHaveScreenshot('homepage.png', {
  maxDiffPixels: 100,        // Allow up to 100 pixels difference
  maxDiffPixelRatio: 0.01,   // Allow 1% pixel difference
  threshold: 0.2,            // Color difference threshold (0-1)
});
```

**Mask dynamic content**:
```typescript
await expect(page).toHaveScreenshot('dashboard.png', {
  mask: [
    page.locator('.current-time'),     // Hide timestamp
    page.locator('.live-data'),        // Hide live-updating data
    page.locator('.user-avatar'),      // Hide user-specific content
  ],
});
```

**Animations**:
```typescript
// Disable animations before screenshot
await page.addStyleTag({
  content: `
    *, *::before, *::after {
      animation-duration: 0s !important;
      transition-duration: 0s !important;
    }
  `,
});

await expect(page).toHaveScreenshot('no-animations.png');
```

### Cross-Browser Visual Testing

```typescript
import { test, devices } from '@playwright/test';

test.use({ browserName: 'chromium' });
test('renders correctly in Chrome', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('chrome-homepage.png');
});

test.use({ browserName: 'firefox' });
test('renders correctly in Firefox', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('firefox-homepage.png');
});

test.use({ browserName: 'webkit' });
test('renders correctly in Safari', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('webkit-homepage.png');
});
```

### Responsive Visual Testing

```typescript
const devices = [
  { name: 'iPhone 12', viewport: { width: 390, height: 844 } },
  { name: 'iPad Pro', viewport: { width: 1024, height: 1366 } },
  { name: 'Desktop', viewport: { width: 1920, height: 1080 } },
];

devices.forEach(({ name, viewport }) => {
  test(`visual test on ${name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');
    await expect(page).toHaveScreenshot(`homepage-${name}.png`, {
      fullPage: true,
    });
  });
});
```

### Percy Visual Testing

**Percy** is a visual testing service with smart diffing and review UI.

```typescript
// Install: npm install --save-dev @percy/playwright
import percySnapshot from '@percy/playwright';

test('homepage visual test', async ({ page }) => {
  await page.goto('/');

  // Send screenshot to Percy
  await percySnapshot(page, 'Homepage');
});

test('responsive snapshots', async ({ page }) => {
  await page.goto('/');

  // Multiple viewport sizes
  await percySnapshot(page, 'Homepage', {
    widths: [375, 768, 1280],
  });
});
```

### Handling Visual Test Failures

**1. Review differences**:
```bash
# Playwright opens visual diff viewer
npx playwright test --update-snapshots
```

**2. Update baselines** (if intentional change):
```bash
# Update all snapshots
npx playwright test --update-snapshots

# Update specific test
npx playwright test homepage.spec.ts --update-snapshots
```

**3. Investigate regression**:
- Check CSS changes in recent commits
- Verify browser version consistency
- Look for timing issues (animations, async content)
- Check for anti-aliasing differences

### Best Practices

**DO**:
- Visual test critical pages (homepage, checkout, dashboard)
- Disable animations and transitions
- Mask dynamic content (timestamps, live data)
- Use consistent browser versions
- Review visual changes before approving

**DON'T**:
- Visual test every page (too slow, too many baselines)
- Include timestamps or user-specific content
- Rely on visual tests for functional logic
- Ignore small, unintended differences

---

## Cross-Browser Testing

### Browser Market Share Strategy

**Prioritize browsers by user base**:
```
Chrome/Edge (Chromium): 65%  → High priority
Safari (WebKit):        20%  → High priority
Firefox:                5%   → Medium priority
Others:                 10%  → Low priority
```

**Testing strategy**:
- **Tier 1** (Chrome, Safari): Test all features, all tests
- **Tier 2** (Firefox): Critical paths only
- **Tier 3** (Edge, Samsung Internet): Smoke tests or skip

### Playwright Multi-Browser Config

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
});
```

**Run all browsers**:
```bash
npx playwright test  # Runs in all configured browsers
```

**Run specific browser**:
```bash
npx playwright test --project=webkit
npx playwright test --project="Mobile Safari"
```

### Browser-Specific Tests

```typescript
test.describe('browser-specific features', () => {
  test('webkit-only test', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'Safari-only test');

    // Safari-specific test
    await page.goto('/');
    // ...
  });

  test('chromium-only test', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Chrome-only test');

    // Chrome-specific test
    await page.goto('/');
    // ...
  });
});
```

### Handling Browser Differences

**User-Agent detection**:
```typescript
test('adapts to browser', async ({ page, browserName }) => {
  await page.goto('/');

  if (browserName === 'webkit') {
    // Safari has different date picker
    await page.click('input[type="date"]');
    await page.selectOption('select', '2024-10-27');
  } else {
    // Chrome/Firefox have standard date input
    await page.fill('input[type="date"]', '2024-10-27');
  }
});
```

**Browser capabilities**:
```typescript
const supportsWebP = await page.evaluate(() => {
  const elem = document.createElement('canvas');
  return elem.toDataURL('image/webp').indexOf('data:image/webp') === 0;
});

if (supportsWebP) {
  await expect(page.locator('img')).toHaveAttribute('src', /\.webp$/);
} else {
  await expect(page.locator('img')).toHaveAttribute('src', /\.png$/);
}
```

### Cross-Browser Best Practices

**Avoid browser-specific APIs**:
```typescript
// ❌ Bad: Chrome-only API
await page.evaluate(() => {
  navigator.share({ title: 'Test', url: 'https://example.com' });
});

// ✅ Good: Feature detection
await page.evaluate(() => {
  if (navigator.share) {
    navigator.share({ title: 'Test', url: 'https://example.com' });
  } else {
    // Fallback for browsers without Web Share API
    window.copyToClipboard('https://example.com');
  }
});
```

**CSS vendor prefixes**:
```typescript
// Verify cross-browser CSS
test('element styling cross-browser', async ({ page }) => {
  await page.goto('/');

  const box = page.locator('.animated-box');
  const transform = await box.evaluate(el => {
    return window.getComputedStyle(el).transform;
  });

  expect(transform).not.toBe('none');
});
```

---

## Handling Complex Interactions

### File Uploads

**Single file**:
```typescript
test('upload profile picture', async ({ page }) => {
  await page.goto('/profile');

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('path/to/profile.jpg');

  await page.click('button:has-text("Upload")');
  await expect(page.locator('.success-message')).toBeVisible();
});
```

**Multiple files**:
```typescript
await fileInput.setInputFiles([
  'path/to/file1.pdf',
  'path/to/file2.pdf',
  'path/to/file3.pdf',
]);
```

**Remove files**:
```typescript
await fileInput.setInputFiles([]); // Clear file selection
```

**Generate file dynamically**:
```typescript
const buffer = Buffer.from('Test file content');
await fileInput.setInputFiles({
  name: 'test-file.txt',
  mimeType: 'text/plain',
  buffer: buffer,
});
```

### Drag and Drop

**HTML5 drag and drop**:
```typescript
test('reorder list items', async ({ page }) => {
  await page.goto('/kanban');

  const source = page.locator('.task[data-id="1"]');
  const target = page.locator('.column[data-status="done"]');

  await source.dragTo(target);

  await expect(target.locator('.task[data-id="1"]')).toBeVisible();
});
```

**Drag to position**:
```typescript
await page.locator('.draggable').drag To(page.locator('.drop-zone'), {
  targetPosition: { x: 100, y: 50 },
});
```

**Manual drag** (for complex cases):
```typescript
const source = page.locator('.draggable');
const sourceBbox = await source.boundingBox();

await page.mouse.move(sourceBbox.x + sourceBbox.width / 2, sourceBbox.y + sourceBbox.height / 2);
await page.mouse.down();
await page.mouse.move(500, 300);
await page.mouse.up();
```

### Keyboard Navigation

**Basic keys**:
```typescript
await page.keyboard.press('Enter');
await page.keyboard.press('Escape');
await page.keyboard.press('Tab');
await page.keyboard.press('ArrowDown');
```

**Modifiers**:
```typescript
await page.keyboard.press('Control+A');   // Select all
await page.keyboard.press('Meta+C');      // Copy (Cmd on Mac)
await page.keyboard.press('Shift+Tab');   // Reverse tab
```

**Type text**:
```typescript
await page.keyboard.type('Hello, world!');
await page.keyboard.type('test@example.com', { delay: 100 }); // Slow typing
```

**Complex keyboard interaction**:
```typescript
test('navigate menu with keyboard', async ({ page }) => {
  await page.goto('/');

  await page.keyboard.press('Tab');       // Focus first element
  await page.keyboard.press('Enter');     // Open menu
  await page.keyboard.press('ArrowDown'); // Navigate to second item
  await page.keyboard.press('ArrowDown'); // Third item
  await page.keyboard.press('Enter');     // Select

  await expect(page).toHaveURL('/selected-page');
});
```

### Mouse Interactions

**Click positions**:
```typescript
await page.click('.button', { button: 'right' });    // Right-click
await page.click('.button', { clickCount: 2 });      // Double-click
await page.click('.button', { position: { x: 10, y: 10 } }); // Click at offset
```

**Hover**:
```typescript
await page.hover('.dropdown-trigger');
await expect(page.locator('.dropdown-menu')).toBeVisible();
```

**Mouse wheel**:
```typescript
await page.mouse.wheel(0, 500); // Scroll down 500px
```

### Iframes

**Access iframe content**:
```typescript
test('interact with iframe', async ({ page }) => {
  await page.goto('/page-with-iframe');

  // Get iframe by selector
  const frame = page.frameLocator('#my-iframe');

  // Interact with elements inside iframe
  await frame.locator('#username').fill('alice');
  await frame.locator('#password').fill('secret');
  await frame.locator('button[type="submit"]').click();

  await expect(frame.locator('.success')).toBeVisible();
});
```

**Multiple iframes**:
```typescript
const frame1 = page.frameLocator('iframe[name="frame1"]');
const frame2 = page.frameLocator('iframe[name="frame2"]');

await frame1.locator('button').click();
await frame2.locator('input').fill('text');
```

### Shadow DOM

```typescript
test('interact with shadow DOM', async ({ page }) => {
  await page.goto('/shadow-dom-page');

  // Playwright automatically pierces shadow DOM
  await page.locator('my-component >>> button').click();

  // Or use specific method
  const shadowRoot = await page.locator('my-component').evaluateHandle(
    el => el.shadowRoot
  );
  await shadowRoot.locator('button').click();
});
```

### Browser Dialogs

**Alert, confirm, prompt**:
```typescript
test('handle browser dialogs', async ({ page }) => {
  // Auto-accept dialogs
  page.on('dialog', dialog => dialog.accept());

  await page.goto('/');
  await page.click('button:has-text("Delete")');
  // Alert auto-accepted
});

test('verify dialog message', async ({ page }) => {
  page.on('dialog', async dialog => {
    expect(dialog.message()).toBe('Are you sure?');
    expect(dialog.type()).toBe('confirm');
    await dialog.accept();
  });

  await page.click('button:has-text("Delete")');
});

test('enter prompt text', async ({ page }) => {
  page.on('dialog', async dialog => {
    await dialog.accept('My custom input');
  });

  await page.click('button:has-text("Enter name")');
});
```

### New Windows/Tabs

```typescript
test('handle new window', async ({ page, context }) => {
  await page.goto('/');

  // Wait for new page to open
  const [newPage] = await Promise.all([
    context.waitForEvent('page'),
    page.click('a[target="_blank"]'),
  ]);

  await newPage.waitForLoadState();
  expect(newPage.url()).toContain('/new-page');

  await newPage.close();
});
```

### Geolocation

```typescript
test('override geolocation', async ({ page, context }) => {
  await context.setGeolocation({ latitude: 37.7749, longitude: -122.4194 });
  await context.grantPermissions(['geolocation']);

  await page.goto('/map');

  const location = await page.locator('.current-location').textContent();
  expect(location).toContain('San Francisco');
});
```

---

## Test Organization and Structure

### Directory Structure

**Recommended layout**:
```
tests/
├── e2e/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   ├── register.spec.ts
│   │   └── logout.spec.ts
│   ├── products/
│   │   ├── browse.spec.ts
│   │   ├── search.spec.ts
│   │   └── details.spec.ts
│   ├── checkout/
│   │   ├── cart.spec.ts
│   │   ├── payment.spec.ts
│   │   └── confirmation.spec.ts
│   └── admin/
│       ├── users.spec.ts
│       └── settings.spec.ts
├── pages/
│   ├── LoginPage.ts
│   ├── ProductPage.ts
│   ├── CheckoutPage.ts
│   └── components/
│       ├── Header.ts
│       └── Footer.ts
├── fixtures/
│   ├── users.json
│   ├── products.json
│   └── test-data.ts
├── helpers/
│   ├── auth.ts
│   ├── database.ts
│   └── api.ts
└── playwright.config.ts
```

### Test File Organization

**Group related tests**:
```typescript
// tests/e2e/auth/login.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage';

test.describe('Login', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test.describe('Valid credentials', () => {
    test('user can login with email', async () => {
      await loginPage.login('alice@example.com', 'secret');
      await expect(loginPage.welcomeMessage).toBeVisible();
    });

    test('user can login with username', async () => {
      await loginPage.login('alice', 'secret');
      await expect(loginPage.welcomeMessage).toBeVisible();
    });
  });

  test.describe('Invalid credentials', () => {
    test('shows error on wrong password', async () => {
      await loginPage.login('alice@example.com', 'wrong');
      await loginPage.expectError('Invalid credentials');
    });

    test('shows error on non-existent user', async () => {
      await loginPage.login('nobody@example.com', 'secret');
      await loginPage.expectError('User not found');
    });
  });
});
```

### Test Hooks

**Before/after hooks**:
```typescript
test.beforeAll(async () => {
  // Runs once before all tests in file
  await setupDatabase();
});

test.beforeEach(async ({ page }) => {
  // Runs before each test
  await page.goto('/');
});

test.afterEach(async ({ page }, testInfo) => {
  // Runs after each test
  if (testInfo.status !== 'passed') {
    await page.screenshot({ path: `failure-${testInfo.title}.png` });
  }
});

test.afterAll(async () => {
  // Runs once after all tests in file
  await cleanupDatabase();
});
```

### Fixtures

**Custom fixtures**:
```typescript
// fixtures/index.ts
import { test as base } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';

type CustomFixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  authenticatedUser: void;
};

export const test = base.extend<CustomFixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },

  authenticatedUser: async ({ page, loginPage }, use) => {
    await loginPage.goto();
    await loginPage.login('user@example.com', 'password');
    await use();
  },
});

// Use in tests
test('user can access dashboard', async ({ authenticatedUser, dashboardPage }) => {
  await dashboardPage.goto();
  await expect(dashboardPage.title).toBeVisible();
});
```

### Test Tags

**Organize with tags**:
```typescript
test('@smoke @critical user can login', async ({ page }) => {
  // Critical smoke test
});

test('@regression user profile update', async ({ page }) => {
  // Full regression test
});
```

**Run tagged tests**:
```bash
npx playwright test --grep @smoke
npx playwright test --grep "@critical|@smoke"
npx playwright test --grep-invert @slow  # Skip slow tests
```

### Parameterized Tests

**Test with different data**:
```typescript
const browsers = ['Chrome', 'Firefox', 'Safari'];

browsers.forEach(browser => {
  test(`works in ${browser}`, async ({ page }) => {
    // Test logic
  });
});

// Or use test.describe.configure
const credentials = [
  { user: 'alice', pass: 'secret1' },
  { user: 'bob', pass: 'secret2' },
  { user: 'charlie', pass: 'secret3' },
];

credentials.forEach(({ user, pass }) => {
  test(`${user} can login`, async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(user, pass);
    await expect(loginPage.welcomeMessage).toBeVisible();
  });
});
```

---

## Flakiness Reduction Techniques

### What Makes Tests Flaky?

**Flaky test**: Passes sometimes, fails sometimes, without code changes.

**Common causes**:
1. **Race conditions**: Async operations complete in unpredictable order
2. **Timing issues**: Elements not ready when test interacts
3. **Non-deterministic data**: Random IDs, timestamps, shuffled order
4. **External dependencies**: Network, third-party APIs
5. **State pollution**: Tests depend on order or shared state
6. **Browser quirks**: Rendering differences, animation timing

### Technique 1: Proper Waiting

**❌ Flaky: Fixed waits**:
```typescript
await page.click('button');
await page.waitForTimeout(1000); // Might be too short or too long
await expect(page.locator('.result')).toBeVisible();
```

**✅ Stable: Wait for actual condition**:
```typescript
await page.click('button');
await page.waitForSelector('.result', { state: 'visible' });
await expect(page.locator('.result')).toBeVisible();
```

### Technique 2: Stable Selectors

**❌ Flaky: Fragile selectors**:
```typescript
await page.click('div > div > button:nth-child(3)'); // Breaks with DOM changes
await page.click('.btn-primary'); // Breaks with CSS refactoring
```

**✅ Stable: Test IDs and semantic selectors**:
```typescript
await page.click('[data-testid="submit-button"]');
await page.getByRole('button', { name: 'Submit' }).click();
```

### Technique 3: Idempotent Tests

**❌ Flaky: Tests depend on order**:
```typescript
test('create user', async () => {
  await createUser('alice'); // Fails if alice already exists
});

test('delete user', async () => {
  await deleteUser('alice'); // Depends on previous test
});
```

**✅ Stable: Independent tests**:
```typescript
test('create user', async () => {
  const username = `user-${Date.now()}`; // Unique user
  await createUser(username);
  // Cleanup
  await deleteUser(username);
});

test('delete user', async () => {
  const username = `user-${Date.now()}`;
  await createUser(username);
  await deleteUser(username);
  // Verify deletion
});
```

### Technique 4: Explicit Assertions

**❌ Flaky: Implicit assumptions**:
```typescript
await page.click('button');
const text = await page.locator('.result').textContent();
// Element might not be ready
```

**✅ Stable: Explicit waits and assertions**:
```typescript
await page.click('button');
await page.waitForSelector('.result', { state: 'visible' });
const text = await page.locator('.result').textContent();
expect(text).toBeTruthy();
```

### Technique 5: Isolation

**❌ Flaky: Shared state**:
```typescript
let user = null;

test.beforeAll(async () => {
  user = await createUser(); // Shared across tests
});

test('test 1', async () => {
  await updateUser(user); // Modifies shared state
});

test('test 2', async () => {
  await deleteUser(user); // Breaks test 3
});
```

**✅ Stable: Isolated state**:
```typescript
test.beforeEach(async () => {
  // Fresh user for each test
  const user = await createUser();
  return user;
});

test.afterEach(async ({ user }) => {
  await deleteUser(user); // Clean up
});
```

### Technique 6: Retry Logic

**Playwright auto-retries**:
```typescript
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 2 : 0, // Retry failed tests in CI
});
```

**Custom retry for specific operation**:
```typescript
async function retryOperation<T>(
  operation: () => Promise<T>,
  maxAttempts = 3
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }
  throw new Error('Should not reach here');
}

test('unstable operation', async ({ page }) => {
  await retryOperation(async () => {
    await page.click('button');
    await expect(page.locator('.result')).toBeVisible({ timeout: 5000 });
  });
});
```

### Technique 7: Disable Animations

**Animations cause timing issues**:
```typescript
test.beforeEach(async ({ page }) => {
  // Disable all animations
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `,
  });
});
```

### Technique 8: Network Stability

**❌ Flaky: Real network calls**:
```typescript
test('fetch users', async ({ page }) => {
  await page.goto('/users');
  // Real API call - might timeout or fail
});
```

**✅ Stable: Mock network**:
```typescript
test('fetch users', async ({ page }) => {
  await page.route('**/api/users', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify([{ id: 1, name: 'Alice' }]),
    });
  });

  await page.goto('/users');
  // Deterministic, always works
});
```

### Technique 9: Parallelization Safety

**❌ Flaky: Shared resources**:
```typescript
test('test 1', async () => {
  await createUser('alice'); // Conflicts with parallel test
});

test('test 2', async () => {
  await createUser('alice'); // Fails - user exists
});
```

**✅ Stable: Unique resources**:
```typescript
test('test 1', async () => {
  await createUser(`alice-${test.info().testId}`);
});

test('test 2', async () => {
  await createUser(`alice-${test.info().testId}`);
});
```

### Technique 10: Logging and Debugging

**Add detailed logging**:
```typescript
test('debug flaky test', async ({ page }) => {
  page.on('console', msg => console.log('CONSOLE:', msg.text()));
  page.on('request', req => console.log('REQUEST:', req.url()));
  page.on('response', res => console.log('RESPONSE:', res.url(), res.status()));

  await page.goto('/');
  await page.click('button');
  await expect(page.locator('.result')).toBeVisible();
});
```

---

## Parallelization and Performance

### Playwright Parallelization

**Default parallel execution**:
```typescript
// playwright.config.ts
export default defineConfig({
  fullyParallel: true, // Run tests in parallel within file
  workers: process.env.CI ? 2 : undefined, // 2 workers in CI, max in local
});
```

**Run tests**:
```bash
npx playwright test  # Automatically parallelized
```

**Control parallelization**:
```typescript
// Disable parallel for specific file
test.describe.configure({ mode: 'serial' });

test('test 1', async ({ page }) => { });
test('test 2', async ({ page }) => { }); // Runs after test 1
```

### Performance Optimization

**1. Reuse authentication state**:
```typescript
// Global setup (runs once)
async function globalSetup() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('/login');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'password');
  await page.click('button[type="submit"]');
  await page.context().storageState({ path: 'auth.json' });
  await browser.close();
}

// Tests reuse auth (no login per test)
test.use({ storageState: 'auth.json' });
```

**2. Mock slow APIs**:
```typescript
test.beforeEach(async ({ page }) => {
  // Mock slow analytics API
  await page.route('**/api/analytics', route => {
    route.fulfill({ status: 200, body: '{}' });
  });
});
```

**3. Limit visual regression tests**:
```typescript
// Only visual test critical pages
test('@visual homepage', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png');
});

// Skip visual tests in local development
test('@visual checkout', async ({ page }) => {
  test.skip(!process.env.CI, 'Visual tests only in CI');
  await page.goto('/checkout');
  await expect(page).toHaveScreenshot('checkout.png');
});
```

**4. Use API for test setup**:
```typescript
// ❌ Slow: Create user via UI
test('user workflow', async ({ page }) => {
  await page.goto('/register');
  await page.fill('#username', 'alice');
  await page.fill('#email', 'alice@example.com');
  await page.click('button[type="submit"]');
  // ... rest of test
});

// ✅ Fast: Create user via API
test('user workflow', async ({ page, request }) => {
  await request.post('/api/users', {
    data: { username: 'alice', email: 'alice@example.com' },
  });

  await page.goto('/login');
  // ... rest of test
});
```

**5. Share expensive resources**:
```typescript
// Shared browser context (faster than new context per test)
test.use({
  // Reuse browser context across tests
  storageState: 'auth.json',
});
```

### Sharding (Distribute Tests)

**Split tests across machines**:
```bash
# Machine 1: Run shard 1 of 4
npx playwright test --shard=1/4

# Machine 2: Run shard 2 of 4
npx playwright test --shard=2/4

# Machine 3: Run shard 3 of 4
npx playwright test --shard=3/4

# Machine 4: Run shard 4 of 4
npx playwright test --shard=4/4
```

**GitHub Actions sharding**:
```yaml
name: E2E Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install
      - run: npx playwright test --shard=${{ matrix.shard }}/4
```

### Test Duration Optimization

**Profile test duration**:
```bash
npx playwright test --reporter=html
# Open report, sort by duration, investigate slowest tests
```

**Set timeouts appropriately**:
```typescript
// playwright.config.ts
export default defineConfig({
  timeout: 30000, // 30 seconds per test (default)
  expect: {
    timeout: 5000, // 5 seconds for assertions
  },
});

// Override for specific test
test('slow test', async ({ page }) => {
  test.setTimeout(60000); // 60 seconds for this test
  await page.goto('/slow-page');
});
```

---

## CI/CD Integration

### GitHub Actions

**Basic Playwright workflow**:
```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npx playwright test

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: screenshots
          path: test-results/
```

**Matrix strategy** (multiple browsers):
```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        browser: [chromium, firefox, webkit]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test --project=${{ matrix.browser }}
```

**Sharding** (parallel execution):
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test --shard=${{ matrix.shard }}/4
```

### GitLab CI

```yaml
# .gitlab-ci.yml
e2e_tests:
  image: mcr.microsoft.com/playwright:v1.40.0-focal
  stage: test
  script:
    - npm ci
    - npx playwright test
  artifacts:
    when: always
    paths:
      - playwright-report/
      - test-results/
    expire_in: 1 week
```

### CircleCI

```yaml
# .circleci/config.yml
version: 2.1
orbs:
  node: circleci/node@5.0
jobs:
  e2e:
    docker:
      - image: mcr.microsoft.com/playwright:v1.40.0-focal
    steps:
      - checkout
      - node/install-packages
      - run:
          name: Run E2E tests
          command: npx playwright test
      - store_artifacts:
          path: playwright-report
      - store_test_results:
          path: test-results
workflows:
  test:
    jobs:
      - e2e
```

### Environment Configuration

**Separate test environments**:
```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    baseURL: process.env.CI
      ? 'https://staging.example.com'
      : 'http://localhost:3000',
  },
});
```

**Environment variables**:
```yaml
# GitHub Actions
- name: Run E2E tests
  run: npx playwright test
  env:
    API_URL: https://api.staging.example.com
    TEST_USER: ${{ secrets.TEST_USER }}
    TEST_PASSWORD: ${{ secrets.TEST_PASSWORD }}
```

### Retry and Failure Handling

```typescript
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 2 : 0, // Retry failed tests twice in CI
  reporter: [
    ['html'],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['github'], // GitHub Actions annotations
  ],
});
```

---

## Debugging Strategies

### Playwright Debugging

**Debug mode**:
```bash
# Run with debugger
PWDEBUG=1 npx playwright test

# Debug specific test
PWDEBUG=1 npx playwright test tests/login.spec.ts

# Headed mode (see browser)
npx playwright test --headed

# Debug with UI
npx playwright test --debug
```

**Pause execution**:
```typescript
test('debug test', async ({ page }) => {
  await page.goto('/');

  await page.pause(); // Pauses execution, opens inspector

  await page.click('button');
});
```

**Screenshots and videos**:
```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry', // Detailed trace for failed tests
  },
});
```

**View trace**:
```bash
npx playwright show-trace test-results/trace.zip
```

**Console logs**:
```typescript
test('log console messages', async ({ page }) => {
  page.on('console', msg => console.log('CONSOLE:', msg.text()));

  await page.goto('/');
  await page.click('button');
});
```

### Cypress Debugging

**Open Cypress UI**:
```bash
npx cypress open
```

**Debug in browser**:
```typescript
it('debug test', () => {
  cy.visit('/');
  cy.get('button').debug(); // Pauses execution
  cy.get('button').click();
});
```

**Time-travel debugging**: Click on command in Cypress UI to see DOM state at that moment.

### Common Debugging Scenarios

**1. Element not found**:
```typescript
// Add explicit wait
await page.waitForSelector('.element', { state: 'visible', timeout: 10000 });

// Log page content
console.log(await page.content());

// Screenshot before failure
await page.screenshot({ path: 'before-error.png' });
```

**2. Timing issues**:
```typescript
// Slow down execution
await page.goto('/', { waitUntil: 'networkidle' });

// Wait for specific condition
await page.waitForFunction(() => document.readyState === 'complete');
```

**3. Network failures**:
```typescript
// Log all network requests
page.on('request', request => {
  console.log('>>', request.method(), request.url());
});

page.on('response', response => {
  console.log('<<', response.status(), response.url());
});
```

---

## Accessibility Testing

### Why Test Accessibility?

**Legal requirements**: WCAG, ADA compliance
**User experience**: 15% of users have disabilities
**SEO benefits**: Better semantic HTML improves search rankings
**Code quality**: Accessible code is often better structured

### Playwright Accessibility Testing

**ARIA roles and labels**:
```typescript
test('buttons have accessible labels', async ({ page }) => {
  await page.goto('/');

  // Get by role (ensures accessibility)
  const submitButton = page.getByRole('button', { name: 'Submit' });
  await expect(submitButton).toBeVisible();

  // Verify ARIA attributes
  await expect(submitButton).toHaveAttribute('aria-label', 'Submit form');
});
```

**Keyboard navigation**:
```typescript
test('app is keyboard navigable', async ({ page }) => {
  await page.goto('/');

  await page.keyboard.press('Tab');
  const firstFocused = await page.evaluate(() => document.activeElement?.tagName);
  expect(firstFocused).toBe('A'); // First focusable element

  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');

  await expect(page).toHaveURL('/next-page');
});
```

**Axe-core integration**:
```typescript
// Install: npm install --save-dev @axe-core/playwright
import { injectAxe, checkA11y } from '@axe-core/playwright';

test('homepage is accessible', async ({ page }) => {
  await page.goto('/');
  await injectAxe(page);
  await checkA11y(page, undefined, {
    detailedReport: true,
    detailedReportOptions: {
      html: true,
    },
  });
});

test('form is accessible', async ({ page }) => {
  await page.goto('/form');
  await injectAxe(page);

  // Check specific element
  await checkA11y(page, 'form', {
    rules: {
      'label': { enabled: true },
      'color-contrast': { enabled: true },
    },
  });
});
```

**Screen reader testing** (manual):
- macOS: VoiceOver (Cmd+F5)
- Windows: NVDA (free), JAWS
- Linux: Orca

---

## Mobile and Responsive Testing

### Playwright Mobile Emulation

**Device emulation**:
```typescript
import { devices } from '@playwright/test';

test.use(devices['iPhone 12']);

test('mobile homepage', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
});
```

**Custom viewport**:
```typescript
test('custom mobile size', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');
});
```

**Multiple devices**:
```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'Desktop Chrome', use: { ...devices['Desktop Chrome'] } },
    { name: 'iPhone 12', use: { ...devices['iPhone 12'] } },
    { name: 'iPad Pro', use: { ...devices['iPad Pro'] } },
    { name: 'Pixel 5', use: { ...devices['Pixel 5'] } },
  ],
});
```

**Touch interactions**:
```typescript
test('mobile swipe', async ({ page }) => {
  await page.goto('/carousel');

  const carousel = page.locator('.carousel');
  const box = await carousel.boundingBox();

  // Swipe left
  await page.touchscreen.tap(box.x + box.width - 10, box.y + box.height / 2);
  await page.touchscreen.swipe(
    { x: box.x + box.width - 10, y: box.y + box.height / 2 },
    { x: box.x + 10, y: box.y + box.height / 2 }
  );
});
```

**Geolocation**:
```typescript
test('location-based feature', async ({ page, context }) => {
  await context.setGeolocation({ latitude: 37.7749, longitude: -122.4194 });
  await context.grantPermissions(['geolocation']);

  await page.goto('/map');
  await expect(page.locator('.location')).toContainText('San Francisco');
});
```

---

## Common Anti-Patterns

### ❌ Never Use `sleep()` or Fixed Waits

```typescript
// ❌ NEVER
await page.click('button');
await page.waitForTimeout(2000);

// ✅ ALWAYS
await page.click('button');
await page.waitForSelector('.result', { state: 'visible' });
```

### ❌ Never Share State Between Tests

```typescript
// ❌ NEVER
let user = null;

test('create user', async () => {
  user = await createUser();
});

test('update user', async () => {
  await updateUser(user); // Depends on previous test
});

// ✅ ALWAYS
test('update user', async () => {
  const user = await createUser(); // Independent
  await updateUser(user);
  await deleteUser(user);
});
```

### ❌ Never Use Fragile Selectors

```typescript
// ❌ NEVER
await page.click('div > div > button:nth-child(3)');
await page.click('.btn-primary');

// ✅ ALWAYS
await page.click('[data-testid="submit-button"]');
await page.getByRole('button', { name: 'Submit' }).click();
```

### ❌ Never Test Too Much with E2E

```typescript
// ❌ NEVER: Test every edge case with E2E
test('validates email format', ...); // Use unit test
test('validates password length', ...); // Use unit test
test('validates special characters', ...); // Use unit test

// ✅ ALWAYS: Test critical happy paths
test('user can register with valid data', ...); // E2E test
```

### ❌ Never Ignore Flaky Tests

```typescript
// ❌ NEVER
test.skip('flaky test', ...); // Hiding the problem

// ✅ ALWAYS
// Investigate and fix flakiness:
// 1. Add proper waits
// 2. Use stable selectors
// 3. Isolate test state
// 4. Mock unreliable dependencies
```

### ❌ Never Leave TODO/Stub Comments

```typescript
// ❌ NEVER
test('user workflow', async ({ page }) => {
  // TODO: Add authentication
  await page.goto('/dashboard');
});

// ✅ ALWAYS
test('user workflow', async ({ page }) => {
  await login(page, 'user', 'password');
  await page.goto('/dashboard');
});
```

---

## Best Practices

### 1. Follow the Testing Pyramid

- **70% unit tests**: Fast, focused, cheap
- **20% integration tests**: Verify boundaries
- **10% E2E tests**: Critical user journeys only

### 2. Use Page Object Model

- Encapsulate page structure in classes
- Reusable, maintainable selectors
- Tests read like user actions

### 3. Prioritize Stable Selectors

1. Data test IDs (`data-testid`)
2. ARIA roles and labels
3. Text content
4. CSS selectors (least preferred)

### 4. Wait for Conditions, Not Time

- Use `waitForSelector`, `waitForResponse`, etc.
- Never use `sleep()` or `waitForTimeout()`

### 5. Isolate Tests

- Each test should be independent
- Clean up test data
- Don't rely on test execution order

### 6. Mock External Services

- Mock payment providers, maps, weather APIs
- Faster, more reliable tests
- Test error scenarios easily

### 7. Optimize for Speed

- Reuse authentication state
- Use API for test setup (not UI)
- Parallelize test execution
- Limit visual regression tests

### 8. Handle Flakiness Proactively

- Investigate failures immediately
- Add retries in CI (2-3 attempts)
- Disable animations
- Use network mocking

### 9. Comprehensive Debugging

- Enable screenshots and videos on failure
- Use trace viewer for detailed debugging
- Log network requests and console messages

### 10. CI/CD Integration

- Run E2E tests on every PR
- Parallelize with sharding
- Upload artifacts (reports, screenshots)
- Retry failed tests automatically

---

## Real-World Test Suites

### E-Commerce Checkout Flow

```typescript
import { test, expect } from '@playwright/test';
import { ProductPage } from '../pages/ProductPage';
import { CartPage } from '../pages/CartPage';
import { CheckoutPage } from '../pages/CheckoutPage';

test.describe('Checkout Flow', () => {
  test('complete purchase journey', async ({ page }) => {
    // 1. Browse product
    const productPage = new ProductPage(page);
    await productPage.goto('laptop-123');
    await productPage.selectSize('15-inch');
    await productPage.selectColor('Silver');
    await productPage.addToCart();

    // 2. Review cart
    const cartPage = new CartPage(page);
    await cartPage.goto();
    await expect(cartPage.itemCount).toBe(1);
    await expect(cartPage.totalPrice).toHaveText('$999.99');
    await cartPage.proceedToCheckout();

    // 3. Checkout
    const checkoutPage = new CheckoutPage(page);
    await checkoutPage.enterShippingAddress({
      name: 'Alice Smith',
      address: '123 Main St',
      city: 'San Francisco',
      zip: '94102',
    });
    await checkoutPage.enterPaymentDetails({
      cardNumber: '4242424242424242',
      expiry: '12/25',
      cvv: '123',
    });
    await checkoutPage.placeOrder();

    // 4. Confirmation
    await expect(page).toHaveURL('**/order-confirmation');
    await expect(page.locator('.success-message')).toContainText('Order placed successfully');
    await expect(page.locator('.order-number')).toBeVisible();
  });
});
```

### SaaS Dashboard with Authentication

```typescript
import { test, expect } from '@playwright/test';
import { test as authTest } from '../fixtures/auth';

authTest.describe('Dashboard', () => {
  authTest('displays user statistics', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    const userCount = await authenticatedPage.locator('[data-stat="users"] .value').textContent();
    expect(parseInt(userCount)).toBeGreaterThan(0);

    const revenue = await authenticatedPage.locator('[data-stat="revenue"] .value').textContent();
    expect(revenue).toMatch(/\$[\d,]+/);
  });

  authTest('can export data', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    const [download] = await Promise.all([
      authenticatedPage.waitForEvent('download'),
      authenticatedPage.click('button:has-text("Export")'),
    ]);

    expect(download.suggestedFilename()).toMatch(/dashboard-export-\d+\.csv/);
    await download.saveAs(`/tmp/${download.suggestedFilename()}`);
  });
});
```

### Form Validation

```typescript
test.describe('Registration Form', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register');
  });

  test('validates email format', async ({ page }) => {
    await page.fill('#email', 'invalid-email');
    await page.click('button[type="submit"]');

    await expect(page.locator('.error-email')).toContainText('Invalid email format');
  });

  test('validates password strength', async ({ page }) => {
    await page.fill('#password', 'weak');
    await page.click('button[type="submit"]');

    await expect(page.locator('.error-password')).toContainText('Password must be at least 8 characters');
  });

  test('successful registration', async ({ page }) => {
    await page.fill('#username', 'alice123');
    await page.fill('#email', 'alice@example.com');
    await page.fill('#password', 'SecurePass123!');
    await page.fill('#password-confirm', 'SecurePass123!');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('**/dashboard');
    await expect(page.locator('.welcome-message')).toContainText('Welcome, alice123');
  });
});
```

---

## References and Resources

### Official Documentation

- **Playwright**: https://playwright.dev
- **Cypress**: https://www.cypress.io
- **Selenium**: https://www.selenium.dev
- **Puppeteer**: https://pptr.dev

### Testing Philosophy

- Martin Fowler - Testing Pyramid: https://martinfowler.com/articles/practical-test-pyramid.html
- Kent C. Dodds - Testing Trophy: https://kentcdodds.com/blog/write-tests
- Google Testing Blog: https://testing.googleblog.com

### Best Practices

- Playwright Best Practices: https://playwright.dev/docs/best-practices
- Cypress Best Practices: https://docs.cypress.io/guides/references/best-practices
- Web.dev Testing Guide: https://web.dev/testing/

### Tools and Libraries

- **Faker.js**: https://fakerjs.dev (test data generation)
- **Axe-core**: https://github.com/dequelabs/axe-core (accessibility testing)
- **Percy**: https://percy.io (visual regression testing)
- **TestRail**: https://www.gurock.com/testrail (test management)

### Communities

- Playwright Discord: https://aka.ms/playwright/discord
- Cypress Discord: https://discord.com/invite/cypress
- Ministry of Testing: https://www.ministryoftesting.com

---

**End of E2E Testing Reference**

*Total lines: ~2,800*
