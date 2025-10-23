# Anti-Patterns to Avoid

## Component Design

❌ **Building custom components when design systems have them**
- Always check shadcn/ui, daisyUI, HeroUI first
- Don't reinvent the wheel

❌ **Using `<div>` for everything**
- Use semantic HTML: `<button>`, `<nav>`, `<main>`, `<article>`
- Improves accessibility and SEO

❌ **Props hell**
- Don't pass 10+ props to a single component
- Use composition instead

## Layout

❌ **Using absolute positioning for layout**
- Use Flexbox or CSS Grid instead
- Absolute positioning is fragile and hard to maintain

❌ **Forgetting mobile users**
- Always test on mobile devices
- Mobile-first approach prevents issues

❌ **Tiny touch targets**
- Minimum 44x44px for touch interfaces
- Especially important on mobile

## Typography

❌ **Mixing multiple sans-serif or monospace fonts**
- Use Geist for UI, JetBrains Mono for code
- Consistency is key

❌ **Using fonts smaller than 14px for code**
- Code needs to be readable
- 14px minimum for JetBrains Mono

❌ **Forgetting font fallbacks**
- Always provide system font fallbacks
- Prevent FOIT (Flash of Invisible Text)

## Colors & Styling

❌ **Using vague color names**
- Use semantic tokens (--color-primary, not --blue)
- Makes theming easier

❌ **Forgetting dark mode**
- Test both light and dark modes
- Different contrast requirements

❌ **Poor contrast ratios**
- Text needs 4.5:1 minimum
- Test with accessibility tools

## Animation

❌ **Animating expensive properties**
- Don't animate width, height, top, left
- Use transform and opacity only

❌ **Ignoring reduced-motion preferences**
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Interactive Elements

❌ **Auto-scrolling when user is reading**
- Respect user scroll position
- Only auto-scroll when near bottom

❌ **Blocking UI during operations**
- Show loading states
- Allow cancellation

❌ **Showing raw ANSI codes in terminals**
- Parse and render ANSI colors
- Make terminals beautiful

❌ **Forgetting empty/loading/error states**
- Handle all states:
  - Empty (no data yet)
  - Loading (fetching)
  - Error (failed)
  - Success (data present)

## Accessibility

❌ **Skipping accessibility**
- It's not optional
- Retrofit is much harder than building it in

❌ **No keyboard navigation**
- All interactive elements must be keyboard accessible
- Test with keyboard only

❌ **Missing alt text**
- Images need descriptive alt text
- Icon buttons need aria-labels

❌ **Using placeholder as label**
- Placeholders disappear on input
- Always provide proper labels

## Performance

❌ **Loading unnecessary JavaScript**
- Code split at route boundaries
- Lazy load below-the-fold content

❌ **Serving unoptimized images**
- Use WebP or AVIF formats
- Implement responsive images
- Lazy load images

❌ **Forgetting to measure performance**
- Use Lighthouse regularly
- Set performance budgets

## Spacing

❌ **Creating inconsistent spacing**
- Use spacing system (8px base)
- Maintain visual rhythm

❌ **Ignoring white space**
- More is better
- Don't cram content

## Developer Experience

❌ **Committing without testing**
- Test on multiple devices
- Check accessibility
- Run Lighthouse

❌ **Not using design system components**
- Don't build what exists
- Leverage shadcn/ui, daisyUI, HeroUI

❌ **Mixing design systems**
- Choose one and stick with it
- Consistency matters

## Quick Reference: Do's

✅ Start with user flows before code
✅ Use design system components first
✅ Think mobile-first
✅ Make accessibility a priority
✅ Use semantic HTML
✅ Create reusable design tokens
✅ Animate with transform and opacity
✅ Handle all states
✅ Measure performance
✅ Use Geist for UI, JetBrains Mono for code
✅ Support keyboard navigation
✅ Stream content when possible
✅ Provide copy buttons for code
✅ Test with real users
