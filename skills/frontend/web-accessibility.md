---
name: frontend-web-accessibility
description: Building accessible web applications
---



# Web Accessibility

**Scope**: WCAG 2.1 AA, ARIA, keyboard navigation, screen readers, color contrast
**Lines**: ~300
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Building accessible web applications
- Implementing WCAG compliance
- Supporting keyboard navigation
- Designing for screen readers
- Testing accessibility
- Fixing accessibility issues

## Core Concepts

### WCAG Principles (POUR)

**Perceivable** - Information must be presentable to users
**Operable** - UI must be operable by all users
**Understandable** - Information must be understandable
**Robust** - Content must work across technologies

### Conformance Levels

**Level A** - Minimum (basic accessibility)
**Level AA** - Recommended (target for most sites)
**Level AAA** - Enhanced (not always achievable)

**Target: WCAG 2.1 AA** for production applications.

---

## Semantic HTML

### Use Correct Elements

```tsx
// ❌ Bad: Divs for everything
<div onClick={handleClick}>Click me</div>
<div>Important message</div>

// ✅ Good: Semantic elements
<button onClick={handleClick}>Click me</button>
<main>Important message</main>
```

### Document Structure

```tsx
<body>
  <header>
    <nav>
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
      </ul>
    </nav>
  </header>

  <main>
    <article>
      <h1>Page Title</h1>
      <section>
        <h2>Section Title</h2>
        <p>Content...</p>
      </section>
    </article>

    <aside>
      <h2>Related Links</h2>
      <ul>...</ul>
    </aside>
  </main>

  <footer>
    <p>&copy; 2025 Company</p>
  </footer>
</body>
```

### Heading Hierarchy

```tsx
// ❌ Bad: Skipping levels
<h1>Page Title</h1>
<h3>Subsection</h3>
<h5>Detail</h5>

// ✅ Good: Proper hierarchy
<h1>Page Title</h1>
<h2>Section</h2>
<h3>Subsection</h3>
```

**Rules**:
- One `<h1>` per page
- Don't skip levels (h1 → h3)
- Headings describe content

---

## ARIA (Accessible Rich Internet Applications)

### When to Use ARIA

**First Rule of ARIA**: Don't use ARIA if you can use native HTML.

```tsx
// ❌ Bad: ARIA on native element
<div role="button" tabIndex={0} onClick={...}>Click</div>

// ✅ Good: Native element
<button onClick={...}>Click</button>
```

### Common ARIA Attributes

**aria-label** - Accessible name
```tsx
<button aria-label="Close dialog">
  <XIcon />
</button>
```

**aria-labelledby** - Reference to label
```tsx
<div role="dialog" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Delete</h2>
  ...
</div>
```

**aria-describedby** - Additional description
```tsx
<input
  type="password"
  aria-describedby="password-hint"
/>
<p id="password-hint">Must be at least 8 characters</p>
```

**aria-live** - Announce dynamic content
```tsx
<div aria-live="polite" aria-atomic="true">
  {status}
</div>
```

**aria-expanded** - Disclosure state
```tsx
<button
  aria-expanded={isOpen}
  aria-controls="dropdown-menu"
  onClick={() => setIsOpen(!isOpen)}
>
  Menu
</button>
<ul id="dropdown-menu" hidden={!isOpen}>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>
```

**aria-hidden** - Hide from screen readers
```tsx
<span aria-hidden="true">★</span>
<span className="sr-only">5 stars</span>
```

### ARIA Roles

```tsx
// Navigation landmark
<nav role="navigation">...</nav>

// Search landmark
<form role="search">...</form>

// Alert (announces to screen reader)
<div role="alert">Error: Form submission failed</div>

// Tab interface
<div role="tablist">
  <button role="tab" aria-selected={true}>Tab 1</button>
  <button role="tab" aria-selected={false}>Tab 2</button>
</div>
<div role="tabpanel">Content</div>
```

---

## Keyboard Navigation

### Focus Management

**Tab Order** - Follow DOM order
```tsx
// ❌ Bad: Breaking tab order with CSS
<div style={{ display: 'flex', flexDirection: 'column-reverse' }}>
  <button>Second (visually first)</button>
  <button>First (visually second)</button>
</div>

// ✅ Good: DOM order matches visual order
<div style={{ display: 'flex', flexDirection: 'column' }}>
  <button>First</button>
  <button>Second</button>
</div>
```

**tabIndex**
```tsx
// 0 = Natural tab order
<div tabIndex={0}>Focusable</div>

// -1 = Programmatically focusable (not in tab order)
<div tabIndex={-1}>Not in tab order</div>

// Positive numbers = Custom tab order (avoid!)
```

### Keyboard Event Handlers

```tsx
function KeyboardAccessibleButton({ onClick, children }: {
  onClick: () => void;
  children: React.ReactNode;
}) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={handleKeyDown}
    >
      {children}
    </div>
  );
}

// ✅ Better: Just use <button>
<button onClick={onClick}>{children}</button>
```

### Focus Trap (Modals)

```tsx
import { useEffect, useRef } from 'react';

function Modal({ isOpen, onClose, children }: {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const dialog = dialogRef.current;
    if (!dialog) return;

    // Focus first focusable element
    const focusableElements = dialog.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    firstElement?.focus();

    // Trap focus inside modal
    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    // Close on Escape
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    dialog.addEventListener('keydown', handleTabKey);
    dialog.addEventListener('keydown', handleEscape);

    return () => {
      dialog.removeEventListener('keydown', handleTabKey);
      dialog.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <h2 id="dialog-title">Dialog Title</h2>
      {children}
    </div>
  );
}
```

---

## Screen Reader Support

### Hidden Text for Screen Readers

```tsx
// CSS approach
<style>
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }
</style>

<button>
  <XIcon aria-hidden="true" />
  <span className="sr-only">Close</span>
</button>
```

### Live Regions

```tsx
function Toast({ message }: { message: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {message}
    </div>
  );
}

function ErrorAlert({ error }: { error: string }) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      {error}
    </div>
  );
}
```

**aria-live values**:
- `off` - No announcements
- `polite` - Announce when idle (default)
- `assertive` - Interrupt and announce immediately

### Form Labels

```tsx
// ❌ Bad: No label
<input type="text" placeholder="Email" />

// ✅ Good: Explicit label
<label htmlFor="email">Email</label>
<input id="email" type="email" />

// ✅ Good: Implicit label
<label>
  Email
  <input type="email" />
</label>

// ✅ Good: aria-label (when visual label not desired)
<input type="search" aria-label="Search products" />
```

---

## Color and Contrast

### Contrast Ratios (WCAG AA)

**Normal text** (< 18pt): 4.5:1 minimum
**Large text** (≥ 18pt or 14pt bold): 3:1 minimum

```tsx
// ❌ Bad: Insufficient contrast
<div style={{ color: '#999', backgroundColor: '#fff' }}>
  Text (2.8:1 - fails AA)
</div>

// ✅ Good: Sufficient contrast
<div style={{ color: '#767676', backgroundColor: '#fff' }}>
  Text (4.5:1 - passes AA)
</div>
```

**Tools**:
- Chrome DevTools (Lighthouse)
- WebAIM Contrast Checker
- Stark (Figma plugin)

### Don't Rely on Color Alone

```tsx
// ❌ Bad: Color only
<span style={{ color: 'red' }}>Error</span>

// ✅ Good: Color + icon + text
<span style={{ color: 'red' }}>
  <ErrorIcon aria-hidden="true" />
  Error: Field is required
</span>
```

---

## Images and Media

### Alt Text

```tsx
// ❌ Bad: Missing alt
<img src="logo.png" />

// ❌ Bad: Redundant alt
<img src="photo.jpg" alt="Image of a photo" />

// ✅ Good: Descriptive alt
<img src="logo.png" alt="Company Logo" />

// ✅ Good: Decorative image
<img src="decoration.png" alt="" />
```

**Alt text guidelines**:
- Describe content and function
- Keep under 125 characters
- Don't start with "Image of"
- Empty alt (`alt=""`) for decorative images

### Video Captions

```tsx
<video controls>
  <source src="video.mp4" type="video/mp4" />
  <track
    kind="captions"
    src="captions.vtt"
    srcLang="en"
    label="English"
    default
  />
</video>
```

---

## Common Accessible Components

### Accessible Button

```tsx
<button
  type="button"
  onClick={handleClick}
  disabled={isDisabled}
  aria-label="Close dialog"
>
  <XIcon aria-hidden="true" />
</button>
```

### Accessible Link

```tsx
// ❌ Bad: Non-descriptive link
<a href="/report.pdf">Click here</a>

// ✅ Good: Descriptive link
<a href="/report.pdf">Download 2025 Annual Report (PDF, 2MB)</a>

// ✅ Good: External link
<a href="https://example.com" target="_blank" rel="noopener noreferrer">
  Visit Example
  <span className="sr-only">(opens in new tab)</span>
</a>
```

### Accessible Dropdown

```tsx
import { useState } from 'react';

function Dropdown({ label, items }: {
  label: string;
  items: Array<{ id: string; label: string; onClick: () => void }>;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div>
      <button
        aria-haspopup="true"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
      >
        {label}
      </button>

      {isOpen && (
        <ul role="menu">
          {items.map(item => (
            <li key={item.id} role="none">
              <button
                role="menuitem"
                onClick={() => {
                  item.onClick();
                  setIsOpen(false);
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Testing Accessibility

### Automated Testing

```tsx
// Jest + Testing Library
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('should have no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Manual Testing

**Keyboard navigation**:
1. Tab through all interactive elements
2. Shift+Tab to go backward
3. Enter/Space to activate
4. Arrow keys for custom widgets

**Screen reader testing**:
- NVDA (Windows, free)
- JAWS (Windows, paid)
- VoiceOver (macOS, built-in)

**Browser DevTools**:
- Lighthouse accessibility audit
- Accessibility tree inspector
- Color contrast checker

---

## Quick Reference

### Accessibility Checklist

```
[ ] Semantic HTML (header, nav, main, footer)
[ ] Heading hierarchy (h1 → h6, no skipping)
[ ] Alt text for images
[ ] Labels for form inputs
[ ] Keyboard navigation (Tab, Enter, Space, Esc)
[ ] Focus indicators (visible outline)
[ ] Color contrast (4.5:1 for text)
[ ] ARIA labels for icon buttons
[ ] aria-live for dynamic content
[ ] Focus trap in modals
[ ] Skip navigation link
[ ] No reliance on color alone
[ ] Descriptive link text
[ ] Captions for video
```

### Common ARIA Patterns

```tsx
// Button
<button aria-label="Close">×</button>

// Toggle
<button aria-pressed={isActive}>Toggle</button>

// Expandable
<button aria-expanded={isOpen} aria-controls="content">Expand</button>

// Live region
<div aria-live="polite" role="status">{message}</div>

// Dialog
<div role="dialog" aria-modal="true" aria-labelledby="title">

// Tab
<div role="tablist">
  <button role="tab" aria-selected={true}>Tab 1</button>
</div>
<div role="tabpanel">Content</div>
```

---

## Common Anti-Patterns

❌ **Div/span as button**: Use `<button>`
✅ Native semantics

❌ **No focus indicators**: Users can't see where they are
✅ Visible focus styles

❌ **Positive tabIndex**: Breaks natural tab order
✅ Use 0 or -1 only

❌ **Color-only indicators**: Not accessible to colorblind
✅ Use color + icon/text

❌ **Missing alt text**: Screen readers can't describe images
✅ Descriptive alt text

❌ **Auto-playing media**: Disorienting, annoying
✅ User-controlled playback

---

## Related Skills

- `react-component-patterns.md` - Custom hook patterns
- `react-form-handling.md` - Accessible form patterns
- `nextjs-app-router.md` - Metadata, SEO
- `frontend-performance.md` - Performance affects accessibility

---

## Level 3: Resources

**Location**: `skills/frontend/web-accessibility/resources/`

### REFERENCE.md

Comprehensive 1,900+ line reference covering:
- **WCAG Guidelines**: Complete Level A, AA, AAA criteria with code examples
- **ARIA Reference**: All roles, states, and properties with usage patterns
- **Semantic HTML**: Document structure, heading hierarchy, lists, tables, forms
- **Keyboard Navigation**: Tab order, focus management, roving tabindex
- **Screen Reader Support**: Hidden text, live regions, form labels, announcements
- **Focus Management**: Focus traps, restoration, programmatic focus
- **Color and Contrast**: WCAG ratios, color blindness, testing tools
- **Forms and Validation**: Labels, error messages, aria-invalid, error summaries
- **Dynamic Content**: Loading states, live announcements, progress indicators
- **Testing Tools**: axe-core, Lighthouse, manual testing workflows
- **Common Patterns**: Modals, accordions, tabs, dropdowns, comboboxes
- **Mobile Accessibility**: Touch targets, gestures, viewport, screen readers
- **Anti-Patterns**: Common mistakes with fixes

### Scripts

**check_accessibility.py** (Python, executable)
- Automated accessibility auditing with axe-core via Selenium
- Scans web pages for WCAG violations
- Multiple standards: WCAG 2.1/2.2 Level A/AA/AAA
- Output: text, JSON, or HTML reports
- Batch URL processing
- Usage: `./check_accessibility.py <url> [--standard wcag2aa] [--json]`

**analyze_aria.py** (Python, executable)
- Analyzes ARIA usage in HTML/JSX files
- Detects invalid roles, attributes, and values
- Checks for common mistakes (redundant roles, hidden focusable elements)
- Validates ARIA patterns and requirements
- Usage: `./analyze_aria.py <path> [--recursive] [--json]`

**test_keyboard_nav.js** (Node.js/Puppeteer, executable)
- Tests keyboard navigation patterns with Puppeteer
- Verifies tab order, focus indicators, keyboard traps
- Checks skip links, interactive elements, modals, menus
- Reports: text or JSON
- Usage: `./test_keyboard_nav.js <url> [--json]`

### Examples

**react/accessible-modal.tsx**
- Complete accessible modal dialog component
- Focus trap (Tab/Shift+Tab cycle)
- Escape key to close
- Focus restoration
- ARIA attributes (role="dialog", aria-modal, aria-labelledby)
- Backdrop click to close

**react/accessible-form.tsx**
- Accessible form with validation
- Proper labels and aria-describedby
- Error messages with aria-invalid
- Error summary with focus management
- Client-side validation
- Required field indicators

**react/accessible-dropdown.tsx**
- ARIA combobox pattern
- Keyboard navigation (Arrow keys, Enter, Escape)
- aria-activedescendant for active option
- Search/filter functionality
- Proper focus management

**html/semantic-examples.html**
- Complete semantic HTML document
- Proper heading hierarchy
- Skip links
- Semantic landmarks (header, nav, main, aside, footer)
- Accessible forms, tables, lists
- Figure with caption

**css/focus-visible.css**
- Modern focus indicator patterns
- :focus-visible for keyboard-only focus
- High contrast mode support
- Dark mode support
- Custom focus styles for buttons, inputs, cards
- Skip link styles
- Animated focus (respecting prefers-reduced-motion)

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
