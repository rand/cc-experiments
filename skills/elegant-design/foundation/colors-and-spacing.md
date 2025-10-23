# Colors and Spacing

## Color System

Create semantic color tokens, not just raw colors. This enables theme switching and maintains consistency.

### Semantic Token Structure

```css
:root {
  /* Background colors */
  --color-background: hsl(0 0% 100%);
  --color-foreground: hsl(222.2 84% 4.9%);
  
  /* Primary brand color */
  --color-primary: hsl(222.2 47.4% 11.2%);
  --color-primary-hover: hsl(222.2 47.4% 16%);
  --color-primary-foreground: hsl(210 40% 98%);
  
  /* Secondary color */
  --color-secondary: hsl(210 40% 96.1%);
  --color-secondary-hover: hsl(210 40% 92%);
  --color-secondary-foreground: hsl(222.2 47.4% 11.2%);
  
  /* Accent color */
  --color-accent: hsl(210 40% 96.1%);
  --color-accent-hover: hsl(210 40% 92%);
  --color-accent-foreground: hsl(222.2 47.4% 11.2%);
  
  /* Muted/subtle elements */
  --color-muted: hsl(210 40% 96.1%);
  --color-muted-foreground: hsl(215.4 16.3% 46.9%);
  
  /* Borders and dividers */
  --color-border: hsl(214.3 31.8% 91.4%);
  
  /* Status colors */
  --color-error: hsl(0 84.2% 60.2%);
  --color-error-foreground: hsl(0 0% 100%);
  
  --color-warning: hsl(38 92% 50%);
  --color-warning-foreground: hsl(0 0% 100%);
  
  --color-success: hsl(142 76% 36%);
  --color-success-foreground: hsl(0 0% 100%);
  
  --color-info: hsl(199 89% 48%);
  --color-info-foreground: hsl(0 0% 100%);
}
```

### Dark Mode

Dark mode is not just inverted colors - it requires different design considerations.

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-background: hsl(222.2 84% 4.9%);
    --color-foreground: hsl(210 40% 98%);
    
    --color-primary: hsl(210 40% 98%);
    --color-primary-hover: hsl(210 40% 95%);
    --color-primary-foreground: hsl(222.2 47.4% 11.2%);
    
    --color-secondary: hsl(217.2 32.6% 17.5%);
    --color-secondary-hover: hsl(217.2 32.6% 22%);
    --color-secondary-foreground: hsl(210 40% 98%);
    
    --color-muted: hsl(217.2 32.6% 17.5%);
    --color-muted-foreground: hsl(215 20.2% 65.1%);
    
    --color-border: hsl(217.2 32.6% 17.5%);
    
    /* Status colors - adjusted for dark mode */
    --color-error: hsl(0 62.8% 30.6%);
    --color-warning: hsl(38 92% 40%);
    --color-success: hsl(142 70% 25%);
    --color-info: hsl(199 89% 35%);
  }
}
```

**Dark Mode Guidelines:**
- Reduce pure whites to warm grays (#E4E4E4 instead of #FFFFFF)
- Increase contrast between elevation levels (cards on background)
- Use desaturated colors (they glow less)
- Test for eye strain in dark environments
- Provide manual toggle, don't rely only on system preference

### Color Palette Creation

**60-30-10 Rule:**
- 60% dominant color (usually background/neutral)
- 30% secondary color (brand color)
- 10% accent color (calls to action)

**Generate Scales:**

Starting with a primary color, generate tints (add white) and shades (add black) in 10% increments:

```javascript
// Example: Generate color scale from base
const baseColor = 'hsl(222, 47%, 11%)';

const scale = {
  50: lighten(baseColor, 0.5),   // lightest
  100: lighten(baseColor, 0.4),
  200: lighten(baseColor, 0.3),
  300: lighten(baseColor, 0.2),
  400: lighten(baseColor, 0.1),
  500: baseColor,                // base
  600: darken(baseColor, 0.1),
  700: darken(baseColor, 0.2),
  800: darken(baseColor, 0.3),
  900: darken(baseColor, 0.4),   // darkest
};
```

### Contrast Requirements

**WCAG AA compliance:**
- Normal text (< 18pt): 4.5:1 minimum contrast
- Large text (≥ 18pt or 14pt bold): 3:1 minimum contrast
- UI components: 3:1 minimum contrast

**Test with:**
- WebAIM Contrast Checker
- Color.review
- Chrome DevTools accessibility panel

```css
/* Good contrast examples */
.good-text {
  background: #ffffff;
  color: #222222; /* 16.1:1 ratio */
}

.good-button {
  background: #0066cc;
  color: #ffffff; /* 7.5:1 ratio */
}

/* Poor contrast - avoid */
.poor-text {
  background: #ffffff;
  color: #999999; /* 2.8:1 - fails WCAG AA */
}
```

## Elevation System

Use subtle shadows to create depth, not heavy drop-shadows.

```css
:root {
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
  --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
}

/* Usage */
.card {
  box-shadow: var(--shadow-md);
}

.modal {
  box-shadow: var(--shadow-xl);
}
```

**Dark Mode Shadows:**
```css
@media (prefers-color-scheme: dark) {
  :root {
    /* Stronger shadows needed in dark mode for depth */
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5);
    --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.6);
  }
}
```

## Spacing System

Use consistent spacing that creates visual rhythm. Base unit of 8px.

### Spacing Scale

```css
:root {
  --space-0: 0;
  --space-0-5: 0.125rem;  /* 2px */
  --space-1: 0.25rem;     /* 4px */
  --space-2: 0.5rem;      /* 8px */
  --space-3: 0.75rem;     /* 12px */
  --space-4: 1rem;        /* 16px */
  --space-5: 1.25rem;     /* 20px */
  --space-6: 1.5rem;      /* 24px */
  --space-8: 2rem;        /* 32px */
  --space-10: 2.5rem;     /* 40px */
  --space-12: 3rem;       /* 48px */
  --space-16: 4rem;       /* 64px */
  --space-20: 5rem;       /* 80px */
  --space-24: 6rem;       /* 96px */
  --space-32: 8rem;       /* 128px */
}
```

### Usage Guidelines

**Spacing creates relationships:**
- **Small spacing (4-8px)**: Related elements within a group
- **Medium spacing (16-24px)**: Between groups within a section
- **Large spacing (32-48px)**: Between sections
- **Extra large spacing (64-96px)**: Between major page divisions

```css
/* Example: Card component */
.card {
  padding: var(--space-6);          /* 24px internal padding */
  margin-bottom: var(--space-4);     /* 16px between cards */
  gap: var(--space-4);               /* 16px between card elements */
}

.card-title {
  margin-bottom: var(--space-2);     /* 8px below title */
}

.card-section {
  margin-top: var(--space-6);        /* 24px between sections */
}
```

### White Space Principles

**More is better:**
- Don't fear empty space
- Use space to create groupings (Gestalt proximity principle)
- Increase space between unrelated elements
- Reduce space between related elements

**Practical application:**
```css
/* Good: Clear grouping with space */
.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);              /* 8px between label and input */
  margin-bottom: var(--space-6);    /* 24px between form groups */
}

/* Good: Section separation */
.section {
  margin-bottom: var(--space-12);   /* 48px between major sections */
}
```

## Complete Example

```css
:root {
  /* ===== COLORS ===== */
  /* Light mode */
  --color-background: #ffffff;
  --color-foreground: #0a0a0a;
  --color-primary: #0070f3;
  --color-primary-hover: #0051cc;
  --color-border: #eaeaea;
  --color-error: #e00;
  --color-success: #0070f3;
  --color-warning: #f5a623;
  
  /* ===== SPACING ===== */
  --space-2: 0.5rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;
  
  /* ===== ELEVATION ===== */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-background: #000000;
    --color-foreground: #e4e4e4;
    --color-primary: #3291ff;
    --color-primary-hover: #0070f3;
    --color-border: #333333;
    
    /* Stronger shadows for dark mode */
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5);
  }
}

/* Apply to document */
body {
  background: var(--color-background);
  color: var(--color-foreground);
}
```

## Color Tools

**Palette generators:**
- Coolors (https://coolors.co)
- Huemint (https://huemint.com) - AI-based palettes
- Adobe Color (https://color.adobe.com)

**Contrast checkers:**
- WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker)
- Color.review (https://color.review)
- Colorable (https://colorable.jxnblk.com)

**Dark mode tools:**
- Night Eye - preview dark mode
- Dark Reader - test dark themes

## Best Practices

### Do:
- ✅ Use semantic color tokens
- ✅ Support both light and dark modes
- ✅ Ensure 4.5:1 contrast for text
- ✅ Test colors with accessibility tools
- ✅ Use consistent spacing (8px base system)
- ✅ Create visual rhythm with spacing
- ✅ Use subtle shadows for elevation
- ✅ Group related elements with reduced spacing

### Don't:
- ❌ Hardcode color values throughout codebase
- ❌ Use pure black (#000) or pure white (#fff) in dark mode
- ❌ Forget to test contrast ratios
- ❌ Use random spacing values
- ❌ Overuse shadows (depth without meaning)
- ❌ Ignore white space (cramped designs feel unprofessional)
- ❌ Make status colors too subtle (errors must be obvious)

## Quick Reference Table

| Element | Light Mode | Dark Mode | Usage |
|---------|-----------|-----------|--------|
| Background | #ffffff | #000000 | Main surface |
| Foreground | #0a0a0a | #e4e4e4 | Primary text |
| Primary | #0070f3 | #3291ff | Brand color, CTAs |
| Border | #eaeaea | #333333 | Dividers, outlines |
| Error | #e00 | #ff3333 | Error states |
| Success | #0070f3 | #3291ff | Success states |
| Card padding | 24px (--space-6) | 24px | Internal spacing |
| Section gap | 48px (--space-12) | 48px | Between sections |
