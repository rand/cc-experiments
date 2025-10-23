# Design Systems Reference

## shadcn/ui (PRIMARY CHOICE)

**When to use:** Most projects, especially with Tailwind CSS

**URL:** https://ui.shadcn.com

**Characteristics:**
- Excellent accessibility defaults (built on Radix UI)
- Copy-paste into your project (not npm package)
- Tailwind CSS based
- Fully customizable source code
- TypeScript support

**Installation:**
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
```

**Pros:**
- Own the code (no external dependencies)
- Accessible by default
- Great TypeScript support
- Extensive component library
- Active development

**Cons:**
- Requires Tailwind CSS
- Need to copy each component
- Updates require manual copying

## daisyUI

**When to use:** Rapid prototyping, semantic HTML preference

**URL:** https://daisyui.com

**Characteristics:**
- Tailwind CSS plugin
- Semantic component names
- Theme system built-in
- Works with pure HTML or frameworks

**Installation:**
```bash
npm install -D daisyui
```

**Pros:**
- Fast to prototype
- Multiple themes out of the box
- Works with plain HTML
- Small footprint

**Cons:**
- Less customizable than shadcn
- Fewer components
- Some accessibility gaps

## HeroUI

**When to use:** Product interfaces, modern design needs

**URL:** https://heroui.com

**Characteristics:**
- Modern, polished design
- Strong design language
- Good for product UIs
- React-based

**Installation:**
```bash
npm install @heroui/react
```

**Pros:**
- Beautiful out of the box
- Consistent design system
- Good documentation

**Cons:**
- More opinionated
- Harder to customize deeply
- Smaller community than shadcn

## Comparison Table

| Feature | shadcn/ui | daisyUI | HeroUI |
|---------|-----------|---------|--------|
| Accessibility | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Customization | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Components | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Setup Speed | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| TypeScript | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Documentation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## Recommendation Flow

```
Need accessibility? → shadcn/ui
Need speed? → daisyUI  
Need polish? → HeroUI
Need customization? → shadcn/ui
Using Tailwind? → shadcn/ui or daisyUI
Not using Tailwind? → HeroUI
```
