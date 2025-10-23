# Typography

Elegant, modern typography sets the foundation for professional interfaces.

## Font Selection

### Primary Fonts

**1. Geist (https://vercel.com/font) - USE FOR ALL UI TEXT**

Designed by Vercel specifically for interfaces.

**Characteristics:**
- Excellent legibility at all sizes
- Perfect for UI text and content
- Crisp rendering on all displays
- Variable font with flexible weights

**Use Geist for:**
- Body text and paragraphs
- Headings and titles
- UI labels and buttons
- Navigation and menus
- Form fields and inputs
- **95% of all typography**

```css
font-family: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
```

**2. JetBrains Mono (https://jetbrains.com/mono) - USE FOR ALL CODE/TECHNICAL**

Purpose-built for developers.

**Characteristics:**
- Increased height for better readability
- Ligatures for common code patterns (=>, >=, !=)
- Clear distinction between similar characters (0/O, 1/l/I)
- Optimized for long reading sessions

**Use JetBrains Mono for:**
- Code blocks and snippets
- Terminal output
- Log viewers
- Diff displays
- File paths
- Technical identifiers
- **Minimum 14px font size**

```css
font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
font-size: 14px; /* minimum */
font-variant-ligatures: common-ligatures; /* enable ligatures */
```

### Alternative Elegant Fonts

If Geist or JetBrains Mono are unavailable:

**Sans-serif alternatives:**
- **Geist Mono** - Companion monospace to Geist (code alternative)
- **Inter** - Highly legible, great metrics, excellent fallback
- **IBM Plex Sans** - Professional, humanist, good brand font
- **Space Grotesk** - Modern, geometric, good for headlines

**Monospace alternatives:**
- **Geist Mono** - Vercel's monospace companion
- **Fira Code** - Excellent ligatures, widely supported
- **Berkeley Mono** - Premium option if budget allows
- **Cascadia Code** - Microsoft's code font with ligatures

**System font fallback:**
```css
/* If custom fonts fail to load */
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
```

## Font Loading Strategy

Use optimal loading to prevent FOIT (Flash of Invisible Text):

```css
@font-face {
  font-family: 'Geist';
  src: url('/fonts/geist.woff2') format('woff2');
  font-display: swap; /* Show fallback immediately, swap when loaded */
  font-weight: 100 900; /* Variable font weight range */
}

@font-face {
  font-family: 'JetBrains Mono';
  src: url('/fonts/jetbrains-mono.woff2') format('woff2');
  font-display: swap;
  font-weight: 400 700;
}
```

## Typography Scales

Use a modular scale for consistent hierarchy.

**Common scales:**
- 1.25 (major third) - compact, good for dense interfaces
- 1.333 (perfect fourth) - balanced, most versatile
- 1.5 (perfect fifth) - generous, good for marketing

**Example: 1.25 scale (recommended):**

```css
:root {
  --font-size-xs: 0.64rem;   /* 10.24px */
  --font-size-sm: 0.8rem;    /* 12.8px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-lg: 1.25rem;   /* 20px */
  --font-size-xl: 1.563rem;  /* 25px */
  --font-size-2xl: 1.953rem; /* 31.25px */
  --font-size-3xl: 2.441rem; /* 39px */
  --font-size-4xl: 3.052rem; /* 48.8px */
}
```

**Usage:**

```css
body {
  font-size: var(--font-size-base);
  line-height: 1.6;
}

h1 { font-size: var(--font-size-4xl); }
h2 { font-size: var(--font-size-3xl); }
h3 { font-size: var(--font-size-2xl); }
h4 { font-size: var(--font-size-xl); }

small { font-size: var(--font-size-sm); }
```

## Line Height

**Body text:** 1.5-1.6 for readability
**Headings:** 1.1-1.3 for impact
**Code:** 1.5-1.6 for clarity

```css
body {
  line-height: 1.6;
}

h1, h2, h3, h4, h5, h6 {
  line-height: 1.2;
}

code, pre {
  line-height: 1.6;
}
```

## Font Weights

**Geist supports variable weights (100-900):**
- 300 (light) - Use sparingly
- 400 (regular) - Body text
- 500 (medium) - UI emphasis
- 600 (semibold) - Headings, buttons
- 700 (bold) - Strong emphasis

**JetBrains Mono:**
- 400 (regular) - Most code
- 700 (bold) - Emphasis in code

```css
/* Semantic weight variables */
:root {
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}
```

## Best Practices

### Do:
- ✅ Limit to 2 font families maximum (one sans, one mono)
- ✅ Use Geist for 95% of text
- ✅ Reserve JetBrains Mono exclusively for code
- ✅ Use font-display: swap for faster rendering
- ✅ Prefer variable fonts (smaller file size, flexible weights)
- ✅ Set minimum 14px for code fonts
- ✅ Enable ligatures in monospace fonts
- ✅ Use semantic weight variables

### Don't:
- ❌ Mix multiple sans-serif fonts
- ❌ Mix multiple monospace fonts
- ❌ Use decorative fonts in interfaces
- ❌ Set code font smaller than 14px
- ❌ Forget fallback fonts
- ❌ Block rendering waiting for fonts (use swap)
- ❌ Use Comic Sans (ever)

## Accessibility

**Minimum sizes:**
- Body text: 16px (1rem)
- Small text: 14px (0.875rem)
- Code: 14px minimum

**Contrast requirements:**
- Normal text: 4.5:1 contrast ratio
- Large text (18pt+): 3:1 contrast ratio
- Use tools like WebAIM Contrast Checker

## Example Complete Setup

```css
/* CSS Variables */
:root {
  /* Font families */
  --font-sans: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  
  /* Font sizes (1.25 scale) */
  --font-size-xs: 0.64rem;
  --font-size-sm: 0.8rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.563rem;
  --font-size-2xl: 1.953rem;
  --font-size-3xl: 2.441rem;
  --font-size-4xl: 3.052rem;
  
  /* Font weights */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}

/* Base styles */
body {
  font-family: var(--font-sans);
  font-size: var(--font-size-base);
  line-height: 1.6;
  font-weight: var(--font-weight-normal);
}

/* Code elements */
code, pre, kbd, samp {
  font-family: var(--font-mono);
  font-size: 14px; /* minimum readable size */
  line-height: 1.6;
  font-variant-ligatures: common-ligatures;
}

/* Headings */
h1 { 
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  line-height: 1.2;
}

h2 { 
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-semibold);
  line-height: 1.2;
}

h3 { 
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: 1.3;
}
```

## Loading Fonts in Next.js/React

```typescript
// app/layout.tsx or _app.tsx
import { Geist } from 'next/font/google';
import localFont from 'next/font/local';

const geist = Geist({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = localFont({
  src: '../public/fonts/jetbrains-mono.woff2',
  variable: '--font-mono',
  display: 'swap',
});

export default function RootLayout({ children }) {
  return (
    <html className={`${geist.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

## Quick Reference

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Body text | Geist | 16px (1rem) | 400 |
| UI labels | Geist | 14-16px | 500 |
| Headings | Geist | Scale-based | 600-700 |
| Buttons | Geist | 14-16px | 500-600 |
| Code blocks | JetBrains Mono | 14px min | 400 |
| Terminal | JetBrains Mono | 14px | 400 |
| Small text | Geist | 14px min | 400 |
