# Component Architecture and Accessibility

## Component Architecture

### Atomic Design Principles

Build from small to large:
- **Atoms**: Buttons, inputs, labels
- **Molecules**: Search bar (input + button), form field (label + input + error)
- **Organisms**: Header, card, form
- **Templates**: Page layouts
- **Pages**: Specific instances

### Component Structure

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

export function Button({ 
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  children,
  onClick,
  type = 'button'
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`btn btn-${variant} btn-${size}`}
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading ? <Spinner /> : children}
    </button>
  );
}
```

### Composition Over Configuration

Prefer composable components:

```typescript
// Good: Composable
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>
    Content here
  </CardContent>
</Card>

// Avoid: Props hell
<Card 
  title="Title"
  content="Content"
  headerActions={[...]}
  footer={...}
/>
```

## Accessibility (WCAG 2.1 AA)

### Semantic HTML

Use proper HTML elements:

```tsx
// Good
<button onClick={handleClick}>Click me</button>
<nav>...</nav>
<main>...</main>
<article>...</article>

// Bad
<div onClick={handleClick}>Click me</div>
<div className="nav">...</div>
```

### ARIA Labels

```tsx
// Icon-only button
<button aria-label="Close dialog">
  <X size={16} />
</button>

// Form field with description
<div>
  <label htmlFor="email">Email</label>
  <input 
    id="email"
    type="email"
    aria-describedby="email-hint"
  />
  <p id="email-hint">We'll never share your email</p>
</div>

// Dynamic content
<div aria-live="polite" aria-atomic="true">
  {status}
</div>
```

### Keyboard Navigation

**All interactive elements must be keyboard accessible:**

```tsx
function Dialog({ open, onClose }: DialogProps) {
  useEffect(() => {
    if (!open) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      tabIndex={-1}
    >
      {/* Dialog content */}
    </div>
  );
}
```

**Focus management:**

```tsx
function Modal({ open }: { open: boolean }) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (open) {
      // Save current focus
      previousFocus.current = document.activeElement as HTMLElement;
      // Focus modal
      modalRef.current?.focus();
    } else {
      // Restore focus
      previousFocus.current?.focus();
    }
  }, [open]);

  return (
    <div ref={modalRef} tabIndex={-1} role="dialog">
      {/* Modal content */}
    </div>
  );
}
```

### Color Contrast

**WCAG Requirements:**
- Normal text: 4.5:1 minimum
- Large text (18pt+ or 14pt+ bold): 3:1 minimum
- UI components: 3:1 minimum

```css
/* Good contrast */
.good-text {
  background: #ffffff;
  color: #222222; /* 16.1:1 */
}

/* Poor contrast - fails WCAG */
.poor-text {
  background: #ffffff;
  color: #999999; /* 2.8:1 */
}
```

**Test with:**
- WebAIM Contrast Checker
- Chrome DevTools accessibility panel
- axe DevTools

### Screen Reader Support

```tsx
// Skip navigation
<a href="#main-content" className="skip-link">
  Skip to main content
</a>

// Alternative text for images
<img src="..." alt="Descriptive text" />

// Hidden labels for icon buttons
<button>
  <span className="sr-only">Delete item</span>
  <Trash size={16} aria-hidden="true" />
</button>
```

```css
/* Screen reader only content */
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
```

### Forms

```tsx
function FormField({ 
  label, 
  error, 
  required,
  ...inputProps 
}: FormFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <div className="form-field">
      <label htmlFor={id}>
        {label}
        {required && <span aria-label="required">*</span>}
      </label>
      <input
        id={id}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        aria-required={required}
        {...inputProps}
      />
      {error && (
        <p id={errorId} className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

## Best Practices

### Do:
- ✅ Use semantic HTML elements
- ✅ Provide ARIA labels for icon-only buttons
- ✅ Ensure keyboard navigation works
- ✅ Test with screen readers
- ✅ Maintain focus management in modals
- ✅ Provide skip navigation links
- ✅ Use proper heading hierarchy (h1-h6)
- ✅ Ensure 4.5:1 contrast for text
- ✅ Make forms accessible with labels and errors

### Don't:
- ❌ Use divs for buttons
- ❌ Forget alt text for images
- ❌ Trap keyboard focus
- ❌ Rely only on color to convey information
- ❌ Use tiny touch targets (< 44x44px)
- ❌ Forget to test with keyboard only
- ❌ Use placeholder as label
- ❌ Auto-play media without controls
