---
name: debugging-browser-devtools
description: Comprehensive guide to browser developer tools for debugging web applications. Covers Chrome/Firefox/Safari DevTools including Sources panel, breakpoints, performance profiling, memory analysis, network debugging, Console API, React/Vue debugging, and Lighthouse/Core Web Vitals.
---

# Browser DevTools

**Last Updated**: 2025-10-26

## Overview

Browser DevTools are essential for web development debugging. This guide covers Chrome DevTools (most feature-rich), with notes on Firefox and Safari differences.

## Opening DevTools

### Keyboard Shortcuts

```
Chrome/Edge:
  F12 / Cmd+Opt+I (Mac) / Ctrl+Shift+I (Windows)
  Cmd+Opt+J (Mac) / Ctrl+Shift+J (Windows) - Console
  Cmd+Opt+C (Mac) / Ctrl+Shift+C (Windows) - Inspect Element

Firefox:
  F12 / Cmd+Opt+I (Mac) / Ctrl+Shift+I (Windows)
  Cmd+Opt+K (Mac) / Ctrl+Shift+K (Windows) - Console

Safari:
  Cmd+Opt+I (Mac) - Enable in Preferences → Advanced first
```

### DevTools Panels

**Core panels**:
- **Elements**: Inspect/modify DOM and CSS
- **Console**: Execute JavaScript, view logs
- **Sources**: Debug JavaScript with breakpoints
- **Network**: Monitor HTTP requests/responses
- **Performance**: Profile runtime performance
- **Memory**: Analyze memory usage and leaks
- **Application**: Inspect storage, service workers, manifest

**Additional panels**:
- **Security**: HTTPS, certificates, mixed content
- **Lighthouse**: Audit performance, accessibility, SEO
- **Recorder**: Record and replay user flows

---

## Elements Panel

### Inspecting DOM

**Navigate DOM tree**:
```
Click element in page → Right-click → Inspect
Or: Cmd+Shift+C, then click element

Arrow keys: Navigate siblings
Enter: Expand/collapse node
H key: Hide/show element
Delete: Delete node (temporary)
```

**Modify DOM**:
```
Right-click element:
  - Edit as HTML
  - Duplicate element
  - Delete element
  - Copy → Copy selector / XPath / element
  - Store as global variable ($0, $1, etc.)
```

**DOM search**:
```
Cmd+F (inside Elements panel)

Search by:
  - Tag name: div
  - Class: .my-class
  - ID: #my-id
  - CSS selector: div.container > p
  - XPath: //div[@class='container']
  - Text content: "Hello World"
```

### Inspecting CSS

**Styles panel** (right side):
```
Shows all CSS rules for selected element:
  - Inline styles (top)
  - Stylesheet rules (ordered by specificity)
  - Inherited styles
  - Browser defaults (user agent stylesheet)

Click checkbox: Toggle rule
Click value: Edit value
Click property: Edit property
Click selector: Edit selector
```

**Computed panel**:
```
Shows final computed values after cascade
Filter by property name
Show all / show only active properties
```

**Live CSS editing**:
```javascript
// Click element → Styles panel → Edit

// Toggle property
☑ color: red;  // Click checkbox to disable

// Add property
element.style {
  /* Click here, type property: value */
  background: blue;
}

// Force pseudo-state
Click :hov → Check :hover/:focus/:active/:visited
```

### Box Model Visualization

```
Blue: Content
Green: Padding
Yellow: Border
Orange: Margin

Click values to edit: width, height, margin, padding
```

---

## Console Panel

### Console API

**Logging**:
```javascript
// Basic logging
console.log('Hello', 'World');  // Multiple args
console.log('User:', { name: 'Alice', age: 30 });

// Log levels
console.info('Information');
console.warn('Warning!');
console.error('Error!');
console.debug('Debug info');  // Hidden by default

// Styled output
console.log('%c Big Red Text', 'color: red; font-size: 20px;');
console.log('%c Blue %c Green', 'color: blue;', 'color: green;');
```

**Structured logging**:
```javascript
// Table view
const users = [
  { name: 'Alice', age: 30 },
  { name: 'Bob', age: 25 }
];
console.table(users);

// Group related logs
console.group('User Details');
console.log('Name:', name);
console.log('Age:', age);
console.groupEnd();

// Collapsible group
console.groupCollapsed('Debug Info');
console.log('Hidden by default');
console.groupEnd();
```

**Assertions and tracing**:
```javascript
// Assert (logs only if false)
console.assert(x > 0, 'x must be positive', { x });

// Stack trace
console.trace('How did we get here?');

// Count calls
console.count('API call');  // API call: 1
console.count('API call');  // API call: 2
console.countReset('API call');

// Timing
console.time('operation');
expensiveOperation();
console.timeEnd('operation');  // operation: 123.45ms
```

### Console Utilities

**DOM selection**:
```javascript
// $ (jQuery-like selector)
$('.my-class')  // querySelector
$$('.my-class')  // querySelectorAll

// Recent inspected elements
$0  // Most recently selected element
$1  // Second most recent
$2  // Third most recent

// Event listeners
getEventListeners($0)  // All listeners on $0
```

**Monitoring**:
```javascript
// Monitor function calls
monitor(myFunction);  // Logs when myFunction is called
unmonitor(myFunction);

// Monitor events
monitorEvents($0);  // Log all events on $0
monitorEvents($0, 'click');  // Log only click events
unmonitorEvents($0);

// Copy to clipboard
copy({ name: 'Alice', age: 30 });  // Copies JSON to clipboard
```

**Inspection**:
```javascript
// Inspect object
inspect($0);  // Opens Elements panel at $0

// List properties
dir($0);  // Interactive object explorer
dirxml($0);  // XML/HTML representation

// Values
values({ a: 1, b: 2, c: 3 });  // [1, 2, 3]
keys({ a: 1, b: 2, c: 3 });    // ['a', 'b', 'c']
```

---

## Sources Panel

### Breakpoints

**Line breakpoints**:
```
1. Open file in Sources panel
2. Click line number → Blue marker
3. Run code → Execution pauses

Right-click breakpoint:
  - Edit breakpoint (condition)
  - Disable breakpoint
  - Remove breakpoint
```

**Conditional breakpoints**:
```javascript
// Right-click line number → Add conditional breakpoint
// Expression: i === 99 (only breaks when true)

for (let i = 0; i < 100; i++) {
  console.log(i);  // Breakpoint here with condition "i === 99"
}
```

**Logpoints** (log without stopping):
```javascript
// Right-click line number → Add logpoint
// Message: "Count is", count

// Equivalent to console.log but without modifying code
```

**DOM breakpoints**:
```
Elements panel → Right-click element:
  - Break on subtree modifications
  - Break on attribute modifications
  - Break on node removal

Pauses when DOM changes
```

**XHR/Fetch breakpoints**:
```
Sources → XHR/fetch Breakpoints → Add
URL contains: api/users

Pauses on matching network requests
```

**Event listener breakpoints**:
```
Sources → Event Listener Breakpoints
Check: Mouse → click
Check: Keyboard → keydown

Pauses when event fires
```

### Stepping Through Code

**Debug controls**:
```
F8 / Cmd+\ : Resume (continue)
F10 / Cmd+' : Step over
F11 / Cmd+; : Step into
Shift+F11 / Cmd+Shift+; : Step out

Step over: Execute current line, don't enter functions
Step into: Enter function on current line
Step out: Continue until current function returns
```

**Call stack**:
```
Shows function call hierarchy:
  myFunction (current)
    ↑ callerFunction
      ↑ main

Click frame → Jump to that context
Async frames: Shows async call chain
```

**Scope variables**:
```
Shows variables in current scope:
  - Local (function scope)
  - Closure (parent scopes)
  - Global (window)

Click value → Edit value
Right-click → Copy value / Store as global variable
```

**Watch expressions**:
```
Add expression to watch:
  count > 10
  user.name
  myArray.length

Updates automatically on each step
```

### Source Maps

**Enable source maps**:
```
Settings (⚙️) → Sources → Enable JavaScript source maps

Debugging minified code:
//# sourceMappingURL=app.min.js.map

DevTools loads original source for debugging
```

**Workspace mapping** (local edits persist):
```
Sources → Filesystem → Add folder
Grant access → Edit files in DevTools
Changes save to disk automatically
```

---

## Network Panel

### Monitoring Requests

**Request list**:
```
Columns:
  - Name: Request URL
  - Status: HTTP status code
  - Type: Content type (document, script, xhr, etc.)
  - Initiator: What triggered request
  - Size: Response size
  - Time: Duration
  - Waterfall: Timeline visualization

Click request → Details panel
```

**Filter requests**:
```
Filter bar:
  - XHR: XMLHttpRequest / fetch
  - JS: JavaScript files
  - CSS: Stylesheets
  - Img: Images
  - Font: Web fonts
  - Doc: HTML documents
  - WS: WebSocket
  - Other: Uncategorized

Search: domain:example.com, method:POST, status-code:404
```

### Request Details

**Headers tab**:
```
General:
  Request URL: https://api.example.com/users
  Request Method: GET
  Status Code: 200 OK

Response Headers:
  content-type: application/json
  cache-control: max-age=3600

Request Headers:
  User-Agent: Mozilla/5.0...
  Authorization: Bearer token...
```

**Preview tab**:
```
Formatted response:
  - JSON: Collapsible tree
  - HTML: Rendered preview
  - Images: Visual preview
```

**Response tab**:
```
Raw response body
Copy response, save as file
```

**Timing tab**:
```
Breakdown of request timing:
  - Queueing: Waiting in queue
  - Stalled: Waiting for connection
  - DNS Lookup: Domain resolution
  - Initial connection: TCP handshake
  - SSL: TLS negotiation
  - Request sent: Sending request
  - Waiting (TTFB): Time to first byte
  - Content Download: Receiving response

Total: 234ms
```

### Network Throttling

**Simulate slow connections**:
```
Network panel → Throttling dropdown:
  - Fast 3G (750 KB/s)
  - Slow 3G (400 KB/s)
  - Offline

Custom: Add custom profile
```

### HAR Files (HTTP Archive)

**Export network activity**:
```
Network panel → Right-click → Save all as HAR with content

Share with teammates, analyze in external tools
Load: Drag HAR file into Network panel
```

---

## Performance Panel

### Recording Performance

**Record runtime performance**:
```
1. Click Record (circle button)
2. Perform actions on page
3. Click Stop

Or: Reload with profiling (Cmd+Shift+E)
```

**Performance profile**:
```
Timeline shows:
  - FPS: Frames per second
  - CPU: CPU usage (colors = activity types)
  - NET: Network requests
  - HEAP: Memory usage

Zoom: Scroll over timeline
Select range: Click and drag
```

### Flame Chart

**Analyze call stack**:
```
Main thread timeline shows function calls:
  - Width = duration
  - Y-axis = call stack depth
  - Color = activity type (scripting, rendering, painting)

Click function → Bottom panel shows:
  - Self time: Time in function (excluding children)
  - Total time: Time in function + children
  - Source file and line number

Red triangle: Long task (>50ms)
```

**Activity types**:
```
Yellow: JavaScript execution
Purple: Rendering (layout, paint)
Green: Painting
Blue: Loading (parsing HTML/CSS)
Gray: Other
```

### Performance Insights (2025 Feature)

**Automated analysis**:
```
Performance Insights panel (new):
  - Identifies performance issues automatically
  - Shows "Insights" for long tasks, layout shifts, etc.
  - Click insight → Jump to relevant code

Common insights:
  - "Long task blocking main thread"
  - "Layout shift caused by image without dimensions"
  - "Render-blocking resource"
```

### Web Vitals

**Core Web Vitals** (2025 thresholds):
```
LCP (Largest Contentful Paint): < 2.5s
FID (First Input Delay): < 100ms
CLS (Cumulative Layout Shift): < 0.1

Performance panel → Experience section shows vitals
Hover over metric → See which element triggered it
```

---

## Memory Panel

### Heap Snapshots

**Take snapshot**:
```
Memory panel → Heap snapshot → Take snapshot

Shows all objects in memory:
  - Constructor: Object type
  - Distance: Steps from root
  - Shallow Size: Object size
  - Retained Size: Object + retained objects

Compare snapshots to find leaks
```

**Find memory leaks**:
```
1. Take snapshot (baseline)
2. Perform action (e.g., open/close modal)
3. Take second snapshot
4. Select "Comparison" view
5. Look for objects with positive delta

Detached DOM nodes = likely leak
```

### Allocation Timeline

**Record allocations over time**:
```
Memory panel → Allocation instrumentation on timeline → Start

Blue bars = allocations
Gray bars = garbage collections

Click bar → See objects allocated at that time
```

### Allocation Sampling

**Lightweight profiling**:
```
Memory panel → Allocation sampling → Start

Shows memory allocations by function
Less overhead than timeline, good for long recordings
```

---

## Application Panel

### Storage

**Local Storage**:
```
Application → Local Storage → domain
View/edit/delete key-value pairs
```

**Session Storage**:
```
Application → Session Storage → domain
Cleared when tab closes
```

**Cookies**:
```
Application → Cookies → domain
View/edit/delete cookies
Attributes: Name, Value, Domain, Path, Expires, Size, HttpOnly, Secure, SameSite
```

**IndexedDB**:
```
Application → IndexedDB → database → object store
Browse records, delete records
```

### Service Workers

**Inspect service workers**:
```
Application → Service Workers

Shows:
  - Status: Activated, Waiting, Installing
  - Source: Service worker script
  - Scope: URLs controlled

Actions:
  - Update: Force update
  - Unregister: Remove service worker
  - Offline: Simulate offline mode
```

### Cache Storage

**Inspect cache entries**:
```
Application → Cache Storage → cache name
View cached requests/responses
Delete individual entries
```

---

## Lighthouse

### Running Audits

**Lighthouse panel**:
```
Categories:
  ☑ Performance
  ☑ Accessibility
  ☑ Best Practices
  ☑ SEO
  ☑ PWA

Device: Mobile / Desktop
Throttling: Simulated / DevTools / None

Click "Analyze page load"
```

### Lighthouse Scores (2025)

**Score ranges**:
```
90-100: Green (Good)
50-89: Orange (Needs Improvement)
0-49: Red (Poor)

Each category has weighted metrics
```

**Performance metrics**:
```
- First Contentful Paint (FCP): < 1.8s
- Largest Contentful Paint (LCP): < 2.5s
- Total Blocking Time (TBT): < 200ms
- Cumulative Layout Shift (CLS): < 0.1
- Speed Index: < 3.4s
```

**Opportunities** (improve load time):
```
- Eliminate render-blocking resources
- Properly size images
- Defer offscreen images
- Minify CSS/JavaScript
- Serve images in next-gen formats (WebP, AVIF)
```

**Diagnostics** (additional info):
```
- Minimize main thread work
- Reduce JavaScript execution time
- Avoid enormous network payloads
- Serve static assets with efficient cache policy
```

---

## Debugging Frameworks

### React DevTools

**Install extension**:
```
Chrome Web Store: React Developer Tools
Firefox Add-ons: React Developer Tools
```

**Components tab**:
```
Browse component tree
Inspect props, state, hooks
Edit props/state in real-time
Search components by name
```

**Profiler tab**:
```
Record component renders
Identify expensive renders
See why component re-rendered
Flame chart shows render duration
```

### Vue DevTools

**Install extension**:
```
Chrome/Firefox: Vue.js devtools
```

**Features**:
```
- Components: Inspect component tree, props, data
- Vuex: State management inspector
- Events: View emitted events
- Routing: Vue Router inspector
- Performance: Component render profiling
```

---

## Advanced Features

### Overrides

**Override network responses**:
```
Sources → Overrides → Select folder
Enable local overrides

Edit file in Sources panel → Saves to local folder
Reloads serve local version instead of network
```

### Snippets

**Save reusable scripts**:
```
Sources → Snippets → New snippet

Write JavaScript:
  console.log('Testing...');
  $$('.my-class').forEach(el => el.remove());

Cmd+Enter: Run snippet
```

### Coverage

**Find unused CSS/JS**:
```
Cmd+Shift+P → Show Coverage

Click Record → Perform actions → Stop

Red: Unused code
Blue: Executed code

Click file → See highlighted unused lines
```

### Rendering Panel

**Debug rendering issues**:
```
Cmd+Shift+P → Show Rendering

Options:
  - Paint flashing: Highlights repaints (green)
  - Layout Shift Regions: Shows CLS culprits (blue)
  - FPS meter: Shows frames per second
  - Scrolling performance issues: Highlights slow scrolling
  - Emulate CSS media: prefers-color-scheme, prefers-reduced-motion
```

---

## Anti-Patterns

### Common Mistakes

```
❌ NEVER: Leave console.log() in production code
   → Performance overhead, exposes debug info

❌ NEVER: Debug minified code without source maps
   → Impossible to read, wastes time

❌ NEVER: Ignore Console errors/warnings
   → Often cause subtle bugs, performance issues

❌ NEVER: Test only on desktop Chrome
   → Mobile Safari, Firefox have different behaviors

❌ NEVER: Use DevTools on production site for testing
   → Use staging/dev environments

❌ NEVER: Disable cache during development
   → Doesn't reflect real user experience
```

### Best Practices

```
✅ ALWAYS: Use Lighthouse for performance audits
✅ ALWAYS: Enable source maps for debugging
✅ ALWAYS: Test Core Web Vitals in Performance panel
✅ ALWAYS: Use React/Vue DevTools for framework debugging
✅ ALWAYS: Clear cache when testing service workers
✅ ALWAYS: Use network throttling for mobile testing
✅ ALWAYS: Export HAR files for sharing network issues
```

---

## Related Skills

- **gdb-fundamentals.md**: GDB for C/C++ debugging
- **lldb-macos-debugging.md**: LLDB for macOS/iOS
- **python-debugging.md**: Python debugging tools
- **remote-debugging.md**: Remote debugging techniques
- **frontend-performance.md**: Frontend optimization
- **web-accessibility-fundamentals.md**: Accessibility testing

---

## Summary

Browser DevTools provide comprehensive web debugging capabilities:

1. **Elements**: Inspect/modify DOM and CSS, force pseudo-states
2. **Console**: Execute JavaScript, advanced logging, utilities
3. **Sources**: Breakpoints, stepping, watch expressions, source maps
4. **Network**: Monitor requests, timing, throttling, HAR export
5. **Performance**: Flame charts, Core Web Vitals, performance insights
6. **Memory**: Heap snapshots, leak detection, allocation profiling
7. **Lighthouse**: Automated audits for performance, accessibility, SEO
8. **Framework DevTools**: React/Vue component inspection and profiling

**Quick start**:
```
F12 → Open DevTools
Cmd+Shift+C → Inspect element
Sources → Set breakpoint → Reload page
Network → Monitor requests → Check timing
Performance → Record → Analyze flame chart
Lighthouse → Run audit → Review opportunities
```

Master browser DevTools for efficient web development and debugging.
