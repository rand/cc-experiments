---
name: design-patterns
description: Reference guide for detecting AI slop patterns in visual and UX design including generic gradients, cookie-cutter layouts, and buzzword-heavy copy. Use as reference when reviewing design quality.
---

# Design Slop Patterns

This reference documents common "AI slop" patterns in visual and UX design that indicate generic, low-quality, AI-generated content.

## Table of Contents
- Visual Design Slop
- Color and Typography
- Layout Antipatterns
- Component Overuse
- UX Writing Slop
- Animation and Interaction

## Visual Design Slop

### Generic Gradient Backgrounds
**High-Risk Patterns:**
- Purple/pink/blue mesh gradients (the "AI startup" gradient)
- Holographic gradients on everything
- Gradient overlays on every image
- Gradients as the primary design element rather than accent

**Better Approach:**
- Use solid colors as foundation
- Gradients sparingly for emphasis
- Consider brand-specific color palettes
- Explore textures, patterns, or illustrations

### Overused Visual Motifs
**Common AI Design Clichés:**
- Floating 3D geometric shapes (cubes, spheres, toruses)
- Glass morphism everywhere
- Neumorphism (soft UI) on inappropriate elements
- Excessive blur effects
- Particle systems for no reason
- Tilt/perspective transforms on cards

**Detection Signal:** If every section has floating 3D shapes or glass effects, it's likely slop.

### Stock Photo Aesthetics
**Red Flags:**
- Generic diverse workplace photos
- Excessive whitespace with minimal content
- Hero images of people pointing at screens enthusiastically
- Business people in suits shaking hands
- Overhead shots of "creative workspace" with MacBook and coffee

**Better:** Use authentic, specific imagery that relates to actual content.

## Color and Typography

### Color Palette Slop
**Generic Palettes to Avoid:**
- Purple (#7F5AF0) + Cyan (#2CB67D) + Pink (#FF6AC1)
- Entire palette of pastel colors
- Neon everything
- Pure black (#000) and pure white (#FFF) as main colors

**Better Approach:**
- Build palette from brand or content needs
- Use color theory intentionally
- Consider accessibility (WCAG contrast ratios)
- Limit palette to 2-3 primary colors + neutrals

### Typography Slop
**Overused Font Combinations:**
- Inter for everything
- Montserrat + Open Sans
- Poppins + Roboto
- Using same font family for headings and body

**Generic Font Choices:**
- Defaulting to "modern" sans-serif for everything
- Using display fonts for body text
- Inconsistent font weights and sizes
- Excessive variation (5+ different fonts)

**Better:**
- Choose fonts that match content tone
- Establish clear hierarchy (H1, H2, body, caption)
- Test readability at various sizes
- Use 2-3 font families maximum

### Type Hierarchy Issues
**Slop Indicators:**
- Every heading the same size
- Body text too small (<16px)
- Insufficient line height (< 1.5 for body text)
- Poor contrast ratios
- Centered text for long paragraphs

## Layout Antipatterns

### Generic Landing Page Structure
**The AI Landing Page Template:**
```
1. Hero with gradient background + "Empower Your Business"
2. Three feature cards with icons
3. Stats section with big numbers
4. Testimonials (often fake-looking)
5. Pricing cards (often generic)
6. FAQ section
7. CTA button "Get Started Today"
```

**Better:** Design layout based on user journey and actual content needs.

### Spacing Slop
**Red Flags:**
- Everything spaced exactly the same
- Excessive whitespace without purpose
- Cramped sections alternating with huge gaps
- No visual grouping (everything floating equally)

**Better:**
- Use spacing to create visual hierarchy
- Group related elements closer
- Vary spacing intentionally
- Follow 8px or 4px grid systems

### Card Overuse
**When Cards Become Slop:**
- Everything is in a card
- Cards within cards within cards
- Cards with excessive shadows and borders
- All cards same size regardless of content

**Better:**
- Use cards to group related information
- Vary card styles based on importance
- Consider alternatives: simple borders, background colors, spacing

### Center-Alignment Everywhere
**Slop Pattern:**
- All text center-aligned
- All elements centered on page
- Symmetry forced where it doesn't belong

**Better:**
- Use alignment intentionally
- Left-align body text for readability
- Center when it serves a purpose
- Consider asymmetric layouts

## Component Overuse

### Button Slop
**Generic Button Patterns:**
- Every button has excessive border radius (fully rounded)
- Buttons floating with huge shadows
- Gradient buttons everywhere
- "Ghost buttons" as primary CTAs
- Buttons with icons but no text labels

**Better:**
- Style buttons based on hierarchy (primary, secondary, tertiary)
- Use appropriate sizes for context
- Ensure sufficient click target size (44x44px minimum)
- Clear, action-oriented labels

### Icon Slop
**Red Flags:**
- Generic line icons for everything
- Icons without labels in unclear contexts
- Decorative icons that add no meaning
- Inconsistent icon styles (mixing outlined and filled)
- Icons from different icon sets

**Better:**
- Use icons to clarify, not decorate
- Maintain consistent icon style
- Include text labels when meaning is unclear
- Source from single icon system

### Form Slop
**Generic Form Patterns:**
- Every input has an icon inside it
- Excessive placeholder text
- Floating labels that don't add value
- No clear error states
- Generic validation messages

**Better:**
- Clear labels outside inputs
- Helpful error messages
- Logical field grouping
- Progressive disclosure for complex forms

## UX Writing Slop

### Generic Microcopy
**Overused Phrases:**
- "Empower your business"
- "Take control of your future"
- "Join thousands of satisfied customers"
- "Transform your workflow"
- "Seamless experience"
- "Unlock your potential"

**Generic CTAs:**
- "Get Started"
- "Learn More"
- "Sign Up Now"
- "Try It Free"

**Better:**
- Be specific about the value proposition
- Use action-oriented, clear language
- Tell users exactly what happens when they click
- Match brand voice and tone

### Empty State Messages
**Generic Slop:**
- "No items found"
- "Nothing to see here"
- "Oops! Something went wrong"
- Unhelpful error messages

**Better:**
- Explain why the state is empty
- Provide next steps or actions
- Use appropriate tone (not overly casual for serious errors)
- Helpful recovery suggestions

## Animation and Interaction

### Animation Slop
**Overused Patterns:**
- Everything fades in on scroll
- Parallax effects on every element
- Excessive slide-in animations
- Bouncing elements
- Rotating 3D elements for no reason

**Better:**
- Use animation to direct attention
- Keep animations subtle and purposeful
- Respect prefers-reduced-motion
- Animation duration < 300ms for most interactions

### Interaction Slop
**Generic Patterns:**
- Hover effects on everything
- Cursor changes to pointer on non-clickable elements
- Confusing interactive vs non-interactive cues
- Inconsistent interaction patterns

**Better:**
- Clear interactive affordances
- Consistent interaction patterns
- Appropriate feedback for all interactions
- Consider touch and keyboard users

## Platform-Specific Slop

### Web Design
- Dashboard templates with generic metrics
- Unnecessary infinite scroll
- Pop-ups and modals for everything
- Cookie consent banners that hide content

### Mobile Design
- Bottom navigation with 5+ items
- Hamburger menus hiding important navigation
- Inconsistent gesture handling
- Ignoring platform conventions (iOS vs Android)

### Presentation Design
- Every slide with same template
- Bullet point overload
- Tiny unreadable text
- Generic stock photos as backgrounds
- Excessive transitions between slides

## Detection Signals

### High-Confidence Slop Indicators
1. Design looks exactly like other AI-generated designs
2. No clear visual hierarchy
3. Generic color palette (purple/pink/cyan)
4. Copy uses only buzzwords and generic CTAs
5. Layout follows template exactly without customization

### Medium-Confidence Indicators
1. Overuse of glassmorphism or neumorphism
2. All components have same visual weight
3. Excessive use of trendy design patterns
4. No clear information architecture
5. Design ignores actual content needs

## Cleanup Strategies

### Visual Audit
1. Remove decorative elements that don't serve purpose
2. Simplify color palette to 2-3 main colors + neutrals
3. Establish clear typographic hierarchy
4. Ensure sufficient contrast for accessibility
5. Remove excessive animations and effects

### Content-First Redesign
1. Start with actual content and user needs
2. Design information hierarchy based on importance
3. Choose visual style that matches content tone
4. Create layouts that serve content, not templates
5. Test with real content, not lorem ipsum

### Accessibility Pass
1. Check color contrast ratios (WCAG AA minimum)
2. Ensure interactive elements are keyboard accessible
3. Add proper ARIA labels where needed
4. Test with screen readers
5. Verify all text is legible at various sizes

## Context Matters

Some patterns are appropriate in context:

- **Gradient backgrounds:** Fine for marketing sites if on-brand
- **Cards:** Appropriate for displaying distinct, comparable items
- **Generic CTAs:** "Get Started" is fine if that's actually what happens
- **Animations:** Purposeful motion can enhance UX
- **Stock photos:** Sometimes you need generic imagery

The issue is **thoughtless application of patterns** without considering whether they serve the user's needs or your design goals.

## Red Flags Checklist

Your design might be slop if:
- [ ] Could be for any product/company
- [ ] Looks like Figma community templates
- [ ] All visuals are decorative, none informative  
- [ ] Copy is entirely buzzwords
- [ ] Design decisions can't be justified
- [ ] Layout doesn't adapt to actual content
- [ ] No clear visual hierarchy
- [ ] Looks trendy but serves no purpose
- [ ] Every element uses the same design treatment
- [ ] Design ignores brand and user context
