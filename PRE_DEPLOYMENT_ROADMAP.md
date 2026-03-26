# Veracity Business Suite: Pre-Deployment Production Readiness Roadmap

**Created:** 2026-03-26
**Status:** In Progress
**Total Effort:** 195-279 hours (2-3 months for single developer)

---

## Context

The Veracity Business Suite is a static HTML single-page application (989KB, 10,896 lines) with embedded React for GAAP research, ASU library, and business tools. Ready for deployment to Cloudflare Pages, but requires security hardening, architectural improvements, and production infrastructure.

**User Requirement:** Top-of-the-line security, architecture, and implementation - professional production-ready deployment.

---

## Quick Reference: Critical Issues Found

### Security Issues (17 total)
- **8 Critical:** Base64 passwords, SVG injection, Function() code execution, hardcoded credentials, no SRI hashes, localStorage auth, Chrome profile exposure, subprocess risks
- **4 High:** File upload validation, sensitive data in JSON
- **5 Medium:** Missing CSP, no CORS validation, no input sanitization, localStorage for auth, no rate limiting

### Architecture Issues
- Monolithic 10,896-line HTML file with 101 functions
- 56.8MB JSON loaded synchronously at startup
- 1,366 inline styles (no CSS extraction)
- No error boundaries, code splitting, or lazy loading
- Limited accessibility (no ARIA, semantic HTML gaps)

### Deployment Gaps
- Missing: robots.txt, sitemap.xml, _headers, _redirects, 404.html, favicons
- No security headers (CSP, X-Frame-Options, HSTS)
- No legal documents (privacy policy, terms of service)
- No monitoring (Sentry, analytics, uptime)
- No testing infrastructure

---

## Phase 0: Pre-Deployment Blockers (CRITICAL)

**Timeline:** 3-5 days | **Effort:** 24-38 hours | **Status:** Not Started

### 0.1 Critical Security Fixes

- [ ] **0.1.1 Remove Authentication System** (2-3h)
  - Delete `AuthModal` component (lines 3193-3210, 3258-3497)
  - Remove localStorage `veracity-users` references
  - Replace with "Contact for Access" button
  - **Why:** Base64 encoding is reversible; static sites cannot securely authenticate

- [ ] **0.1.2 Sanitize SVG Injection** (3-4h)
  - Fix `dangerouslySetInnerHTML` at line 10226
  - Parse SVG with DOMParser, whitelist safe elements
  - Strip script tags and event handlers
  - Alternative: Use `<img src="data:image/svg+xml,{encoded}">`

- [ ] **0.1.3 Replace Function() Constructor** (1-2h)
  - Replace calculator `Function()` call at line 4556
  - Add math.js library with SRI hash
  - Use `math.evaluate()` instead
  - Test with injection attempts

- [ ] **0.1.4 Secure File Upload Validation** (2-3h)
  - Add file type and size validation (lines 2490, 3748, 4995, 5630)
  - Implement CSV formula sanitization (Excel DDE injection prevention)
  - Add 5MB file size limit

- [ ] **0.1.5 Remove Hardcoded Credentials** (1h)
  - Fix sync_viam_data.py (lines 7, 32: connor@sperocfo.com, ConnorFinuf)
  - Move to environment variables with `os.getenv()`
  - Create `.env.example` file
  - Update `.gitignore` to exclude `.env`

### 0.2 CDN Security & Integrity

- [ ] **0.2.1 Add SRI Hashes** (1h)
  - Generate hashes for React, Babel, SheetJS CDN resources (lines 12-15)
  - Command: `curl -s [URL] | openssl dgst -sha384 -binary | openssl base64 -A`
  - Add `integrity="sha384-[HASH]" crossorigin="anonymous"` attributes

- [ ] **0.2.2 Create Security Headers** (1h)
  - Create `_headers` file for Cloudflare Pages
  - Add CSP, X-Frame-Options, HSTS, X-Content-Type-Options
  - Verify at https://securityheaders.com/ after deployment

### 0.3 Legal & Compliance

- [ ] **0.3.1 Create Legal Documents** (4-6h)
  - Create `legal/privacy-policy.html` (GDPR/CCPA compliant)
  - Create `legal/terms-of-service.html` (liability disclaimers)
  - Create `legal/cookie-policy.html`
  - Use templates: TermsFeed.com, Termly.io

- [ ] **0.3.2 Add Cookie Consent Banner** (2-3h)
  - Integrate vanilla-cookieconsent library
  - Configure for localStorage (essential cookies only)
  - Link to privacy/cookie policies

### 0.4 Critical Deployment Files

- [ ] **Create Missing Files** (2-3h total)
  - `robots.txt` - SEO crawler directives
  - `sitemap.xml` - Search engine indexing
  - `404.html` - Custom error page
  - `_redirects` - Cloudflare Pages routing
  - Favicon suite: .ico, 16x16, 32x32, apple-touch-icon, android-chrome (192x192, 512x512)
  - `site.webmanifest` - PWA metadata

### 0.5 Basic Monitoring

- [ ] **0.5.1 Add Error Tracking** (2h)
  - Set up Sentry account
  - Integrate Sentry SDK in index.html
  - Test error capturing

- [ ] **0.5.2 Add Analytics** (30min)
  - Enable Cloudflare Web Analytics (privacy-focused)

- [ ] **0.5.3 Add Uptime Monitoring** (30min)
  - Configure UptimeRobot or Better Uptime
  - Set alert to connor@sperocfo.com

### 0.6 Performance Quick Wins

- [ ] **0.6.1 Defer Large JSON Loading** (3-4h)
  - Lazy load 56.8MB JSON data (51MB asu-index.json, 5.4MB asu-knowledge.json)
  - Use async fetch with loading states
  - **Impact:** Initial load 989KB → ~200KB, FCP improves 2-3s

---

## Phase 1: Essential Post-Launch Improvements

**Timeline:** 2 weeks | **Effort:** 40-59 hours | **Status:** Not Started

### 1.1 Error Boundaries & Resilience (8-12h)

- [ ] Add React Error Boundaries wrapping major sections
- [ ] Implement safe localStorage wrappers (handle quota exceeded errors)
- [ ] Add network retry logic with exponential backoff

### 1.2 Accessibility Improvements (12-16h)

- [ ] Add ARIA attributes (labels, roles, live regions, describedby)
- [ ] Ensure full keyboard navigation (Tab, Escape, Enter)
- [ ] Add visible focus indicators
- [ ] Run color contrast audit (WCAG AA: 4.5:1 normal text, 3:1 large text)
- [ ] Test with screen readers (NVDA, JAWS)
- [ ] Target: Lighthouse Accessibility score >90

### 1.3 Mobile Optimization (6-10h)

- [ ] Increase touch target sizes to 44x44px minimum
- [ ] Optimize form inputs (type="email", type="tel", inputmode="numeric")
- [ ] Add autocomplete attributes
- [ ] Test on real devices (iOS Safari, Android Chrome)

### 1.4 Testing Infrastructure (8-12h)

- [ ] Set up Playwright for E2E tests
- [ ] Write tests for critical flows:
  - Homepage load without errors
  - Navigate to ASC topics
  - Create/delete project
  - Export project data
- [ ] Add smoke tests for deployment verification
- [ ] Target: 70% test coverage for user flows

### 1.5 Documentation (10-14h)

- [ ] Create `docs/user-guide.md` (Getting started, features, troubleshooting, FAQ)
- [ ] Create `docs/developer.md` (Architecture, state management, deployment, testing)

---

## Phase 2: Architecture Refactoring (HIGH RISK)

**Timeline:** 3-6 weeks | **Effort:** 86-121 hours | **Status:** Not Started

### 2.1 Build System Setup (16-24h)

- [ ] Install Vite: `npm init vite@latest`
- [ ] Extract React components from index.html to separate files
- [ ] Extract CSS to external stylesheets
- [ ] Move JSON data to `/public/data/`
- [ ] Remove runtime Babel (use esbuild)
- [ ] **Benefits:** 60-70% bundle reduction, eliminate `unsafe-eval` from CSP

### 2.2 Component Refactoring (30-40h)

- [ ] Break 10,896-line HTML into modular structure:
  ```
  /src/
    /components/
      /layout/ (NavRail, NavSidebar, TopNavbar, MobileNavPanel)
      /asc/ (ASCTopicGrid, ASCTopicCard, ASCDetailView)
      /modules/ (ModulesView, ModuleCard, ModuleDetailView)
      /projects/ (Dashboard, ProjectCard, ProjectDetail, tabs)
      /calculators/ (FinancialCalculator, TimeValueMoney, etc.)
      /shared/ (Button, Card, Modal, BufferedInput, ErrorBoundary)
    /hooks/ (useLocalStorage, useProjects, useKnowledgeBase)
    /utils/ (formatters, validators, exporters, localStorage)
    /styles/ (base, components, layout, utilities)
  ```

### 2.3 CSS Architecture (12-16h)

- [ ] Extract 1,366 inline styles to external CSS
- [ ] Organize with BEM methodology
- [ ] Create base, components, layout, utilities stylesheets
- [ ] Consider CSS Modules for scoped styles

### 2.4 Data Optimization (16-24h)

- [ ] Implement virtual scrolling (react-window) for large lists
- [ ] Paginate ASU data by year (split 51MB file into yearly chunks)
- [ ] Add client-side search indexing (Fuse.js)
- [ ] Move large data to IndexedDB (more reliable than localStorage)

### 2.5 Progressive Web App (8-11h)

- [ ] Add service worker with Workbox
- [ ] Implement offline support and caching
- [ ] Add update notifications
- [ ] Target: Lighthouse PWA score >90

---

## Phase 3: Long-Term Optimization (Ongoing)

**Timeline:** Ongoing | **Effort:** 45-61 hours | **Status:** Not Started

### 3.1 Advanced Features (36-48h)

- [ ] Dark mode implementation (8-12h)
- [ ] Advanced search with filters (12-16h)
- [ ] Data visualization with Chart.js (16-20h)

### 3.2 Automation & CI/CD (9-13h)

- [ ] GitHub Actions workflow for automated testing/deployment (4-6h)
- [ ] Automated security scanning (Snyk, Dependabot) (3-4h)
- [ ] Lighthouse CI for performance tracking (2-3h)

### 3.3 Content Management

- [ ] Automate ASU updates (scheduled GitHub Actions workflow)
- [ ] Consider Decap CMS for non-technical content editing

---

## Testing Strategy

### Phase 0 Testing Checklist
- [ ] Security audit with OWASP ZAP
- [ ] Manual penetration testing
- [ ] Browser compatibility (Chrome, Firefox, Safari, Edge - latest 2 versions)
- [ ] Mobile devices (iOS Safari, Android Chrome - real devices)
- [ ] Deployment verification (headers, redirects, 404 pages, favicons)

### Phase 1 Testing Checklist
- [ ] Accessibility audit (NVDA/JAWS screen readers, axe DevTools, Lighthouse)
- [ ] Performance testing (Lighthouse, WebPageTest, network throttling)
- [ ] Error scenarios (localStorage quota, network failures, corrupted data)
- [ ] Usability testing with 5-10 real users

### Phase 2 Testing Checklist
- [ ] Bundle analysis (verify code splitting, tree shaking, minification)
- [ ] Performance benchmarks (compare before/after LCP, TTI, bundle size)
- [ ] Full regression testing (E2E suite)
- [ ] PWA audit (Lighthouse PWA score, offline functionality)

---

## Success Metrics

### Phase 0 Goals (Pre-Launch)
- [ ] Zero critical vulnerabilities (OWASP ZAP scan)
- [ ] A+ rating on securityheaders.com
- [ ] All legal documents reviewed and published
- [ ] Lighthouse scores: Performance >50, Accessibility >70, Best Practices >80, SEO >90

### Phase 1 Goals (Post-Launch)
- [ ] Zero production errors in Sentry for 7 consecutive days
- [ ] Lighthouse Accessibility score >90
- [ ] <1% bounce rate on critical pages
- [ ] E2E test coverage >70% of user flows

### Phase 2 Goals (Refactored)
- [ ] Initial bundle size <50KB (gzipped)
- [ ] Core Web Vitals: LCP <2.5s, FID <100ms, CLS <0.1
- [ ] Lighthouse Performance score >90
- [ ] Zero `unsafe-eval` in CSP

### Phase 3 Goals (Optimized)
- [ ] PWA installable, Lighthouse PWA score >90
- [ ] Offline functionality working
- [ ] Dark mode implemented
- [ ] 95th percentile page load <3s (Real User Monitoring)

---

## Deployment Checklist

### Pre-Deployment (Before Going Live)
- [ ] All Phase 0 tasks completed
- [ ] Security audit passed (OWASP ZAP, manual testing)
- [ ] Legal documents reviewed by lawyer (or validated templates used)
- [ ] Sentry configured and tested
- [ ] Analytics configured
- [ ] Uptime monitoring configured
- [ ] Domain/SSL configured in Cloudflare
- [ ] DNS records propagated
- [ ] `_headers` file deployed and verified
- [ ] `robots.txt` and `sitemap.xml` deployed
- [ ] 404 page tested
- [ ] Favicon set verified on all devices (Chrome, Safari, mobile)

### Post-Deployment (First 24 Hours)
- [ ] Smoke tests passed
- [ ] Security headers verified at securityheaders.com
- [ ] Lighthouse audit run on production URL
- [ ] Test from 3+ geographic locations
- [ ] Test on 5+ device/browser combinations
- [ ] Monitor Sentry for errors
- [ ] Check Cloudflare Analytics for traffic patterns
- [ ] Verify uptime monitoring alerts working

### Week 1 Post-Launch
- [ ] Review Sentry errors, prioritize fixes
- [ ] Analyze Cloudflare Analytics (top pages, referrers, devices)
- [ ] Collect user feedback (survey, support tickets)
- [ ] Update documentation based on user questions
- [ ] Plan Phase 1 work based on usage data and feedback

---

## Risk Mitigation

### High-Risk Items
1. **Phase 2 refactoring** - Massive code changes could introduce bugs
   - **Mitigation:** Incremental migration, feature flags, comprehensive E2E tests

2. **CSP with unsafe-eval** - Required for runtime Babel
   - **Mitigation:** Phase 2 build system removes this requirement

3. **localStorage limitations** - Safari Private Mode, quota issues
   - **Mitigation:** Error handling, export reminders, IndexedDB migration (Phase 2)

4. **Large data files** - 56.8MB could cause memory issues on low-end devices
   - **Mitigation:** Phase 0 lazy loading, Phase 2 pagination and compression

---

## Estimated Effort Summary

| Phase | Duration | Developer Hours | Risk Level | Status |
|-------|----------|----------------|------------|--------|
| **Phase 0** (Pre-launch blockers) | 3-5 days | 24-38 hours | CRITICAL | Not Started |
| **Phase 1** (Essential improvements) | 2 weeks | 40-59 hours | MEDIUM | Not Started |
| **Phase 2** (Architecture refactoring) | 3-6 weeks | 86-121 hours | HIGH | Not Started |
| **Phase 3** (Long-term optimization) | Ongoing | 45-61 hours | LOW | Not Started |
| **TOTAL** | 2-3 months | **195-279 hours** | - | - |

**Single developer estimate:** 2-3 months full-time
**Small team (2-3 devs) estimate:** 1-1.5 months

---

## Critical File Paths Reference

**Phase 0 Files:**
- `index.html` - Security fixes, lazy loading
- `_headers` - NEW (security headers)
- `legal/privacy-policy.html` - NEW
- `legal/terms-of-service.html` - NEW
- `legal/cookie-policy.html` - NEW
- `scripts/sync_viam_data.py` - Remove credentials
- `scripts/fasb_asu_downloader.py` - Remove credentials
- `robots.txt` - NEW
- `sitemap.xml` - NEW
- `404.html` - NEW
- `_redirects` - NEW
- Multiple favicon files - NEW

**Phase 1 Files:**
- `index.html` - Error boundaries, localStorage handling
- `tests/critical-flows.spec.js` - NEW
- `docs/user-guide.md` - NEW
- `docs/developer.md` - NEW

**Phase 2 Files:**
- `vite.config.js` - NEW
- `src/` directory - NEW (entire component restructure)
- `src/components/`, `src/hooks/`, `src/utils/`, `src/styles/` - NEW

---

## Quick Wins (High Impact, Low Effort)

If time-constrained, prioritize these first:

1. **Enable gzip on Cloudflare** (5 min) → 60-75% compression
2. **Remove dev artifacts** (5 min) → 2.8MB saved
3. **Add meta/OG tags for SEO** (15 min) → Better social sharing
4. **Generate and add SRI hashes** (30 min) → Major security improvement
5. **Create _headers file** (30 min) → Security headers
6. **Lazy load JSON data** (3-4h) → 2-3s faster initial load

---

## Notes & Learnings

**2026-03-26:** Initial security, architecture, and deployment audits completed. Comprehensive roadmap created. 17 security issues identified (8 critical). Plan approved for phased implementation over 2-3 months.

---

**Last Updated:** 2026-03-26
**Next Review:** After Phase 0 completion
