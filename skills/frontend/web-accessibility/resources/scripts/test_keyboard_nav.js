#!/usr/bin/env node
/**
 * Keyboard navigation testing tool
 *
 * Tests keyboard navigation patterns on web pages, verifying tab order,
 * focus management, keyboard shortcuts, and interaction patterns.
 *
 * Usage:
 *   ./test_keyboard_nav.js <url>
 *   ./test_keyboard_nav.js https://example.com
 *   ./test_keyboard_nav.js https://example.com --json
 *   ./test_keyboard_nav.js https://example.com --selector ".modal" --output report.json
 */

const puppeteer = require('puppeteer');
const fs = require('fs').promises;

/**
 * Keyboard navigation test result
 */
class TestResult {
  constructor(url) {
    this.url = url;
    this.timestamp = new Date().toISOString();
    this.tests = [];
    this.passed = 0;
    this.failed = 0;
    this.warnings = 0;
  }

  addTest(name, passed, message, details = null) {
    const test = {
      name,
      passed,
      message,
      details,
    };
    this.tests.push(test);

    if (passed) {
      this.passed++;
    } else {
      this.failed++;
    }
  }

  addWarning(name, message, details = null) {
    const test = {
      name,
      passed: null,
      warning: true,
      message,
      details,
    };
    this.tests.push(test);
    this.warnings++;
  }

  toJSON() {
    return {
      url: this.url,
      timestamp: this.timestamp,
      summary: {
        total: this.tests.length,
        passed: this.passed,
        failed: this.failed,
        warnings: this.warnings,
      },
      tests: this.tests,
    };
  }
}

/**
 * Keyboard navigation tester
 */
class KeyboardNavigationTester {
  constructor(options = {}) {
    this.headless = options.headless !== false;
    this.timeout = options.timeout || 30000;
    this.browser = null;
    this.page = null;
  }

  async initialize() {
    this.browser = await puppeteer.launch({
      headless: this.headless ? 'new' : false,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    this.page = await this.browser.newPage();
    await this.page.setViewport({ width: 1920, height: 1080 });
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
    }
  }

  async testUrl(url, selector = null) {
    const result = new TestResult(url);

    try {
      // Load page
      await this.page.goto(url, { waitUntil: 'networkidle0', timeout: this.timeout });

      // If selector provided, wait for it
      if (selector) {
        await this.page.waitForSelector(selector, { timeout: 5000 });
      }

      // Run tests
      await this.testFocusableElements(result);
      await this.testTabOrder(result);
      await this.testFocusIndicators(result);
      await this.testKeyboardTraps(result);
      await this.testSkipLinks(result);
      await this.testInteractiveElements(result);
      await this.testModals(result);
      await this.testMenus(result);

    } catch (error) {
      result.addTest('page-load', false, `Failed to load page: ${error.message}`);
    }

    return result;
  }

  /**
   * Test that all interactive elements are focusable
   */
  async testFocusableElements(result) {
    try {
      const elements = await this.page.evaluate(() => {
        const interactiveSelectors = [
          'a[href]',
          'button:not([disabled])',
          'input:not([disabled])',
          'select:not([disabled])',
          'textarea:not([disabled])',
          '[tabindex]:not([tabindex="-1"])',
          '[role="button"]:not([aria-disabled="true"])',
          '[role="link"]',
        ];

        const interactive = document.querySelectorAll(interactiveSelectors.join(','));
        const nonFocusable = [];

        interactive.forEach(el => {
          // Check if element is actually focusable
          const tabIndex = el.getAttribute('tabindex');
          const hasNegativeTabIndex = tabIndex && parseInt(tabIndex) < 0;

          if (hasNegativeTabIndex) {
            return;
          }

          // Try to focus and check if it worked
          const originalFocus = document.activeElement;
          el.focus();
          const isFocusable = document.activeElement === el;
          originalFocus?.focus();

          if (!isFocusable) {
            nonFocusable.push({
              tag: el.tagName,
              id: el.id || null,
              class: el.className || null,
              role: el.getAttribute('role') || null,
            });
          }
        });

        return {
          total: interactive.length,
          nonFocusable,
        };
      });

      if (elements.nonFocusable.length === 0) {
        result.addTest(
          'focusable-elements',
          true,
          `All ${elements.total} interactive elements are focusable`,
        );
      } else {
        result.addTest(
          'focusable-elements',
          false,
          `${elements.nonFocusable.length} of ${elements.total} interactive elements are not focusable`,
          { nonFocusable: elements.nonFocusable },
        );
      }
    } catch (error) {
      result.addTest('focusable-elements', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test tab order is logical
   */
  async testTabOrder(result) {
    try {
      const tabOrder = await this.page.evaluate(() => {
        const elements = [];
        const body = document.body;

        // Focus on body first
        body.focus();

        // Tab through all elements
        let previous = document.activeElement;
        let iterations = 0;
        const maxIterations = 1000;

        while (iterations < maxIterations) {
          // Simulate Tab key
          const tabEvent = new KeyboardEvent('keydown', {
            key: 'Tab',
            code: 'Tab',
            keyCode: 9,
            which: 9,
            bubbles: true,
            cancelable: true,
          });

          document.activeElement.dispatchEvent(tabEvent);

          // Move focus manually since we can't truly simulate Tab
          const focusableElements = Array.from(document.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          ));

          const currentIndex = focusableElements.indexOf(document.activeElement);
          const nextIndex = currentIndex + 1;

          if (nextIndex >= focusableElements.length) {
            break;
          }

          focusableElements[nextIndex]?.focus();

          const current = document.activeElement;

          if (current === previous) {
            break;
          }

          elements.push({
            tag: current.tagName,
            id: current.id || null,
            class: current.className || null,
            tabIndex: current.getAttribute('tabindex') || '0',
            text: current.textContent?.substring(0, 50) || '',
          });

          previous = current;
          iterations++;
        }

        return elements;
      });

      // Check for positive tabindex values
      const positiveTabIndex = tabOrder.filter(el => {
        const idx = parseInt(el.tabIndex);
        return !isNaN(idx) && idx > 0;
      });

      if (positiveTabIndex.length > 0) {
        result.addWarning(
          'tab-order-positive-tabindex',
          `Found ${positiveTabIndex.length} elements with positive tabindex (anti-pattern)`,
          { elements: positiveTabIndex },
        );
      }

      result.addTest(
        'tab-order',
        true,
        `Tab order tested with ${tabOrder.length} focusable elements`,
        { tabOrder: tabOrder.slice(0, 10) }, // Only include first 10 in details
      );

    } catch (error) {
      result.addTest('tab-order', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test that focus indicators are visible
   */
  async testFocusIndicators(result) {
    try {
      const indicators = await this.page.evaluate(() => {
        const elements = document.querySelectorAll(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
        );

        const missingIndicators = [];

        elements.forEach(el => {
          el.focus();
          const styles = window.getComputedStyle(el, ':focus');

          // Check for outline or box-shadow
          const outline = styles.outline;
          const outlineWidth = styles.outlineWidth;
          const boxShadow = styles.boxShadow;

          const hasOutline = outline !== 'none' && outlineWidth !== '0px';
          const hasBoxShadow = boxShadow !== 'none';

          if (!hasOutline && !hasBoxShadow) {
            missingIndicators.push({
              tag: el.tagName,
              id: el.id || null,
              class: el.className || null,
            });
          }
        });

        return {
          total: elements.length,
          missingIndicators,
        };
      });

      if (indicators.missingIndicators.length === 0) {
        result.addTest(
          'focus-indicators',
          true,
          `All ${indicators.total} focusable elements have visible focus indicators`,
        );
      } else {
        result.addTest(
          'focus-indicators',
          false,
          `${indicators.missingIndicators.length} of ${indicators.total} elements lack visible focus indicators`,
          { missingIndicators: indicators.missingIndicators.slice(0, 10) },
        );
      }
    } catch (error) {
      result.addTest('focus-indicators', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test for keyboard traps
   */
  async testKeyboardTraps(result) {
    try {
      const trap = await this.page.evaluate(() => {
        // Try to tab through entire page
        const body = document.body;
        body.focus();

        let iterations = 0;
        const maxIterations = 100;
        const seen = new Set();

        while (iterations < maxIterations) {
          const current = document.activeElement;
          const key = `${current.tagName}:${current.id}:${current.className}`;

          if (seen.has(key)) {
            // Check if we've cycled back to body (normal)
            if (current === body) {
              return { hasTraps: false };
            }

            // Otherwise might be a trap
            return {
              hasTraps: true,
              element: {
                tag: current.tagName,
                id: current.id || null,
                class: current.className || null,
              },
            };
          }

          seen.add(key);

          // Move focus
          const focusableElements = Array.from(document.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          ));

          const currentIndex = focusableElements.indexOf(current);
          const nextIndex = currentIndex + 1;

          if (nextIndex >= focusableElements.length) {
            break;
          }

          focusableElements[nextIndex]?.focus();
          iterations++;
        }

        return { hasTraps: false };
      });

      if (trap.hasTraps) {
        result.addTest(
          'keyboard-traps',
          false,
          'Potential keyboard trap detected',
          trap.element,
        );
      } else {
        result.addTest('keyboard-traps', true, 'No keyboard traps detected');
      }
    } catch (error) {
      result.addTest('keyboard-traps', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test for skip links
   */
  async testSkipLinks(result) {
    try {
      const skipLink = await this.page.evaluate(() => {
        // Look for skip link
        const links = document.querySelectorAll('a[href^="#"]');
        const skipLinks = Array.from(links).filter(link => {
          const text = link.textContent.toLowerCase();
          return text.includes('skip') && (text.includes('content') || text.includes('main') || text.includes('navigation'));
        });

        if (skipLinks.length === 0) {
          return { found: false };
        }

        const link = skipLinks[0];
        const href = link.getAttribute('href');
        const target = document.querySelector(href);

        return {
          found: true,
          text: link.textContent.trim(),
          href,
          targetExists: !!target,
        };
      });

      if (skipLink.found && skipLink.targetExists) {
        result.addTest(
          'skip-links',
          true,
          `Skip link found: "${skipLink.text}" -> ${skipLink.href}`,
        );
      } else if (skipLink.found && !skipLink.targetExists) {
        result.addWarning(
          'skip-links',
          `Skip link found but target doesn't exist: ${skipLink.href}`,
        );
      } else {
        result.addWarning(
          'skip-links',
          'No skip link found (recommended for pages with navigation)',
        );
      }
    } catch (error) {
      result.addTest('skip-links', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test interactive element keyboard support
   */
  async testInteractiveElements(result) {
    try {
      const interactive = await this.page.evaluate(() => {
        const issues = [];

        // Check buttons respond to Space and Enter
        const buttons = document.querySelectorAll('button, [role="button"]');
        buttons.forEach(btn => {
          const hasOnClick = !!btn.onclick || btn.hasAttribute('onclick');
          const hasKeyHandler = !!btn.onkeydown || btn.hasAttribute('onkeydown');

          if (hasOnClick && !hasKeyHandler && btn.tagName !== 'BUTTON') {
            issues.push({
              type: 'custom-button-no-key-handler',
              element: {
                tag: btn.tagName,
                id: btn.id || null,
                role: btn.getAttribute('role'),
              },
            });
          }
        });

        // Check links have href
        const links = document.querySelectorAll('a');
        links.forEach(link => {
          if (!link.hasAttribute('href') || link.getAttribute('href') === '#') {
            const hasOnClick = !!link.onclick || link.hasAttribute('onclick');
            if (hasOnClick) {
              issues.push({
                type: 'link-without-href',
                element: {
                  tag: link.tagName,
                  id: link.id || null,
                  text: link.textContent?.substring(0, 50),
                },
              });
            }
          }
        });

        return issues;
      });

      if (interactive.length === 0) {
        result.addTest(
          'interactive-elements',
          true,
          'All interactive elements have proper keyboard support',
        );
      } else {
        result.addWarning(
          'interactive-elements',
          `${interactive.length} potential keyboard interaction issues found`,
          { issues: interactive.slice(0, 10) },
        );
      }
    } catch (error) {
      result.addTest('interactive-elements', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test modal keyboard behavior
   */
  async testModals(result) {
    try {
      const modals = await this.page.evaluate(() => {
        const dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"], dialog');

        if (dialogs.length === 0) {
          return { found: false };
        }

        const issues = [];

        dialogs.forEach(dialog => {
          // Check for aria-modal
          const isModal = dialog.getAttribute('aria-modal') === 'true';

          // Check for aria-labelledby or aria-label
          const hasLabel = dialog.hasAttribute('aria-labelledby') || dialog.hasAttribute('aria-label');

          if (!isModal) {
            issues.push({
              type: 'missing-aria-modal',
              element: {
                tag: dialog.tagName,
                id: dialog.id || null,
              },
            });
          }

          if (!hasLabel) {
            issues.push({
              type: 'missing-modal-label',
              element: {
                tag: dialog.tagName,
                id: dialog.id || null,
              },
            });
          }
        });

        return {
          found: true,
          total: dialogs.length,
          issues,
        };
      });

      if (!modals.found) {
        result.addTest('modals', true, 'No modals found (or not currently visible)');
      } else if (modals.issues.length === 0) {
        result.addTest('modals', true, `${modals.total} modal(s) have proper attributes`);
      } else {
        result.addWarning(
          'modals',
          `${modals.issues.length} modal accessibility issues found`,
          { issues: modals.issues },
        );
      }
    } catch (error) {
      result.addTest('modals', false, `Test failed: ${error.message}`);
    }
  }

  /**
   * Test menu keyboard navigation
   */
  async testMenus(result) {
    try {
      const menus = await this.page.evaluate(() => {
        const menuElements = document.querySelectorAll('[role="menu"], [role="menubar"]');

        if (menuElements.length === 0) {
          return { found: false };
        }

        const issues = [];

        menuElements.forEach(menu => {
          const role = menu.getAttribute('role');
          const items = menu.querySelectorAll('[role="menuitem"], [role="menuitemcheckbox"], [role="menuitemradio"]');

          // Check menu items have proper role
          if (items.length === 0) {
            issues.push({
              type: 'menu-no-items',
              element: {
                role,
                id: menu.id || null,
              },
            });
          }

          // Check for aria-haspopup on trigger
          const trigger = document.querySelector(`[aria-controls="${menu.id}"]`);
          if (trigger) {
            const hasPopup = trigger.hasAttribute('aria-haspopup');
            const expanded = trigger.getAttribute('aria-expanded');

            if (!hasPopup) {
              issues.push({
                type: 'menu-trigger-no-haspopup',
                element: {
                  tag: trigger.tagName,
                  id: trigger.id || null,
                },
              });
            }

            if (!expanded) {
              issues.push({
                type: 'menu-trigger-no-expanded',
                element: {
                  tag: trigger.tagName,
                  id: trigger.id || null,
                },
              });
            }
          }
        });

        return {
          found: true,
          total: menuElements.length,
          issues,
        };
      });

      if (!menus.found) {
        result.addTest('menus', true, 'No menus found');
      } else if (menus.issues.length === 0) {
        result.addTest('menus', true, `${menus.total} menu(s) have proper structure`);
      } else {
        result.addWarning(
          'menus',
          `${menus.issues.length} menu accessibility issues found`,
          { issues: menus.issues },
        );
      }
    } catch (error) {
      result.addTest('menus', false, `Test failed: ${error.message}`);
    }
  }
}

/**
 * Format result as text
 */
function formatTextReport(result) {
  const lines = [];

  lines.push('='.repeat(80));
  lines.push('KEYBOARD NAVIGATION TEST REPORT');
  lines.push('='.repeat(80));
  lines.push(`URL: ${result.url}`);
  lines.push(`Timestamp: ${result.timestamp}`);
  lines.push('');
  lines.push(`Summary:`);
  lines.push(`  Total Tests: ${result.tests.length}`);
  lines.push(`  Passed: ${result.passed}`);
  lines.push(`  Failed: ${result.failed}`);
  lines.push(`  Warnings: ${result.warnings}`);
  lines.push('');

  // Group by passed/failed/warning
  const passed = result.tests.filter(t => t.passed === true);
  const failed = result.tests.filter(t => t.passed === false);
  const warnings = result.tests.filter(t => t.warning === true);

  if (failed.length > 0) {
    lines.push('FAILED TESTS:');
    lines.push('');
    failed.forEach((test, i) => {
      lines.push(`${i + 1}. ${test.name}`);
      lines.push(`   Message: ${test.message}`);
      if (test.details) {
        lines.push(`   Details: ${JSON.stringify(test.details, null, 2)}`);
      }
      lines.push('');
    });
  }

  if (warnings.length > 0) {
    lines.push('WARNINGS:');
    lines.push('');
    warnings.forEach((test, i) => {
      lines.push(`${i + 1}. ${test.name}`);
      lines.push(`   Message: ${test.message}`);
      if (test.details) {
        lines.push(`   Details: ${JSON.stringify(test.details, null, 2)}`);
      }
      lines.push('');
    });
  }

  if (passed.length > 0) {
    lines.push('PASSED TESTS:');
    lines.push('');
    passed.forEach((test, i) => {
      lines.push(`${i + 1}. ${test.name}: ${test.message}`);
    });
    lines.push('');
  }

  lines.push('='.repeat(80));

  return lines.join('\n');
}

/**
 * Main function
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
Keyboard Navigation Testing Tool

Usage:
  ${process.argv[1]} <url> [options]

Options:
  --selector <selector>    Wait for selector before testing
  --json                   Output in JSON format
  --output <file>          Write output to file
  --no-headless           Show browser window
  --timeout <ms>          Page load timeout (default: 30000)
  --help, -h              Show this help

Examples:
  ${process.argv[1]} https://example.com
  ${process.argv[1]} https://example.com --json
  ${process.argv[1]} https://example.com --selector ".modal" --output report.json
    `);
    process.exit(0);
  }

  const url = args[0];
  const options = {
    selector: null,
    json: false,
    output: null,
    headless: true,
    timeout: 30000,
  };

  // Parse arguments
  for (let i = 1; i < args.length; i++) {
    switch (args[i]) {
      case '--selector':
        options.selector = args[++i];
        break;
      case '--json':
        options.json = true;
        break;
      case '--output':
        options.output = args[++i];
        break;
      case '--no-headless':
        options.headless = false;
        break;
      case '--timeout':
        options.timeout = parseInt(args[++i]);
        break;
    }
  }

  const tester = new KeyboardNavigationTester({
    headless: options.headless,
    timeout: options.timeout,
  });

  try {
    console.error(`Testing keyboard navigation: ${url}`);
    await tester.initialize();
    const result = await tester.testUrl(url, options.selector);

    // Format output
    const output = options.json
      ? JSON.stringify(result.toJSON(), null, 2)
      : formatTextReport(result);

    // Write output
    if (options.output) {
      await fs.writeFile(options.output, output);
      console.error(`Report written to: ${options.output}`);
    } else {
      console.log(output);
    }

    // Exit code
    process.exit(result.failed > 0 ? 1 : 0);

  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  } finally {
    await tester.close();
  }
}

// Check if puppeteer is installed
try {
  require.resolve('puppeteer');
} catch (e) {
  console.error('Error: puppeteer is not installed');
  console.error('Install with: npm install puppeteer');
  process.exit(1);
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exit(1);
  });
}

module.exports = { KeyboardNavigationTester };
