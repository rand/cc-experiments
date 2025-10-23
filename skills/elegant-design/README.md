# Elegant Design Skill for Claude Code

A comprehensive, modular skill system for creating world-class, accessible, responsive interfaces with sophisticated interactive elements.

## Structure

This skill follows Anthropic's best practices with progressive disclosure:

```
elegant-design/
├── SKILL.md (302 lines - main entry point)
├── foundation/ (design system basics)
│   ├── typography.md (Geist, JetBrains Mono, scales)
│   ├── colors-and-spacing.md (palettes, tokens, dark mode)
│   └── layout-patterns.md (grids, responsive, containers)
├── interactive/ (sophisticated UI elements)
│   ├── chat-and-messaging.md (chat UIs, streaming)
│   ├── terminals-and-code.md (terminals, syntax highlighting)
│   ├── streaming-and-loading.md (progressive loading, skeletons)
│   └── diffs-and-logs.md (version control UI, log viewers)
├── implementation/ (building & optimizing)
│   ├── components-and-accessibility.md (WCAG AA compliance)
│   ├── performance.md (Core Web Vitals, optimization)
│   └── testing-and-qa.md (comprehensive testing)
└── reference/ (tools & resources)
    ├── design-systems.md (shadcn, daisyUI, HeroUI)
    ├── tools-and-libraries.md (complete toolkit)
    └── anti-patterns.md (what not to do)
```

## Usage with Claude Code

### Quick Start

1. Read `SKILL.md` first - it's the orchestrator (under 500 lines)
2. Follow the workflow for your project type
3. Reference specific guides as needed

### Decision Tree

**Need basics?** → Read foundation/ files
**Building chat?** → Read interactive/chat-and-messaging.md
**Building terminal/code editor?** → Read interactive/terminals-and-code.md
**Need loading states?** → Read interactive/streaming-and-loading.md
**Building diffs/logs?** → Read interactive/diffs-and-logs.md
**Ready to implement?** → Read implementation/ files
**Need tools or anti-patterns?** → Read reference/ files

### Key Features

- **Typography**: Geist for UI, JetBrains Mono for code
- **Chat interfaces**: Streaming, auto-scroll, markdown rendering
- **Terminals**: ANSI colors, command history, beautiful aesthetics
- **Code display**: Shiki syntax highlighting, copy buttons, line numbers
- **Streaming**: Progressive loading, skeleton screens, optimistic updates
- **Diffs & logs**: Split/unified views, virtual scrolling, filtering
- **Accessibility**: WCAG 2.1 AA compliant from the start
- **Performance**: Core Web Vitals optimization

## Design Process

1. **Discovery** (15-30 min): Map flows, OODA loops, identify affordances
2. **Foundation** (20-40 min): Typography, colors, spacing, layout
3. **Interactive** (30-60 min): Build sophisticated elements
4. **Implementation** (1-3 hours): Components, accessibility, performance
5. **Validation**: Test, refine, optimize

## Best Practices Compliance

This skill follows all Anthropic best practices:
- ✅ Main SKILL.md under 500 lines (302 lines)
- ✅ Progressive disclosure (13 referenced files)
- ✅ One level deep references (no nested refs)
- ✅ Descriptive file names
- ✅ Consistent terminology
- ✅ Forward slashes in paths
- ✅ No time-sensitive information
- ✅ Gerund form name ("Designing Elegant Interfaces")
- ✅ Clear description with what+when

## For Developers

**Simple projects**: Read SKILL.md + foundation files
**Complex projects**: Read SKILL.md + all interactive files
**Developer tools**: Read ALL interactive files + performance

## Typography Standards

- **Geist** (https://vercel.com/font) - ALL UI text
- **JetBrains Mono** (https://jetbrains.com/mono) - ALL code (14px min)

Never mix multiple sans-serif or monospace fonts.

## Design Systems Priority

1. shadcn/ui (https://ui.shadcn.com) - PRIMARY
2. daisyUI (https://daisyui.com) - Alternative
3. HeroUI (https://heroui.com) - Alternative

## License

MIT
