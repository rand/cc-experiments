# End-to-End Testing

## When to Use This Skill

Use this skill when you need to:
- Test complete user workflows from UI to backend
- Verify cross-browser compatibility
- Implement Page Object Model (POM) for maintainable tests
- Handle waiting strategies (explicit vs implicit waits)
- Test complex user interactions (drag-drop, file uploads)
- Implement visual regression testing
- Debug flaky E2E tests
- Balance E2E coverage with speed and reliability

**ACTIVATE THIS SKILL**: When testing full user journeys, browser automation, or UI workflows

## Core Concepts

### E2E Testing Philosophy

**E2E tests verify complete user workflows**:
- Simulate real user behavior (clicks, typing, navigation)
- Test against real browser (Chrome, Firefox, Safari)
- Exercise full stack (UI, API, database)
- Highest confidence, slowest execution
- Focus on critical user paths

**Testing Pyramid**:
```
    /\
   /E2E\      <- Few, slow, high confidence
  /-----\
 /Integr\     <- More, medium speed
/--------\
|  Unit  |    <- Many, fast, focused
----------
```

### Playwright vs Cypress

**Playwright** (Recommended):
- Multi-browser (Chrome, Firefox, Safari, Edge)
- True parallelization
- Native mobile viewports
- Auto-wait for elements
- Network interception
- Multiple tabs/contexts

**Cypress**:
- Excellent DX (developer experience)
- Time-travel debugging
- Real-time reloads
- Limited to Chromium-based browsers
- Single tab limitation

### Page Object Model (POM)

**Encapsulate page structure and actions**:

```typescript
// ❌ WITHOUT POM: Brittle, duplicated selectors
test('user login', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.fill('#username', 'alice');
  await page.fill('#password', 'secret');
  await page.click('button[type="submit"]');
  await expect(page.locator('.welcome-message')).toBeVisible();
});

// ✅ WITH POM: Reusable, maintainable
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

test('user login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('alice', 'secret');
  await expect(loginPage.welcomeMessage).toBeVisible();
});
```

## Patterns

### Waiting Strategies

**Auto-Wait (Playwright)**: Built-in smart waiting
```typescript
// Playwright auto-waits for:
// 1. Element to be visible
// 2. Element to be enabled
// 3. Element to be stable (not animating)

await page.click('button'); // Waits automatically
await page.fill('input', 'text'); // Waits for enabled state
await expect(page.locator('.message')).toBeVisible(); // Waits up to timeout
```

**Explicit Waits**: Wait for specific conditions
```typescript
// Wait for element
await page.waitForSelector('.dynamic-content', { state: 'visible' });

// Wait for network idle
await page.waitForLoadState('networkidle');

// Wait for custom condition
await page.waitForFunction(() => {
  return document.querySelectorAll('.item').length > 5;
});

// Wait for response
const responsePromise = page.waitForResponse(
  response => response.url().includes('/api/users') && response.status() === 200
);
await page.click('button');
await responsePromise;
```

**Polling Pattern**: Retry until condition met
```typescript
async function waitForCondition(
  condition: () => Promise<boolean>,
  timeout = 5000
) {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (await condition()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error('Condition not met within timeout');
}

await waitForCondition(async () => {
  const count = await page.locator('.item').count();
  return count > 5;
});
```

### Page Object Model Patterns

**Basic POM**:
```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}

  // Selectors
  private usernameInput = '#username';
  private passwordInput = '#password';
  private submitButton = 'button[type="submit"]';
  private errorMessage = '.error-message';

  // Actions
  async goto() {
    await this.page.goto('/login');
  }

  async login(username: string, password: string) {
    await this.page.fill(this.usernameInput, username);
    await this.page.fill(this.passwordInput, password);
    await this.page.click(this.submitButton);
  }

  async loginAsAdmin() {
    await this.login('admin', 'admin123');
  }

  // Assertions
  async expectErrorMessage(message: string) {
    await expect(this.page.locator(this.errorMessage)).toHaveText(message);
  }
}
```

**POM with Components**:
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
}

// pages/DashboardPage.ts
export class DashboardPage {
  readonly header: Header;

  constructor(private page: Page) {
    this.header = new Header(page);
  }

  async goto() {
    await this.page.goto('/dashboard');
  }

  async getStatValue(statName: string): Promise<string> {
    return await this.page.locator(`.stat[data-name="${statName}"] .value`).textContent();
  }
}

// test
test('dashboard shows correct stats', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.goto();

  const userCount = await dashboard.getStatValue('users');
  expect(userCount).toBe('1,234');

  await dashboard.header.logout();
});
```

### Network Mocking and Interception

```typescript
// Mock API responses
test('displays users from API', async ({ page }) => {
  // Intercept and mock API
  await page.route('**/api/users', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 1, name: 'Alice' },
        { id: 2, name: 'Bob' },
      ]),
    });
  });

  await page.goto('/users');
  await expect(page.locator('.user-item')).toHaveCount(2);
  await expect(page.locator('.user-item').first()).toContainText('Alice');
});

// Test error handling
test('handles API errors gracefully', async ({ page }) => {
  await page.route('**/api/users', route => {
    route.fulfill({ status: 500 });
  });

  await page.goto('/users');
  await expect(page.locator('.error-message')).toBeVisible();
});

// Verify request payload
test('sends correct data to API', async ({ page }) => {
  let requestBody: any;

  await page.route('**/api/users', async route => {
    requestBody = route.request().postDataJSON();
    await route.fulfill({ status: 201, body: JSON.stringify({ id: 1 }) });
  });

  await page.goto('/users/new');
  await page.fill('#name', 'Alice');
  await page.click('button[type="submit"]');

  expect(requestBody).toEqual({ name: 'Alice' });
});
```

### Authentication Patterns

**Reusable Auth State**:
```typescript
// global-setup.ts
async function globalSetup() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto('https://example.com/login');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');

  // Save authenticated state
  await page.context().storageState({ path: 'auth.json' });
  await browser.close();
}

// playwright.config.ts
export default defineConfig({
  globalSetup: require.resolve('./global-setup'),
  use: {
    storageState: 'auth.json', // Reuse auth across tests
  },
});

// Tests start already authenticated
test('access protected page', async ({ page }) => {
  await page.goto('/dashboard'); // Already logged in
  await expect(page.locator('.welcome')).toBeVisible();
});
```

**Auth Fixture**:
```typescript
// fixtures/auth.ts
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/login');
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
    await use(page);
  },
});

// Use in tests
test('admin can access settings', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/settings');
  await expect(authenticatedPage.locator('h1')).toContainText('Settings');
});
```

### Visual Regression Testing

```typescript
// Playwright visual comparison
test('homepage visual regression', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png', {
    fullPage: true,
    maxDiffPixels: 100, // Allow small differences
  });
});

// Component-level screenshot
test('button visual states', async ({ page }) => {
  await page.goto('/components');

  const button = page.locator('button.primary');
  await expect(button).toHaveScreenshot('button-default.png');

  await button.hover();
  await expect(button).toHaveScreenshot('button-hover.png');

  await button.focus();
  await expect(button).toHaveScreenshot('button-focus.png');
});

// Cross-browser visual testing
test.describe('cross-browser visuals', () => {
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
});
```

### Handling Complex Interactions

**File Uploads**:
```typescript
test('upload profile picture', async ({ page }) => {
  await page.goto('/profile');

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('path/to/image.png');

  await page.click('button:has-text("Upload")');
  await expect(page.locator('.success-message')).toBeVisible();
});
```

**Drag and Drop**:
```typescript
test('reorder items with drag and drop', async ({ page }) => {
  await page.goto('/kanban');

  const source = page.locator('.task[data-id="1"]');
  const target = page.locator('.column[data-status="done"]');

  await source.dragTo(target);

  await expect(target.locator('.task[data-id="1"]')).toBeVisible();
});
```

**Keyboard Navigation**:
```typescript
test('navigate menu with keyboard', async ({ page }) => {
  await page.goto('/');

  await page.keyboard.press('Tab'); // Focus first element
  await page.keyboard.press('Enter'); // Activate
  await page.keyboard.press('ArrowDown'); // Navigate menu
  await page.keyboard.press('Enter'); // Select item

  await expect(page).toHaveURL('/selected-page');
});
```

## Examples by Framework

### Playwright

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});

// tests/example.spec.ts
import { test, expect } from '@playwright/test';

test('complete user journey', async ({ page }) => {
  // Navigate to homepage
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('Welcome');

  // Search for product
  await page.fill('input[name="search"]', 'laptop');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/search?q=laptop');

  // Add to cart
  await page.click('.product-card:first-child .add-to-cart');
  await expect(page.locator('.cart-count')).toContainText('1');

  // Checkout
  await page.click('.cart-icon');
  await page.click('button:has-text("Checkout")');

  // Fill form
  await page.fill('#email', 'customer@example.com');
  await page.fill('#card', '4242424242424242');
  await page.click('button:has-text("Pay")');

  // Verify success
  await expect(page.locator('.success-message')).toBeVisible();
  await expect(page).toHaveURL('**/order-confirmation');
});
```

### Cypress

```typescript
// cypress/e2e/user-journey.cy.ts
describe('User Journey', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('completes purchase flow', () => {
    // Search
    cy.get('input[name="search"]').type('laptop');
    cy.get('button[type="submit"]').click();

    // Add to cart
    cy.get('.product-card').first().find('.add-to-cart').click();
    cy.get('.cart-count').should('contain', '1');

    // Checkout
    cy.get('.cart-icon').click();
    cy.contains('button', 'Checkout').click();

    // Fill form
    cy.get('#email').type('customer@example.com');
    cy.get('#card').type('4242424242424242');
    cy.contains('button', 'Pay').click();

    // Verify
    cy.get('.success-message').should('be.visible');
    cy.url().should('include', '/order-confirmation');
  });
});

// Custom commands (cypress/support/commands.ts)
Cypress.Commands.add('login', (username: string, password: string) => {
  cy.visit('/login');
  cy.get('#username').type(username);
  cy.get('#password').type(password);
  cy.get('button[type="submit"]').click();
  cy.url().should('include', '/dashboard');
});

// Use custom command
it('admin accesses settings', () => {
  cy.login('admin', 'admin123');
  cy.visit('/settings');
  cy.contains('h1', 'Settings').should('be.visible');
});
```

### Selenium (Python)

```python
# test_user_journey.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytest

@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

def test_user_login(driver):
    driver.get("https://example.com/login")

    # Fill form
    driver.find_element(By.ID, "username").send_keys("alice")
    driver.find_element(By.ID, "password").send_keys("secret")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Wait for dashboard
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "welcome-message"))
    )

    assert "Dashboard" in driver.title
```

## Checklist

**Before Writing E2E Tests**:
- [ ] Identify critical user paths to test
- [ ] Set up test environment (test database, API)
- [ ] Choose E2E framework (Playwright recommended)
- [ ] Plan Page Object Model structure
- [ ] Configure browser targets (Chrome, Firefox, Safari)

**Writing Tests**:
- [ ] Use Page Object Model for maintainability
- [ ] Implement proper waiting strategies (avoid sleep)
- [ ] Test realistic user workflows (multi-step)
- [ ] Mock external services when appropriate
- [ ] Handle authentication (fixtures or global setup)
- [ ] Add visual regression tests for critical pages

**Reliability**:
- [ ] Tests pass consistently (no flakiness)
- [ ] Use data-testid for stable selectors
- [ ] Avoid timing-dependent assertions
- [ ] Retry failed tests in CI (2-3 retries)
- [ ] Clean test data between runs

**Performance**:
- [ ] Run tests in parallel (multiple workers)
- [ ] Reuse authentication state
- [ ] Limit visual regression tests (slow)
- [ ] Keep test count focused (critical paths only)

**After Writing Tests**:
- [ ] Tests run in CI/CD pipeline
- [ ] Screenshots/videos on failure
- [ ] Clear failure messages
- [ ] Tests complete in reasonable time (< 10 min suite)

## Anti-Patterns

```
❌ NEVER: Use sleep/wait for fixed time
   → Flaky tests, slow execution

❌ NEVER: Test everything with E2E
   → Slow feedback, expensive to maintain

❌ NEVER: Use fragile selectors (nth-child, absolute XPath)
   → Breaks with UI changes

❌ NEVER: Share state between tests
   → Order dependencies, flakiness

❌ NEVER: Skip Page Object Model
   → Duplicated selectors, hard to maintain

❌ NEVER: Test browser quirks with E2E
   → Use unit tests for logic, E2E for flows

❌ NEVER: Ignore flaky tests
   → Undermines trust in test suite
```

## Related Skills

**Foundation**:
- `unit-testing-patterns.md` - Testing individual components
- `integration-testing.md` - API and database testing

**E2E Specific**:
- `visual-regression-testing.md` - Advanced screenshot comparison
- `cross-browser-testing.md` - Multi-browser strategies

**Supporting**:
- `test-driven-development.md` - TDD workflow
- `test-coverage-strategy.md` - What to test

**Tools**:
- Playwright: Modern, multi-browser, fast
- Cypress: Great DX, Chromium-only
- Selenium: Legacy, wide language support
- Puppeteer: Chrome-only, good for scraping
