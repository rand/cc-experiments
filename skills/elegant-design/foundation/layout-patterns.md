# Layout Patterns

## Grid Systems

### 12-Column Grid

Standard for complex layouts:

```css
.container {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--space-4);
}

.col-6 {
  grid-column: span 6; /* Half width */
}

.col-4 {
  grid-column: span 4; /* Third width */
}

.col-3 {
  grid-column: span 3; /* Quarter width */
}
```

### CSS Grid vs Flexbox

**Use CSS Grid for:**
- 2D layouts (rows AND columns)
- Complex, structured layouts
- Overlapping elements
- Precise placement

```css
.grid-layout {
  display: grid;
  grid-template-columns: 250px 1fr 300px; /* sidebar, main, aside */
  grid-template-rows: auto 1fr auto; /* header, content, footer */
  gap: var(--space-4);
}
```

**Use Flexbox for:**
- 1D layouts (single axis)
- Dynamic content sizing
- Alignment within containers
- Navigation, toolbars

```css
.flex-layout {
  display: flex;
  flex-direction: row;
  gap: var(--space-4);
  align-items: center;
}
```

## Container Widths

```css
:root {
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
  --container-2xl: 1536px;
}

.container {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding: 0 var(--space-4);
}
```

## Responsive Breakpoints

Mobile-first approach:

```css
/* Mobile base styles (< 640px) */
.element {
  padding: var(--space-4);
  flex-direction: column;
}

/* Tablet (≥ 640px) */
@media (min-width: 640px) {
  .element {
    padding: var(--space-6);
  }
}

/* Desktop (≥ 1024px) */
@media (min-width: 1024px) {
  .element {
    padding: var(--space-8);
    flex-direction: row;
  }
}

/* Large desktop (≥ 1280px) */
@media (min-width: 1280px) {
  .element {
    padding: var(--space-12);
  }
}
```

## Responsive Patterns

**Stack on mobile, side-by-side on desktop:**
```css
.responsive-layout {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

@media (min-width: 768px) {
  .responsive-layout {
    flex-direction: row;
  }
}
```

**Single column mobile, multi-column desktop:**
```css
.responsive-grid {
  display: grid;
  grid-template-columns: 1fr; /* mobile: 1 column */
  gap: var(--space-4);
}

@media (min-width: 768px) {
  .responsive-grid {
    grid-template-columns: repeat(2, 1fr); /* tablet: 2 columns */
  }
}

@media (min-width: 1024px) {
  .responsive-grid {
    grid-template-columns: repeat(3, 1fr); /* desktop: 3 columns */
  }
}
```

## Layout Inspiration

### Vercel Style
- Generous white space (--space-12 to --space-24 between sections)
- Large, clear typography
- Subtle gradients and blurs
- Minimal borders, maximum contrast
- Hero sections with strong CTAs

```css
.vercel-hero {
  padding: var(--space-24) var(--space-4);
  text-align: center;
  background: linear-gradient(to bottom, var(--color-background), var(--color-muted));
}
```

### Hex Style
- Data-dense but organized
- Strong visual hierarchy with cards
- Card-based layouts with clear groupings
- Effective use of color to categorize

```css
.hex-card {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
}
```

### Baseten Style
- Clear documentation structure
- Code examples integrated smoothly
- Left sidebar navigation (250px width)
- Right sidebar table of contents (250px width)
- Main content centered (800px max-width)

```css
.baseten-layout {
  display: grid;
  grid-template-columns: 250px 1fr 250px;
  gap: var(--space-8);
}

@media (max-width: 1024px) {
  .baseten-layout {
    grid-template-columns: 1fr; /* stack on mobile */
  }
}
```

## Touch Targets

**Minimum 44x44px for touch interfaces:**

```css
.touch-target {
  min-width: 44px;
  min-height: 44px;
  padding: var(--space-3);
  /* Ensure actual interactive area, not just visible area */
}

/* Increase spacing between touch targets on mobile */
@media (max-width: 640px) {
  .touch-toolbar {
    gap: var(--space-4); /* 16px between buttons */
  }
}
```

## Common Layout Patterns

### Dashboard Layout
```css
.dashboard {
  display: grid;
  grid-template-areas:
    "header header header"
    "sidebar main aside"
    "footer footer footer";
  grid-template-columns: 250px 1fr 300px;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
}

.dashboard-header { grid-area: header; }
.dashboard-sidebar { grid-area: sidebar; }
.dashboard-main { grid-area: main; }
.dashboard-aside { grid-area: aside; }
.dashboard-footer { grid-area: footer; }
```

### Documentation Layout
```css
.docs-layout {
  display: grid;
  grid-template-columns: 250px minmax(0, 800px) 250px;
  gap: var(--space-8);
  max-width: var(--container-2xl);
  margin: 0 auto;
  padding: var(--space-4);
}

.docs-nav { /* left sidebar */ }
.docs-content { /* main content */ }
.docs-toc { /* right sidebar table of contents */ }
```

### Card Grid
```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}

/* Cards automatically wrap and maintain consistent width */
```

## Best Practices

### Do:
- ✅ Start mobile-first, enhance for larger screens
- ✅ Use CSS Grid for 2D layouts
- ✅ Use Flexbox for 1D layouts
- ✅ Test on multiple device sizes
- ✅ Ensure touch targets are ≥ 44x44px
- ✅ Use consistent container widths
- ✅ Embrace white space generously

### Don't:
- ❌ Use absolute positioning for layout
- ❌ Forget mobile users
- ❌ Make text lines too long (65-75 characters max)
- ❌ Ignore touch target sizes
- ❌ Use fixed widths without media queries
- ❌ Cram content without spacing
