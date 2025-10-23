# Testing and Quality Assurance

## Visual Testing Checklist

- [ ] Mobile (320px, 375px, 414px widths)
- [ ] Tablet (768px, 1024px widths)
- [ ] Desktop (1280px, 1920px widths)
- [ ] Both light and dark modes
- [ ] Different font sizes (browser zoom 100%, 125%, 150%)
- [ ] Slow 3G network simulation

## Functional Testing

- [ ] All links work
- [ ] Forms validate correctly
- [ ] Error states display properly
- [ ] Loading states appear appropriately
- [ ] Empty states handled
- [ ] Navigation works on all devices

## Accessibility Testing

**Automated:**
- [ ] Run Lighthouse accessibility audit (score > 95)
- [ ] Run axe DevTools scan (0 violations)
- [ ] Check WAVE report

**Manual:**
- [ ] Test with keyboard only (no mouse)
- [ ] Test with screen reader (NVDA, VoiceOver)
- [ ] Verify color contrast (WebAIM)
- [ ] Ensure focus indicators are visible
- [ ] Test form error announcements
- [ ] Verify heading hierarchy

## Performance Testing

- [ ] Lighthouse performance score > 90
- [ ] Check bundle size (< 200KB initial)
- [ ] Measure load time on slow 3G
- [ ] Verify images are optimized
- [ ] Check for layout shift (CLS < 0.1)
- [ ] Test with throttled CPU

## Cross-browser Testing

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (macOS/iOS)

## Tools

**Accessibility:**
- Lighthouse (Chrome DevTools)
- axe DevTools extension
- WAVE browser extension
- NVDA screen reader (Windows)
- VoiceOver (macOS/iOS)

**Performance:**
- Lighthouse
- WebPageTest
- Chrome DevTools Performance panel

**Visual:**
- Responsively (responsive testing)
- BrowserStack (cross-browser)
