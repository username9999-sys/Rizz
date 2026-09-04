# Accessibility (WCAG 2.1 AA)

This document is the accessibility checklist for the Rizz platform's
user-facing components (`web-app/`, `portfolio/`). The API itself
has no user interface, but its responses must include accessibility
metadata (e.g. CSRF tokens, session cookies) that work with screen
readers.

Goal: **WCAG 2.1 Level AA** conformance.

> **Note**: This is a checklist, not a manual audit. To claim
> conformance, run the page through axe-core, WAVE, or Lighthouse
> and a screen reader test (NVDA / VoiceOver / JAWS).

## Quick check (run before every release)

  - [ ] Keyboard-only navigation works for every flow
  - [ ] Tab order is logical (left-to-right, top-to-bottom)
  - [ ] Focus indicator is visible on every focusable element
  - [ ] Color contrast meets 4.5:1 for text, 3:1 for UI components
  - [ ] No information conveyed by color alone
  - [ ] All form fields have associated `<label>` or `aria-label`
  - [ ] All images have `alt` text (or `alt=""` if decorative)
  - [ ] All interactive elements have accessible names
  - [ ] No keyboard traps
  - [ ] No timeouts < 20 seconds (or warning + extension)
  - [ ] Page has `<title>` that describes the page
  - [ ] Page has exactly one `<h1>`
  - [ ] Language attribute set: `<html lang="en">`
  - [ ] Focus is moved to dynamic content updates (or `aria-live` set)
  - [ ] Error messages are programmatically associated with fields

## Per-component checklist

### Navigation / header

  - [ ] `<header>` element wraps site header
  - [ ] `<nav>` element wraps navigation
  - [ ] Skip link: `<a href="#main-content" class="skip-link">Skip to main content</a>`
  - [ ] Skip link is the first focusable element
  - [ ] Skip link becomes visible on focus
  - [ ] All nav items are `<a>` or `<button>` (never `<div onclick>`)
  - [ ] Current page is marked `aria-current="page"`

### Forms

  - [ ] Every `<input>` has a `<label>` with matching `for` attribute
  - [ ] Or: `aria-label` / `aria-labelledby` references a visible label
  - [ ] Required fields: `aria-required="true"` + visual indicator
  - [ ] Error messages: `aria-describedby` linking to message element
  - [ ] `aria-invalid="true"` on fields with errors
  - [ ] Submit button has descriptive text (not just "Click here")
  - [ ] Fieldset/legend for grouped inputs (radio, checkbox groups)

### Images

  - [ ] Informative images: `alt` describes the content
  - [ ] Decorative images: `alt=""` (empty) + `role="presentation"`
  - [ ] Complex images (charts, graphs): have long description
  - [ ] Icons: `<button>` or `<a>` with `aria-label` if no visible text
  - [ ] Logo: `alt` includes the company name

### Buttons & links

  - [ ] Text describes the destination (no "click here")
  - [ ] External links: indicate they open in a new tab
  - [ ] Icon-only buttons: `aria-label`
  - [ ] Disabled buttons: `aria-disabled="true"` + explanation
  - [ ] Loading buttons: `aria-busy="true"` while loading

### Tables

  - [ ] `<th scope="col">` and `<th scope="row">` where applicable
  - [ ] `<caption>` for table description (when not redundant)
  - [ ] No tables for layout (use CSS grid/flexbox)

### Dynamic content

  - [ ] Single-page app: route changes announced via `aria-live="polite"`
  - [ ] Modals: focus trap inside modal, Escape closes, focus returns
  - [ ] Toasts: `role="status"` or `aria-live="polite"`
  - [ ] Carousels: pause on hover + keyboard arrows + no auto-rotation
        unless user opts in

### Color & contrast

  - [ ] All text: 4.5:1 contrast minimum (3:1 for large text 18pt+)
  - [ ] UI components & graphics: 3:1 contrast
  - [ ] Don't rely on color alone (use icons or text too)
  - [ ] Test with color-blindness simulator (e.g. Chrome DevTools)

### Forms (auth flow specifics)

  - [ ] Password field has `autocomplete="current-password"` or
        `autocomplete="new-password"`
  - [ ] Show/hide password toggle is keyboard accessible
  - [ ] CAPTCHA has an audio alternative
  - [ ] 2FA input has clear instructions and accessible error states
  - [ ] Session timeout warning is announced

### Mobile

  - [ ] Touch targets at least 44x44px
  - [ ] Pinch-to-zoom not disabled
  - [ ] Orientation not locked
  - [ ] Text scales with system font size (no fixed `font-size` in px)
  - [ ] Inputs don't trigger zoom on focus (iOS): font-size >= 16px

### Screen reader testing

Test with at least one of:
  - [ ] NVDA on Windows + Firefox
  - [ ] VoiceOver on macOS/iOS + Safari
  - [ ] TalkBack on Android + Chrome

Check:
  - [ ] All content is announced (no `aria-hidden="true"` on important
        content)
  - [ ] Form labels are read
  - [ ] Error messages are announced when triggered
  - [ ] Modal focus management works
  - [ ] Live regions announce updates

## Automated checks

### axe-core via Lighthouse CI

```bash
# In your CI:
npm install -g @lhci/cli
lhci autorun --collect.staticDistDir=web-app/dist
```

This fails the build if accessibility score < 95.

### Pa11y for ad-hoc checks

```bash
npm install -g pa11y
pa11y http://localhost:3000
```

### Manual `prefers-reduced-motion`

  - [ ] Animations honor `@media (prefers-reduced-motion: reduce)`
  - [ ] No essential information conveyed only by animation
  - [ ] Parallax / scroll-jacking disabled when reduce is set

## Known limitations

  - PDF export (if any) is not WCAG-compliant. Use a tagged PDF generator.
  - 3D content / canvas elements are out of scope. Provide a textual
    alternative.
  - Real-time collaboration features (cursors, presence) are decorative
    and marked `aria-hidden="true"`.

## Resources

  - [WCAG 2.1 spec](https://www.w3.org/TR/WCAG21/)
  - [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
  - [axe-core rules](https://github.com/dequelabs/axe-core/tree/develop/doc/rules)
  - [WebAIM contrast checker](https://webaim.org/resources/contrastchecker/)

## Reporting accessibility issues

If you find an accessibility problem, please file an issue with
`a11y` label, or email `a11y@rizz.dev` for private disclosure.
We aim to fix AA-level issues within 30 days.
