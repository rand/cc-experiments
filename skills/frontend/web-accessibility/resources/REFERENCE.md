# Web Accessibility Reference

**Comprehensive reference for WCAG 2.1/2.2, ARIA, semantic HTML, keyboard navigation, screen readers, and accessible patterns**

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: ~1,900

---

## Table of Contents

1. [WCAG Guidelines](#wcag-guidelines)
2. [ARIA Reference](#aria-reference)
3. [Semantic HTML](#semantic-html)
4. [Keyboard Navigation](#keyboard-navigation)
5. [Screen Reader Support](#screen-reader-support)
6. [Focus Management](#focus-management)
7. [Color and Contrast](#color-and-contrast)
8. [Forms and Validation](#forms-and-validation)
9. [Dynamic Content](#dynamic-content)
10. [Testing Tools and Workflows](#testing-tools-and-workflows)
11. [Common Accessible Patterns](#common-accessible-patterns)
12. [Mobile Accessibility](#mobile-accessibility)
13. [Anti-Patterns and Fixes](#anti-patterns-and-fixes)

---

## WCAG Guidelines

### WCAG Principles (POUR)

**Perceivable**: Information and user interface components must be presentable to users in ways they can perceive.

**Operable**: User interface components and navigation must be operable.

**Understandable**: Information and the operation of user interface must be understandable.

**Robust**: Content must be robust enough that it can be interpreted reliably by a wide variety of user agents, including assistive technologies.

### Conformance Levels

**Level A (Minimum)**
- Basic web accessibility features
- Must be satisfied
- Example: Text alternatives for non-text content

**Level AA (Recommended)**
- Target for most websites and applications
- Addresses the biggest and most common barriers
- Example: Color contrast ratio of 4.5:1

**Level AAA (Enhanced)**
- Highest level of accessibility
- Not always achievable for all content
- Example: Color contrast ratio of 7:1

**Best Practice**: Target WCAG 2.1 Level AA for production applications.

---

### WCAG 2.1 Level A Guidelines

#### 1.1.1 Non-text Content (A)

All non-text content has a text alternative.

```html
<!-- ❌ Bad -->
<img src="logo.png">

<!-- ✅ Good -->
<img src="logo.png" alt="Acme Corporation Logo">

<!-- ✅ Good: Decorative -->
<img src="decoration.png" alt="">

<!-- ✅ Good: Complex content -->
<img src="chart.png" alt="Sales data for Q4 2025" longdesc="chart-description.html">
```

#### 1.2.1 Audio-only and Video-only (A)

Provide an alternative for time-based media.

```html
<!-- Video alternative -->
<video controls>
  <source src="video.mp4" type="video/mp4">
  <track kind="descriptions" src="descriptions.vtt" srclang="en" label="English">
</video>
<details>
  <summary>Transcript</summary>
  <p>Full text transcript of the video...</p>
</details>
```

#### 1.2.2 Captions (Prerecorded) (A)

Captions are provided for all prerecorded audio content.

```html
<video controls>
  <source src="video.mp4" type="video/mp4">
  <track kind="captions" src="captions-en.vtt" srclang="en" label="English" default>
  <track kind="captions" src="captions-es.vtt" srclang="es" label="Español">
</video>
```

#### 1.3.1 Info and Relationships (A)

Information, structure, and relationships can be programmatically determined.

```html
<!-- ❌ Bad: Visual structure only -->
<div>
  <div style="font-size: 24px; font-weight: bold;">Section Title</div>
  <div>Content here</div>
</div>

<!-- ✅ Good: Semantic structure -->
<section>
  <h2>Section Title</h2>
  <p>Content here</p>
</section>
```

#### 1.3.2 Meaningful Sequence (A)

The reading order of content is meaningful.

```html
<!-- ❌ Bad: Visual order != DOM order -->
<div style="display: flex; flex-direction: column-reverse;">
  <div>Second (appears first)</div>
  <div>First (appears second)</div>
</div>

<!-- ✅ Good: DOM order matches visual order -->
<div style="display: flex; flex-direction: column;">
  <div>First</div>
  <div>Second</div>
</div>
```

#### 1.3.3 Sensory Characteristics (A)

Instructions don't rely solely on sensory characteristics.

```html
<!-- ❌ Bad: Shape-only reference -->
<p>Click the round button to continue</p>

<!-- ✅ Good: Multiple characteristics -->
<p>Click the "Continue" button (round, blue) to proceed</p>

<!-- ✅ Better: Direct reference -->
<button id="continue-btn">Continue</button>
```

#### 1.4.1 Use of Color (A)

Color is not the only visual means of conveying information.

```html
<!-- ❌ Bad: Color only -->
<span style="color: red;">Error</span>
<span style="color: green;">Success</span>

<!-- ✅ Good: Color + icon + text -->
<span style="color: red;">
  <svg aria-hidden="true"><use href="#error-icon"/></svg>
  Error: Field is required
</span>
```

#### 1.4.2 Audio Control (A)

If audio plays automatically for more than 3 seconds, provide a mechanism to pause/stop it.

```html
<audio id="background-music" autoplay loop>
  <source src="music.mp3" type="audio/mp3">
</audio>
<button onclick="document.getElementById('background-music').pause()">
  Pause Background Music
</button>
```

#### 2.1.1 Keyboard (A)

All functionality is available from a keyboard.

```html
<!-- ❌ Bad: Mouse-only interaction -->
<div onmouseover="showTooltip()">Hover me</div>

<!-- ✅ Good: Keyboard accessible -->
<button
  onmouseenter="showTooltip()"
  onfocus="showTooltip()"
  onmouseleave="hideTooltip()"
  onblur="hideTooltip()"
>
  Show tooltip
</button>
```

#### 2.1.2 No Keyboard Trap (A)

Keyboard focus can be moved away from a component using only the keyboard.

```javascript
// ✅ Good: Allow escape from modal
function Modal({ onClose }) {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);
}
```

#### 2.1.4 Character Key Shortcuts (A - WCAG 2.1)

If a keyboard shortcut uses only character keys, then at least one of the following is true:
- Can be turned off
- Can be remapped
- Only active when component has focus

```javascript
// ✅ Good: Scoped shortcuts
function Editor() {
  const editorRef = useRef();

  const handleKeyPress = (e) => {
    if (!editorRef.current.contains(document.activeElement)) {
      return; // Only active when editor has focus
    }

    if (e.key === 's' && e.ctrlKey) {
      e.preventDefault();
      save();
    }
  };

  return <div ref={editorRef} onKeyDown={handleKeyPress}>...</div>;
}
```

#### 2.2.1 Timing Adjustable (A)

User can turn off, adjust, or extend time limits.

```html
<div role="alert">
  <p>Your session will expire in 60 seconds.</p>
  <button onclick="extendSession()">Extend Session</button>
</div>
```

#### 2.2.2 Pause, Stop, Hide (A)

Provide mechanism to pause, stop, or hide moving, blinking, or auto-updating content.

```html
<div class="carousel">
  <button aria-label="Pause carousel">⏸</button>
  <button aria-label="Play carousel">▶</button>
  <!-- Carousel items -->
</div>
```

#### 2.3.1 Three Flashes or Below Threshold (A)

Content does not flash more than three times per second.

```css
/* ❌ Bad: Rapid flashing */
@keyframes flash {
  0%, 50% { opacity: 1; }
  25%, 75% { opacity: 0; }
}

/* ✅ Good: Slow transition */
@keyframes fade {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
```

#### 2.4.1 Bypass Blocks (A)

A mechanism is available to bypass blocks of content that are repeated.

```html
<!-- Skip navigation link -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<nav><!-- Navigation --></nav>

<main id="main-content">
  <!-- Main content -->
</main>

<style>
  .skip-link {
    position: absolute;
    left: -9999px;
    top: 0;
  }

  .skip-link:focus {
    left: 0;
    top: 0;
    z-index: 9999;
  }
</style>
```

#### 2.4.2 Page Titled (A)

Web pages have titles that describe topic or purpose.

```html
<head>
  <title>User Profile - Settings | Acme Corp</title>
</head>
```

#### 2.4.3 Focus Order (A)

Focusable components receive focus in an order that preserves meaning.

```html
<!-- ✅ Good: Logical focus order -->
<form>
  <label for="first-name">First Name</label>
  <input id="first-name" type="text">

  <label for="last-name">Last Name</label>
  <input id="last-name" type="text">

  <button type="submit">Submit</button>
</form>
```

#### 2.4.4 Link Purpose (In Context) (A)

The purpose of each link can be determined from the link text alone.

```html
<!-- ❌ Bad: Non-descriptive -->
<a href="report.pdf">Click here</a>

<!-- ✅ Good: Descriptive -->
<a href="report.pdf">Download 2025 Annual Report (PDF, 2MB)</a>

<!-- ✅ Good: Context -->
<h2>2025 Annual Report</h2>
<p>Our annual financial summary.</p>
<a href="report.pdf">Download (PDF, 2MB)</a>
```

#### 2.5.1 Pointer Gestures (A - WCAG 2.1)

All functionality that uses multipoint or path-based gestures can be operated with a single pointer.

```javascript
// ✅ Good: Single-pointer alternative
function ImageZoom() {
  return (
    <div>
      {/* Pinch to zoom alternative */}
      <button onClick={zoomIn}>Zoom In</button>
      <button onClick={zoomOut}>Zoom Out</button>
      <img src="photo.jpg" alt="Landscape" />
    </div>
  );
}
```

#### 2.5.2 Pointer Cancellation (A - WCAG 2.1)

For functionality that can be operated using a single pointer:
- No down-event trigger
- Abort or undo available
- Up-event reverses down-event
- Essential to trigger on down-event

```javascript
// ✅ Good: Up-event trigger
<button onPointerUp={handleClick}>Click me</button>

// ❌ Bad: Down-event trigger (avoid unless essential)
<button onPointerDown={handleClick}>Click me</button>
```

#### 2.5.3 Label in Name (A - WCAG 2.1)

The accessible name contains the visible text label.

```html
<!-- ❌ Bad: Mismatch -->
<button aria-label="Submit form">Send</button>

<!-- ✅ Good: Match -->
<button aria-label="Send message">Send</button>

<!-- ✅ Better: No aria-label needed -->
<button>Send</button>
```

#### 2.5.4 Motion Actuation (A - WCAG 2.1)

Functionality triggered by device motion can also be operated by user interface components.

```javascript
// ✅ Good: Motion + button alternative
function ShakeToRefresh() {
  return (
    <>
      {/* Shake to refresh */}
      <button onClick={refresh}>Refresh</button>
    </>
  );
}
```

#### 3.1.1 Language of Page (A)

The default human language of each page can be programmatically determined.

```html
<html lang="en">
  <head>
    <title>Welcome</title>
  </head>
  <body>
    <p>This is English content.</p>
    <p lang="es">Este es contenido en español.</p>
  </body>
</html>
```

#### 3.2.1 On Focus (A)

When a component receives focus, it does not initiate a change of context.

```javascript
// ❌ Bad: Auto-submit on focus
<input onFocus={submitForm} />

// ✅ Good: Explicit action required
<input />
<button onClick={submitForm}>Submit</button>
```

#### 3.2.2 On Input (A)

Changing the setting of a user interface component does not automatically cause a change of context.

```javascript
// ❌ Bad: Auto-submit on change
<select onChange={submitForm}>
  <option>Option 1</option>
  <option>Option 2</option>
</select>

// ✅ Good: Explicit action
<select onChange={handleChange}>
  <option>Option 1</option>
  <option>Option 2</option>
</select>
<button onClick={submitForm}>Apply</button>
```

#### 3.3.1 Error Identification (A)

If an input error is automatically detected, the item in error is identified and described to the user in text.

```html
<label for="email">Email</label>
<input
  id="email"
  type="email"
  aria-invalid="true"
  aria-describedby="email-error"
>
<span id="email-error" role="alert">
  Error: Please enter a valid email address
</span>
```

#### 3.3.2 Labels or Instructions (A)

Labels or instructions are provided when content requires user input.

```html
<label for="password">
  Password
  <span aria-label="required">*</span>
</label>
<input
  id="password"
  type="password"
  aria-describedby="password-hint"
  required
>
<p id="password-hint">
  Must be at least 8 characters with one uppercase letter and one number
</p>
```

#### 4.1.1 Parsing (A)

In content implemented using markup languages, elements have complete start and end tags, are nested correctly, do not contain duplicate attributes, and IDs are unique.

```html
<!-- ❌ Bad: Duplicate IDs -->
<div id="content">First</div>
<div id="content">Second</div>

<!-- ✅ Good: Unique IDs -->
<div id="content-1">First</div>
<div id="content-2">Second</div>
```

#### 4.1.2 Name, Role, Value (A)

For all user interface components, the name and role can be programmatically determined.

```html
<!-- ❌ Bad: No role/name -->
<div onclick="toggleMenu()">Menu</div>

<!-- ✅ Good: Proper role/name -->
<button
  aria-label="Toggle menu"
  aria-expanded="false"
  aria-controls="menu"
  onclick="toggleMenu()"
>
  Menu
</button>
```

---

### WCAG 2.1 Level AA Guidelines

#### 1.2.4 Captions (Live) (AA)

Captions are provided for all live audio content.

```html
<!-- Live streaming with captions -->
<video controls>
  <source src="livestream.m3u8" type="application/x-mpegURL">
  <track kind="captions" src="live-captions.vtt" srclang="en" label="English">
</video>
```

#### 1.2.5 Audio Description (Prerecorded) (AA)

Audio description is provided for all prerecorded video content.

```html
<video controls>
  <source src="video.mp4" type="video/mp4">
  <track kind="descriptions" src="audio-description.vtt" srclang="en" label="Audio Description">
</video>
```

#### 1.3.4 Orientation (AA - WCAG 2.1)

Content does not restrict its view and operation to a single display orientation.

```css
/* ✅ Good: Support both orientations */
@media (orientation: portrait) {
  .content { flex-direction: column; }
}

@media (orientation: landscape) {
  .content { flex-direction: row; }
}
```

#### 1.3.5 Identify Input Purpose (AA - WCAG 2.1)

The purpose of each input field can be programmatically determined when the input field serves a purpose from the autocomplete list.

```html
<label for="email">Email</label>
<input
  id="email"
  type="email"
  autocomplete="email"
  name="email"
>

<label for="street">Street Address</label>
<input
  id="street"
  type="text"
  autocomplete="street-address"
  name="street"
>
```

#### 1.4.3 Contrast (Minimum) (AA)

Text has a contrast ratio of at least 4.5:1 (or 3:1 for large text).

```css
/* ❌ Bad: Insufficient contrast (2.8:1) */
.text {
  color: #999999;
  background-color: #ffffff;
}

/* ✅ Good: Sufficient contrast (4.5:1) */
.text {
  color: #767676;
  background-color: #ffffff;
}

/* ✅ Good: Large text (3:1) */
.large-text {
  font-size: 18pt;
  color: #949494;
  background-color: #ffffff;
}
```

#### 1.4.4 Resize Text (AA)

Text can be resized up to 200% without loss of content or functionality.

```css
/* ✅ Good: Use relative units */
.text {
  font-size: 1rem; /* Not px */
  line-height: 1.5;
}

/* ✅ Good: Responsive containers */
.container {
  max-width: 100%;
  overflow: auto;
}
```

#### 1.4.5 Images of Text (AA)

Use actual text rather than images of text.

```html
<!-- ❌ Bad: Text in image -->
<img src="heading.png" alt="Welcome to our site">

<!-- ✅ Good: Actual text -->
<h1>Welcome to our site</h1>
```

#### 1.4.10 Reflow (AA - WCAG 2.1)

Content can be presented without loss of information or functionality at 320 CSS pixels width.

```css
/* ✅ Good: Responsive design */
.content {
  max-width: 100%;
  word-wrap: break-word;
}

@media (max-width: 320px) {
  .sidebar {
    display: block;
    width: 100%;
  }
}
```

#### 1.4.11 Non-text Contrast (AA - WCAG 2.1)

Visual presentation of UI components and graphical objects have a contrast ratio of at least 3:1.

```css
/* ✅ Good: Button with sufficient contrast */
.button {
  background-color: #0066cc; /* 3:1 against white */
  border: 2px solid #0052a3;
  color: #ffffff;
}

.button:focus {
  outline: 2px solid #0052a3; /* 3:1 against background */
}
```

#### 1.4.12 Text Spacing (AA - WCAG 2.1)

No loss of content or functionality when text spacing is adjusted.

```css
/* User may apply these adjustments */
* {
  line-height: 1.5 !important;
  letter-spacing: 0.12em !important;
  word-spacing: 0.16em !important;
}

p {
  margin-bottom: 2em !important;
}

/* ✅ Good: Design accommodates text spacing */
.container {
  padding: 1em;
  min-height: fit-content;
}
```

#### 1.4.13 Content on Hover or Focus (AA - WCAG 2.1)

Additional content triggered by hover or focus is dismissible, hoverable, and persistent.

```javascript
// ✅ Good: Accessible tooltip
function Tooltip({ trigger, content }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div>
      <button
        onMouseEnter={() => setIsVisible(true)}
        onFocus={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onBlur={() => setIsVisible(false)}
        aria-describedby="tooltip"
      >
        {trigger}
      </button>
      {isVisible && (
        <div
          id="tooltip"
          role="tooltip"
          onMouseEnter={() => setIsVisible(true)}
        >
          {content}
        </div>
      )}
    </div>
  );
}
```

#### 2.4.5 Multiple Ways (AA)

More than one way is available to locate a page within a set of pages.

```html
<!-- Navigation menu -->
<nav>
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/products">Products</a></li>
  </ul>
</nav>

<!-- Search -->
<form role="search">
  <input type="search" aria-label="Search site">
  <button type="submit">Search</button>
</form>

<!-- Site map -->
<a href="/sitemap">Site Map</a>
```

#### 2.4.6 Headings and Labels (AA)

Headings and labels describe topic or purpose.

```html
<!-- ✅ Good: Descriptive headings -->
<h1>User Account Settings</h1>
<h2>Privacy Preferences</h2>
<h3>Email Notifications</h3>

<!-- ✅ Good: Descriptive labels -->
<label for="email-frequency">How often would you like to receive emails?</label>
<select id="email-frequency">
  <option>Daily</option>
  <option>Weekly</option>
  <option>Monthly</option>
</select>
```

#### 2.4.7 Focus Visible (AA)

Keyboard focus indicator is visible.

```css
/* ❌ Bad: Removing focus indicator */
:focus {
  outline: none;
}

/* ✅ Good: Visible focus indicator */
:focus {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}

/* ✅ Good: Custom focus style */
button:focus-visible {
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.5);
  outline: 2px solid #0066cc;
}
```

#### 3.1.2 Language of Parts (AA)

The human language of each passage or phrase can be programmatically determined.

```html
<p>
  The word <span lang="fr">rendezvous</span> is French.
</p>

<blockquote lang="es">
  <p>La vida es bella.</p>
</blockquote>
```

#### 3.2.3 Consistent Navigation (AA)

Navigational mechanisms that are repeated on multiple pages occur in the same relative order.

```html
<!-- Same navigation on every page -->
<nav aria-label="Main">
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/about">About</a></li>
    <li><a href="/contact">Contact</a></li>
  </ul>
</nav>
```

#### 3.2.4 Consistent Identification (AA)

Components that have the same functionality are identified consistently.

```html
<!-- ✅ Good: Consistent icon usage -->
<button aria-label="Close dialog">
  <svg><use href="#close-icon"/></svg>
</button>

<!-- Same icon/label in different context -->
<button aria-label="Close panel">
  <svg><use href="#close-icon"/></svg>
</button>
```

#### 3.3.3 Error Suggestion (AA)

If an input error is detected and suggestions for correction are known, then the suggestions are provided.

```html
<label for="username">Username</label>
<input
  id="username"
  type="text"
  aria-invalid="true"
  aria-describedby="username-error"
>
<span id="username-error" role="alert">
  Username must be 3-20 characters. Try: johndoe123
</span>
```

#### 3.3.4 Error Prevention (Legal, Financial, Data) (AA)

For pages that cause legal commitments or financial transactions, submissions are reversible, checked, or confirmed.

```html
<form>
  <h2>Payment Details</h2>
  <!-- Form fields -->

  <button type="button" onclick="showConfirmation()">
    Review Order
  </button>
</form>

<div id="confirmation" role="dialog" aria-labelledby="confirm-title">
  <h2 id="confirm-title">Confirm Your Order</h2>
  <!-- Order summary -->
  <button onclick="submitOrder()">Confirm and Pay</button>
  <button onclick="editOrder()">Edit Order</button>
</div>
```

#### 4.1.3 Status Messages (AA - WCAG 2.1)

Status messages can be programmatically determined through role or properties.

```html
<!-- Success message -->
<div role="status" aria-live="polite">
  Your changes have been saved.
</div>

<!-- Error alert -->
<div role="alert" aria-live="assertive">
  Error: Unable to save changes.
</div>

<!-- Progress indicator -->
<div role="status" aria-live="polite" aria-atomic="true">
  Uploading: 45% complete
</div>
```

---

### WCAG 2.1 Level AAA Guidelines (Selected)

#### 1.2.6 Sign Language (Prerecorded) (AAA)

Sign language interpretation is provided for all prerecorded audio content.

#### 1.2.7 Extended Audio Description (Prerecorded) (AAA)

Where pauses in foreground audio are insufficient for audio descriptions to convey the sense of the video, extended audio description is provided.

#### 1.4.6 Contrast (Enhanced) (AAA)

Text has a contrast ratio of at least 7:1 (or 4.5:1 for large text).

```css
/* ✅ AAA: Enhanced contrast (7:1) */
.text {
  color: #595959;
  background-color: #ffffff;
}
```

#### 1.4.8 Visual Presentation (AAA)

For text presentation:
- Width is no more than 80 characters
- Text is not justified
- Line spacing is at least 1.5
- Paragraph spacing is at least 2x line spacing

```css
/* ✅ AAA: Optimal reading */
.text {
  max-width: 80ch;
  line-height: 1.5;
  text-align: left; /* Not justified */
}

.text p {
  margin-bottom: 3em; /* 2x line height */
}
```

#### 2.1.3 Keyboard (No Exception) (AAA)

All functionality is available from a keyboard without exception.

#### 2.4.9 Link Purpose (Link Only) (AAA)

The purpose of each link can be identified from link text alone.

```html
<!-- ✅ AAA: No context needed -->
<a href="report.pdf">Download 2025 Annual Report (PDF, 2MB)</a>
```

#### 2.4.10 Section Headings (AAA)

Section headings are used to organize the content.

```html
<article>
  <h1>Article Title</h1>

  <section>
    <h2>Introduction</h2>
    <p>...</p>
  </section>

  <section>
    <h2>Methods</h2>
    <p>...</p>
  </section>

  <section>
    <h2>Results</h2>
    <p>...</p>
  </section>
</article>
```

---

## ARIA Reference

### ARIA Roles

#### Landmark Roles

**banner**: Site header with logo, site title

```html
<header role="banner">
  <h1>Site Name</h1>
</header>
```

**navigation**: Collection of navigational links

```html
<nav role="navigation" aria-label="Main">
  <ul>
    <li><a href="/">Home</a></li>
  </ul>
</nav>
```

**main**: Main content of the document

```html
<main role="main">
  <article>...</article>
</main>
```

**complementary**: Supporting content (sidebar)

```html
<aside role="complementary">
  <h2>Related Links</h2>
</aside>
```

**contentinfo**: Footer information

```html
<footer role="contentinfo">
  <p>&copy; 2025 Company</p>
</footer>
```

**search**: Search functionality

```html
<form role="search">
  <input type="search" aria-label="Search">
  <button type="submit">Search</button>
</form>
```

**region**: Significant section of content

```html
<section role="region" aria-labelledby="region-title">
  <h2 id="region-title">Special Offers</h2>
</section>
```

**form**: Landmark containing form controls

```html
<form role="form" aria-labelledby="form-title">
  <h2 id="form-title">Contact Us</h2>
</form>
```

#### Widget Roles

**button**: Clickable element that triggers a response

```html
<div role="button" tabindex="0">Custom Button</div>
<!-- Prefer: <button>Custom Button</button> -->
```

**checkbox**: Checkable input with three states: true, false, mixed

```html
<div role="checkbox" aria-checked="true" tabindex="0">
  Accept terms
</div>
```

**radio**: Checkable input in a group of radio roles

```html
<div role="radiogroup" aria-labelledby="group-label">
  <span id="group-label">Size</span>
  <div role="radio" aria-checked="true" tabindex="0">Small</div>
  <div role="radio" aria-checked="false" tabindex="-1">Large</div>
</div>
```

**textbox**: Input that allows free-form text

```html
<div role="textbox" contenteditable="true" aria-label="Note"></div>
```

**link**: Interactive reference to a resource

```html
<span role="link" tabindex="0" onclick="navigate()">Click here</span>
<!-- Prefer: <a href="...">Click here</a> -->
```

**menubar**: Presentation of a menu in a horizontal bar

```html
<ul role="menubar">
  <li role="menuitem"><a href="/file">File</a></li>
  <li role="menuitem"><a href="/edit">Edit</a></li>
</ul>
```

**menu**: List of choices presented to the user

```html
<ul role="menu">
  <li role="menuitem">Save</li>
  <li role="menuitem">Save As...</li>
  <li role="separator"></li>
  <li role="menuitem">Exit</li>
</ul>
```

**menuitem**: Option in a menu

**menuitemcheckbox**: Checkable menuitem

```html
<ul role="menu">
  <li role="menuitemcheckbox" aria-checked="true">Show toolbar</li>
</ul>
```

**menuitemradio**: Checkable menuitem in group of menuitems

```html
<ul role="menu">
  <li role="menuitemradio" aria-checked="true">Small</li>
  <li role="menuitemradio" aria-checked="false">Large</li>
</ul>
```

**option**: Selectable item in a listbox

```html
<div role="listbox" aria-label="Colors">
  <div role="option" aria-selected="true">Red</div>
  <div role="option" aria-selected="false">Blue</div>
</div>
```

**progressbar**: Element that displays progress status

```html
<div
  role="progressbar"
  aria-valuenow="75"
  aria-valuemin="0"
  aria-valuemax="100"
  aria-label="Upload progress"
>
  75%
</div>
```

**scrollbar**: Graphical object that controls scrolling

```html
<div
  role="scrollbar"
  aria-controls="content"
  aria-valuenow="50"
  aria-valuemin="0"
  aria-valuemax="100"
  aria-orientation="vertical"
  tabindex="0"
></div>
```

**slider**: Input where user selects a value from a range

```html
<div
  role="slider"
  aria-valuenow="50"
  aria-valuemin="0"
  aria-valuemax="100"
  aria-label="Volume"
  tabindex="0"
></div>
```

**spinbutton**: Form of range with increase/decrease buttons

```html
<div
  role="spinbutton"
  aria-valuenow="5"
  aria-valuemin="0"
  aria-valuemax="10"
  aria-label="Quantity"
  tabindex="0"
></div>
```

**switch**: Checkbox that represents on/off values

```html
<button
  role="switch"
  aria-checked="true"
  aria-label="Enable notifications"
>
  <span>On</span>
</button>
```

**tab**: Tab in a tablist

```html
<div role="tablist" aria-label="Sections">
  <button role="tab" aria-selected="true" aria-controls="panel1">
    Tab 1
  </button>
  <button role="tab" aria-selected="false" aria-controls="panel2">
    Tab 2
  </button>
</div>
<div role="tabpanel" id="panel1">Content 1</div>
<div role="tabpanel" id="panel2" hidden>Content 2</div>
```

**tablist**: List of tab elements

**tabpanel**: Container for resources associated with a tab

**combobox**: Composite widget with input and popup

```html
<div role="combobox" aria-expanded="false" aria-haspopup="listbox">
  <input type="text" aria-autocomplete="list" aria-controls="listbox">
  <ul role="listbox" id="listbox" hidden>
    <li role="option">Option 1</li>
    <li role="option">Option 2</li>
  </ul>
</div>
```

**grid**: Composite widget containing cells of tabular data

```html
<div role="grid" aria-labelledby="grid-title">
  <div role="row">
    <div role="columnheader">Name</div>
    <div role="columnheader">Age</div>
  </div>
  <div role="row">
    <div role="gridcell">John</div>
    <div role="gridcell">30</div>
  </div>
</div>
```

**listbox**: Widget that allows user to select one or more items

```html
<ul role="listbox" aria-label="Fruits">
  <li role="option" aria-selected="true">Apple</li>
  <li role="option" aria-selected="false">Banana</li>
</ul>
```

**tree**: Widget that allows user to select items from hierarchical list

```html
<ul role="tree" aria-label="File system">
  <li role="treeitem" aria-expanded="true">
    Documents
    <ul role="group">
      <li role="treeitem">Resume.pdf</li>
    </ul>
  </li>
</ul>
```

**treegrid**: Grid whose rows can be expanded and collapsed

**treeitem**: Item in a tree

#### Document Structure Roles

**article**: Self-contained composition

```html
<article role="article">
  <h2>Article Title</h2>
  <p>Content...</p>
</article>
```

**definition**: Definition of a term or concept

```html
<dl>
  <dt>Accessibility</dt>
  <dd role="definition">The practice of making content usable by all people</dd>
</dl>
```

**directory**: List of references to members of a group

**document**: Content that contains primarily static information

**feed**: Scrollable list of articles

**figure**: Perceivable content with optional caption

```html
<figure role="figure" aria-labelledby="fig-caption">
  <img src="chart.png" alt="">
  <figcaption id="fig-caption">Sales data for 2025</figcaption>
</figure>
```

**group**: Set of user interface objects

```html
<div role="group" aria-labelledby="group-title">
  <h3 id="group-title">Shipping Address</h3>
  <input type="text" aria-label="Street">
  <input type="text" aria-label="City">
</div>
```

**heading**: Heading for a section of the page

```html
<div role="heading" aria-level="2">Section Title</div>
<!-- Prefer: <h2>Section Title</h2> -->
```

**img**: Container for a collection of elements that form an image

```html
<div role="img" aria-label="Company logo">
  <svg>...</svg>
</div>
```

**list**: Group of non-interactive list items

```html
<div role="list">
  <div role="listitem">Item 1</div>
  <div role="listitem">Item 2</div>
</div>
<!-- Prefer: <ul><li>Item 1</li><li>Item 2</li></ul> -->
```

**listitem**: Single item in a list

**math**: Mathematical expression

```html
<div role="math" aria-label="Pythagorean theorem">
  a² + b² = c²
</div>
```

**note**: Parenthetic or ancillary content

```html
<aside role="note" aria-label="Editor's note">
  <p>This article was updated on 2025-10-27.</p>
</aside>
```

**presentation/none**: Element whose semantics should be removed

```html
<table role="presentation">
  <tr>
    <td>Layout cell</td>
  </tr>
</table>
```

**separator**: Divider between sections

```html
<hr role="separator">
<div role="separator" aria-orientation="horizontal"></div>
```

**table**: Non-interactive table

```html
<div role="table" aria-labelledby="table-title">
  <div id="table-title">Employee List</div>
  <div role="rowgroup">
    <div role="row">
      <div role="columnheader">Name</div>
      <div role="columnheader">Title</div>
    </div>
  </div>
  <div role="rowgroup">
    <div role="row">
      <div role="cell">John Doe</div>
      <div role="cell">Engineer</div>
    </div>
  </div>
</div>
<!-- Prefer: <table>...</table> -->
```

**term**: Word or phrase with an optional corresponding definition

```html
<span role="term" aria-describedby="def1">ARIA</span>
<span id="def1">Accessible Rich Internet Applications</span>
```

**toolbar**: Collection of commonly used controls

```html
<div role="toolbar" aria-label="Text formatting">
  <button aria-label="Bold">B</button>
  <button aria-label="Italic">I</button>
  <button aria-label="Underline">U</button>
</div>
```

**tooltip**: Contextual popup that displays information

```html
<button aria-describedby="tooltip1">Help</button>
<div role="tooltip" id="tooltip1">
  Click for more information
</div>
```

#### Live Region Roles

**alert**: Important, time-sensitive message

```html
<div role="alert">
  Error: Your session has expired
</div>
```

**log**: Live region where new information is added

```html
<div role="log" aria-live="polite" aria-atomic="false">
  <p>User joined: Alice</p>
  <p>User joined: Bob</p>
</div>
```

**marquee**: Live region with non-essential information that changes

```html
<div role="marquee" aria-live="off">
  Latest news: ...
</div>
```

**status**: Advisory information for user

```html
<div role="status" aria-live="polite">
  Changes saved successfully
</div>
```

**timer**: Numerical counter or countdown

```html
<div role="timer" aria-live="off" aria-atomic="true">
  Time remaining: 5:00
</div>
```

#### Window Roles

**alertdialog**: Dialog that contains an alert message

```html
<div role="alertdialog" aria-modal="true" aria-labelledby="alert-title">
  <h2 id="alert-title">Confirm Delete</h2>
  <p>Are you sure you want to delete this item?</p>
  <button>Delete</button>
  <button>Cancel</button>
</div>
```

**dialog**: Application window designed to interrupt

```html
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Settings</h2>
  <!-- Dialog content -->
</div>
```

### ARIA States and Properties

#### Widget Attributes

**aria-autocomplete**: Indicates autocomplete behavior

```html
<input
  type="text"
  role="combobox"
  aria-autocomplete="list"
  aria-controls="suggestions"
>
```

Values: `none`, `inline`, `list`, `both`

**aria-checked**: Indicates checked state

```html
<div role="checkbox" aria-checked="true" tabindex="0">
  Option 1
</div>
```

Values: `true`, `false`, `mixed`

**aria-disabled**: Indicates element is disabled

```html
<button aria-disabled="true">Submit</button>
```

Values: `true`, `false`

**aria-expanded**: Indicates expanded state

```html
<button aria-expanded="false" aria-controls="menu">
  Menu
</button>
<ul id="menu" hidden>...</ul>
```

Values: `true`, `false`, `undefined`

**aria-haspopup**: Indicates element triggers popup

```html
<button aria-haspopup="menu">Options</button>
```

Values: `false`, `true`, `menu`, `listbox`, `tree`, `grid`, `dialog`

**aria-hidden**: Indicates element is hidden from accessibility tree

```html
<span aria-hidden="true">★</span>
<span class="sr-only">5 stars</span>
```

Values: `true`, `false`, `undefined`

**aria-invalid**: Indicates invalid value

```html
<input
  type="email"
  aria-invalid="true"
  aria-describedby="email-error"
>
<span id="email-error">Please enter a valid email</span>
```

Values: `true`, `false`, `grammar`, `spelling`

**aria-label**: Defines accessible name

```html
<button aria-label="Close dialog">×</button>
```

**aria-level**: Defines hierarchical level

```html
<div role="heading" aria-level="2">Subsection</div>
```

**aria-modal**: Indicates modal dialog

```html
<div role="dialog" aria-modal="true">...</div>
```

Values: `true`, `false`

**aria-multiline**: Indicates multiline text input

```html
<div role="textbox" aria-multiline="true" contenteditable>
</div>
```

Values: `true`, `false`

**aria-multiselectable**: Indicates multiple selection allowed

```html
<ul role="listbox" aria-multiselectable="true">
  <li role="option">Option 1</li>
  <li role="option">Option 2</li>
</ul>
```

Values: `true`, `false`

**aria-orientation**: Indicates orientation

```html
<div role="scrollbar" aria-orientation="vertical">
</div>
```

Values: `horizontal`, `vertical`, `undefined`

**aria-placeholder**: Defines placeholder text

```html
<div
  role="textbox"
  contenteditable
  aria-placeholder="Enter text here"
>
</div>
```

**aria-pressed**: Indicates pressed state of toggle button

```html
<button aria-pressed="true">Bold</button>
```

Values: `true`, `false`, `mixed`, `undefined`

**aria-readonly**: Indicates element is not editable

```html
<input type="text" aria-readonly="true" value="Read only">
```

Values: `true`, `false`

**aria-required**: Indicates required field

```html
<input
  type="text"
  aria-required="true"
  aria-label="Email (required)"
>
```

Values: `true`, `false`

**aria-selected**: Indicates selected state

```html
<div role="option" aria-selected="true">Option 1</div>
```

Values: `true`, `false`, `undefined`

**aria-sort**: Indicates sort order

```html
<th role="columnheader" aria-sort="ascending">Name</th>
```

Values: `ascending`, `descending`, `none`, `other`

**aria-valuemax**: Maximum value

```html
<div
  role="slider"
  aria-valuemin="0"
  aria-valuemax="100"
  aria-valuenow="50"
>
</div>
```

**aria-valuemin**: Minimum value

**aria-valuenow**: Current value

**aria-valuetext**: Human-readable value text

```html
<div
  role="slider"
  aria-valuenow="2"
  aria-valuetext="Medium"
>
</div>
```

#### Live Region Attributes

**aria-atomic**: Indicates if entire region should be announced

```html
<div role="status" aria-live="polite" aria-atomic="true">
  Loading: 50%
</div>
```

Values: `true`, `false`

**aria-busy**: Indicates element is being modified

```html
<div aria-busy="true">Loading...</div>
```

Values: `true`, `false`

**aria-live**: Indicates live region update priority

```html
<div aria-live="polite">Status message</div>
```

Values: `off`, `polite`, `assertive`

**aria-relevant**: Indicates what changes should be announced

```html
<div
  role="log"
  aria-live="polite"
  aria-relevant="additions text"
>
</div>
```

Values: `additions`, `removals`, `text`, `all`

#### Relationship Attributes

**aria-activedescendant**: Identifies active descendant

```html
<div
  role="combobox"
  aria-activedescendant="option-2"
>
  <input type="text">
  <ul role="listbox">
    <li role="option" id="option-1">Option 1</li>
    <li role="option" id="option-2">Option 2</li>
  </ul>
</div>
```

**aria-colcount**: Defines total number of columns

```html
<div role="table" aria-colcount="10">
  <!-- Only showing 3 of 10 columns -->
  <div role="row">
    <div role="cell" aria-colindex="1">Cell 1</div>
    <div role="cell" aria-colindex="2">Cell 2</div>
    <div role="cell" aria-colindex="3">Cell 3</div>
  </div>
</div>
```

**aria-colindex**: Defines column index

**aria-colspan**: Defines number of columns spanned

**aria-controls**: Identifies controlled elements

```html
<button aria-expanded="false" aria-controls="dropdown">
  Expand
</button>
<div id="dropdown" hidden>Content</div>
```

**aria-describedby**: References descriptive elements

```html
<input
  type="password"
  aria-describedby="password-hint"
>
<p id="password-hint">Must be at least 8 characters</p>
```

**aria-details**: References detailed description

```html
<img
  src="chart.png"
  alt="Sales chart"
  aria-details="chart-description"
>
<div id="chart-description">
  <h3>Detailed Description</h3>
  <p>The chart shows...</p>
</div>
```

**aria-errormessage**: References error message

```html
<input
  type="email"
  aria-invalid="true"
  aria-errormessage="email-error"
>
<span id="email-error" role="alert">
  Please enter a valid email address
</span>
```

**aria-flowto**: Identifies next element in alternate reading order

```html
<div id="step1" aria-flowto="step2">Step 1</div>
<div id="step2">Step 2</div>
```

**aria-labelledby**: References labeling elements

```html
<div role="dialog" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Action</h2>
</div>
```

**aria-owns**: Identifies owned elements

```html
<div role="listbox" aria-owns="option1 option2">
  <div role="option" id="option1">Option 1</div>
</div>
<div role="option" id="option2">Option 2 (elsewhere in DOM)</div>
```

**aria-posinset**: Defines position in set

```html
<div role="listitem" aria-posinset="2" aria-setsize="10">
  Item 2 of 10
</div>
```

**aria-rowcount**: Defines total number of rows

**aria-rowindex**: Defines row index

**aria-rowspan**: Defines number of rows spanned

**aria-setsize**: Defines total number of items in set

```html
<div role="listitem" aria-posinset="1" aria-setsize="5">
  Item 1 of 5
</div>
```

---

## Semantic HTML

### Document Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Title - Site Name</title>
</head>
<body>
  <!-- Skip link -->
  <a href="#main-content" class="skip-link">Skip to main content</a>

  <!-- Site header -->
  <header>
    <div class="logo">
      <img src="logo.png" alt="Company Name">
    </div>

    <!-- Main navigation -->
    <nav aria-label="Main">
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/contact">Contact</a></li>
      </ul>
    </nav>
  </header>

  <!-- Main content -->
  <main id="main-content">
    <!-- Page heading -->
    <h1>Page Title</h1>

    <!-- Primary article -->
    <article>
      <header>
        <h2>Article Title</h2>
        <p>By <span class="author">John Doe</span> on <time datetime="2025-10-27">October 27, 2025</time></p>
      </header>

      <section>
        <h3>Section 1</h3>
        <p>Content...</p>
      </section>

      <section>
        <h3>Section 2</h3>
        <p>Content...</p>
      </section>

      <footer>
        <p>Article footer content</p>
      </footer>
    </article>

    <!-- Sidebar -->
    <aside>
      <h2>Related Links</h2>
      <ul>
        <li><a href="/related1">Related Article 1</a></li>
        <li><a href="/related2">Related Article 2</a></li>
      </ul>
    </aside>
  </main>

  <!-- Site footer -->
  <footer>
    <nav aria-label="Footer">
      <ul>
        <li><a href="/privacy">Privacy Policy</a></li>
        <li><a href="/terms">Terms of Service</a></li>
      </ul>
    </nav>
    <p>&copy; 2025 Company Name. All rights reserved.</p>
  </footer>
</body>
</html>
```

### Heading Hierarchy

**Rules:**
1. One `<h1>` per page
2. Don't skip levels (h1 → h2 → h3, not h1 → h3)
3. Headings describe content that follows
4. Use headings for structure, not styling

```html
<!-- ✅ Good: Proper hierarchy -->
<h1>Main Page Title</h1>

<h2>First Section</h2>
<p>Content...</p>

<h3>Subsection 1.1</h3>
<p>Content...</p>

<h3>Subsection 1.2</h3>
<p>Content...</p>

<h2>Second Section</h2>
<p>Content...</p>

<!-- ❌ Bad: Skipping levels -->
<h1>Main Page Title</h1>
<h3>Subsection</h3> <!-- Skipped h2 -->
<h5>Detail</h5> <!-- Skipped h4 -->
```

### Lists

```html
<!-- Unordered list -->
<ul>
  <li>First item</li>
  <li>Second item</li>
  <li>Third item</li>
</ul>

<!-- Ordered list -->
<ol>
  <li>Step 1</li>
  <li>Step 2</li>
  <li>Step 3</li>
</ol>

<!-- Description list -->
<dl>
  <dt>Term 1</dt>
  <dd>Definition 1</dd>

  <dt>Term 2</dt>
  <dd>Definition 2</dd>
</dl>

<!-- Nested lists -->
<ul>
  <li>
    Parent item
    <ul>
      <li>Child item 1</li>
      <li>Child item 2</li>
    </ul>
  </li>
</ul>
```

### Tables

```html
<table>
  <caption>Employee Salaries for 2025</caption>

  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Title</th>
      <th scope="col">Salary</th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <th scope="row">John Doe</th>
      <td>Engineer</td>
      <td>$100,000</td>
    </tr>
    <tr>
      <th scope="row">Jane Smith</th>
      <td>Designer</td>
      <td>$95,000</td>
    </tr>
  </tbody>

  <tfoot>
    <tr>
      <th scope="row" colspan="2">Total</th>
      <td>$195,000</td>
    </tr>
  </tfoot>
</table>
```

### Forms

```html
<form action="/submit" method="post">
  <fieldset>
    <legend>Personal Information</legend>

    <!-- Text input -->
    <label for="name">Full Name</label>
    <input
      id="name"
      type="text"
      name="name"
      required
      autocomplete="name"
    >

    <!-- Email input -->
    <label for="email">Email Address</label>
    <input
      id="email"
      type="email"
      name="email"
      required
      autocomplete="email"
      aria-describedby="email-hint"
    >
    <p id="email-hint">We'll never share your email</p>

    <!-- Select -->
    <label for="country">Country</label>
    <select id="country" name="country" autocomplete="country">
      <option value="">Select a country</option>
      <option value="us">United States</option>
      <option value="uk">United Kingdom</option>
      <option value="ca">Canada</option>
    </select>

    <!-- Checkbox -->
    <input
      id="subscribe"
      type="checkbox"
      name="subscribe"
      value="yes"
    >
    <label for="subscribe">Subscribe to newsletter</label>

    <!-- Radio buttons -->
    <fieldset>
      <legend>Preferred Contact Method</legend>

      <input
        id="contact-email"
        type="radio"
        name="contact"
        value="email"
        checked
      >
      <label for="contact-email">Email</label>

      <input
        id="contact-phone"
        type="radio"
        name="contact"
        value="phone"
      >
      <label for="contact-phone">Phone</label>
    </fieldset>

    <!-- Textarea -->
    <label for="message">Message</label>
    <textarea
      id="message"
      name="message"
      rows="5"
      maxlength="500"
      aria-describedby="message-hint"
    ></textarea>
    <p id="message-hint">Maximum 500 characters</p>

    <!-- Submit button -->
    <button type="submit">Submit Form</button>
  </fieldset>
</form>
```

### Buttons vs Links

**Button**: Performs an action (submit, open, toggle)

```html
<button type="button" onclick="openModal()">Open Modal</button>
<button type="submit">Submit Form</button>
```

**Link**: Navigates to a destination

```html
<a href="/page">Go to Page</a>
<a href="/report.pdf" download>Download Report</a>
```

**Anti-pattern**: Don't use links that look/act like buttons

```html
<!-- ❌ Bad: Link that acts like button -->
<a href="#" onclick="doSomething(); return false;">Click me</a>

<!-- ✅ Good: Use button -->
<button type="button" onclick="doSomething()">Click me</button>
```

---

## Keyboard Navigation

### Standard Keyboard Interactions

**Tab**: Move forward through focusable elements
**Shift+Tab**: Move backward through focusable elements
**Enter**: Activate links and buttons
**Space**: Activate buttons, toggle checkboxes
**Arrow keys**: Navigate within composite widgets (menus, tabs, etc.)
**Escape**: Close dialogs, cancel actions
**Home**: Move to first item
**End**: Move to last item
**Page Up/Down**: Scroll large amounts

### Tab Order

```html
<!-- ✅ Good: Natural tab order -->
<form>
  <input type="text" id="field1"> <!-- Tab stop 1 -->
  <input type="text" id="field2"> <!-- Tab stop 2 -->
  <button type="submit">Submit</button> <!-- Tab stop 3 -->
</form>

<!-- ❌ Bad: Positive tabindex -->
<form>
  <input type="text" tabindex="3">
  <input type="text" tabindex="1"> <!-- Will receive focus first -->
  <input type="text" tabindex="2">
</form>

<!-- ✅ Good: tabindex values -->
<div tabindex="0">Focusable (in natural tab order)</div>
<div tabindex="-1">Programmatically focusable (not in tab order)</div>
<button tabindex="0">Button (default, no tabindex needed)</button>
```

### Focus Styles

```css
/* ❌ Bad: Removing focus indicator */
*:focus {
  outline: none;
}

/* ✅ Good: Visible focus indicator */
:focus {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}

/* ✅ Better: Custom focus style */
button:focus-visible {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(0, 102, 204, 0.2);
}

/* ✅ High contrast support */
@media (prefers-contrast: high) {
  :focus-visible {
    outline-width: 3px;
    outline-offset: 3px;
  }
}
```

### Skip Links

```html
<a href="#main-content" class="skip-link">Skip to main content</a>

<style>
  .skip-link {
    position: absolute;
    left: -9999px;
    z-index: 999;
    padding: 1em;
    background-color: #000;
    color: #fff;
    text-decoration: none;
  }

  .skip-link:focus {
    left: 50%;
    transform: translateX(-50%);
    top: 0;
  }
</style>
```

### Roving Tab Index (for composite widgets)

```javascript
// Toolbar with arrow key navigation
function Toolbar({ items }) {
  const [focusedIndex, setFocusedIndex] = useState(0);
  const itemRefs = useRef([]);

  const handleKeyDown = (e, index) => {
    let nextIndex;

    switch (e.key) {
      case 'ArrowRight':
        nextIndex = (index + 1) % items.length;
        break;
      case 'ArrowLeft':
        nextIndex = (index - 1 + items.length) % items.length;
        break;
      case 'Home':
        nextIndex = 0;
        break;
      case 'End':
        nextIndex = items.length - 1;
        break;
      default:
        return;
    }

    e.preventDefault();
    setFocusedIndex(nextIndex);
    itemRefs.current[nextIndex]?.focus();
  };

  return (
    <div role="toolbar" aria-label="Text formatting">
      {items.map((item, index) => (
        <button
          key={index}
          ref={el => itemRefs.current[index] = el}
          tabIndex={index === focusedIndex ? 0 : -1}
          onKeyDown={(e) => handleKeyDown(e, index)}
          onClick={item.onClick}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
```

---

## Screen Reader Support

### Screen Reader Basics

**Popular Screen Readers:**
- **NVDA** (Windows, free)
- **JAWS** (Windows, paid)
- **VoiceOver** (macOS/iOS, built-in)
- **TalkBack** (Android, built-in)
- **ORCA** (Linux, free)

**Common Shortcuts:**

NVDA:
- Ctrl: Stop speaking
- Insert+Down: Read all
- H: Next heading
- Insert+F7: Elements list

VoiceOver (macOS):
- Cmd+F5: Toggle VoiceOver
- VO+A: Start reading
- VO+Right/Left: Navigate
- VO+Space: Activate

### Screen Reader Only Text

```css
/* Visually hidden but screen reader accessible */
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

/* Show on focus (for skip links) */
.sr-only-focusable:focus {
  position: static;
  width: auto;
  height: auto;
  overflow: visible;
  clip: auto;
  white-space: normal;
}
```

```html
<button>
  <svg aria-hidden="true"><use href="#save-icon"/></svg>
  <span class="sr-only">Save document</span>
</button>
```

### Live Regions

```html
<!-- Status (polite) -->
<div role="status" aria-live="polite" aria-atomic="true">
  File uploaded successfully
</div>

<!-- Alert (assertive) -->
<div role="alert" aria-live="assertive" aria-atomic="true">
  Error: Connection lost
</div>

<!-- Log (additions only) -->
<div role="log" aria-live="polite" aria-atomic="false">
  <p>User1 joined</p>
  <p>User2 joined</p>
</div>

<!-- Timer -->
<div role="timer" aria-live="off" aria-atomic="true">
  Time remaining: 5:00
</div>
```

**aria-live values:**
- `off`: No announcements (default)
- `polite`: Announce when idle
- `assertive`: Interrupt and announce immediately

**aria-atomic values:**
- `false`: Announce changes only (default)
- `true`: Announce entire region

### Best Practices

1. **Always provide text alternatives**
```html
<!-- Images -->
<img src="photo.jpg" alt="Sunset over mountains">

<!-- Icon buttons -->
<button aria-label="Close dialog">×</button>

<!-- SVG icons -->
<svg aria-label="Search">...</svg>
```

2. **Use semantic HTML**
```html
<!-- ✅ Good -->
<button>Click me</button>

<!-- ❌ Bad -->
<div role="button" tabindex="0" onclick="...">Click me</div>
```

3. **Provide context**
```html
<!-- ❌ Bad: No context -->
<a href="/edit">Edit</a>
<a href="/edit">Edit</a>

<!-- ✅ Good: Unique names -->
<h2 id="article1-title">Article 1</h2>
<a href="/edit/1" aria-labelledby="article1-title">Edit</a>

<h2 id="article2-title">Article 2</h2>
<a href="/edit/2" aria-labelledby="article2-title">Edit</a>
```

4. **Announce dynamic changes**
```javascript
function UploadStatus({ status }) {
  return (
    <div role="status" aria-live="polite" aria-atomic="true">
      {status}
    </div>
  );
}

// Usage
<UploadStatus status="Uploading: 25%" />
<UploadStatus status="Uploading: 50%" />
<UploadStatus status="Upload complete" />
```

---

## Focus Management

### When to Manage Focus

**Always manage focus when:**
- Opening modals/dialogs
- Closing modals and returning to trigger
- After deleting items from a list
- After navigating in single-page apps
- When showing error messages

### Focus Trap (Modal Pattern)

```javascript
import { useEffect, useRef } from 'react';

function Modal({ isOpen, onClose, children }) {
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    // Save the element that triggered the modal
    triggerRef.current = document.activeElement;

    const dialog = dialogRef.current;
    if (!dialog) return;

    // Get all focusable elements
    const focusableElements = dialog.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstElement?.focus();

    // Trap focus inside modal
    const handleTab = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift+Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    // Close on Escape
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    dialog.addEventListener('keydown', handleTab);
    dialog.addEventListener('keydown', handleEscape);

    return () => {
      dialog.removeEventListener('keydown', handleTab);
      dialog.removeEventListener('keydown', handleEscape);

      // Restore focus to trigger element
      triggerRef.current?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="modal-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <h2 id="modal-title">Modal Title</h2>
        {children}
        <button onClick={onClose}>Close</button>
      </div>
    </>
  );
}
```

### Focus Management After Deletion

```javascript
function ItemList({ items, onDelete }) {
  const itemRefs = useRef([]);

  const handleDelete = (index) => {
    onDelete(index);

    // Focus next item, or previous if deleting last
    const nextIndex = index < items.length - 1 ? index : index - 1;
    setTimeout(() => {
      itemRefs.current[nextIndex]?.focus();
    }, 0);
  };

  return (
    <ul>
      {items.map((item, index) => (
        <li key={item.id}>
          <span>{item.name}</span>
          <button
            ref={el => itemRefs.current[index] = el}
            onClick={() => handleDelete(index)}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
```

### Focus Management in SPAs

```javascript
// When navigating to new page, focus the main heading
function navigateToPage(url) {
  // Update URL
  history.pushState(null, '', url);

  // Load new content
  loadPageContent(url);

  // Focus main heading
  setTimeout(() => {
    const heading = document.querySelector('h1');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      heading.focus();
    }
  }, 0);
}
```

---

## Color and Contrast

### WCAG Contrast Requirements

**Level AA:**
- Normal text (< 18pt): 4.5:1
- Large text (≥ 18pt or ≥ 14pt bold): 3:1
- UI components: 3:1

**Level AAA:**
- Normal text: 7:1
- Large text: 4.5:1

### Contrast Examples

```css
/* ❌ Fails AA (2.8:1) */
.text-fail {
  color: #999999;
  background-color: #ffffff;
}

/* ✅ Passes AA (4.54:1) */
.text-aa {
  color: #767676;
  background-color: #ffffff;
}

/* ✅ Passes AAA (7.05:1) */
.text-aaa {
  color: #595959;
  background-color: #ffffff;
}

/* ✅ Large text passes AA (3.04:1) */
.text-large {
  font-size: 18pt;
  font-weight: bold;
  color: #949494;
  background-color: #ffffff;
}

/* ✅ Button contrast (3:1) */
.button {
  background-color: #0066cc; /* 3.14:1 against white */
  color: #ffffff;
  border: 2px solid #0052a3;
}

.button:focus {
  outline: 2px solid #0052a3;
  outline-offset: 2px;
}
```

### Color Blindness Considerations

**Types:**
- **Protanopia**: Red-blind (1% of men)
- **Deuteranopia**: Green-blind (1% of men)
- **Tritanopia**: Blue-blind (rare)
- **Achromatopsia**: Total color blindness (very rare)

**Best Practices:**
1. Don't rely on color alone
2. Use patterns, icons, and labels
3. Test with color blindness simulators

```html
<!-- ❌ Bad: Color only -->
<span style="color: red;">Error</span>
<span style="color: green;">Success</span>

<!-- ✅ Good: Color + icon + text -->
<span class="error">
  <svg aria-hidden="true"><use href="#error-icon"/></svg>
  Error: Field is required
</span>

<span class="success">
  <svg aria-hidden="true"><use href="#success-icon"/></svg>
  Success: Form submitted
</span>
```

### Testing Tools

**Automated:**
- Chrome DevTools Lighthouse
- axe DevTools browser extension
- WAVE browser extension
- WebAIM Contrast Checker

**Manual:**
- Color Contrast Analyzer (CCA)
- Stark (Figma plugin)
- WhoCanUse.com

---

## Forms and Validation

### Accessible Form Pattern

```html
<form action="/submit" method="post" novalidate>
  <fieldset>
    <legend>Contact Information</legend>

    <!-- Text input with label -->
    <div class="form-field">
      <label for="name">
        Full Name
        <span aria-label="required">*</span>
      </label>
      <input
        id="name"
        name="name"
        type="text"
        required
        aria-required="true"
        aria-invalid="false"
        aria-describedby="name-hint name-error"
        autocomplete="name"
      >
      <p id="name-hint" class="hint">Your first and last name</p>
      <p id="name-error" class="error" role="alert" hidden>
        Error: Please enter your full name
      </p>
    </div>

    <!-- Email with validation -->
    <div class="form-field">
      <label for="email">
        Email Address
        <span aria-label="required">*</span>
      </label>
      <input
        id="email"
        name="email"
        type="email"
        required
        aria-required="true"
        aria-invalid="false"
        aria-describedby="email-hint email-error"
        autocomplete="email"
      >
      <p id="email-hint" class="hint">We'll never share your email</p>
      <p id="email-error" class="error" role="alert" hidden>
        Error: Please enter a valid email address
      </p>
    </div>

    <!-- Password with requirements -->
    <div class="form-field">
      <label for="password">
        Password
        <span aria-label="required">*</span>
      </label>
      <input
        id="password"
        name="password"
        type="password"
        required
        aria-required="true"
        aria-invalid="false"
        aria-describedby="password-hint password-error"
        autocomplete="new-password"
      >
      <p id="password-hint" class="hint">
        Must be at least 8 characters with one uppercase, one lowercase, and one number
      </p>
      <p id="password-error" class="error" role="alert" hidden>
        Error: Password does not meet requirements
      </p>
    </div>

    <!-- Checkbox -->
    <div class="form-field">
      <input
        id="terms"
        name="terms"
        type="checkbox"
        required
        aria-required="true"
        aria-invalid="false"
        aria-describedby="terms-error"
      >
      <label for="terms">
        I agree to the <a href="/terms">Terms of Service</a>
        <span aria-label="required">*</span>
      </label>
      <p id="terms-error" class="error" role="alert" hidden>
        Error: You must agree to the terms
      </p>
    </div>

    <!-- Submit button -->
    <button type="submit">Create Account</button>
  </fieldset>
</form>
```

### Client-Side Validation

```javascript
function AccessibleForm() {
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const validate = (name, value) => {
    switch (name) {
      case 'email':
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return 'Please enter a valid email address';
        }
        break;
      case 'password':
        if (value.length < 8) {
          return 'Password must be at least 8 characters';
        }
        if (!/[A-Z]/.test(value)) {
          return 'Password must contain an uppercase letter';
        }
        if (!/[a-z]/.test(value)) {
          return 'Password must contain a lowercase letter';
        }
        if (!/[0-9]/.test(value)) {
          return 'Password must contain a number';
        }
        break;
      default:
        if (!value.trim()) {
          return 'This field is required';
        }
    }
    return null;
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched({ ...touched, [name]: true });

    const error = validate(name, value);
    setErrors({ ...errors, [name]: error });
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);
    const newErrors = {};

    // Validate all fields
    for (const [name, value] of formData.entries()) {
      const error = validate(name, value);
      if (error) {
        newErrors[name] = error;
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setTouched(Object.keys(newErrors).reduce((acc, key) => ({ ...acc, [key]: true }), {}));

      // Announce errors
      const errorMessage = `Form has ${Object.keys(newErrors).length} error(s)`;
      announceToScreenReader(errorMessage, 'assertive');

      // Focus first error
      const firstErrorField = Object.keys(newErrors)[0];
      document.getElementById(firstErrorField)?.focus();

      return;
    }

    // Submit form
    submitForm(formData);
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="form-field">
        <label htmlFor="email">
          Email Address
          <span aria-label="required">*</span>
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          aria-required="true"
          aria-invalid={touched.email && errors.email ? 'true' : 'false'}
          aria-describedby={errors.email ? 'email-error' : 'email-hint'}
          onBlur={handleBlur}
        />
        <p id="email-hint" className="hint">Your email address</p>
        {touched.email && errors.email && (
          <p id="email-error" className="error" role="alert">
            Error: {errors.email}
          </p>
        )}
      </div>

      <button type="submit">Submit</button>
    </form>
  );
}

function announceToScreenReader(message, priority = 'polite') {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', priority === 'assertive' ? 'alert' : 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;

  document.body.appendChild(announcement);

  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}
```

### Error Summary

```javascript
function ErrorSummary({ errors }) {
  const errorSummaryRef = useRef(null);

  useEffect(() => {
    if (errors.length > 0) {
      errorSummaryRef.current?.focus();
    }
  }, [errors]);

  if (errors.length === 0) return null;

  return (
    <div
      ref={errorSummaryRef}
      role="alert"
      aria-labelledby="error-summary-title"
      tabIndex="-1"
      className="error-summary"
    >
      <h2 id="error-summary-title">
        There {errors.length === 1 ? 'is' : 'are'} {errors.length} error{errors.length === 1 ? '' : 's'}
      </h2>
      <ul>
        {errors.map(error => (
          <li key={error.field}>
            <a href={`#${error.field}`}>{error.message}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Dynamic Content

### Loading States

```javascript
function LoadingButton({ isLoading, onClick, children }) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      aria-busy={isLoading}
    >
      {isLoading && (
        <>
          <span className="spinner" aria-hidden="true"></span>
          <span className="sr-only">Loading...</span>
        </>
      )}
      {!isLoading && children}
    </button>
  );
}
```

### Skeleton Screens

```javascript
function ContentLoader({ isLoading, children }) {
  if (isLoading) {
    return (
      <div aria-busy="true" aria-label="Loading content">
        <div className="skeleton-line"></div>
        <div className="skeleton-line"></div>
        <div className="skeleton-line short"></div>
      </div>
    );
  }

  return children;
}
```

### Live Announcements

```javascript
function useLiveAnnouncement() {
  const announce = (message, priority = 'polite') => {
    const region = document.createElement('div');
    region.setAttribute('role', priority === 'assertive' ? 'alert' : 'status');
    region.setAttribute('aria-live', priority);
    region.setAttribute('aria-atomic', 'true');
    region.className = 'sr-only';
    region.textContent = message;

    document.body.appendChild(region);

    setTimeout(() => {
      document.body.removeChild(region);
    }, 1000);
  };

  return { announce };
}

// Usage
function UploadForm() {
  const { announce } = useLiveAnnouncement();
  const [progress, setProgress] = useState(0);

  const handleUpload = async () => {
    announce('Upload started', 'polite');

    // Upload logic...
    setProgress(25);
    announce('Upload 25% complete', 'polite');

    setProgress(50);
    announce('Upload 50% complete', 'polite');

    setProgress(100);
    announce('Upload complete', 'polite');
  };

  return (
    <>
      <button onClick={handleUpload}>Upload</button>
      {progress > 0 && (
        <div
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="Upload progress"
        >
          {progress}%
        </div>
      )}
    </>
  );
}
```

---

## Testing Tools and Workflows

### Automated Testing

**axe-core (JavaScript library)**

```bash
npm install --save-dev @axe-core/react jest-axe
```

```javascript
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('should have no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Playwright with axe**

```javascript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('should not have accessibility violations', async ({ page }) => {
  await page.goto('http://localhost:3000');

  const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

  expect(accessibilityScanResults.violations).toEqual([]);
});
```

**Lighthouse CI**

```json
{
  "ci": {
    "collect": {
      "url": ["http://localhost:3000"],
      "numberOfRuns": 3
    },
    "assert": {
      "assertions": {
        "categories:accessibility": ["error", {"minScore": 0.9}]
      }
    }
  }
}
```

### Manual Testing Checklist

**Keyboard Navigation:**
- [ ] All interactive elements reachable by Tab
- [ ] Focus order is logical
- [ ] Focus indicators are visible
- [ ] Escape closes modals
- [ ] Enter/Space activates buttons
- [ ] Arrow keys work in composite widgets

**Screen Reader Testing:**
- [ ] Page title is descriptive
- [ ] Headings create logical structure
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Error messages are announced
- [ ] Dynamic content changes are announced
- [ ] Landmarks are used correctly

**Visual Testing:**
- [ ] Text has sufficient contrast
- [ ] Focus indicators are visible
- [ ] Color is not the only indicator
- [ ] Content reflows at 200% zoom
- [ ] Content works at 320px width

**Content Testing:**
- [ ] Links have descriptive text
- [ ] Headings describe content
- [ ] Language is specified
- [ ] Instructions are clear

### Browser DevTools

**Chrome DevTools:**
1. Lighthouse audit: DevTools → Lighthouse → Accessibility
2. Accessibility tree: DevTools → Elements → Accessibility
3. Contrast checker: DevTools → Elements → Styles
4. Emulate vision deficiencies: DevTools → Rendering

**Firefox DevTools:**
1. Accessibility inspector: DevTools → Accessibility
2. Check for issues: Accessibility → Check for Issues

### Testing Tools Reference

**Browser Extensions:**
- axe DevTools (Chrome, Firefox, Edge)
- WAVE (Chrome, Firefox, Edge)
- Lighthouse (Chrome built-in)
- Accessibility Insights (Chrome, Edge)

**Standalone Tools:**
- Color Contrast Analyzer (CCA)
- NVDA Screen Reader (Windows)
- JAWS Screen Reader (Windows)
- VoiceOver (macOS/iOS built-in)
- TalkBack (Android built-in)

**Online Tools:**
- WebAIM Contrast Checker
- WebAIM WAVE (online version)
- AccessiBe Ace
- WhoCanUse.com (color contrast simulator)

---

## Common Accessible Patterns

### Modal Dialog

```javascript
function Modal({ isOpen, onClose, title, children }) {
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    // Save previous focus
    previousFocusRef.current = document.activeElement;

    // Focus dialog
    const dialog = dialogRef.current;
    if (!dialog) return;

    const focusableElements = dialog.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    firstElement?.focus();

    // Focus trap
    const handleTab = (e) => {
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

    // Escape to close
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    dialog.addEventListener('keydown', handleTab);
    dialog.addEventListener('keydown', handleEscape);

    return () => {
      dialog.removeEventListener('keydown', handleTab);
      dialog.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
      previousFocusRef.current?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <div
        className="modal-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="modal"
      >
        <h2 id="modal-title">{title}</h2>
        <div className="modal-content">
          {children}
        </div>
        <button onClick={onClose} aria-label="Close dialog">
          ×
        </button>
      </div>
    </>
  );
}
```

### Accordion

```javascript
function Accordion({ items }) {
  const [expandedId, setExpandedId] = useState(null);

  const toggle = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="accordion">
      {items.map(item => {
        const isExpanded = expandedId === item.id;
        const headingId = `accordion-heading-${item.id}`;
        const panelId = `accordion-panel-${item.id}`;

        return (
          <div key={item.id} className="accordion-item">
            <h3 id={headingId}>
              <button
                aria-expanded={isExpanded}
                aria-controls={panelId}
                onClick={() => toggle(item.id)}
                className="accordion-button"
              >
                {item.title}
                <span aria-hidden="true">{isExpanded ? '−' : '+'}</span>
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={headingId}
              hidden={!isExpanded}
              className="accordion-panel"
            >
              {item.content}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

### Tabs

```javascript
function Tabs({ tabs }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const tabRefs = useRef([]);

  const handleKeyDown = (e, index) => {
    let nextIndex;

    switch (e.key) {
      case 'ArrowRight':
        nextIndex = (index + 1) % tabs.length;
        break;
      case 'ArrowLeft':
        nextIndex = (index - 1 + tabs.length) % tabs.length;
        break;
      case 'Home':
        nextIndex = 0;
        break;
      case 'End':
        nextIndex = tabs.length - 1;
        break;
      default:
        return;
    }

    e.preventDefault();
    setSelectedIndex(nextIndex);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <div className="tabs">
      <div role="tablist" aria-label="Content sections">
        {tabs.map((tab, index) => {
          const isSelected = index === selectedIndex;
          const tabId = `tab-${index}`;
          const panelId = `panel-${index}`;

          return (
            <button
              key={index}
              ref={el => tabRefs.current[index] = el}
              id={tabId}
              role="tab"
              aria-selected={isSelected}
              aria-controls={panelId}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => setSelectedIndex(index)}
              onKeyDown={(e) => handleKeyDown(e, index)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {tabs.map((tab, index) => {
        const isSelected = index === selectedIndex;
        const tabId = `tab-${index}`;
        const panelId = `panel-${index}`;

        return (
          <div
            key={index}
            id={panelId}
            role="tabpanel"
            aria-labelledby={tabId}
            hidden={!isSelected}
            tabIndex={0}
          >
            {tab.content}
          </div>
        );
      })}
    </div>
  );
}
```

### Dropdown Menu

```javascript
function DropdownMenu({ trigger, items }) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const menuRef = useRef(null);
  const itemRefs = useRef([]);

  const handleTriggerClick = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setTimeout(() => itemRefs.current[0]?.focus(), 0);
    }
  };

  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setIsOpen(true);
        setTimeout(() => itemRefs.current[0]?.focus(), 0);
      }
      return;
    }

    let nextIndex;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        nextIndex = (focusedIndex + 1) % items.length;
        break;
      case 'ArrowUp':
        e.preventDefault();
        nextIndex = (focusedIndex - 1 + items.length) % items.length;
        break;
      case 'Home':
        e.preventDefault();
        nextIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        nextIndex = items.length - 1;
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        return;
      default:
        return;
    }

    setFocusedIndex(nextIndex);
    itemRefs.current[nextIndex]?.focus();
  };

  return (
    <div className="dropdown">
      <button
        aria-haspopup="true"
        aria-expanded={isOpen}
        onClick={handleTriggerClick}
        onKeyDown={handleKeyDown}
      >
        {trigger}
      </button>

      {isOpen && (
        <ul
          ref={menuRef}
          role="menu"
          className="dropdown-menu"
        >
          {items.map((item, index) => (
            <li key={index} role="none">
              <button
                ref={el => itemRefs.current[index] = el}
                role="menuitem"
                tabIndex={-1}
                onClick={() => {
                  item.onClick();
                  setIsOpen(false);
                }}
                onKeyDown={handleKeyDown}
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

### Combobox (Autocomplete)

```javascript
function Combobox({ label, options, value, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value || '');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef(null);
  const listboxRef = useRef(null);
  const optionRefs = useRef([]);

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(inputValue.toLowerCase())
  );

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);
    setIsOpen(true);
    setHighlightedIndex(0);
  };

  const handleKeyDown = (e) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        } else {
          const nextIndex = Math.min(highlightedIndex + 1, filteredOptions.length - 1);
          setHighlightedIndex(nextIndex);
          optionRefs.current[nextIndex]?.scrollIntoView({ block: 'nearest' });
        }
        break;

      case 'ArrowUp':
        e.preventDefault();
        if (isOpen) {
          const prevIndex = Math.max(highlightedIndex - 1, 0);
          setHighlightedIndex(prevIndex);
          optionRefs.current[prevIndex]?.scrollIntoView({ block: 'nearest' });
        }
        break;

      case 'Enter':
        e.preventDefault();
        if (isOpen && filteredOptions[highlightedIndex]) {
          selectOption(filteredOptions[highlightedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        break;
    }
  };

  const selectOption = (option) => {
    setInputValue(option);
    setIsOpen(false);
    onChange(option);
    inputRef.current?.focus();
  };

  const comboboxId = useId();
  const listboxId = `${comboboxId}-listbox`;

  return (
    <div className="combobox">
      <label htmlFor={comboboxId}>{label}</label>
      <input
        ref={inputRef}
        id={comboboxId}
        type="text"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-activedescendant={
          isOpen && filteredOptions[highlightedIndex]
            ? `${comboboxId}-option-${highlightedIndex}`
            : undefined
        }
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsOpen(true)}
      />

      {isOpen && filteredOptions.length > 0 && (
        <ul
          ref={listboxRef}
          id={listboxId}
          role="listbox"
          className="combobox-listbox"
        >
          {filteredOptions.map((option, index) => (
            <li
              key={index}
              ref={el => optionRefs.current[index] = el}
              id={`${comboboxId}-option-${index}`}
              role="option"
              aria-selected={index === highlightedIndex}
              onClick={() => selectOption(option)}
            >
              {option}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Mobile Accessibility

### Touch Target Size

**WCAG 2.1 Success Criterion 2.5.5 (Level AAA)**: Touch targets are at least 44×44 CSS pixels.

```css
/* ✅ Good: Minimum touch target */
button, a {
  min-width: 44px;
  min-height: 44px;
  padding: 12px 16px;
}

/* ✅ Good: Spacing between targets */
.button-group button {
  margin: 4px;
}
```

### Gesture Alternatives

```javascript
// ✅ Good: Swipe + button alternatives
function ImageGallery({ images }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Touch handlers
  const handleTouchStart = (e) => {
    setTouchStart(e.touches[0].clientX);
  };

  const handleTouchEnd = (e) => {
    const touchEnd = e.changedTouches[0].clientX;
    const diff = touchStart - touchEnd;

    if (Math.abs(diff) > 50) {
      if (diff > 0) {
        nextImage();
      } else {
        previousImage();
      }
    }
  };

  const nextImage = () => {
    setCurrentIndex((currentIndex + 1) % images.length);
  };

  const previousImage = () => {
    setCurrentIndex((currentIndex - 1 + images.length) % images.length);
  };

  return (
    <div
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <img src={images[currentIndex]} alt={`Image ${currentIndex + 1}`} />

      {/* Button alternatives for swipe gestures */}
      <button onClick={previousImage} aria-label="Previous image">
        ← Previous
      </button>
      <button onClick={nextImage} aria-label="Next image">
        Next →
      </button>
    </div>
  );
}
```

### Viewport and Zoom

```html
<!-- ✅ Good: Allow zooming -->
<meta name="viewport" content="width=device-width, initial-scale=1">

<!-- ❌ Bad: Prevent zooming -->
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

### Orientation

```css
/* ✅ Good: Support both orientations */
@media (orientation: portrait) {
  .container {
    flex-direction: column;
  }
}

@media (orientation: landscape) {
  .container {
    flex-direction: row;
  }
}
```

### Mobile Screen Reader Support

**iOS VoiceOver:**
- Two-finger swipe up: Read all from top
- Two-finger swipe down: Read all from current position
- One-finger swipe right/left: Navigate elements
- Double-tap: Activate element
- Two-finger double-tap: Magic Tap (primary action)

**Android TalkBack:**
- Swipe right/left: Navigate elements
- Double-tap: Activate element
- Swipe down then right: Read from top
- Swipe up then down: Read from current position

```javascript
// Optimize for mobile screen readers
function MobileAccessibleCard({ title, description, action }) {
  return (
    <article>
      <h2>{title}</h2>
      <p>{description}</p>
      <button onClick={action}>
        Read more
        <span className="sr-only"> about {title}</span>
      </button>
    </article>
  );
}
```

---

## Anti-Patterns and Fixes

### Anti-Pattern 1: Div/Span as Button

```html
<!-- ❌ Bad -->
<div class="button" onclick="handleClick()">Click me</div>

<!-- ✅ Good -->
<button type="button" onclick="handleClick()">Click me</button>
```

**Why bad**: No keyboard support, no semantic meaning, no screen reader support

### Anti-Pattern 2: Missing Focus Indicators

```css
/* ❌ Bad */
*:focus {
  outline: none;
}

/* ✅ Good */
:focus-visible {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}
```

**Why bad**: Keyboard users can't see where they are

### Anti-Pattern 3: Positive tabIndex

```html
<!-- ❌ Bad -->
<input type="text" tabindex="3">
<input type="text" tabindex="1">
<input type="text" tabindex="2">

<!-- ✅ Good -->
<input type="text">
<input type="text">
<input type="text">
```

**Why bad**: Breaks natural tab order, confusing for users

### Anti-Pattern 4: Color-Only Indicators

```html
<!-- ❌ Bad -->
<span style="color: red;">Required field</span>

<!-- ✅ Good -->
<label for="email">
  Email
  <span aria-label="required" style="color: red;">*</span>
</label>
```

**Why bad**: Not accessible to colorblind users

### Anti-Pattern 5: Empty Links

```html
<!-- ❌ Bad -->
<a href="/delete" onclick="deleteItem()">
  <svg><use href="#delete-icon"/></svg>
</a>

<!-- ✅ Good -->
<a href="/delete" onclick="deleteItem()" aria-label="Delete item">
  <svg aria-hidden="true"><use href="#delete-icon"/></svg>
</a>
```

**Why bad**: Screen readers have no text to announce

### Anti-Pattern 6: Auto-Playing Media

```html
<!-- ❌ Bad -->
<video autoplay loop>
  <source src="video.mp4">
</video>

<!-- ✅ Good -->
<video controls>
  <source src="video.mp4">
</video>
```

**Why bad**: Disorienting, annoying, accessibility barrier

### Anti-Pattern 7: Placeholder as Label

```html
<!-- ❌ Bad -->
<input type="text" placeholder="Email">

<!-- ✅ Good -->
<label for="email">Email</label>
<input id="email" type="email" placeholder="you@example.com">
```

**Why bad**: Placeholder disappears on focus, not accessible

### Anti-Pattern 8: CAPTCHA Without Alternative

```html
<!-- ❌ Bad -->
<img src="captcha.png" alt="CAPTCHA">

<!-- ✅ Good -->
<img src="captcha.png" alt="CAPTCHA: Type the letters you see">
<button type="button">Get audio CAPTCHA</button>
<button type="button">Get new CAPTCHA</button>
```

**Why bad**: Visual-only, not accessible to blind users

### Anti-Pattern 9: Time Limits Without Warning

```javascript
// ❌ Bad
setTimeout(() => {
  logout();
}, 900000); // 15 minutes

// ✅ Good
setTimeout(() => {
  showTimeoutWarning(); // Show warning at 14 minutes
}, 840000);

function showTimeoutWarning() {
  // Show modal with "Extend session" button
}
```

**Why bad**: Users may not have time to complete tasks

### Anti-Pattern 10: Modal Without Focus Trap

```javascript
// ❌ Bad
function Modal({ isOpen, children }) {
  if (!isOpen) return null;
  return <div role="dialog">{children}</div>;
}

// ✅ Good
function Modal({ isOpen, onClose, children }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    const previousFocus = document.activeElement;
    const dialog = dialogRef.current;

    // Focus trap implementation...

    return () => {
      previousFocus?.focus();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
    >
      {children}
    </div>
  );
}
```

**Why bad**: Keyboard users can tab outside modal

---

## Quick Reference

### ARIA Cheat Sheet

```javascript
// Labels
aria-label="Close dialog"
aria-labelledby="dialog-title"
aria-describedby="hint-text"

// States
aria-checked="true|false|mixed"
aria-expanded="true|false"
aria-hidden="true|false"
aria-invalid="true|false"
aria-pressed="true|false|mixed"
aria-selected="true|false"

// Live regions
aria-live="off|polite|assertive"
aria-atomic="true|false"
aria-busy="true|false"

// Relationships
aria-controls="element-id"
aria-owns="element-id"
aria-activedescendant="element-id"

// Widget properties
aria-haspopup="true|false|menu|listbox|tree|grid|dialog"
aria-required="true|false"
aria-readonly="true|false"
aria-disabled="true|false"

// Values
aria-valuenow="50"
aria-valuemin="0"
aria-valuemax="100"
aria-valuetext="Medium"
```

### Keyboard Shortcuts

```
Tab                 Next focusable element
Shift+Tab           Previous focusable element
Enter               Activate link/button
Space               Activate button, toggle checkbox
Arrow keys          Navigate within composite widgets
Escape              Close dialog, cancel action
Home                First item
End                 Last item
Page Up/Down        Scroll
```

### Testing Checklist

```
Keyboard:
[ ] Tab through all interactive elements
[ ] Focus order is logical
[ ] Focus indicators are visible
[ ] Escape closes modals
[ ] Enter/Space activates buttons

Screen Reader:
[ ] Page title is descriptive
[ ] Headings create structure
[ ] Images have alt text
[ ] Form inputs have labels
[ ] Errors are announced
[ ] Dynamic content announced

Visual:
[ ] Text contrast 4.5:1 (AA)
[ ] Focus visible
[ ] Color not sole indicator
[ ] Works at 200% zoom
[ ] Works at 320px width
```

---

**End of Reference**

**Last Updated**: 2025-10-27
**Lines**: ~1,900
**Format**: Markdown
