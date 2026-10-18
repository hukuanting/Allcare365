# AllCare365 frontend design iteration

Status: Complete for the local frontend design and acceptance scope. Evidence and limits are recorded below; historical iterations retain their original status.
Updated: 2026-10-17 (Asia/Taipei). Historical iterations retain their original evidence and limitations.

## Current checkpoint — 2026-10-17

- Real Chrome inspection now covers the desktop dashboard, synthetic patient search/chart, intake identity and BMI, FHIR JSON/XML multi-file preview, risk results and paired disease network, research cohorts/reports, continuous signals, public home and account forms. Saved screenshots and scoped results are in `artifacts/frontend_design/*20261017*`. See `browser-acceptance-20261017.json`, `research-browser-20261017.json` and `clinical-home-browser-20261017.json` for exact coverage. The earlier successful browser JSON import remains documented in `browser_acceptance_20261010.md`; it is not a fresh mixed-file confirmation test.
- Browser findings produced concrete fixes: metabolic-syndrome result localization, cohort numeric labels/range alignment, modified-key handling in home tabs, and public touch targets. Lighthouse additionally identified four diagram caption contrast failures; the scoped color correction passed re-audit. Registration now explains the verified password requirements before submission.
- Production homepage Lighthouse 13.5.0 results: mobile performance 98/accessibility 100 after contrast repair; desktop 100/100. These are separate local lab runs, not field performance or whole-system accessibility certification. HTML/JSON reports, tool/settings metadata and screenshots are linked from `lighthouse-verification-20261017.json` and `desktop-register-verification-20261017.json`. Public registration accessibility also scored 100; its full-page screenshot was inspected after the password hint change.
- Final frontend regression passed 201 tests in 28 files against the latest source (`node node_modules/vitest/vitest.mjs run --maxWorkers=1`, 70.41 seconds, exit 0); production build passed after the final focus correction. Earlier parallel runs exposed an intermittent import focus failure and separate MFA/timing failures. Import focus restoration now runs after the file-list commit; existing regression coverage and actual Chrome removal checks passed. The auth suite separately passed all 10 tests without changing authentication behavior. The final single-worker suite passed without increasing assertion or test timeouts. FHIR re-import counter repair previously passed 24 isolated backend tests, including JSON/XML repeat import and full golden-patient model execution.

Final interactive acceptance used Playwright Core 1.64.1 installed outside the project, an independent installed Chrome profile, and the user's authorized local development account. Browser automation did not modify project dependencies, disable Chromium sandboxing, reuse the user's profile, or persist credentials. The earlier interpretation that a further permission loop was required was corrected under the existing authorization for autonomous local browser acceptance.

- Mixed identity JSON and clinical XML: actual chooser accepted both files; preview showed 44 resources and focused its heading. Confirmation returned HTTP 201, 44 successful resources and zero errors. Re-import created zero observations and zero questionnaire responses. The result link selected the same synthetic patient for actual risk execution: 82 resolved models, 77 scored, 5 not applicable, zero missing inputs. Keyboard selection and 390px network reflow passed. Evidence: `artifacts/frontend_design/browser-workflow-20261017.json`; screenshots `fhir-preview-playwright-20261017.png`, `fhir-result-playwright-20261017.png`, `network-mobile-playwright-20261017.png`.
- Report lifecycle: submitted an explicitly empty aggregate cohort (SBP minimum 999), verified the artifact remained locked before approval, approved it, and opened a completed FHIR MeasureReport with population zero. Desktop/mobile preview inspected; no individual clinical records were changed. Evidence: `report-workflow-20261017.json`, `report-artifact-playwright-20261017.png`, `report-artifact-mobile-20261017.png`.
- Actual browser zoom: fresh temporary Chrome profiles used Chrome's own default page-zoom preference. At the same outer width 1440, inner width changed from 1418 to 709 and devicePixelRatio from 1 to 2; visual viewport scale remained 1. Homepage and registration had no page overflow; registration fields, hint and submit button were inspected at 200%. Native CDP viewport captures avoid Playwright full-page screenshot cropping at browser zoom. Evidence: `browser-zoom200-20261017.json`, `home-browser-zoom200-20261017.png`, `register-browser-zoom200-fields-20261017.png`. Preference interpretation follows Chromium's `chrome/browser/ui/zoom/chrome_zoom_level_prefs.cc` and `third_party/blink/common/page/page_zoom.cc`.
- File removal: actual Chrome confirmed both removals returned focus to the picker, invalidated preview and disabled confirmation; removing all files disabled preview. Evidence: `file-removal-browser-20261017.json` and reproducible environment-credential-only QA scripts `verify_browser_workflow.mjs`, `verify_reports_zoom.mjs`, `verify_file_removal.mjs`.

Local service correction: overlapping Vite processes shared an optimizer cache and caused observed `504 Outdated Optimize Dep` failures. The old duplicate was stopped and a single port-3000 Vite service rebuilt dependencies. The earlier duplicate no-reload Django instance was also removed, retaining the user's auto-reloading port-8000 service. Subsequent browser acceptance completed successfully.

Limits: these are local Chrome/lab checks, not cross-browser certification, production deployment, field performance, or clinical validation of predictive accuracy. The exact 15-minute idle boundary was not timed uninterrupted; earlier actual idle expiry and fresh logins were observed. Real research participants and external FHIR servers were not used in this final synthetic workflow.

Development entry remains `http://localhost:3000/` with backend on port 8000. Port 3001 is the anonymous production-build preview used for approved Lighthouse audits; it is not the authenticated workspace entry.

## Product and direction

Existing product: React/Vite clinical data workspace with patient charts, health screening intake, risk analysis, research cohorts and governed reports. Existing authenticated routes and role policy remain authoritative.

Clinical Atlas direction: warm paper, ink green, compact clinical typography, fine rules, editorial space on the public page and higher density within the workspace. A cross with a square centre is the brand mark. The circular home illustration explains the connection between records, health insights and research; it contains no fabricated patient data or metrics.

## Research sources inspected

- https://linear.app — current public product illustration: persistent navigation, working object and contextual properties.
- https://docs.stripe.com/dashboard/basics — official resource-oriented Dashboard navigation and local section index; no signed-in Stripe account workflow inspected.
- https://developer.apple.com/design/human-interface-guidelines/typography — current rendered guidance/examples for legibility, hierarchy and testing in context; native point sizes are not web requirements.
- https://www.raycast.com — current public page: clear primary action and distinct product identity; its artwork/palette are not copied.
- https://mobbin.com/explore/screens/04517e3b-abac-4250-8af0-433d2c26d7de — public KakaoBank Account Overview screenshot: object identity, summary and contextual actions. No authenticated library access claimed.
- https://www.awwwards.com/sites/function-health and its published Tracked Overtime component — measurement, unit and date context; medical thresholds and promotional claims were not adopted.

The public-source visual comparison was completed on 2026-10-17 and recorded in `artifacts/frontend_design/reference-touch-review-20261017.json`. These are scoped design interpretations of inspected pages and published examples, not exhaustive product or authenticated-library studies.

## Implemented

- Replaced engineering-focused public copy with care, intake and research workflows.
- Added an original shared brand component and purposeful data continuum illustration.
- Implemented actual account and workspace links, accessible keyboard-operated workflow tabs.
- Replaced crowded desktop top navigation with grouped, role-aware sidebar and mobile drawer.
- Nested patient chart routes preserve the patient navigation selection.
- Updated common theme, panels, auth forms and responsive spacing.
- Removed the legacy global stylesheet import that applied broad label/input overrides and gradients.
- Added skip navigation, visible focus treatment and reduced-motion support.
- Dashboard wording now describes the user's work; research shortcuts follow the existing role policy.

## Initial verification evidence (historical)

Commands executed from frontend using Node directly (shell helper failed to initialise):

- node node_modules/vite/bin/vite.js build — success.
- node node_modules/vitest/vitest.mjs run — 10 files, 30 tests passed.
- DesignNavigation.test.jsx checks keyboard focus/content switching, account destinations, role visibility and nested-chart current state.

Local Vite launched on 127.0.0.1:3000. Browser surface inventory was empty; both iab and chrome creation reported Browser is not available. No screenshots, viewport measurements, live authenticated backend walkthrough or browser accessibility audit have been obtained. Passing jsdom tests and compilation do not prove visual quality.

## Initial acceptance plan (historical; completed evidence is in the current checkpoint)

1. Inspect named design references visually, including relevant Awwwards/Mobbin cases where access permits.
2. Capture desktop and mobile home, login and workspace screenshots; review typography, spacing, overflow, contrast and target sizes.
3. Refine patient registry/chart, intake, risk and all research views to the shared direction; check existing route-specific CSS.
4. Exercise actual search, chart navigation, validation, upload, errors, empty states, report workflow and session behaviour in a connected development environment.
5. Verify responsive and keyboard behaviour in a real browser; assess performance and accessibility with tools covering the real rendered pages.
6. Repeat the final build/tests and requirement-by-requirement audit before marking the goal complete.

## Iteration 2 — Patient registry

Previous turn classification: progress (source changes and verified build/test evidence).

Current-state checks reconfirmed the worktree and source contracts. Backend uses PageNumberPagination with 25 records per page, and supports name/MRN search. The API client accepts AbortSignal.

Implemented:
- Page navigation and backend total count, replacing current-page-only count.
- One debounced initial/search request; cancellation and request sequence checks prevent stale responses, including during debounce and unmount.
- Prior records are cleared while loading or after failure to avoid presenting results for the wrong query.
- Purposeful table spacing, monospaced MRNs and keyboard-accessible named chart links.
- Static skeleton rows with labelled progress and busy state.
- Separate no-results and empty-registry copy, clear-search and error retry actions.
- Status labels no longer colour every patient as active.
- New-patient form uses submit semantics, native input validation, a named dialog, in-dialog errors and disabled dismissal during save.

Verification: production build passed; complete frontend suite passed (11 files / 34 tests). The targeted registry suite was rerun after strengthening the stale-response assertion to flush its asynchronous resolution. These tests mock the API and do not prove live backend operation or visual quality.

Browser revalidation: cua inventory still returned apps: [], browsers: []. Real screenshots remain unavailable. Goal remains active; patient chart, intake, risk, research views and full visual/runtime acceptance are outstanding.

## Iteration 3 — Patient chart

Previous turn classification: progress. Current chart and serializer/model contracts were inspected before editing.

Implemented:
- Identity-first chart header, compact identifiers and neutral treatment for inactive/unknown status.
- Linked accessible tab/panel structure and actionable record index.
- Allergy summary and full allergy details sourced from substance/reaction/severity. Missing allergy records explicitly do not imply absence of allergies.
- Medication instructions, route, dates and source status; order details and dates; care team contacts.
- Clinical note content is now readable as plain text preserving line breaks, rather than only showing its type/date.
- Named loading status, error/back/retry paths, request abort and route-bound results.
- A response with the wrong patient ID is rejected before records are displayed.
- Patient-specific risk-analysis link uses the existing patient_id query contract.
- Synthetic demo patient label is preserved when provided by the API.

Evidence: final production build passed. Complete frontend suite: 12 files / 39 tests passed. Five chart tests cover source details and panel linkage, empty allergy semantics, retry, cancelled late responses and wrong-patient response rejection. The initial new test file had a multiline string parsing error; it was corrected and the complete suite rerun successfully.

Browser revalidation: inventory remains apps: [], browsers: []. No chart screenshot or live authenticated walkthrough was obtained. Tests use synthetic mocked records, not actual clinical data.

Next: patient context in health-data entry (its chart action currently opens the general entry form), intake/validation UI, risk/research route-specific visual consistency, complete reference research and real desktop/mobile visual/accessibility/runtime verification. The full goal remains active.

## Iteration 4 — Health intake

Previous turn: progress. Inspected existing entry form, patient chart, serializer and ingestion source before editing.

Implemented:
- Chart action passes patient_id; entry resolves that patient through the detail endpoint, including patients beyond the first list page.
- Checks the returned patient ID before allowing save; failed loading offers retry.
- General entry supports debounced name/MRN search. One abortable loading effect covers list, detail and search, preventing old responses from overwriting current results.
- Added numbered section anchors and clear Chinese headings for patient details, measurements, lab results and questionnaire/history.
- Numeric inputs support decimals; values must be finite to enter the payload. BMI preview uses a neutral informational treatment.
- Questionnaire and problem inputs distinguish unanswered, yes and no. Unanswered flags are omitted from the request; explicit no remains false. Smoking/alcohol flags have a single selection source, removing conflicting duplicate checkboxes.
- Date defaults use the local calendar date. The required screening date retains native form validation.
- Save locks the fieldset while in flight. Success action preserves the saved patient's risk-analysis context.

Verification: final Vite production build succeeded. Complete frontend suite passed: 13 files / 43 tests. Four intake tests cover exact patient resolution, decimal payload and omitted unknown answers, explicit yes/no and smoking flags, failed/mismatched patient load and name/MRN search. The tests initially exposed disabled retry/selection handling; corrected before the successful full run.

Scope limitation: tests use mocked synthetic API data; request payload checks do not prove downstream persisted representations. No backend changes were made. Real save/validation and native keyboard checks remain outstanding.

Browser inventory is still empty (apps: [], browsers: []). No screenshots obtained. Remaining work includes intake visual acceptance, bulk import, history/risk/research UI refinement, design reference case study review and full browser/accessibility/performance/live workflow acceptance. Goal remains active.

## Iteration 5 — Import pipeline and history

Previous turn classified as progress. Existing import/history views and backend preview/result contracts were inspected before edits.

Implemented:
- Three-stage import guidance: choose, preview, confirm. File/FHIR import cannot start without the corresponding preview.
- Format selector, file input and JSON input are locked during processing. Completed imports cannot be resubmitted until source/reset changes.
- FHIR structural preview rejects missing resourceType or malformed/empty Bundle entries; this is not full FHIR conformance validation.
- Named JSON/file inputs, busy status, source-change preview invalidation, and native file input reset.
- Partial import failures display row context and can expand the complete error list. Missing result counts display as unavailable rather than invented zero.
- Restrained ruled progress and result presentation matching Clinical Atlas.
- History has backend total count, abortable page loading, loading rows, error/retry and separate empty state.
- History links to patient chart and patient-context risk analysis. Removed vitals/lab columns which the list serializer does not supply, avoiding false missing/zero claims.

Verification: Vite production build passed. Full frontend suite passed: 14 files / 48 tests. Five new tests verify preview gating and partial-error expansion, JSON/format locks and preview invalidation, malformed Bundle rejection, history totals/page links and retry. diff --check for tracked CSS passed.

No real import was submitted and no backend data altered. Tests mock responses using synthetic data. Browser inventory again returned apps: [], browsers: []; no screenshots or actual viewport review obtained.

Goal remains active. Remaining scope: risk/research/continuous signal route-specific design and workflow checks, deeper named-reference case studies, actual desktop/mobile iteration, live save/import and governed-report flows, browser keyboard/accessibility/performance checks and final completion audit.

## Iteration 6 — Risk workspace and research reports

Previous turn classification: progress. Inspected the risk component/state/helpers, existing tests, research report queue and stylesheet before editing.

Implemented:
- Replaced the risk page's decorative gradient hero/ring/overlap with a ruled title, textual model progress and explicit patient controls.
- Preserved risk grouping, model details, missing-data limitations and source snapshots. Group headers use flat semantic colour rather than gradients; panel radius/shadows reduced.
- Searchable patient selection and exact detail resolution when the chart-selected patient lies beyond the first list page.
- Route changes abort analysis; selection changes clear prior results. Execution requires a resolved patient, and late cancelled responses cannot apply.
- Patient loading/error/retry and synthetic demo messaging are explicit.
- Report queues support paginated response objects in mocked tests, cancelable requests, loading rows and separate failure/empty states. Correction in iteration 18: the current research_reports view returns a capped array, so these tests did not prove live backend pagination support.
- Pending report count labelled as current-page count; unknown privacy suppression is reported as unknown.
- Review failures remain in the named dialog with the entered note. In-flight review dismissal is disabled.
- Artifact loading prevents duplicate reads; request submission uses form semantics. Switching a new request back to pending status does not fetch an obsolete filter.
- Report styling uses Clinical Atlas colours and fine rules.

Verification: production build passed. Full frontend suite: 16 files / 54 tests passed. New risk tests cover out-of-page patient resolution, selection reset and cancelled late analysis. New report tests cover total/page scope, privacy unknown state, in-dialog review failure, role visibility and retry.

No live risk calculation or report approval was performed. Tests use mocked synthetic data. Browser inventory remains apps: [], browsers: []; actual screenshots and visual review still unavailable.

Remaining: cohort and continuous-signal UI/flow refinement, deeper reference study, typography/layout audit, real browser desktop/mobile iteration, live workflow checks, accessibility/performance evidence and final requirement audit. Goal remains active.

## Iteration 7 — Cohorts and continuous signals

Inspected existing components and the Sotera report service response contract before editing.

Implemented:
- Cohort and similarity criteria changes cancel requests and invalidate prior results; late cancelled responses cannot repopulate the screen.
- Reject reversed numeric/date ranges before querying; errors are local to the relevant query.
- Boolean controls use unique label IDs, advanced disclosure exposes its state, and summary tables are named.
- Zero similarity remains visible; privacy suppression uses true/false/unknown and does not imply release authorization.
- Cohort surfaces use the shared restrained paper/green palette with ruled metrics.
- Continuous signal import/FHIR/AO status and monitoring duration now derive from response fields rather than fixed success/not-run claims.
- Missing numeric values remain missing, zero remains zero, and all numeric signals are shown. Source limitations are visible and quality warning labels do not invent counts.
- Report loading is cancelable with error retry; decorative stamp/texture/shadows/gradients removed in favour of shared typography and flat coverage bars.

Verification: complete frontend suite passed, 17 files / 59 tests; Vite production build passed. Five new synthetic tests cover truthful signal status/duration/missing values, retry/abort, cancelled late cohorts, reversed range validation and zero similarity/invalidation. Tracked CSS diff --check passed (line-ending notices only).

No live research query, data import or AO run was performed. Browser inventory remains apps: [], browsers: []; screenshot, desktop/mobile visual review and native keyboard verification remain unavailable. Tests are mocked and do not prove backend integration.

Goal remains active. Remaining: deeper named-reference study, final typography/layout audit, actual desktop/mobile browser iteration, live workflow checks, accessibility/performance evidence and final requirement audit.

## Iteration 8 — Account access and overview

Previous turn classification: progress. Inspected current git status, login/registration, overview, role helpers, theme and existing authentication tests before editing. Preserved unrelated backend and migration changes.

Implemented:
- Shared AuthFrame: restrained editorial context, brand mark, ordered access/application steps, focused form, real home link and responsive single-column layout. Reduced-motion preference bypasses the subtle form entry transition.
- Login form submission follows its current MFA phase, including native form submission; identity changes discard the previous provisioning URI and OTP. Requests lock the form fields and expose busy state. MFA verification errors now retain error severity.
- Registration adds autofill metadata, locks pending input, and replaces the form with an approval-pending confirmation after success. Does not establish an authenticated session.
- Overview uses a ruled metric strip and linked task list; task entries remain available during loading.
- Overview requests are cancelable and parse failures are isolated per endpoint. Successful results remain visible on partial failure; unknown values remain missing. Role changes cancel the earlier load, and nonresearch accounts do not fetch/display research summaries.

Verification: 18 test files / 66 tests passed; production build passed. Seven added tests cover MFA form phase/identity reset, pending locks, registration confirmation, dashboard task availability/abort, role-scoped requests, partial failure/refresh and stale role responses. Two existing login smoke assertions updated for the new H1. Tracked App.css diff --check passed (line-ending notice only).

Runtime: frontend http://127.0.0.1:3000/ responds 200 text/html; localhost:8000 does not respond. CUA inventory returns apps: [], browsers: []. No screenshots, native keyboard operation, live login/registration or backend writes performed. Test data and credentials are synthetic.

Goal remains active. Remaining: deeper reference case study, final typography/layout audit, browser desktop/mobile visual iterations, live workflow validation, accessibility/performance evidence and requirement-by-requirement final audit.

## Iteration 9 — Design study and reading hierarchy

Previous turn classification: progress. Inspected current style sources and existing design log before changes.

Research inspected on 2026-10-09:
- Linear, A calmer interface for a product in motion (2026-03-12): orientation elements should carry less weight than task content; stable header positions aid familiarity. Source: https://linear.app/now/behind-the-latest-design-refresh
- Linear, How we redesigned the Linear UI (2024-03-28): compare multiple view types and states, align sidebar labels/icons and test hierarchy before rollout. Source: https://linear.app/now/how-we-redesigned-the-linear-ui
- Stripe, Designing accessible color systems (2019-10-15): colour choices should have predictable contrast across actual surfaces. Source: https://stripe.com/blog/accessible-color-systems
- Raycast, A Technical Deep Dive Into the New Raycast (2026-05-14): behaviour, transitions and measured responsiveness form part of perceived craft. Desktop-specific conventions are not copied into this browser product. Source: https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast
- Awwwards Moxie case: search-indexed official metadata identifies an inclusive care site and warm light/dark palette. This supports investigating distinctive care branding; it does not establish visual or usability quality. Original case fetch timed out. Source: https://www.awwwards.com/sites/moxie
- Mobbin public MCP page exposes examples of progressive onboarding; the app catalogue redirects to a page without usable case contents. No individual authenticated Linear flow inspected. Sources: https://mobbin.com/mcp and https://mobbin.com/discover/apps/web
- Apple typography documentation requires JavaScript; support/search summaries confirm display customisation, but full typography guidance and visual study remain unverified. Source: https://developer.apple.com/design/human-interface-guidelines/typography

Design judgment applied: preserve the Clinical Atlas identity, reduce decorative status cues, and make evidence/limitations readable. These are our product decisions, not claims of copying or matching reference products.

Implemented:
- Replaced seven pale signal-report text colours with the shared muted ink.
- Signal metadata now has a 12px floor; important descriptions use 14px and supporting content 13px with more line-height.
- Raised 17 shared CSS font-size declarations from 9–11px to 12px, including navigation/clinical metadata.
- Added wrapping/min-width safeguards and aligned ruled metric borders for the two-column report layout.
- Removed unused stamp/status/accent CSS and obsolete metric accent props; removed a live-looking decorative dot from a static report.

Static contrast evidence: relative sRGB luminance, ratio (lighter + 0.05)/(darker + 0.05). Shared muted #65716a on #f8f9f5 = 4.816301; on white = 5.092745. Prior affected colours ranged from 3.214 to 3.990 on paper. Verdict accent #7fe0d2 on #245747 = 5.335631. Scope is explicit colour pairs, not computed DOM/cascade or a whole-app accessibility certification. Threshold reference: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

Verification: affected synthetic research-state suite passed 5/5; final production build passed. CSS diff --check passed with line-ending notices only. Previous complete suite remains 18 files / 66 tests, not rerun for this typography-focused iteration.

CUA inventory still apps: [], browsers: []; no screenshots obtained. Actual resized text, zoom/reflow, desktop/mobile layout, contrast in all rendered states, and live workflows remain unverified. Full reference visual study and performance acceptance remain open. Goal remains active.

## Iteration 10 — Route orientation and recovery

Previous turn classification: progress. Rechecked App, ProtectedRoute, Vite/test setup and current frontend git changes before implementation. Shell helper remains unavailable; verification executed with Node directly.

Implemented:
- RouteExperience supplies generic page titles without patient names, identifiers or query strings.
- After a different path commits, focus moves to the existing main landmark. Query-only navigation preserves form focus; PUSH/REPLACE resets scroll while POP does not force a reset (full history scroll restoration is not implemented).
- Suspense is keyed by pathname so a pending destination presents a loading status; a shared previous-path ref delays focus until destination content commits.
- Route-level rendering errors show a concise recovery page with explicit full-page reload and home link. The boundary resets on path change; no exception detail is displayed or explicitly logged by this component.
- Unknown paths show a 404 page with a real destination rather than silently redirecting.
- Permission denial uses shared Clinical Atlas styling and Traditional Chinese, with a stable overview link instead of window.history.back. Existing authorization checks remain.
- Added explicit H1 semantics to patient registry, intake, bulk import, cohort and governed-report headings.

Verification: full frontend suite passed, 19 files / 72 tests. Vite production build passed. Tracked App.css diff --check passed with line-ending notice only. Six new tests cover private titles/focus, query preservation, render recovery/reset, lazy-load timing, 404 links and restricted role entry. Tests initially revealed that router transitions retained the prior page without a loading status; corrected with keyed Suspense before the successful full run.

Implementation references (official): https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary and https://reactrouter.com/api/hooks/useLocation . React error boundaries cover descendant rendering failures; async/event-handler/API errors continue to use page-specific handling. Test scope does not prove real screen-reader output, actual browser reload or all lazy chunk failure variants.

CUA inventory remains apps: [], browsers: []; no native browser or screenshots obtained. Goal remains active. Remaining: visual case study access, full desktop/mobile screenshot iteration, actual keyboard/assistive-technology checks, live backend workflows and measured performance before final completion audit.

## Iteration 11 — Initial-load scope and stylesheet cleanup

Previous turn classification: progress. Inspected index.html, package scripts, generated dist/index.html, navigation/auth hook, current stylesheet and existing tests before edits.

Implemented:
- Public navigation remains synchronous and lightweight; authenticated WorkspaceNavigation loads only when the authenticated branch renders. Sidebar, account menu, icons and mobile drawer remain intact.
- Session-check and workspace-load statuses are explicit. A failed workspace module exposes a local navigation fallback with full-page reload; the shared error boundary now accepts a custom fallback.
- ProtectedRoute module deferred until a protected route is rendered; it still evaluates authorization before rendering children.
- Updated navigation tests for asynchronous module resolution; added session-check and auth-ending/menu-removal tests.
- Used rg over non-test JSX to confirm old homepage/auth-card/metric rules were unused, then removed 49 selector occurrences (including occurrences in combined/media rules), preserving active chart/header/form rules. No dependency installed.

Build evidence:
- Before: initial HTML script/modulepreload static JS closure = 433607 bytes; Node gzip sum = 140427 bytes.
- After: closure = 340635 bytes; Node gzip sum = 112263 bytes. Reduction = 21.44% raw / 20.06% gzip.
- Measurement begins at JS assets referenced by dist/index.html, recursively follows static from/import dependencies, deduplicates filenames and sums Buffer length and node:zlib gzipSync length. It excludes dynamically loaded landing/route modules, CSS and network overhead; this is a bootstrap artifact measure, not browser timing or total authenticated-session transfer.
- After closure filenames: index-BAUc8_Qy.js, jsx-runtime-BaSZ_JNh.js, DefaultPropsProvider-6fI5UY80.js, useId-BLXzxAqL.js, api-d55ifNhO.js, auth-DqQr9Jv0.js.
- App.css source shrank from 31615 to 28316 bytes.

Verification: final full frontend suite passed 19 files / 74 tests; production build passed. Tracked CSS diff --check passed with line-ending notice only. Lazy-loading tradeoff: workspace modules download when first needed, and actual request scheduling/transition behavior still requires browser validation.

Official implementation references: https://react.dev/reference/react/lazy and https://vite.dev/guide/features.html#async-chunk-loading-optimization .

CUA remains apps: [], browsers: []. No screenshots, LCP/INP/CLS measurements or live authenticated walkthrough obtained. Goal remains active. Remaining: branded external app assets, visual/reference review in a working browser, full responsive and keyboard audit, live backend workflows and measured performance before final completion audit.

## Iteration 12 — Browser and install identity

Previous turn classification: progress. Inspected manifest, HTML references, Brand geometry, public asset inventory and targeted git status before edits. Viewed the original logo192.png and confirmed it was the React mark.

Implemented:
- Shared code-native geometry in src/config/brand.js drives both Brand.jsx and a Node-only asset generator. No AI raster image generation or external asset dependency used.
- Generated favicon.svg, multiresolution favicon.ico (16/32/48/64), apple-touch-icon.png (180), logo192.png and logo512.png using the existing square-centred cross.
- Opaque green app tile and paper cross; mark scaled to 72% with generous maskable inset. Maximum geometric mark radius = 9.793059 / 32-unit canvas; 40%-radius safe zone = 12.8.
- Manifest now uses AllCare365 identity, Traditional Chinese language metadata and shared green/paper colours. Declares PNG icons for any/maskable usage, SVG and ICO alternatives. Existing standalone display/start_url preserved; no offline or installability claim added.
- HTML uses branded SVG/ICO and the dedicated 180px touch icon, shared theme colour and Traditional Chinese product description.
- Rebuild assets with npm run generate:brand (node scripts/generate-brand-assets.mjs).

Verification:
- Visually inspected generated 192px PNG. Pillow decoder verified PNG sizes 180/192/512 and all four embedded ICO sizes.
- Two consecutive generator runs produced identical SHA-256 hashes in this environment.
- All HTML/manifest asset references exist in dist; SVG 335 bytes, ICO 841, Apple PNG 906, 192 PNG 944, 512 PNG 4722.
- Final full frontend suite passed 19 files / 74 tests; production build passed. Targeted diff --check passed.

Technical reference: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/icons . Raster dimensions and maskable purpose are declarations, not evidence of actual OS installation/cropping.

CUA remains apps: [], browsers: []. Browser favicon selection/cache, device install/touch icons, real viewport screenshots and native interaction still unverified. Goal remains active. Remaining: browser/reference visual access, responsive/accessibility/performance acceptance, live backend workflows and final requirement audit.

## Iteration 13 — Responsive navigation and drawer focus

Previous turn classification: progress. Inspected workspace navigation, stylesheet breakpoints, responsive report/cohort/signal rules and targeted git status before edits. Preserved unrelated repository changes.

Implemented:
- CSS and JavaScript now share an exact 1200px desktop threshold; fractional widths below 1200px retain mobile navigation.
- Opening a desktop viewport closes the mobile drawer. Path changes also close it.
- Added a named dialog, expanded/control semantics on the trigger and an explicit close button. Drawer width is bounded by viewport width.
- Disabled automatic modal focus restoration; after the exit transition, closing returns focus to the trigger, while destination selection or widening to desktop focuses main content.
- Drawer heading and flexible sidebar accommodate the close action; reduced-motion preference sets transition duration to zero.

Verification: final full frontend suite passed 20 files / 78 tests with no stderr; production build passed. Four new tests cover named dialog/explicit close/focus restoration, destination focus, fractional-width/desktop transition, and Escape dismissal. Targeted diff --check passed with a line-ending notice only. Media queries and focus were verified in the test DOM using mocked matchMedia; this does not establish real viewport layout, transition timing or assistive-technology behavior. Responsive data-page source rules were inspected, but no viewport rendering claim is made.

Official implementation references: https://mui.com/material-ui/api/drawer/ and https://mui.com/material-ui/react-use-media-query/ . Current online docs identify MUI v9; the installed MUI v7 Drawer source was separately checked for supported slotProps/transition APIs before implementation.

CUA inventory remains apps: [], browsers: []. No actual browser screenshots or authenticated walkthrough obtained. Goal remains active. Remaining: browser/reference visual access, responsive and keyboard/assistive-technology acceptance, measured browser performance, live backend workflows and final requirement audit.

## Iteration 14 — Unambiguous patient creation

Previous turn classification: progress. Inspected current PatientManagement, existing tests, form styles, error helpers and targeted git status before edits. Browser inventory revalidated as apps: [], browsers: [].

Implemented:
- A synchronous submission lock prevents duplicate create requests, including repeated form submit events before a React render.
- All creation fields are disabled during submission; the form exposes aria-busy. Existing Escape/backdrop/cancel safeguards remain. Failure unlocks the form and preserves entered values.
- Creation success uses its own dismissible, polite status, independent of list loading/error state. Returning from a later page to page one no longer erases confirmation.
- Successful mutation closes/resets the form without waiting for list refresh. If refresh fails, both creation confirmation and list error remain visible, distinguishing the two outcomes. No API contract or backend changed.

Verification: two new synthetic tests cover pending-field locks, duplicate submit prevention, Escape safeguard, failure recovery, and creation from page two followed by a failed list refresh. Targeted suite passed 6 tests. Final full suite passed 20 files / 80 tests with no stderr; Vite production build passed. The affected source/test files are untracked in the current worktree, so git diff --check cannot validate their content; direct trailing-whitespace inspection found none. No live patient mutation performed.

Goal remains active. Real browser dialog layout/keyboard/focus behavior, viewport screenshots, reference visual review, measured browser performance and live backend workflows remain unverified. These DOM tests establish state behavior only and do not satisfy visual acceptance.

## Iteration 15 — Proportional public illustration

Previous turn classification: progress. Inspected current LandingPage, global/theme typography, responsive illustration rules and navigation tests before editing. Targeted git status showed existing modified CSS and untracked LandingPage; preserved other changes. CUA revalidated as apps: [], browsers: [].

Implemented:
- Replaced fixed ring dimensions with container-bounded width and aspect-ratio. Crosshair lengths and inner ring inset now follow the outer circle.
- Central mark retains a capped 116px diameter, bounded by 60% of the ring, to preserve brand/text space. Top label is centered; lower labels use relative corner anchors with reserved side margins.
- Removed the 13px mobile introductory-copy override; mobile inherits the shared 15px, line-height 2 reading style.
- Product diagram now has img semantics and an accessible description explaining the person-centred relationship among clinical records, health risk and research, including its illustrative nature.

Source geometry estimate for 320/360/390/480px viewport widths (20px hero sides, 18px diagram padding and 1px borders): diagram content widths 242/282/312/402px; declared ring widths 178/218/240/240px; declared core widths 106.8/116/116/116px; side-anchor reserves 14.2/10.2/12/57px. These arithmetic estimates exclude browser font metrics, rounding and rendered text extents; they do not prove absence of overlap/clipping.

Verification: existing full frontend suite passed 20 files / 80 tests with no stderr; Vite production build passed. Tracked CSS diff --check passed with line-ending notice only. No tests added for CSS implementation details. Actual typography/illustration balance, label positioning, zoom, narrow viewport screenshots and screen-reader behavior require browser review. No screenshot or visual acceptance claim made.

Goal remains active. Remaining: working browser/reference visual access, full desktop/mobile visual iterations, keyboard and assistive-technology validation, measured browser performance, live backend workflows and final scope audit.

## Iteration 16 — Risk results with complete context

Previous turn classification: progress. Revalidated local frontend HTTP 200 on port 3000; backend port 8000 connection failed. Inspected result normalization, existing risk tests, result-card rendering and targeted git status. CUA inventory remains apps: [], browsers: []; no alternative browser control capability found in enabled tool inventory.

Finding: normalized missing fields, model limitations, recommendation text and review flags existed, but the old compact card only showed the first three missing fields or first limitation in certain applicability states. Full context had no disclosure. Titles and metadata were truncated; metadata used 10.5px, while passive cards lifted on hover.

Implemented:
- Result cards now follow the shared paper/ink/line typography, with wrapped 15px headings, 12px metadata/status labels, tabular serif results, and no hover lift/shadow. Severity colors and labels remain explicit.
- Container-driven columns use repeat(auto-fit, minmax(min(100%, 240px), 1fr)), replacing a four-column breakpoint that could compress cards after the system index consumes width.
- Visible missing-field count and backend review flag summarize attention needs. Native details/summary exposes every missing field, every model limitation and the existing backend recommendation, including limitations for applicable calculated models.
- No risk formula, normalization, backend API, thresholds or recommendation content changed.

Verification: new synthetic UI test covers a long model heading, all four missing fields, both limitations, review flag, backend recommendation and a calculated 0% result with a limitation. Native disclosure click/open state passed in the test DOM. Targeted risk suite passed 15 tests; full frontend suite passed 20 files / 81 tests with no stderr; Vite production build passed. CSS diff --check passed with line-ending notice only; direct trailing-whitespace checks passed for untracked source/test files. No live analysis performed.

Implementation reference: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details . Browser-native disclosure supports keyboard interaction, but this turn did not verify real browser/assistive-technology behavior. Test DOM coverage does not prove viewport balance, font metrics or disclosure layout.

Goal remains active. Remaining: browser/reference visual access, actual desktop/mobile screenshot iterations and keyboard/assistive-technology review, measured browser performance, live backend workflows and final requirement audit.

## Iteration 17 — SMART launch states

Previous turn classification: progress. Inspected Launch and its existing test, AuthFrame, installed fhirclient 3.0.0 package exports and esm browser/SMART source before editing. The installed browser entry exports authorize directly; online documentation examples vary by version. CUA inventory revalidated as apps: [], browsers: [].

Finding: Launch was an unstyled English waiting screen. It did not handle authorization rejection or offer recovery. Its effect could call authorize twice during React StrictMode effect replay.

Implemented:
- Shared Clinical Atlas paper/ink/ruled layout, Traditional Chinese heading and loading status, and an indeterminate progress indicator. No fabricated completion percentage or local authentication-success claim.
- Synchronous/asynchronous SDK failures produce a generic visible error, explicit reconnect button and login return link; raw provider diagnostics are not displayed.
- Pending authorization promise reused during StrictMode replay; explicit retry resets the attempt. Each effect subscription ignores late rejection after unmount.
- Preserved existing clientId, scope, issuer and dashboard redirect configuration. No OAuth protocol changes, tokens or external messages added.

Verification: Launch suite passed 5 tests, including configuration/status, StrictMode single launch with rejection, failure/retry, synchronous failure, and obsolete rejection after unmount. Full frontend suite passed 20 files / 85 tests with no stderr; Vite production build passed. CSS diff --check passed with line-ending notice only; direct trailing-whitespace checks passed for untracked Launch source/test files.

Official SDK reference: https://docs.smarthealthit.org/client-js/api.html . authorize normally redirects away; no success-side effect was added to its promise chain. The UI cleanup guard prevents obsolete local error updates, not cancellation of the SDK network/redirect operation. No in-flight cancellation claim made.

Goal remains active. All new authorization tests mock the SDK; real provider availability, consent, redirect/callback completion, browser layout, keyboard behavior and assistive-technology output remain unverified. Broader missing evidence still includes reference visual access, desktop/mobile screenshot iterations, measured browser performance, live backend workflows and final acceptance audit.

## Iteration 18 — Research queue scope and mutation consistency

Previous turn classification: progress. Inspected ResearchReports, existing tests and actual research_report_service/views sources before edits. CUA revalidated as apps: [], browsers: [].

Authoritative finding: apps/clinical/health_screening/views.py research_reports GET serializes queryset[:100] as an array. It supports status/report_type filtering but does not consume page or return count/next. Earlier iteration 6 mocks used a paginated response and were insufficient evidence of live backend pagination; its wording has been corrected. No backend change made.

Implemented:
- Array responses now display loaded snapshot counts, not claimed matching totals. A 100-item snapshot explains that older records may not be included and offers status filtering as the existing way to narrow scope.
- Explicit count/next response objects remain supported; page counts retain their appropriate scope. Pending-count chips distinguish current snapshot/page and avoid showing zero during loading or failure.
- A shared synchronous mutation lock prevents duplicate request/review operations before render. All request fields are disabled while submitting, the form exposes aria-busy and the button shows processing state.
- HbA1c numeric input accepts decimals through step=any. No query meaning or medical threshold changed.
- Successful mutations release the submission state without waiting for list refresh; success and list errors remain separate. Review failure releases the lock for explicit retry and preserves the note.

Verification: four new synthetic tests cover current array contract, cap notice, one decimal-filter submission with locked fields/recovery, and review retry after failure. Existing mocked paginated-contract coverage remains. Final full frontend suite passed 20 files / 89 tests with no stderr; production build passed. Direct trailing-whitespace checks passed for the untracked source/test files. No live request, report approval or artifact read performed.

Goal remains active. Actual browser/keyboard layout and screenshots, reference visual access, live authenticated backend workflows, performance measurements and final acceptance audit remain outstanding. The capped endpoint still cannot expose earlier reports through page navigation; the UI now represents that limitation accurately rather than claiming a total.

## Iteration 19 — Contextual research preview lifecycle

Previous turn classification: progress. Inspected artifact reading code, report service, cohort/similarity/FHIR source shapes, existing tests and targeted git status before edits. CUA inventory remains apps: [], browsers: [].

Implemented:
- Selecting an available report immediately opens a named preview with selected title, report type and request timestamp. Indeterminate loading is local and explicitly announced.
- Reading failures stay inside the selected preview, with a retry for that same report. No stale output is shown while loading or after failure.
- Cancel/close aborts the active request and clears preview state. Page unmount aborts the preview as well. Late cancelled responses cannot reopen or replace another preview.
- Synchronous request-reference guard prevents repeated reads while pending. Raw complete JSON output remains unchanged and is focusable for keyboard scrolling; no metric transformation or privacy-state inference introduced. Backend artifact access enforcement remains authoritative.

Verification: three synthetic tests cover selected-report failure/retry, cancel followed by another report and a late original response, and unmount abortion. Initial cancellation test attempted another row before the MUI dialog exit transition completed; corrected the test to wait until the row button becomes accessible, preserving modal isolation. Targeted report suite passed 10 tests. Final full frontend suite passed 20 files / 92 tests with no stderr; Vite production build passed. Tracked CSS diff --check passed with line-ending notice; direct trailing-whitespace checks passed for untracked source/test files. No live artifact read performed.

Goal remains active. Test DOM evidence verifies lifecycle and state handling, not real focus restoration, screen-reader announcements, narrow viewport readability, or authorization/audit behavior on a live server. Actual browser/reference visual access, desktop/mobile screenshot iterations, measured performance, live backend workflows and final acceptance audit remain outstanding.

## Iteration 20 — Dashboard report count provenance

Previous turn classification: progress. Inspected current Dashboard, tests, count helper and shared metric rules before editing. Rechecked current research_reports view: capped queryset[:100] array response remains.

Implemented:
- Pending-report metric now carries its count scope alongside the value. Array/list snapshots are described as loaded records; a 100-entry array explains its limit and possible omitted earlier requests.
- Explicit finite nonnegative backend count values are treated as totals, independently of response-page length.
- Metric notes use shared muted color, 12px type and wrapping. Loading/failure do not assert a snapshot scope; failed report reads remain missing rather than zero. Existing role gating, partial failures, patient/screening counts and abort handling remain.

Verification: three synthetic tests cover a capped 100-entry report array, a 321 total with one response item, and report-only failure without a false zero/snapshot claim. Final full frontend suite passed 20 files / 95 tests with no stderr; production build passed. CSS diff --check passed with line-ending notice; direct whitespace checks passed for the untracked Dashboard source/test files. No live authenticated data read performed.

Browser attempts: createBrowserTab(chrome, localhost:3000) returned Browser is not available: chrome; createBrowserTab(iab, localhost:3000) returned Browser is not available: iab. No browser session was created, and no screenshots or real performance/focus/viewport evidence obtained.

Goal remains active. This turn provides scoped-count correctness and DOM-test evidence only. Required visual/reference studies, desktop/mobile screenshot iterations, real keyboard/assistive-technology checks, measured browser performance, live backend workflows and final acceptance audit remain incomplete.

## Iteration 21 — Shared core design tokens

Previous turn classification: progress. Inspected current theme, brand geometry/config, shared CSS and three research stylesheets, installed MUI CssBaseline source and targeted git status before edits. Preserved unrelated API configuration changes.

Implemented:
- config/designTokens.js now owns core paper/surface/wash/ink/green/muted/line colors, theme accent/success colors and sans/serif stacks.
- config/theme.js creates the shared MUI theme and emits ten core CSS custom properties through MuiCssBaseline styleOverrides. App now consumes this theme rather than defining a separate inline palette.
- Research stylesheet aliases and shared color declarations consume these variables. Body font uses the shared stack; early body paper/ink and font fallbacks remain for initial loading. Semantic risk/status colors and contextual washes remain separate.
- Brand asset renderer gets its two colors from the same core tokens. The mark now uses a dedicated local --atlas-mark-centre variable, avoiding the old local --atlas-paper override that conflicted with paper-colored foreground during alias migration.

Verification:
- Regenerated SVG/ICO/180/192/512 assets; all five SHA-256 hashes matched the before-refactor baseline.
- Node React renderToStaticMarkup of ThemeProvider + CssBaseline emitted all ten custom properties, with palette/background/font values matching tokens. Initial literal-string check failed for font values because Emotion removes spaces after commas; inspected emitted style and corrected the comparison for this serialization before the successful check. This confirms emitted CSS, not browser computed appearance.
- Final full frontend suite passed 20 files / 95 tests with no stderr; Vite production build passed. Tracked diff --check passed with line-ending notices only; direct trailing-whitespace checks passed for untracked JS/JSX files. No dependency installed.

Official implementation reference: https://mui.com/material-ui/react-css-baseline/ . Current online docs describe MUI v9; installed MUI v7 CssBaseline source was checked for its styleOverrides merging behavior. Isolated visual previews must render the shared ThemeProvider/CssBaseline to obtain the core variables. No new CSS-mirroring tests added.

CUA inventory remains apps: [], browsers: []. Goal remains active. Typography fallback metrics, computed colors/contrast after stylesheet integration, desktop/mobile visual equivalence and screenshots remain unverified in a real browser. Full reference visual research, keyboard/assistive-technology checks, measured performance, live backend workflows and final acceptance audit remain outstanding.

## Iteration 22 — Apple design evidence and acceptance priorities

Previous turn classification: progress. Re-read product direction and earlier research claims, inspected shared/report font declarations, and researched official sources before deciding whether another visual change was justified. No application code changed in this turn.

Sources inspected on 2026-10-09:
- Apple, Principles of great design, WWDC26 session 250: https://developer.apple.com/videos/play/wwdc2026/250/ . Read the official transcript, especially Simplicity 11:13 and Craft 13:42. Evidence: hierarchy relies on order/spacing/contrast; useful context can reduce friction; consistent behavior, immediate feedback and careful iteration help people trust the product. Application judgment: preserve the current contextual report preview and complete model-limit disclosure rather than compressing all detail into decorative summaries. This is a design interpretation, not a user-study result.
- Apple, Get started with Dynamic Type, WWDC24 session 10074: https://developer.apple.com/videos/play/wwdc2024/10074/ . Official native-platform guidance addresses retaining hierarchy when text grows and adapting layout. Web application judgment: typography acceptance must cover enlarged text, long Chinese/English labels and disclosure contents; do not equate native Dynamic Type APIs with web behavior.
- W3C, Understanding SC 1.4.4 Resize Text: https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html . Read the criterion/intent for resizing text up to 200% without losing content/functionality. Fixed px declarations alone do not establish failure or compliance; actual browser resizing and content checks are required.
- Awwwards, Moxie: https://www.awwwards.com/sites/moxie . Indexed award metadata remains accessible (Honorable Mention 2024-02-13, healthcare brand context, desktop/mobile elements and listed palette); direct page open failed again with Internal Error. No case screenshot, interaction or complete visual case study was inspected.

Current-state evidence: local frontend HTTP returned 200 on port 3000; backend port 8000 connection failed. CUA inventory remains apps: [], browsers: []. Fixed font declarations exist in the shared and continuous-report CSS, but this source observation is not a resizing result. Retained the current source styles until actual large-text/viewport review can distinguish problems from unnecessary redesign. No build/test rerun because application code did not change; the prior verified suite was 20 files / 95 tests, not a new result from this turn.

Acceptance priorities derived from the objective remain: inspect named references visually (especially Awwwards/Mobbin), capture actual desktop/mobile product states, test reading/overflow at enlarged text and zoom, exercise keyboard/focus and real workflows, measure browser performance, then perform the complete requirement audit. These cannot be replaced by source inspection, server response codes, mocks or emitted CSS. Goal remains active.

## Iteration 23 — Restore the existing development API

Previous turn classification: progress (new first-party research evidence). Rechecked startup instructions, project interpreter/dependency availability and service state before launch. No application/dependency/settings/database-schema edits made.

Runtime work:
- The general aptagen3d interpreter lacks Django; the existing project venv/Scripts/python.exe has Django, DRF, psycopg2 and dotenv. Used the project environment without installing anything.
- Ran project Python manage.py check: passed, System check identified no issues, no reported check codes.
- Ran a read-only Django SELECT 1 database probe: passed. No migration or seed command executed.
- Started project Python manage.py runserver 127.0.0.1:8000 --noreload as a hidden process (PID 18760). Kept stdout/stderr diagnostics to exception-class/port-conflict/unapplied-migration flags only; no raw diagnostics or configuration values written to this record.
- Revalidated this exact live process handle: exit remains null, no collected exception/port-conflict/unapplied-migration flags.

HTTP evidence from unauthenticated read-only probes:
- /api/health-check/: 200 application/json, status healthy.
- /api/auth/login/: GET returns 405; verifies route reachability, not successful login (the endpoint uses POST).
- /api/patients/: 401, no patient response body read. This is one unauthenticated boundary check, not a complete authorization/security audit.
- /fhir/R4/metadata: 200 application/fhir+json, resourceType CapabilityStatement, fhirVersion 4.0.1. Only these public metadata fields were recorded.

No authenticated account, patient mutation, import, analysis, research request/approval or live artifact read performed. No frontend source changed and no build/test rerun; last source-change verification remains 20 files / 95 tests and successful production build from iteration 21.

CUA inventory after backend restoration remains apps: [], browsers: []. Goal remains active. Backend connectivity is now available for later browser walkthrough, but this does not prove frontend rendering, consent/callback completion or any authenticated workflow. Remaining: working browser/reference visual access, desktop/mobile screenshot iterations, real keyboard/large-text/assistive-technology review, measured browser performance, live authenticated workflows and final acceptance audit.

## Iteration 24 — JSON response contract and local CORS evidence

Previous turn classification: progress (restored API). Inspected existing API changes before editing; retained Vite base URL, MFA endpoints, authentication headers, request options and logout behavior. No backend/settings/dependency/database changes.

Finding and change:
- Live public metadata responds with application/fhir+json; the original parser only recognized application/json and therefore wrapped FHIR JSON in a detail string. Existing page mocks did not exercise this real media-type contract.
- Extracted parseApiResponse to frontend/src/utils/apiResponse.js and re-exported the existing API name from config/api.js. Recognizes normalized application/json and structured +json media types, preserving JSON arrays and primitive values.
- HTTP 204/205 returns an empty object. Plain text keeps the existing detail fallback. Malformed JSON returns a generic Traditional Chinese message rather than response fragments; abort and other non-syntax errors retain their original semantics.
- Reference: IETF RFC 6839 section 3.1, https://datatracker.ietf.org/doc/html/rfc6839 (consulted 2026-10-09), describes +json generic JSON processing. Response.json behavior and exceptions: https://developer.mozilla.org/en-US/docs/Web/API/Response/json .

Verification:
- Added 13 contract cases using real Response objects: JSON parameters/case, FHIR/problem suffixes, zero/false/null, media-type parameter false positives, empty text, 204/205, malformed JSON and cancellation.
- Full Vitest run: 21 files / 108 tests passed. Production Vite build passed.
- Imported the exact pure parser with native Node and applied it to the live unauthenticated /fhir/R4/metadata response: HTTP 200, application/fhir+json; charset=utf-8, parsed resourceType CapabilityStatement, fhirVersion 4.0.1. Only public metadata fields recorded; no authenticated report/patient body read.
- OPTIONS probes for /api/health-check/ (GET) and /api/auth/login/ (POST) with Origin http://localhost:3000 and requested content-type/authorization headers: HTTP 200, matching allowed origin and requested methods/headers. This verifies server preflight headers only; Node does not enforce browser CORS.
- Targeted tracked diff whitespace check and direct checks for new parser/test/doc passed. Preserved unrelated existing changes.

CUA inventory remains apps: [], browsers: []. No actual rendering, screenshot, browser CORS enforcement, authenticated artifact preview or workflow acceptance demonstrated. Goal remains active. Remaining required acceptance evidence: desktop/mobile visual iterations, browser keyboard/large-text/accessibility checks, measured browser performance, live authenticated workflows and final review.


## Iteration 25 — Expanded risk workspace and FHIR trial evidence (2026-10-10)

Previous turn classification: progress. Inspected the current runtime catalog, source adapters, input repository, synthetic fixture, risk workspace, and regression suites before changes. Preserved existing unrelated worktree changes.

Implemented across the risk integration iterations:
- Runtime catalog now contains 82 executable items, including prediction probabilities, screening scores, and derived reference measures. This count does not prove that all source-folder model families have been integrated. The 144 canonical input contracts include explicit assay-specific measurements and questionnaire fields.
- Risk workspace distinguishes informational reference indicators and exposes units supplied by the result adapter. Added bilingual result search, status filters, visible/total count, and an empty-filter recovery action. Overall execution and missing-input summaries remain based on the full result set.
- Model disclosures now preserve available source document, model version, horizon, and original literature link. Credential-bearing URLs and non-web protocols are rejected.
- Updated synthetic Golden Patient inputs and JSON/XML exports. A full-pipeline test caught diabetes_medication missing from questionnaire scalar mapping; fixed that mapping and reverified. Custom observation concepts now carry a local code system rather than LOINC.

Evidence:
- Backend risk catalog/formula/strict-input/unit/FHIR projection selection: 63 tests passed before the Golden Patient update.
- Golden conformance pipeline: 4 tests passed after the mapping fix. Delivered synthetic JSON and XML both passed public import and risk APIs in the isolated test database; 82 executable items resolved without missing inputs. Inapplicable models remain explicitly inapplicable. This is not a claim that every item produces a risk probability or has independent reference vectors.
- Complete frontend suite: 22 files / 127 tests passed after provenance changes. Subsequently added one DOM interaction scenario verifying result search, clear-filter recovery, visible source/link, and preservation of the full summary; targeted RiskWorkspace suite: 5 tests passed. The expanded full suite has not been rerun after this test-only addition.
- Production build passed after filtering changes; subsequent provenance JSX compiles in Vitest, but a fresh production build after provenance changes remains to be recorded.

Acceptance limits:
- Browser inventory returned no enabled surfaces. Explicitly creating an in-app tab at localhost:3000 failed with Browser is not available: iab. No screenshots, browser interactions, responsive/zoom review, computed contrast, or measured browser performance were obtained in these iterations.
- All source-folder models, individual independent numerical reference vectors for every new model, and full final design acceptance remain incomplete. Research/source audit artifacts are historical evidence, not a declaration of completed integration. Goal remains active.


## Iteration 26 — Patient-scoped result filters

Previous turn classification: progress. Current component state showed search/status filters survived patient changes. Added a patientId-dependent reset so another patient starts with all results visible. Extended the existing DOM workflow scenario to filter the first patient, navigate to another patient, rerun analysis, and verify the query is empty and both results are displayed. Targeted RiskWorkspace and RiskAnalysis suites passed 18 tests. Fresh Vite production build passed after provenance and filter-reset changes. This remains component/test and build evidence; no real browser visual acceptance or screenshots obtained. Goal remains active.


## Iteration 27 — Reference research and readability evidence

Previous turn classification: progress. Inspected risk-result CSS: titles, English subtitles, values, outcomes and disclosure contents already use overflow-wrap; disclosures preserve whitespace for explanatory text. This is source evidence, not a browser overflow or 200% text-resize result. No speculative layout change made without rendering evidence.

Primary research consulted 2026-10-10:
- Raycast, A fresh look and feel (2022-07-19): https://www.raycast.com/blog/a-fresh-look-and-feel . Read the official explanation of larger search prominence, consolidated contextual actions/status, and focused compact presentation. Design judgment for this clinical product: keep patient selection and execution distinct from result search; keep full-run status visible while filtering; reveal source and limitation details within their model context. These are application judgments, not validated user-study outcomes. The article image endpoint https://www.raycast.com/uploads/redesign/navbar.png was retrieved by web tooling, but no rendered product/reference visual comparison was completed.
- Mobbin web-app directory: https://mobbin.com/discover/apps/web . Public page extraction returned login/join links and social navigation, without app cases or interaction screenshots. Do not count this access as a completed Mobbin visual study. No account creation, login or paid access performed.

The objective still requires live browser/reference visual access, desktop/mobile screenshots and iteration, keyboard/assistive-technology review, enlarged-text checks, measured browser performance and authenticated workflow acceptance. Prior build/tests are useful engineering evidence but do not establish the requested visual standard. Goal remains active.


## Iteration 28 — Expanded clinical input snapshot

Previous turn classification: progress. Inspected the snapshot filter and confirmed it excluded newly introduced fields absent from the frontend label map. Added the 28 new backend clinical labels to the frontend snapshot map, explicit assay/measurement units for nine added observations, readable diabetes-medication labels and selected source-population labels. Kept false answers distinct from missing answers. Added min-width/overflow wrapping to snapshot cells for long labels/values. Targeted risk suites passed 19 tests; production build passed after the final empty-value unit guard. This does not establish measured browser reflow or full coverage of every legacy input label. Browser visual acceptance and full final objective remain incomplete; goal remains active.


## Iteration 29 — Browser acceptance blocked audit

Previous turn classification: progress (input snapshot improvements and tests/build). Re-read the product direction, six remaining acceptance requirements, and iteration evidence rather than treating passing tests as visual acceptance. Current CUA getState again returned apps: [] and browsers: []; earlier explicit localhost tab creation failed because iab was unavailable. This same external condition has recurred across more than three consecutive resumed goal turns. No browser surface or confirmed browser job is live to wait on.

Completion is unproven: reference case visuals, actual desktop/mobile screenshots and design iteration, text-resize/reflow, computed contrast/target-size review, keyboard/assistive-technology behavior, measured browser performance, and authenticated browser workflow acceptance remain missing. Existing source, jsdom, isolated API and build checks cover engineering subsets only. Route refinements cannot be judged against the requested visual standard without rendered evidence. No further speculative styling changes justified now. Restoring an enabled browser connection is the external change required to perform these acceptance steps. This audit applies to the frontend design Goal, not a claim that the separate complete risk-source integration task is finished.


## Resumed goal browser audit after disease-network integration

The prior resumed turns made concrete progress: patient-specific model-input graph and routing, direct UI copy, actual shared measurements, and measured/pending connection distinction. Source/API/build/component evidence is recorded in docs/disease_network.md. Current CUA getState still returns apps: [] and browsers: []; earlier Chrome creation failed. This external condition persisted through three consecutive goal turns after resume. Local HTTP 200 does not restore browser control. No confirmed browser process handle is live to wait on.

Outstanding acceptance remains actual desktop/mobile rendering, screenshots and visual iteration, enlarged-text/overflow/contrast checks, real keyboard and assistive technology checks, browser performance, reference case visuals, and authenticated browser workflows. These require the missing browser surface. Source-level changes cannot establish the user-requested perfected visual outcome, and no further speculative aesthetic edits are justified without rendering evidence. Goal blocked audit passed; resume requires an enabled browser connection. No claim that the broader clinical risk-source task or full product design is complete.

## Iteration 30 — 實際 Chrome 網絡與病患巡檢

前一輪有實際登入、FHIR 匯入與 82 模型解析證據，分類為 progress。本輪以即時 worktree 和 Chrome 為依據。

- 疾病網絡將數值與模型清單改為原生 details/summary，減少右欄長頁；展開後實際 BMI/TG 等值仍可讀，切換領域重新收合。
- 桌面圖隨詳情捲動保持可對照；手機僅圖水平捲動，領域按鈕置前、44px 高度。
- Chrome viewport 設定 390×844，工具回報 DOM 416px：document clientWidth=scrollWidth=416，圖可視384／捲動600，無全頁水平溢出。完成後已 reset viewport。
- 病患列表不顯示缺少 Email 的重複副行；性別和 research 狀態中文化，病歷摘要同步。精確 MRN 搜尋回傳一位 Golden Patient，病歷鏈結正常。
- 相關網絡／列表測試 10 passed；病歷測試 5 passed；建置通過。

目標仍 active：尚需其餘研究頁面、健檢輸入、跨尺寸及全產品視覺與操作巡檢，不能據此宣稱全部 production-grade 驗收完成。

## Iteration 31 — 健檢與研究族群的實際巡檢

前一輪分類 progress（已修改網絡／病患並取得測試與瀏覽器證據）。

- 即時 Chrome 登入後巡檢 HealthDataInput 與 ResearchCohorts。
- 健檢預設就診類型顯示年度健檢，送出仍用 annual_physical；保留自訂類型。常用量測／檢驗加入中文名稱並改善單位排字；病患未選取狀態直接提示選擇病患。
- 瀏覽器輸入身高170與體重62.5，BMI顯示21.6；僅操作表單，未寫入健檢避免覆蓋 Golden Patient 測試基準。
- 研究相似族群欄位去除 SBP_DELTA/LIMIT 原始命名；摘要統一中文，區段 heading 使用 h2，保留資料遮蔽行為。
- 實際族群查詢：958 人、未遮蔽、可讀群體摘要與指標。手機設定390×844，工具 DOM寬416，document clientWidth=scrollWidth=416，完成後reset viewport。
- HealthDataInput測試4、ResearchDataStates測試5通過；最終vite build通過。

尚未達成全目標：研究報告／連續訊號頁視覺巡檢、健檢頁手機與鍵盤細節、全產品一致性與來源風險模組完整性仍需繼續；goal保持active。


## Iteration 32 — 2026-10-10

Research reports: localized cohort summary and similar-patient report names; request and queue sections now use semantic h2 headings. Continuous signals: localized import status, validity labels, sample/channel units, clinical database and ground-truth labels without changing source values. Chrome DOM verified both pages; signal mobile document width and scrollWidth were both 416px under the 390×844 override. Screenshot capture timed out, so visual proof is incomplete. Viewport reset requested. ResearchReports 10 tests passed; npm run build passed. FHIR XML/REST browser acceptance and full-system visual acceptance remain unfinished.


## Iteration 33 — 2026-10-10

Continuous signal loading, failed and unavailable responses now retain the report h1 and framed layout; each state has an h2, loading announces progress, failure retains retry, and unavailable data explains the resulting report without displaying invented metrics. Added an asynchronous test for loading-to-empty transitions and updated the prior signal assertions for localized status/validity labels. Full frontend suite: 24 files, 134 tests passed. Production build passed. Chrome verified the new loading heading/status in the live local app and the subsequent populated desktop report via screenshot. Empty/error states are verified by component tests, not live backend mutation. Screenshot now works at default desktop size after the prior mobile capture timeout. Full goal remains active; XML/REST browser acceptance and complete visual audit are not yet proven.


## Iteration 34 — 2026-10-10

Live Chrome FHIR XML acceptance: collection Bundle and single Patient XML each previewed successfully (1 Patient); invalid namespace produced a specific alert, cleared the preview and disabled confirmation. No test Patient was written to the database. Replaced repetitive FHIR count cards with a semantic resource-summary table: Chinese purpose, original FHIR type and count, plus explicit unwritten status. Import section headings now use h2. Preview/result completion focuses its heading and scrolls into view with sticky-header margin. Desktop screenshots showed the initial focus alone left the summary below the viewport; explicit scrolling corrected this and the complete summary was visible. Existing multi-file test now asserts preview and result focus. ImportHistory: 7 passed; build passed. REST and XML file-upload acceptance remain unproven; overall goal active.


## Iteration 35 — 2026-10-10

FHIR REST form: live malformed URL request produced backend HTTP(S)/userinfo/fragment validation alert. Added immediate field validation for absolute HTTP(S) URLs, userinfo and fragments; invalid inputs block preview before network requests, valid input restores preview. Backend source-origin validation remains authoritative. All import-page buttons now have 44px minimum height; source groups can wrap. Chrome at requested 390×844 measured document width=scrollWidth=416, and buttons approximately 43.993px (device rounding); mobile screenshot verified field error and readable groups. Valid localhost URL cleared aria-invalid and enabled preview. Viewport reset. ImportHistory 8 tests passed, build passed. Successful authenticated REST retrieval and XML file upload remain unverified.


## Iteration 36 — 2026-10-10

Reference research: Chrome successfully rendered https://mobbin.com/explore/web/flows/onboarding (public Rox landing/account screenshots; full authenticated flow not opened). Viewed Awwwards health catalogue and https://www.awwwards.com/sites/function-health case overlay, including its featured visual and palette metadata. Interpretation: expressive public storytelling and focused task forms can coexist; the operational workspace should retain restrained typography, ruled data and explicit feedback. References are inspiration, not medical evidence or assets copied into the product.

Shared theme now uses 44px minimum regular and toggle buttons, 4px button corners; removed the duplicate import-specific height rule. History displays annual_physical as 年度健檢, preserving unknown/custom values. Full frontend suite: 24 files / 135 tests passed; production build passed. Live Chrome history displayed two annual-physical labels and measured refresh/add/risk actions at approximately 43.993px with 4px corners. Header screenshot inspected. These checks do not prove every route layout after the common theme change; full visual acceptance, authenticated successful REST retrieval and XML file upload remain outstanding. Goal remains active.


## Iteration 37 — 2026-10-10

History mobile screenshot exposed horizontal table panning (383px container / 526px content) that hid the patient risk action. Added a narrow-screen ruled row layout with patient name first, date/type below and visible 44px risk action. Desktop retains the table. Explicit table/rowgroup/row/cell roles preserve table semantics across CSS display changes. Known inpatient/outpatient/H2U types localized; unknown source values preserved. Chrome mobile after change: document width=scrollWidth=416, table container width=scrollWidth=383, first risk link within x288–382 and height approximately 43.993px. Screenshot confirmed readable rows/actions. Viewport reset: width1880, row computed display table-row. ImportHistory 8 passed; production build passed. Full goal still active; other route visual checks and remaining FHIR file/REST acceptance remain unproven.


## Iteration 38 — 2026-10-10

Patient registry mobile screenshot showed 918px table content inside a 383px container, hiding identification and chart actions. Added mobile ruled patient rows with name/status, complete MRN, birth/age, sex, phone and a visible 44px chart action. Header actions share one wrapping row. Desktop retains the existing columns; explicit table roles preserve semantics across CSS display changes. Chrome mobile document width=scrollWidth=416 and table width=scrollWidth=383 after change. Exact synthetic Golden Patient MRN search returned one result; screenshot showed the full identifier, and chart action opened the matching patient record. Viewport reset and returned to registry. PatientManagement 6 tests passed; build passed. Overall goal remains active with remaining route and FHIR acceptance gaps.


## Iteration 39 — 2026-10-10

Completed registry mobile state layouts: skeleton rows use a two-column grid matching the compact records; empty-state cells wrap and size to the container, replacing inherited nowrap table-cell layout. Chrome exact synthetic non-match search returned 0 with a named clear-search action. Clearing restored 25 actual rows and empty query; mobile document width=scrollWidth=416, table width=scrollWidth=383. Empty-state screenshot inspected; separate initial measurement during transition was 433/433, so no horizontal document overflow was evidenced by that measurement. Viewport reset. PatientManagement 6 passed; production build passed. Goal remains active.


## Iteration 40 — 登入返回位置與 XML 檔案驗收（2026-10-10）

- ProtectedRoute 保留登出原因；Login 顯示閒置、期限與登入失效等原因提示。登入返回位置保留 pathname、search、hash，避免遺失 patient_id。
- AuthLifecycle、RouteExperience、sessionManager 共 21 項測試通過；frontend production build 通過。此修正未變更 15 分鐘閒置政策，未將先前驗收中斷歸因為已證實的 idle 或 JWT 問題。
- Chrome 實測：未登入時進入 Golden Patient risk-analysis URL，登入後返回完整 patient_id URL，病患選單與 MRN 正確還原。
- 使用者啟用 Chrome 檔案網址權限後，新控制分頁成功選入 golden_patient.fhir.xml（86.7 KB），預覽回傳 44 筆資源：Patient 1、Encounter 1、Observation 40、Condition 1、QuestionnaireResponse 1。畫面確認匯入按鈕可用，摘要明示尚未寫入系統。此次停於預覽，未重複写入既有 golden patient。
- 保留本地 Chrome XML 預覽頁供檢查；截圖於瀏覽器工具輸出，未宣稱有本地截圖檔。完整 REST 瀏覽器讀取及所有系統頁面驗收仍有後續工作。


## Iteration 41 — MFA 步驟語意與焦點（2026-10-10）

- 上輪分類為 progress：XML 檔案預覽取得 44 資源實測證據，登入返回病患 query 修正已驗證。
- 檢查現有 Login 與 AuthFrame：MFA 只在伺服器要求後出現，屬實作功能。將 mfa_required 提示改為資訊級別，避免正常驗證步驟呈現為登入錯誤。
- 驗證碼輸入在請求結束、欄位可操作時取得焦點；重試失敗後亦可接續輸入。修正設定資訊 helper，明確要求輸入代碼並驗證登入，避免引導使用者在未完成驗證前關閉頁面。
- AuthLifecycle 7 項測試通過，其中既有 MFA 流程新增焦點與資訊提示驗證；production build 通過。未使用真實帳號重新設定 MFA，瀏覽器未重現此帳號無需 MFA 的分支；該分支證據為元件測試。
- Chrome 檢查 FHIR REST API 來源表單，URL、token 說明與讀取限制可見；成功讀取帶認證 FHIR API 尚待後續驗收。


## Iteration 42 — FHIR 來源授權錯誤的恢復路徑（2026-10-10）

- 上輪分類 progress：MFA 提示級別、焦點與設定指引修正並取得測試與建置證據。
- Chrome 實測本地 FHIR Patient URL 未提供來源 token：preview 回傳來源 HTTP 401，工作空間保持登入，確認匯入維持停用。這證明來源認證失败分支，並不證明 REST 成功讀取。
- API 401 提示提供有效來源 token 再預覽；403 提示確認來源資料讀取權限。既有伺服器錯誤內容保留，來源 URL 保留供重試，token 仍於讀取後清除。
- 全部匯入錯誤提示可取得鍵盤焦點並捲入可見範圍，成功結果仍沿用結果標題焦點。Chrome 實測新版 401 提示為 active alert 且可見；未將來源 401 當作工作空間登出。
- ImportHistory 10 項測試通過，涵蓋 401／403 說明、焦點、URL 保留、token 清除及禁止匯入；production build 通過。帶有效來源認證的 REST 成功讀取仍待驗收。


## Iteration 43 — 疾病網絡觸控操作（2026-10-10）

- 上輪分類 progress：FHIR 401／403 恢復提示與錯誤焦點實作、測試與 Chrome 401 驗證。
- Chrome 選取 SyntheticGolden 並執行分析：82/82 模型解析，網絡 8 領域、15 資料關聯。手機實際 CSS 寬度 416，document scrollWidth 同為 416；圖保持容器內橫向探索。
- 實測延伸探索按钮高度 23.99 px，修正為 44 px 及整欄點擊範圍；領域清單與完整模型入口同步採 44 px。修改後量測 43.99 px，點選腎臟系統後圖、領域清單與詳情一致切換。
- 補齊共同因子 ever_smoker（曾有吸菸史）及 hba1c（HbA1c）標籤，避免畫面暴露資料欄位名稱。
- DiseaseNetwork 元件與工具共 4 項既有測試通過；production build 通過。手機修改後截圖遇到單次逾時，DOM 與尺寸取得驗證；恢復桌面後截圖成功。未將模型解析數當作全部模型臨床有效性的證明。


## Iteration 44 — 暫時 refresh 失敗與有效登入（2026-10-10）

- 上輪分類 progress：疾病網絡觸控高度修正、標籤補齊、手機互動與建置驗證。
- Chrome 從網絡切換模型頁時出現 refresh_failed 登入提示。此為實際觀察；未取得該 refresh 請求 HTTP 狀態，不將其直接歸因於網路或伺服器失敗。
- 源碼確認 requestRefresh catch 原本對任何錯誤清除登入。現改為網路失敗、429、5xx 且 access token 仍有效時保留 credential，30 秒後允許再次 refresh；一旦 access 已失效或回應明確拒絕認證仍清除。15 分鐘閒置登出、跨分頁 single-flight 與過時 refresh 防護維持。
- 新增網路、503、429 暫時失敗後保留與成功重試測試，以及 401 拒絕與過期 token 不保留測試。SessionManager/AuthLifecycle/RouteExperience 合計 26 項通過，production build 通過。
- 全部前端目標仍未完成；本輪原定手機模型結果審查因實際登入中斷轉向此較高優先問題，尚待接續。


## Iteration 45 — 手機模型結果區的固有寬度（2026-10-10）

- 上輪分類 progress：有效 credential 的暫時 refresh 失敗保留與重試實作、26 項測試及重新登入。
- Chrome 合成病患分析後手機檢查發現 document 416 px、scrollWidth 1350 px；卡片區父層 1327.84 px，排成五欄。原因為外層 grid 使用 1fr 的 auto minimum，橫向索引清單固有寬度撐開 grid。
- 外層 xs 欄改 minmax(0,1fr)，索引 nav minWidth 0，維持索引容器內捲動。實測 document 416／scrollWidth 416，卡片單欄 354.86 px；索引點選後可完整閱讀模型名稱、數值及展開入口。桌面 viewport 已還原。
- 為實測 26 個原始用途代碼顯示補齊 20 個唯一 outcome 中文映射，保留未知代碼與已有中文標籤，未改計算或適用條件。
- RiskAnalysis 14 項既有測試通過；production build 通過。模型展開內容與其餘頁面完整驗收仍待接續。


## Iteration 46 — 模型詳情與篩選恢復（2026-10-10）

- 上輪為 progress：手機 grid 溢出修正及用途標籤補齊取得瀏覽器證據。
- Chrome 手機展開 HSI：判讀文字、模型版本及原始參考文獻均可讀。量測 summary 31.38 px、文獻連結 18.52 px；調整兩入口 min-height 44 px 並增 focus-visible，修改後兩者均 43.99 px。
- 搜尋 HSI 得 1/82；不存在的合成搜尋字串得 0/82、無結果提示與清除篩選入口可操作。驗收後恢復桌面 viewport 與完整篩選。
- production build 通過。本輪是樣式修正，未新增鏡像樣式測試；以實際 Chrome 尺寸及互動作證。手機展開截圖單次逾時，未聲稱有成功截圖檔。


## Iteration 47 — 完整回歸與研究頁章節（2026-10-10）

- 上輪 progress：模型詳情觸控與焦點樣式、搜尋及無結果恢復實測。
- 完整 frontend npm test：24 個測試檔、143 項通過，無 stderr。測試證據涵蓋既有元件／工具行為，並不替代整體視覺、效能或臨床驗證。
- Chrome 研究 Cohort 手機表單截圖可讀，實際頁面 clientWidth／scrollWidth 均 416。
- 研究頁摘要原本數值以 h5／h6 產生，調整為 component p 且維持 typography variant；修改後 Chrome main 章節僅 H1 研究族群工作台及 H2 功能區，不再含數值標題。production build 通過，viewport 已恢復桌面。
- 全面目標仍 active；FHIR REST 成功認證讀取、跨頁分析接續與其餘響應式視覺證據尚有工作。


## Iteration 48 — 查詢完成導向族群結果（2026-10-10）

- 上輪 progress：完整 143 項前端測試與研究摘要語意修正。
- Chrome 真實族群查詢成功取得摘要；手機指標表容器寬 383、內容 414，捲動限制於表內，結果並未直接引導焦點。
- 加入族群查詢結果 H2 與 ref；族群／相似族群成功回應後將對應結果標題 focus 並 scrollIntoView，使用 instant 與 88 px margin。資料編輯清除結果不會觸發此導引。
- Chrome 手機重新查詢後結果 H2 為 activeElement，top 178 px 可見；viewport 已恢復。ResearchDataStates 6 項通過、production build 通過。相似族群成功分支的瀏覽器驗收仍待後續，未將元件測試當作全部操作完成。


## Iteration 49 — 相似族群實際回傳與指標語言（2026-10-10）

- 上輪 progress：族群结果導引與手機焦點實测。
- Chrome 使用合成條件年齡40／SBP120查詢相似族群，成功回傳摘要，相似族群 H2 active。手機 document 416／scrollWidth416。未讀取或輸出個別病患識別資料。
- 相似指標 Mean／Mean delta 改平均／平均變化；六項已知 delta 指標透過 numericFilters 標籤映射，與輸入條件一致；未知指標保留來源 label。Chrome 重查確認中文標籤顯示，未釋出的變化值仍維持未釋出。
- ResearchDataStates 6 項測試通過、production build 通過，viewport已恢復。条件編輯清除結果已有元件測試，本輪尚未補瀏覽器操作證據。


## Iteration 50 — 手機研究報告列（2026-10-10）

- 上輪 progress：相似族群成功回傳與中文指標摘要。
- Chrome 本地報告清單全部狀態：手機容器333 px、內容539 px，操作入口在右側；調整 <=600px 報告列grid，標題、隱私、時間及操作全寬，類型與狀態並列。保留table/rowgroup/row/cell語意及桌面表格。
- 修改後容器333／scrollWidth333，報告預覽入口實際可點並開啟具名 dialog，等待後 MeasureReport 內容回傳、關閉入口可用。未建立、核准或拒絕任何報告。
- ResearchReports 10 項測試通過，production build 通過。本輪曾因登入頁中斷而重新登入恢復；無登出原因提示，未宣稱根因已明確。viewport恢復桌面。

- 建置第一次因命令輸出緩衝上限終止，增加輸出緩衝後重跑結果如下；不將輸出截斷當作建置成功。


## Iteration 51 — 可閱讀的 FHIR MeasureReport（2026-10-10）

- 上輪 progress：手機報告列布局與預覽成功。
- 實際 MeasureReport 原本直接呈現完整JSON；新增獨立 FhirReportSummary，依標準 initial-population 及既有Allcare numeric-feature-summary extension呈現族群數、狀態、日期、已知指標名稱、平均及樣本數。遮蔽值保留已遮蔽，零值保留，不推導缺漏值。
- MeasureReport 原始 JSON 收於可展開 details，其他輸出格式沿用原始檢視。桌面實際既有報告摘要 DOM 與截圖確認顯示完整指標列。未更改報告內容、核准或資料權限。
- ResearchReports10項及新增zero／suppression測試1項通過，production build通過。手機摘要及其他報告格式的瀏覽器驗收仍待補。


## Iteration 52 — 手機摘要與預覽返回焦點（2026-10-10）

- 上輪 progress：可讀 MeasureReport 摘要與零值／遮蔽驗證。
- Chrome 手機 dialog clientWidth／scrollWidth369，摘要304／304；原始資料展開304／304且內容可見。手機截圖單次逾時，未宣稱取得該截圖。
- 實測關閉預覽焦點落BODY，修正為捕捉開啟按鈕並在Dialog退出動畫完成後返回，已移除按鈕則不強行聚焦。Chrome重新開啟／關閉後檢視報告按鈕為activeElement。
- ResearchReports10項通過、production build通過。viewport已恢復桌面。


## Iteration 53 — 病歷手機分頁發現性（2026-10-10）

- 上輪 progress：手機MeasureReport摘要不溢出、原始資料展開與關閉後焦點修正。
- 合成病患病歷Chrome實測手機document416／scrollWidth416，主要入口44 px；tablist可見384、內容541，手機原先無捲動按鈕。
- 啟用 allowScrollButtonsMobile，透過現有MUI slots加入中文前／後分類按鈕，設定原生button語意與44px寬度。現有PatientChart5項測試通過，production build通過。
- 桌面文件分頁成功選取且顯示對應空狀態。手機捲動後立即點擊的第一次結果落到醫囑，改桌面再選文件才正確；從桌面縮成手機時已選文件仍在右側不可見（left510px），此問題尚未修正，不將手機末端分頁驗收視為完成。viewport已還原。


## Iteration 54 — 手機病歷分類完整可見

將 App.css 的 600px 以下病歷分類改為三欄、兩列，隱藏橫向捲動箭頭及指示線，以背景和邊框標示選取；桌面保留原分頁列。Chrome 實際量測六個分類約 44px 高，首次 mobile CSS viewport/scrollWidth 均 416px；文件可直接點擊並顯示文件 panel。桌面選取文件後再縮至手機，選取仍為 true，viewport/scrollWidth 均 433px，全部分類位於視窗內（最右 417.34px），無水平溢出。已恢復桌面視窗。前端 production build 通過。

限制：恢复驗收時登入頁再次顯示「無法延續登入狀態」，使用已授權本地帳號重新登入成功；登入續期問題仍未完全結案。這次手機證據為 DOM 狀態與尺寸，沒有成功手機截圖，不宣稱全系統驗收完成。


## Iteration 55 — 修正連續續期的實際根因

前一輪為有進展：手機分類 CSS 與瀏覽器尺寸證據已落地。這輪查明 start_system.bat 使用 venv，該環境的 TokenRefreshSerializer 會輪替 refresh，卻沒有登記 successor；.venv-production 的新版會呼叫 outstand。專案 VersionedTokenRefreshSerializer 要求 OutstandingToken 存在，因此第二次續期遭拒。最近伺服器日誌多次呈現 login 200 → 5 分鐘 refresh 200 → 再 5 分鐘 refresh 401。

在原子交易內以 get_or_create 登記已驗證的新 refresh token，保留前任 token blacklist、token_version、帳號狀態及 MFA 檢查；沒有修改 timeout 或權限。新增連續三次輪替測試，核對 successor 紀錄、access 身分及所有 predecessor 被拒。venv 修正前測試因缺少 successor 紀錄失敗，修正後 tests/test_auth_lifecycle.py 全部 10 passed；.venv-production 新版同一輪替測試 1 passed。官方背景：https://django-rest-framework-simplejwt.readthedocs.io/en/stable/rest_framework_simplejwt.html（outstand）與 /settings.html（rotation/blacklist）。

Chrome 目前仍可顯示本地病歷頁。限制：本輪尚未完成修正後跨兩個真實五分鐘週期的瀏覽器觀測，不能把單元/整合測試當作已完成長時間 UI 驗收；目標維持 active。


## Iteration 56 — 延伸探索的閱讀位置與焦點

前輪為實際進展（續期根因修正、venv 10 tests 與新版 1 test）。Chrome 執行 Golden patient 網絡分析，呈現 82 個模型解析、8 領域與15關聯。手機點擊腎臟延伸探索後，其標題 top -135.69px 且 focused false，閱讀停留在旧列表。DiseaseNetwork 新增僅延伸探索觸發的標題焦點與 scrollIntoView，圖節點及領域清單保留原選取操作。標題有 100px scroll-margin，避開固定導覽；加入焦點可見樣式與 type=button。

Chrome 修正後點心血管延伸探索，標題 focused true、top190.23px；viewport/scrollWidth 同為416px，沒有水平溢出。兩個網絡 test files 共4項通過，包含詳情標題焦點、圖節點選取同步與既有資料關聯檢查。production build 通過，已恢復桌面視窗。

續期限制：本輪開始時日誌最新新登入為22:47:01，尚未到兩個真實續期週期；未把仍在頁面誤認為連續續期成功。整體目標維持 active。


## Iteration 57 — 網絡圖節點間距

前轮為實際進展：延伸探索焦點修正與手機驗收已完成。桌面 screenshot 察覺節點邊框相交；Chrome DOM 量測證實四對重疊，約9.73px ×3.33px。將節點橢圓半徑由255/230增為280/270，軌道改為相同半徑的 ellipse，仍保留760×650 viewBox。

Chrome 更新後八節點 overlapCount=0，全部在SVG邊界內；手機 overlapCount=0，viewport/scrollWidth均416px。桌面前後 screenshot 已視覺審查，已恢復桌面。production build通過；此次為可逆幾何调整，以真實DOM邊界驗收，未新增鏡像測試。

登入續期仍以伺服器新登入後的續期紀錄為驗收條件，未將短時間仍登入視為兩次續期完成。目標維持 active。


## Iteration 58 — 領域摘要與模型分級一致

前輪有進展：四組圖節點重疊修正並驗收。本輪手機展開心血管19模型清單，發現只有名稱與數值，難以追蹤領域摘要7項需關注。加入卡片既有 levelLabel，high/moderate_high 分級用深紅文字；缺少標籤的關注卡片以需關注為文字備援，未新增任何模型推論或分級。名稱可換行，數值使用tabular-nums。

Chrome 實際19列、7項 attention、分級包含低/中/高/中高/不適用/參考指標；清單clientWidth/scrollWidth均384px，頁面均416px。production build通過，已恢復桌面。這次為既有結果的呈現改善，使用真實結果核對摘要與明細，未加入鏡像樣式測試。登入實際兩次續期驗收仍待紀錄支持。整體目標active。


## Iteration 59 — 累積變更完整回歸

前輪有進展：疾病網絡分級顯示實作及19列/7關注項的手機驗收。此輪針對目前 worktree 執行 frontend npm test，25 files、144 tests 全部通過，exitCode0、stderr空，15.88秒。範圍包含既有登入/SessionManager、病患清單與病歷、健檢输入、FHIR多檔/JSON/XML/API匯入、風險工作空間、疾病網絡、cohort、報告與可讀FHIR摘要測試。此結果證明現有測試涵蓋行为的回歸，不能取代未涵蓋流程的實際驗收。

未完成入口關鍵字搜尋未找到符合項；不是全系統不存在mock的充分證據，需繼續從路由及真實互動驗收。伺服器紀錄目前新登入22:47:01、首次續期22:52:01為200，尚無第二次續期證據。Production build上一輪通過、此輪未修改產品程式。目標active。


## Iteration 60 — 健檢紀錄真實流程驗收

前輪有進展：目前前端25files/144tests完整回歸通過。本輪 Chrome 轉至健檢紀錄，後端呈現963筆总數、每頁25筆。手機 table clientWidth/scrollWidth均383px，頁面均416px。下一頁完成後25rows、table top321.22px，可看到新頁；返回上一頁後點擊 SyntheticGolden 的風險連結，risk-analysis URL patient_id與Golden UUID一致，combobox正確顯示Golden合成識別。已恢復桌面并保留風險頁。未保存其他病患個別資料，未修改產品程式，未宣稱不存在所有未驗收問題。此輪完成的是 read-only實際瀏覽器流程驗證；整體目標active。


## Iteration 61 — 總覽資料品質範圍與標題語意

前輪為進展：健檢紀錄手機分頁與Golden身分接續實際驗收。總覽Chrome桌面截圖顯示h2u_cvd_csv摘要與全局病患/健檢总數並列，可供研究狀態缺少範圍；日期與數字形成h6。Dashboard已為資料狀態加評估範圍，H2U來源識別顯示H2U心血管健檢，未知來源保留其原名稱，缺值仍未提供；日期和重複筆數改p保留視覺大小。

相關7tests及production build通過。首次測試指出缺值標籤回歸，已修正後重跑通過。Chrome手機確認評估範圍文字存在、heading僅h1與兩個h2、viewport/scrollWidth均416px。已恢復桌面。目標active，其他驗收缺口未宣稱完成。


## Iteration 62 — 手機導覽返回與跨頁焦點

前輪進展包括Dashboard範圍/語意修改與兩次實際refresh200（22:52:01、22:57:01）。本輪Chrome手機開啟工作空間導覽，dialog名稱與aria-modal存在，Escape關閉後trigger focused true、aria-expanded false。第一次點病患後曾觀察dialog關閉但仍dashboard；重驗同連結href /patients後成功到patients與病患管理heading，尚不能判定初次未換頁根因，不臆測或改動導航實作。再驗證patients經手機導覽至history成功，heading健檢紀錄，activeElement id main-content、viewport/scrollWidth均416px。已恢復桌面并保留頁面，未修改產品程式。該次異常仍需後續觀察，不能宣稱導航全無問題或全系統完工。目標active。


## Iteration 63 — 連續訊號來源說明可讀性

前輪有進展：手機導覽Escape、跨兩頁與main-content焦點實際驗收，記錄一次未確定未換頁現象。本輪Chrome連續訊號頁載入實際後端資料，非mock：監測、數值摘要、波形覆蓋與AO執行數量各自呈現。發現底部三段固定英文來源限制和重複防禦頁尾。新增已知英文來源說明的中文映射，未知內容仍保留；來源與處理方式標題、報告內容標籤及中文品質摘要頁尾，保留波形儲存、無效資料排除及報告範圍的事實。

production build通過；Chrome手機三段說明完整顯示，viewport/scrollWidth均416px。已恢復桌面。曾嘗試 ContinuousSignalReport.test.jsx，但檔案不存在，命令exit1為no tests found，沒有宣稱此頁測試通過或新增鏡像文案測試。整體目標active。


## Iteration 64 — 連續訊號資料狀態驗證

前輪實際進展：來源說明中文化與手機驗收。本輪新增ContinuousSignalReport.test.jsx，測試資料狀態而非文案/樣式鏡像：available=false不偽裝AO zero或載入波形；失敗可retry成功，未知來源note保留，未提供metric與outputs0分開；unmount取消請求且晚回應不重新顯示結果。3tests通過、stderr空，未修改產品程式。正常資料載入的實際browser證據沿用上一輪，不把mock回應測試稱作本地後端故障演練。整體目標active。


## Iteration 65 — 真實多檔混合格式與衝突回復

後續更正（Iteration75）：當時Golden兩格式的衝突並非來源資料不同，而是XML parser把無小數點decimal解析成float，造成canonical JSON比較誤判。原觀察的拒絕/焦點狀態成立，當時對衝突合理性的推論不成立。

前輪有進展：連續訊號3項狀態測試與第三次實際refresh成功。Chrome選取既有Golden JSON與XML，多檔chooser isMultiple true，選取後兩檔名稱/大小可見。setFiles工具等待約602秒，未自行新增sleep或將等待當成功；後續DOM證實選檔成功。預覽回傳多份資料包含衝突的fullUrl、alert focused、確認匯入disabled，沒有寫入資料庫。這兩份檔案是同一patient/resource的不同格式版本，衝突拒絕不代表混合格式功能全面失敗。

BulkHealthDataImport針對此錯誤補上可操作回復：檢查同資料不同格式版本、保留一份或修正來源網址衝突再預覽。production build通過，ImportHistory既有10tests通過。新錯誤回復文案尚未重新經真實選檔觸發，不能把源碼修改稱為已完成該文字的browser驗收；仍需不同資源混合格式成功預覽證據。目標active。


## Iteration 66 — Golden 混合格式成功路徑

前輪有進展：真實多檔選擇/衝突拒絕與回復指引。依当前Golden44資源建立互補artifact：golden_patient.identity.fhir.json含Patient1，golden_patient.clinical.fhir.xml含43其他資源，均使用原既有合成資料，未改主Golden。

venv執行tests/test_fhir_import_formats.py首先1failed/16passed：既有測試過時35資源/31Observations，實際preview已回44。對照当前fixture44/40後更新三個數量assert，重跑17passed。測試涵蓋JSON病患 + XML其他資源multipart preview 200且Patient無寫入，再import201、createdPatient1、Observation40、零錯誤；另含XML型別、惡意XML、重複/衝突、無效第二檔不寫入、REST來源/分頁/token策略。測試寫入為隔離test DB，未匯入本地運行資料庫。

限制：此為APIClient整合驗證，互補檔案尚未在Chrome完成新一輪選檔成功預覽，前輪setFiles等待602秒為工具層現象；未宣稱已完成所有瀏覽器混合格式驗收。目標active。


## Iteration 67 — Chrome混合JSON/XML成功預覽

前輪進展：互補artifact產生、實際decoder44資源及17後端FHIR tests通過。Chrome先重新預覽原衝突檔，已驗證新版fullUrl回復指引實際顯示。再以filechooser選取identity JSON1.6KB與clinicalXML87.9KB，setFiles有長等待，最後promise complete且頁面檔案清單一致。預覽實際成功：44資源、Patient1 Encounter1 Observation40 Condition1 QuestionnaireResponse1；FHIR預覽heading active，明確尚未寫入系統，確認匯入enabled。沒有點擊寫入，既有Golden已存在，避免重複紀錄干擾。

手機資源摘要clientWidth/scrollWidth均349px，頁面均416px；已恢復桌面并保留預覽頁。此輪驗收成功混合格式瀏覽器路徑与衝突指引，不改產品程式，不宣稱其他來源/所有前端已驗收完。目標active。


## Iteration 68 — 路由標題與404回復

前輪progress：Chrome JSON/XML成功44資源預覽與手機摘要實驗。此輪來源路由盤點發現disease-network缺pageTitles，導致存在頁面標題為找不到頁面；404不分登入狀態返回公開首頁。補登疾病網絡title，PageNotFound以useAuth決定已登入dashboard或未登入home。回復文字與link一致。

RouteExperience8tests通過（已登入/未登入404、疾病網絡title、既有lazy/error/focus/限制路由），production build通過。Chrome未知路徑顯示404；修正後回到工作空間href/dashboard，點擊到臨床資料工作台，再選疾病網絡，heading正確、tab title疾病網絡·AllCare365。保留頁面，整體goal active。


## Iteration 69 — 實際文字對比與裝飾語意

前輪progress：路由標題與404實際回復修正。Chrome疾病網絡入口可見DOM文字的前景/最近不透明背景做sRGB亮度比檢查，低於4.5的小字僅breadcrumb裝飾斜線2.37。連續訊號頁抽樣computed style：輔助說明4.82、mapped6.06、partial5.85、evaluation6.09，均達小字4.5。保留現有品牌顏色；WorkspaceNavigation斜線加入aria-hidden=true，避免讀屏將裝飾當內容。production build通過。

限制：DOM抽樣不是全系統WCAG稽核，未涵蓋SVG fill、透明背景合成、所有hover/focus狀態或所有頁面；沒有以此宣稱完整無障礙符合。目標active。


## Iteration 70 — 手動登出與返回工作流程

前輪progress：對比值查核與breadcrumb装飾語意修正。Chrome連續訊號頁以帳號選單登出，URL返回首頁；browser Back返回原受保護頁後，顯示登入表單而沒有監測報告內容。使用既有已授權帳號重新登入，URL恢復/research-continuous-signals，報告heading及各段結果正確載入。未把帳密寫入文件或log。此輪無產品程式修改，完成實際登出→Back→登入→原工作頁的端到端驗證。仍未宣稱所有頁面/角色、真實15分鐘idle、多browser競爭與完整goal已完成。目標active。


## Iteration 71 — 頁面錯誤回復一致性

前輪progress為手動logout/Back/login回原工作頁實測。本輪RouteErrorBoundary原fallback對所有登入狀態一律返回首頁；改為獨立PageLoadFailure以useAuth分流，已登入/dashboard、未登入/，保留重新載入操作與不暴露rawerror資料。custom fallback保持優先。

RouteExperience9tests通過，包含兩登入狀態的真實render error、正確回復destination、導航後boundary重設、rawerror不呈現，以及既有404/lazy/焦點等測試。production build通過。這次错误觸發在測試環境，沒有在本地運行頁注入故障，不能宣稱實際Chrome異常回復已驗收。整體目標active。


## Iteration 72 — FHIR匯入前身分核對

前輪progress：頁面render failure回復分流與9路由tests。本輪FHIR預覽先前僅有類型/筆數，加入核對病患資料section：normalized FHIR Patient正式姓名優先、識別碼，無識別碼以資源ID顯示；最多前5位，額外筆數明示，避免大量清單佔滿預覽。欄位可換行，預覽失效依原fhirPreview清除而一起移除，不新增寫入。

ImportHistory10tests及production build通過。Chrome貼上Golden合成Patient JSON並預覽成功，region實際顯示Synthetic Golden與SYNTHETIC-GOLDEN識別碼，手機viewport/scrollWidth均416px。停在preview未寫入，已恢復桌面。此實測為單Patient身分區塊，先前44資源混合格式驗收仍成立，但未宣稱所有多病患姓名變體都實測完。目標active。


## Iteration 73 — 累積變更整合回歸

前輪progress：匯入前病患核對UI、10tests、Chrome合成Patient預覽及手機尺寸。因前次完整測試後加入多項路由/資料狀態/預覽修改，本輪重新完整frontend npm test：26files/150tests pass，stderr空。並行venv後端auth lifecycle與FHIR formats：27pass、2既有DRF converter Django6棄用警告，無失敗。未修改產品程式。

artifact frontend_design/regression-20261010-73.json保存時間、命令、結果、七個相關source SHA256與範圍限制。此結果為目前worktree自動回歸證據，不代表所有視覺、角色、醫療模型、無障礙或部署條件皆完成。目標active。


## Iteration 74 — 多病患核對與來源編輯失效

前輪progress：前端150/後端27整合回歸。本輪新增identity preview行为測試，涵蓋official優先、family/given組合、無識別碼resource id、六位截斷明示、來源修改後移除舊身份review且disable匯入；ImportHistory共11tests通過。Chrome六位合成Patient實際預覽成功，顯示前5位與另有1/總6；再修改貼上內容，review count0、確認匯入disabled。沒有寫入運行資料庫，也沒有把真實病患內容保存。此輪只新增測試與實際驗證，沒有產品程式修改。目標active。


## Iteration 75 — 排除相同JSON/XML的錯誤衝突

前輪progress：多病患核對/編輯失效實際驗收。本輪比對原Golden JSON/XML逐欄位，數值等值差異0；但merge以json.dumps比較，XML decimal無小數點仍轉float，0對0.0字串不同造成假fullUrl衝突。新兩個tests先重現失敗；XMLdecimal先保留既有有限值檢查，改json.loads lexical數字解碼，使無小數點保持int、含小數保持float，未改merge的真實衝突判定。Golden兩份合併去重44資源，原資源內容完整。2/2.0差異仍拒絕。全部FHIRformats19tests通過，2既有DRF警告。

官方依據https://hl7.org/fhir/R4/json.html與https://hl7.org/fhir/R4/datatypes.html：decimal精度/尾零對呈現有意義，所以沒有一律將float整數化。限制：既有JSON/float解析仍非任意精度完整實作，2.00尾零及超大數字精度不因這次修正而宣稱完全保留；本輪修正未再Chrome重選原兩檔驗收，已由真實artifact整合測試覆蓋。目標active。


## Iteration 76 — Original Golden multipart preview regression (2026-10-11)

Added an API regression using the unchanged saved Golden JSON and XML files together. The multipart preview returns HTTP 200 and 44 deduplicated resources: Patient 1, Encounter 1, Observation 40, Condition 1, QuestionnaireResponse 1. The test verifies Patient count remains unchanged. FHIR format suite: 20 passed, 2 existing DRF converter deprecation warnings (venv Python; pytest tests/test_fhir_import_formats.py -q --reuse-db).

Chrome initially displayed a stale ERR_CONNECTION_REFUSED page; socket checks showed both ports 3000 and 8000 listening. A fresh Chrome tab loaded the authenticated import page successfully, without changing server configuration. Actual file chooser accepted both original Golden files (89.2 KB JSON, 86.7 KB XML); preview showed 44 resources with the expected five type counts, synthetic patient identity, and “尚未寫入系統”. Focus moved to the preview heading. Did not click confirm import. The live preview is retained. This confirms the iteration 75 parser fix in the running browser workflow, not just a helper test. Earlier iteration 65 interpretation of these same files as a legitimate source conflict was incorrect.


## Iteration 77 — Confirm after reviewing import data (2026-10-11)

Moved the active confirm-import action to the end of both CSV/Excel and FHIR preview panels. Before a preview exists the source panel retains a disabled confirmation control; once preview exists there is a single confirm action after the summary. Existing busy, stale-preview and completed-result guards remain. On small screens the action spans the panel width. This avoids requiring users to scroll back above the preview after reading patient details and resource counts.

Validation: ImportHistory.test.jsx 11 tests passed; npm run build passed. Live Chrome retained the original Golden 44-resource preview during hot reload. At measured CSS viewport width 416, document scroll width also 416; summary bottom 1030.38 and confirm top 1071.41, confirming the action follows the summary. Button height 43.99px, enabled once preview ready. Did not confirm or write data. Temporary viewport override reset and live import page retained. Goal remains active; this is a focused workflow improvement, not full-system completion.


## Iteration 78 — Start a new preview after completed import (2026-10-11)

Both preview handlers now clear the prior import result and expanded error state before requesting a new preview. Previously the previous result remained authoritative: confirmation stayed disabled and heading focus selected the old result despite a fresh successful preview. CSV import handler also checks current preview, busy and completed-result guards, matching the UI and FHIR handler. Added two parameterized tests (FHIR and CSV) covering preview → import complete → fresh preview, confirmation restored, old result removed, preview heading focused, and exactly three requests. ImportHistory suite: 13 passed. Production build passed. Uses mocked API for this state sequence; did not write additional live patient records.


## Iteration 79 — Risk analysis status follows current workflow (2026-10-11)

Live Chrome Golden synthetic patient selection revealed the completion header still instructed selection after a patient had already been selected, and during calculation. Updated shared RiskAnalysis header: selected patient prompts execution; pending calculation shows “正在分析” and current work description; completed evaluation retains resolved/total count. Completion area is a polite atomic status region. Chrome performed actual Golden analysis and reported 82 / 82 resolved, 100%, with one labelled SVG network present; this does not prove clinical validity or all expert workbook coverage. RiskWorkspace + RiskAnalysis tests: 19 passed. Production build passed. Initial attempted .jsx test target did not exist; located authoritative .js and workspace tests and reran successfully. Live network page retained.


## Iteration 80 — Live disease network keyboard and touch verification (2026-10-11)

Read-only Chrome interaction using Golden synthetic analysis. Focused liver SVG node, pressed Tab: focus moved to kidney node and :focus-visible was true. Pressed Space: active SVG node aria-pressed became true, detail heading became 腎臟系統, and exactly matching list control selected. Focus remained on the activated node. This verifies the real SVG keyboard handler rather than inferring accessibility from markup alone.

At temporary 390x844 requested viewport (actual measured CSS width 416), all eight domain list buttons measured 43.99px height. Selecting heart domain showed five extension exploration controls, each 43.99px height. Existing reduced-motion and focus-visible styles inspected. No app code changed: current keyboard and touch behavior passed this focused check. Viewport reset and live disease-network retained. These checks are scoped and do not establish full WCAG compliance.


## Iteration 81 — Full frontend regression after workflow changes (2026-10-11)

Initial npm test: one DesignNavigation patient-role assertion timed out while the lazy workspace navigation fallback remained visible; all other cases passed. Preloaded the real WorkspaceNavigation module in that suite before role tests, retaining actual component, lazy boundary and unchanged role assertions. This removes parallel module transform time from permissions assertions, without increasing global timeouts or mocking the navigation. Full rerun: 26 files, 153 tests passed, no stderr. Evidence and changed-source hashes: artifacts/frontend_design/regression-20261011-81.json. No product behavior changed in this iteration. Full goal completion remains unproven: this automated regression does not substitute for remaining design and domain coverage audits.


## Iteration 82 — Distinguish not-applicable network models (2026-10-11)

Chrome verified bidirectional heart ↔ kidney exploration, shared factors and heading focus. No edge asymmetry found. Added a conditional “不適用” count to selected-domain totals using actual card applicability. This explains resolved-versus-calculated differences without classifying non-applicable models as missing or errors. Golden heart domain rendered 18 calculated, 7 attention, 0 missing, 1 not applicable (19 model cards). Existing network component/helper tests: 4 passed; build passed. Phone measured totals client/scroll width both 384, document client/scroll width both 416. Viewport reset and network retained. No medical inference or applicability rules changed.


## Iteration 83 — Surface source applicability explanation in network (2026-10-11)

For not-applicable model rows, show existing normalized recommendation text below the label; no explanation is invented and no applicability rule changed. Source may provide a generic explanation rather than a model-specific reason. Live Chrome expanded Golden heart models: Reynolds female model displayed 不適用 with the backend text “目前不符合此模型的已驗證適用條件。” Existing two component tests and production build passed. This adds source context to the network without requiring a page switch. Retained live network.


## Iteration 84 — Rendered model-list visual review (2026-10-11)

Captured and inspected two actual Chrome viewport screenshots of Golden heart-domain expanded details, including extension links and model list. Fine separators, left aligned names, right aligned tabular results and red high/moderate-high text establish hierarchy without repeated card surfaces. Not-applicable explanation wraps beneath model label rather than forcing the numeric column to wrap. Source values retain precision and UCUM unit text; no numeric rounding change made during this visual review. Screenshot bytes were emitted in the tool result, not saved as filesystem artifacts, so this is a reviewed live view rather than an exportable screenshot deliverable.

Re-read initial goal acceptance requirements against current iteration history. Comprehensive reference visual comparison and rendered performance/accessibility assessment remain outstanding; passing regression and focused network screenshots do not prove full objective complete. Next phase must cover those broader acceptance gaps instead of continuing only small network refinements. No app code changed in this iteration.


## Iteration 85 — Apple visual comparison and context-aware home actions (2026-10-11)

Viewed official https://www.apple.com/ in Chrome and inspected a real viewport screenshot: compact navigation, a single dominant headline/subline, filled versus outlined paired actions, and substantial separation from the product visual. Interpretation: clarity comes from a limited hierarchy and explicit action priority, not from copying dark backgrounds or pill buttons. Compared a real authenticated AllCare home screenshot: editorial hero, purposeful care continuum diagram and primary action already establish distinct brand hierarchy. Identified actionable mismatch: authenticated homepage still invited login and account registration.

LandingPage now reads auth context; hero and closing actions return authenticated users to /dashboard, while anonymous users retain /login and /register. Added both auth-state cases to DesignNavigation suite: 9 passed. Production build passed. Chrome counted two 返回工作空間 links and verified /dashboard destination; hero click navigated to the dashboard. Screenshots inspected in tool output, not persisted files. Apple reference scope is current homepage viewport only, not a complete Apple product audit. Research tab not retained; original network live tab retained.


## Iteration 86 — Build-resource and rendered semantic evidence (2026-10-11)

Confirmed no Lighthouse/axe/browser automation dependency installed in frontend; did not install dependencies. Inspected production entry asset sizes and gzip bytes (artifact rendered-check-20261011-86.json). This is bundle transfer-size evidence, not LCP/INP/CLS or dev-server performance evidence. No downloaded font declarations/imports found in source.

Live disease-network DOM: zh-Hant, one H1, one main, heading progression 1→2→3→4; no unnamed links or buttons under scoped name checks. Search input labelled. Initial broad input check found one unlabelled input; focused inspection identified MUI select native backing input aria-hidden=true/tabindex=-1, while actual patient combobox is named in AX snapshots. No user-facing label defect found. This check does not implement a complete accessible-name algorithm and does not establish WCAG compliance. No app code changed. Existing live network retained.


## Iteration 87 — Account menu respects reduced-motion transition timing (2026-10-11)

Read current motion rules: global reduced-motion CSS disables animation/transition, account entrance is no-preference only, network node transitions disabled under reduce, and workspace drawer already passes zero transition duration using reducedMotion. Account Menu omitted this JavaScript transition-duration setting. Added the same conditional zero duration to Menu, preventing a residual JS transition wait when animation is suppressed by CSS. Navigation/DesignNavigation suites: 13 passed; production build passed. Tests verify existing menu/navigation lifecycle, not a live OS reduced-motion setting; browser capability does not expose media emulation, and no OS preference changed. Goal remains active.


## Iteration 88 — Role-aware home workflow entrances (2026-10-11)

Read current App routes and searched non-test frontend JS/JSX for mock/TODO/unfinished markers; no matching markers found, which alone does not prove all functions complete. Found concrete role mismatch: home workflow tabs exposed write/research destinations even for authenticated Viewer. Added existing shared role constraints to workflow definitions and filtered authenticated options; anonymous public introduction retains all three. Keyboard navigation now uses available option count rather than hardcoded three, and active selection clamps when available workflows change. No route/backend permission changes.

Added Viewer, Researcher and Manager cases covering available tabs plus End/ArrowRight focus wrapping. DesignNavigation: 12 passed; production build passed. Auth-state homepage action tests remain passing. This role behavior is verified in mocked auth tests, not a live Viewer login (no Viewer credentials created or used). Network live tab retained.


## Iteration 89 — Home auth lifecycle and permission-change regression (2026-10-11)

Inspected useAuth and checkAuthStatus implementation: homepage reads local stored auth state, not an extra profile/API request. Hook subscriptions reuse auth-change, session-logout and storage events and remove listeners on unmount. Added a mounted-page regression: Manager selects research workflow, auth mock changes to Viewer, rerender removes the research destination, selects the remaining clinical workflow, preserves tabpanel aria linkage, and ArrowLeft focus wraps correctly with one option. DesignNavigation suite: 13 passed. This verifies UI response to updated auth state; does not test live server role mutation. No product code changed.


## Iteration 90 — Raycast visual research (2026-10-11)

Visited https://www.raycast.com/ in Chrome; inspected actual hero screenshot and feature-wall screenshot plus visible accessibility tree. Hero uses one dominant proposition and download action, while feature wall pairs action-oriented names with demonstration imagery. Screenshots were tool-output observations, not saved artifacts. Scope is public marketing page, not installed launcher use. Attempted Search files demo click did not yield a verified File Search result; observed demo remained Flight Tracker, so no successful demo-switch claim is made.

Design interpretation for AllCare: task-first action labels and concise destinations are useful; autoplay demonstration, dark gradients and keyboard spectacle are not appropriate substitutes for stable clinical navigation. Existing contextual chart/risk links and manually selected home workflow tabs already implement the relevant interaction principle. No product modification justified from this reference alone. Further Linear/Stripe rendered comparison and broader runtime accessibility/performance evidence remain in scope. Research tab not retained; local network retained.


## Iteration 91 — Linear rendered workspace-reference comparison (2026-10-11)

Visited https://linear.app/ and inspected real hero/product-demo viewport screenshot plus public accessibility tree. Observed stable left navigation, central issue/activity content and separate right properties; muted visual separators, small status accents and clear content headings support a dense workspace. Reference is an embedded public demo, not authenticated real Linear account use. Screenshot inspected in tool output; no exported file.

AllCare interpretation: preserve stable task navigation, patient identity context and separated domain-detail panel; reserve attention color for sourced risk status. Existing Clinical Atlas typography/paper/green language remains distinct. No new product changes justified solely by matching this reference. This fills rendered reference evidence beyond prior text-only homepage inspection, but not a full comparative UX evaluation. Stripe rendered comparison and comprehensive runtime performance/accessibility remain outstanding. Research tab not retained; local network retained.


## Iteration 92 — Stripe rendered information-architecture comparison (2026-10-11)

Chrome https://stripe.com/ initial navigation observation timed out; same established tab re-inspection confirmed it loaded, without restarting. Inspected actual hero screenshot and product-purpose grid screenshot. Hero separates primary Get started from Google signup and distinguishes sign-in/sales in navigation. Public grid titles describe business purposes rather than implementation labels. Interpretation for AllCare: retain care/data/research purpose grouping, explicit workflow actions and FHIR source choices where relevant to clinical users; no gradient or decorative imitation.

Scope limitations: product grid illustration assets were blank in inspected screenshot; Products button did not visibly expand, so menu interaction is unverified. Marketing site comparison does not establish Stripe authenticated-product usability or complete visual research. Screenshots tool-output only. No app changes justified by reference alone; local network retained, research tab not retained. Runtime performance/comprehensive accessibility acceptance remain open.


## Iteration 93 — Expanded network text contrast measurement (2026-10-11)

Read W3C official SC 1.4.3 explanation, then measured actual computed colors for 73 visible HTML detail/model/legend elements on Golden heart network. Solid backgrounds only; complex opacity/images would be skipped (none in selected scope). Unrounded ratio comparisons: muted 4.8163:1, attention 5.8411:1, ink 13.5465:1 against paper rgb(248,249,245). No failures; no color change needed. Artifact contrast-20261011-93.json retains method, source and scope. SVG, icons, focus indicators, hover states and other routes excluded; this is not full WCAG compliance evidence. Initial evaluator lacked parseFloat; used numeric CSS-px conversion and reran successfully. Local network retained.


## Iteration 94 — Improve selected network-edge contrast (2026-10-11)

Consulted official W3C SC 1.4.11 non-text contrast. Live selected observed edge computed stroke rgb(107,140,118), opacity .85 over paper rgb(248,249,245): effective contrast 2.8128:1. Updated active stroke #39715c, observed active opacity .95 and pending active .85. Calculated effective ratios 4.8497:1 observed and 3.9588:1 pending; dash semantics preserved. Chrome confirmed five observed active paths use updated stroke/opacity; pending branch contrast calculated from source but absent in fully populated Golden state. Production build passed. Scope is selected-domain edges only, not all graphic/whole-site WCAG compliance. Inactive background edges remain contextual. Live network retained.


## Iteration 95 — Narrow network viewport verification (2026-10-11)

Requested viewport 320 produced measured CSS width 338; adjusted requested width 300 and measured actual CSS width 316. At 316: document client/scroll both 316, detail client/scroll both 284, four totals client/scroll both 284; zero overflowing model rows. Confirmed model disclosure open before accepting row check. Network diagram client 284 / scroll 600, contained in the intended local scrolling area. Actual narrow screenshot showed model titles wrap, values retained separate alignment and applicability explanation readable. Screenshot emitted in tool output only. No app code change needed. Viewport reset and live network retained. This is responsive narrow-layout evidence, not actual 200% browser zoom/text-resize testing.


## Iteration 96 — Bound DOM-test concurrency and verify latest frontend (2026-10-11)

Initial full regression: 158 pass / 1 HealthDataInput test timeout at 5 seconds; no assertion mismatch, heavy suite took 11.6 seconds. Diagnostic full run with maxWorkers=4: 159 passed (26 files), preserving assertions and 5s timeout. Set test maxWorkers:4 in vite.config.js; default npm test rerun: 159 passed / 26 files in 22.84s, no stderr. Evidence supports resource contention, not a proven product defect. No production behavior or test isolation changes. Latest frontend workflow, auth-state, navigation and network tests pass. Remaining goal acceptance is broader than this automated suite.


## Iteration 97 — Narrow patient chart and return after sign-in (2026-10-11)

Opened existing synthetic Golden patient chart in Chrome. Prior session had ended after inactivity; authorized sign-in returned automatically to the originally requested chart. This observation does not establish the exact 15-minute expiry trigger. At measured CSS width 316, document client/scroll widths were both 316, no overflowing main elements, six tabs each approximately 92.11 x 43.99px arranged in three columns, and chart action links approximately 43.99px high. Selected Documents tab retained selected/focus semantics and chart-panel-documents linkage; panel showed zero records and truthful empty state. Narrow screenshot visually confirmed readable identity, actions, tabs and empty panel; screenshot emitted in tool output only. No application source change needed. Temporary viewport reset and chart retained as live deliverable. Latest full frontend regression remains iteration 96: 159 tests / 26 files passed.


## Iteration 98 — Live keyboard patient-chart navigation (2026-10-11)

Reviewed current PatientChart source and five existing tests, then exercised actual Chrome chart with synthetic Golden data. ArrowRight on final Documents tab wrapped focus to Summary while Documents stayed selected (manual activation); focus-visible true. Enter selected Summary with corresponding chart-panel-summary. Tab entered the focusable summary panel, computed outline rgb(36,87,71) solid 1.48148px; exactly one tab had tabIndex 0, other five -1. Clicking Documents record-index action selected Documents and transferred focus to chart-tab-documents, with matching chart-panel-documents. No source changes or repeat regression needed: browser evidence verifies existing keyboard and index-focus behavior. Live chart retained. This scope is patient-chart tabs, not complete application accessibility certification.


## Iteration 99 — Preserve registry search and page across chart navigation (2026-10-11)

Live Chrome reproduced loss of synthetic Golden search after chart return. PatientManagement now initializes validated search/page from navigation state and replaces current history state as they change; both chart links carry that context. PatientChart return link passes it back. Search is absent from URL and no local/session storage added. Added two actual-router integration tests using real chart component: explicit chart return and history back both restore search and page 2 / corresponding API query. PatientManagement + PatientChart: 13 tests passed; production build passed. Actual Chrome verified both return paths retain synthetic Golden search; filtered one-row screenshot reviewed, emitted in tool output only. Page-2 live journey not attempted against unrelated patient data; covered by integration tests. Live filtered registry retained. No scroll-position restoration claimed.


## Iteration 100 — Refine new-patient form language and focus (2026-10-11)

Reviewed backend serializer/model and PatientDataValidator: supported M/F/O/U. Existing form exposed raw F/M/U and omitted O. Changed labels to 女/男/其他/未知, preserving code values and separate blank 未填寫. Separated dialog title from descriptive text with aria-describedby. Added first-field autoFocus and transition onEntered focus via inputRef; live immediate AX initially showed dialog focus during transition, subsequent DOM and screenshot confirmed focused INPUT / 名 after transition. Extended existing error test to verify exact dialog name, accessible description, initial input focus, Other selection and submitted sex O. Eight registry tests passed before final transition focus addition; final rerun and build results returned with this documentation write. Chrome verified all five options and final input focus; reviewed empty form screenshot. No new patient submitted. One close/reopen batch failed during transition; fresh state and sequential actions succeeded. No full-site accessibility claim.


## Iteration 101 — Keep new-patient actions visible on narrow screens (2026-10-11)

Live narrow dialog initially scrolled the entire form: actions bottom 1029px outside measured viewport height 822px. Nested form prevented DialogContent flex scrolling. Set form flex column / minHeight 0 / overflow hidden and paper overflow hidden; content now scrolls independently. Chrome after fix: actual CSS viewport 333 x 822, dialog client/scroll width 269, zero overflowing controls, content height 633 / scroll height 880, actions top 738 / bottom 782 inside viewport. Screenshot confirmed visible footer; focusing last state field then Tab reached Cancel with content scrollTop 247.4, verifying bottom-field access. Added useMediaQuery and zero Dialog transition duration for reduced motion, matching existing navigation pattern; no live OS preference emulation claimed. Related registry tests and build rerun, both exit 0. No patient submitted; temporary viewport reset and registry retained.


## Iteration 102 — Preserve search focus when clearing registry filters (2026-10-11)

Actual synthetic no-match search rendered accurate zero-result state. Clicking existing empty-state Clear Search removed the button and left focus on BODY. Added shared clearSearch handler and search inputRef: both empty-state clear and new 44px input-end clear control restore input focus and reset page. Clear control accessible name 清除搜尋條件 distinguishes it from empty-state 清除搜尋. Chrome verified both paths: empty input and focusMatchesSearch true. Restored Golden-only filtered list for handoff. Existing eight registry tests and production build passed. No extra implementation-mirroring test added for this reversible UI refinement. No patient data modified.


## Iteration 103 — Full frontend regression after registry improvements (2026-10-11)

Default npm test passed 161 tests across 26 files in 23.64s, stderr empty. Covers recent real-router search/page restoration tests and existing auth lifecycle, role navigation, import preview/history, risk workspace, research state handling and patient chart suites. Saved exact sanitized command output and SHA-256 of changed registry/chart/test files plus Vite test configuration in artifacts/frontend_design/regression-20261011-103.json. Latest production build passed iteration 102 with current product sources. Browser current registry has one main, one H1 病患管理 and exactly one named inline clear control; live tab retained. These checks confirm automated regressions and current DOM structure, not clinical validity, backend completeness, full accessibility compliance or measured runtime performance. Full design objective remains active.


## Iteration 104 — Intake section focus and single-flight saving (2026-10-11)

Live Golden chart-to-intake route confirmed exact locked patient selection and identity with MRN/age. Before fix, section link scrolled to Labs but activeElement became BODY. Added tabIndex -1 to four section headings: native fragment navigation now focuses Vitals H2, and next Tab enters numeric input in that section (Chrome verified). Reviewed submit handler: state-only saving disabled UI but no synchronous guard for repeated submit events. Added saveLock ref, acquired only after valid patient/date check, released finally. Meaningful pending-submit test fires two synchronous submits, verifies one POST, frozen fields, retained decimal after failure and explicit retry succeeds as a second call. Five intake tests passed; production build passed. No live screening submitted. Browser live form retained. This improves client single-flight behavior; no cross-tab/server idempotency guarantee claimed.


## Iteration 105 — Narrow intake and accessible measurement units (2026-10-11)

Chrome at actual CSS width 316: document client/scroll widths 316, no overflowing form controls. Reviewed patient section and lab section screenshots; selected-patient select visually truncates long identity, separate sourced identity alert remains available. Lab control width 246.83 / FPG input width 196.16 with mg/dL suffix; no unit/input overlap. Section anchor focus retained on intake-labs. Numeric units were visual only; added field-specific unit IDs and aria-describedby to numeric inputs. Existing decimal submission test now asserts accessible descriptions kg and mg/dL; all five intake tests passed and production build passed. Live DOM confirms FPG description intake-unit-fasting_glucose resolves mg/dL. No actual screen-reader speech session claimed; no screening submitted. Viewport reset and live intake retained.


## Iteration 106 — Confirm identity before entering screening details (2026-10-11)

Moved existing sourced selected-patient identity alert from after Location to immediately after patient-selection status, before selector/date/encounter fields. Added overflowWrap anywhere for long identifiers. Chrome actual CSS width 316: document client/scroll both 316, identity message client/scroll both 179, identity top 312.87 before selector top 419.66. Screenshot confirms full synthetic name/MRN/age wrap without truncation in identity alert; select still truncates its redundant long option. Existing five intake tests and production build passed. No clinical data/selection logic changed, no screening submitted. Viewport reset and live form retained.


## Iteration 107 — Editorial patient identity instead of notification styling (2026-10-11)

Replaced selected-patient blue info Alert with a named group 本次健檢病患: prominent sourced name, semantic MRN/age definition list, restrained separators and existing brand tokens. Missing values remain explicit. Scoped intake CSS uses row layout at wide widths, stacked name and two-column details below 700px. Chrome actual width 316: document client/scroll 316; identity client/scroll 247, MRN 197, age 30. Narrow screenshot confirms complete MRN wraps, age stays separate, name hierarchy clear. After reset, desktop identity flex direction row, client/scroll 799. Five existing intake tests and production build passed. No clinical calculation, patient-selection or payload change. Live form retained.


## Iteration 108 — Increase intake section touch targets (2026-10-11)

Measured four live section links approximately 63.97 x 27.97px versus Save button 43.99px high. Increased section links min-height to 44px with inline-flex alignment, preserving restrained text navigation. Chrome actual CSS width 316: document client/scroll widths 316, all four links 63.97 x 43.99px, three first-row / one second-row, no overflow. Clicking History still focuses intake-history H2. Production build passed; no duplicated low-impact CSS test added or unrelated regression repeated. 44px is this product target choice, not a claim the prior 28px failed WCAG minimum. Viewport reset and live form retained.


## Iteration 109 — Put screening save outcome next to the action (2026-10-11)

Reviewed long form: save outcome and post-save analysis link were at page heading, away from bottom Save action. Moved feedback and analysis link directly after fieldset/save area; focus feedback when message arrives, successful outcome role status and errors alert. Form now named 新增健檢資料 and exposes aria-busy. Extended existing success/failure tests to assert actual focused result regions; initial new status query was ambiguous with existing patient status, corrected to locate exact saved-message status ancestor rather than weaken focus assertion. Five tests and production build passed. Browser verified named form aria-busy false; no live save performed, so success/error geometry is not claimed browser-verified. Existing synthetic form retained.


## Iteration 110 — Distinguish patient-load failure from zero search results (2026-10-11)

Current source showed patientLoadError alert while status caption still stated 目前沒有符合的病患. Extended existing failed-fetch test first: red proved misleading empty-status rendered after failed request. Updated status priority loading > load error 病患資料尚未載入 > successful selection/results/empty, and disabled empty selector on load failure while retry remains available. Five intake tests and production build passed, including successful actual-empty search behavior and wrong-patient protection. Failure state verified through component API test, not forced in live service/browser. No patient/clinical data modified; live intake retained.


## Iteration 111 — Full regression after intake workflow refinements (2026-10-11)

Default npm test passed 162 tests / 26 files in 25.62s, stderr empty. Exact output and hashes of current intake/test/global CSS, registry/chart and Vite config saved in artifacts/frontend_design/regression-20261011-111.json. Current production build passed iteration 110. Chrome confirmed one named patient identity group, four focusable section-heading targets and 27 numeric inputs with unit descriptions; live form retained. Regression is evidence for covered frontend behavior, not full design-goal completion or runtime/clinical validation. Next broader visual review can proceed without repeating this suite absent further changes or concerns.


## Iteration 112 — Live narrow screening-history review (2026-10-11)

Reviewed current HistoryRecords source, request cancellation/error/empty handling and narrow CSS. Actual Chrome CSS width 316: document client/scroll 316, zero overflowing history rows; heading refresh/new-screening controls approximately 44px high. All 25 row analysis actions and both pagination buttons approximately 44px high, first-page Previous disabled/Next enabled. Explicit table role, four columnheader roles and aria-busy false preserved in live DOM despite narrow grid row styling. Cropped header screenshot visually reviewed; no patient identifiers saved in artifact. No code change required for this inspected scope. Viewport reset and history retained. No historical-prediction semantics or complete application accessibility claims inferred; current analysis actions route by patient rather than screening ID.


## Iteration 113 — Clarify history links open patient-level risk analysis (2026-10-11)

Checked current risk route/API/service/repository: UI posts patient_id, service builds patient snapshot; repository selection policy latest_valid_at_or_before_evaluation_per_field. History rows do not send screening ID or evaluation date. Updated row action visible label 病患風險, named action 開啟 [name] 的病患風險分析, column 病患分析 and intro clarifying integration of currently valid patient data. Updated existing link assertion preserving patient-specific href. Thirteen import/history tests and production build passed. Chrome confirmed updated intro/action texts. No selection/calculation change, no analysis executed during this review. Live history retained.


## Iteration 114 — Add missing units to similar-cohort numeric conditions (2026-10-11)

Reviewed current ResearchCohorts source and live DOM: numeric similarity profile fields had no unit adornments, unlike basic cohort conditions. Added units sourced from existing numericFilters metadata, mapping delta fields to base measure units; result limit 筆. Added field-specific aria-describedby references. No algorithm/values/payload change. Existing six research-state tests and production build passed. Chrome actual CSS width 316: document client/scroll 316, all nine described fields client/scroll 235; resolved units mmHg, %, mg/dL, kg/m2 and 筆 as expected. No cohort query executed this turn. Viewport reset and live research workspace retained. Age field remains plainly labelled 年齡, no additional unit claim.


## Iteration 115 — Place advanced-cohort disclosure before its fields (2026-10-11)

Narrow screenshot reviewed current research hierarchy. Live advanced group exposed 14 numeric fields with zero overflowing controls at actual CSS width 316. Source order placed inserted advanced fields before disclosure button, so forward keyboard navigation after expansion skipped the new controls. Moved disclosure directly before advanced group; query/clear remain below all criteria. Six research-state tests and production build passed. Chrome Tab from expanded disclosure focused first advanced numeric input 舒張壓 DBP 下限; document client/scroll 316. Initial attempt to click 更多條件 after HMR failed because expanded state remained true; inspected actual state and used current 收合條件 control. Viewport reset and research workspace retained. No query or data modification.


## Iteration 116 — Live cohort query and keyboard-scrolling results (2026-10-11)

Executed current local cohort query; actual result heading received focus, summary and statistics table rendered, no error alerts, displayed privacy state 未遮蔽. No individual records exported. At actual CSS width 316 document client/scroll 316; statistics container client 283 / scroll 414 with overflowX auto. Added named focusable region 族群指標摘要捲動區 to table container. Chrome ArrowRight focused region and advanced scrollLeft to 44.44; six research-state tests and build passed. Narrow screenshot reviewed: focus scrolled into body rows and header was outside current viewport, leaving a further result-reading refinement to inspect. This is not a privacy audit or full research correctness claim. Viewport reset and research result retained.


## Iteration 117 — Bound cohort table height and retain header semantics (2026-10-11)

Reviewed current .cohort-table rule and StatsTable, then added Table stickyHeader and container overflow auto / max-height min(70vh,640px). Production build passed. Chrome actual CSS width 316: document client/scroll 316; container clientHeight 557 / scrollHeight 728. ArrowDown changed internal scrollTop 44.44; computed th position sticky, container top 168.39 / header top 169.13. Home returned internal scrollTop 0. Screenshot views did not agree with measured viewport placement (body rows at narrow size, page top after reset), so visual proof that header remains in captured viewport is still unresolved; DOM sticky position evidence alone is recorded without full visual acceptance claim. Viewport reset and research result retained. No extra query, no clinical data modified.


## Iteration 118 — Reconcile table screenshot scope (2026-10-11)

Read live AX state (existing result/region remained present). Used documented native browser interaction and text positioning to obtain actual normal-window screenshot with entire six-column header and all statistic rows visible. This closes normal-window table visual placement uncertainty from iteration 117, but does not alone prove sticky behavior in narrow screenshots. Subsequent narrow captures produced mismatched positions and transient capture timeouts; same tab retained, no repeated query/restart. Reset viewport successfully; live DOM confirms table present and all th computed sticky. Read browser-troubleshooting documentation; no unrelated automation used. Narrow sticky screenshot acceptance remains open; authoritative DOM behavior from iteration 117 still applies. No source changes or repeated tests this turn. Research result retained.


## Iteration 119 — Distinguish pending and failed research summaries (2026-10-11)

Narrow sticky visual review revalidated on same live table/handle; direct columnheader click succeeded but capture timed out, so narrow screenshot acceptance remains open. Independent source review found pending/failed cohort and similarity metrics still said 未執行. Added per-query placeholders 查詢中… / 比對中… and 查詢未完成 / 比對未完成; successful result missing dataset now 未提供. Extended existing deferred/range/zero-similarity tests to assert pending and failed summary states. Six tests and build passed, then extended tests rerun all six passed. No query algorithm/payload changes, no new query executed. Viewport reset and research page retained.


## Iteration 120 — Full frontend regression after research-page changes (2026-10-11)

Default npm test passed 162 tests / 26 files in 20.11s, stderr empty. Command output and current source hashes saved in artifacts/frontend_design/regression-20261011-120.json. Production build with current product source passed iteration 119. Browser current research result still present with named scroll region and expanded disclosure. No repeat query or source change. Narrow sticky screenshot acceptance remains unresolved and is not covered by jsdom tests; broader design completion is unproven. Live research page retained.


## Iteration 122 — readable cohort table columns

- Inspected the live queried cohort table in Chrome. At a 444px viewport, the sample-count header wrapped into three lines; its column measured 55.29px.
- Scoped nowrap to cohort table cells, retaining tabular numerals and the existing keyboard-accessible internal scroll region. No query or statistical logic changed.
- Live screenshot now shows complete single-line sample-count and minimum-value headings, intact SBP/DBP labels and decimal statistics. DOM reports internal scroll width 495px versus container 377px; document width 427px within viewport 444px, so the table does not expand the page. All six headers retain sticky positioning.
- The subsequent ArrowDown screenshot showed the page top rather than the table. Scrolled-header visual acceptance remains unproven; do not count DOM sticky positioning as that acceptance. Viewport override remains reset and the requested local tab is retained.
- Production build passed, 735 modules; output recorded in artifacts/frontend_design/build-20261011-122.json. No additional tests added for this scoped reversible CSS change.


## Iteration 123 — cohort unit descriptions and scrolled-header evidence

- Inspected current ResearchCohorts.jsx; basic and advanced cohort units were visually present without input descriptions, unlike the similar-profile inputs. Linked the 3 basic and 14 advanced unit spans via aria-describedby, with distinct ids per feature and bound. Query payload and statistics are unchanged.
- Live Chrome DOM verified all 17 descriptions resolve to the correct visible unit. This proves markup associations, not a screen-reader speech trial.
- Clicking the visible sample-count header and taking a screenshot yielded the previously missing scrolled-table evidence: SBP had moved out of view, DBP/BMI/FPG and later rows were visible, and the full single-line header remained fixed at the top of the scroll region. Screenshot was displayed in the tool output; no local screenshot file is claimed.
- All 6 existing ResearchDataStates tests and the production build passed; command output preserved in artifacts/frontend_design/checks-20261011-123.json.


## Iteration 124 — separate patient intake drafts

- Current source review found that the general-entry selector changed only patient id, retaining measurements, questionnaire answers, saved success feedback and the prior analysis link. Added an integration regression using two synthetic patients. After correcting the test to wait for actual loaded status (MUI aria-disabled is not detected by toBeEnabled), it failed on retained weight 62.5.
- Selecting a different patient now resets the draft and clears saved feedback/analysis destination. Searching from an existing selection also passes through this reset; choosing the same patient preserves the draft. A selector description states that changing patient clears unsaved data.
- All six intake tests passed, including saved-then-switch scenario and payload isolation. Production build passed; outputs in artifacts/frontend_design/checks-20261011-124.json.
- Live Chrome showed the general entry hint below the selector and verified aria-describedby resolves to its id; screenshot displayed in tool output. No actual screening was submitted. Browser cross-patient save execution is not claimed. Pending save across a URL patient-context change still requires a separate audit.


## Iteration 125 — ignore old-context intake save responses

- Inspected current intake save lock and patient-id route effect. Two delayed-response regression cases first failed because a new patient context remained locked by the previous pending save.
- Added a context generation ref invalidated by route-effect cleanup (including unmount). Each save captures its generation; old success/error/finally callbacks cannot alter the new draft, feedback, analysis destination or current save lock. The new route resets the UI save lock. This does not cancel an already-sent backend write.
- Both late-success and late-failure tests additionally start a new save before resolving the old one, proving old finally cannot unlock it; the new payload and analysis link remain scoped to patient 74. All 8 intake tests passed.
- Initial full regression found an unrelated FHIR preview focus assertion racing its React effect; 13 isolated import tests passed. Changed that one assertion to waitFor the same expected focus, preserving behavior requirements. Full regression then passed all 165 tests in 26 files; production build passed. Logs are in checks-20261011-125.json and regression-20261011-125.json under artifacts/frontend_design.
- Existing local Chrome intake tab remains visible and retained. No live screening submission or real medical write used to simulate the delayed request.


## Iteration 126 — quiet derived measurement

- Revalidated current worktree on 2026-10-13: patient-switch reset and save context generation guards remain in source. Existing user changes were inspected and preserved.
- Earlier live narrow intake inspection measured no overflowing form controls, four approximately 44px-high section links, and correctly focused the labs heading via its native fragment link. Its viewport screenshot timed out; these measurements do not prove visual acceptance.
- Replaced the BMI informational Alert with a compact derived measurement row using semantic output, an accessible name and an explicit source note. The value and calculation remain unchanged; the row uses the existing atlas typography/colors and wraps at narrow widths. This keeps alert styling for actual notices and save feedback.
- Eight intake integration tests and production build passed; output in artifacts/frontend_design/checks-20261013-126.json. No new test added for this reversible presentation change.
- Current tool inventory does not expose the Chrome/computer-use interface. Fresh browser screenshot and viewport cleanup could not be performed this turn, and no live-render acceptance is claimed for the new BMI row. This limits browser evidence but does not prevent source/engineering progress.


## Iteration 127 — navigation follows work purpose

- Inspected current WorkspaceNavigation.jsx and its existing navigation tests. Sidebar grouping used the presence of allowedRoles, placing clinical-write intake/import links under Research.
- Added explicit research group metadata only to cohort/reports/continuous signals. Clinical entry/import now belong to Care and Data, while role visibility remains controlled by the unchanged allowedRoles checks. Both groups have accessible names via role=group.
- Seventeen existing navigation tests passed, including role visibility, active route, modal focus restoration and desktop-boundary handling. Production build exit code 0. Logs in artifacts/frontend_design/checks-20261013-127.json.
- Current tool inventory still has no browser control interface. No fresh live screenshot or visual acceptance claimed for the changed sidebar. The full product goal remains incomplete.


## Iteration 128 — auth feedback focus

- Current login and registration source already has appropriate username/password/email/name autocomplete metadata. Error feedback lacked a focus target and registration removed the form without focusing confirmation.
- Login now focuses failed-request feedback after fields unlock; MFA informational feedback retains OTP focus. Registration errors focus their explanation and successful registration focuses the confirmation heading. Success feedback uses status instead of alert.
- Existing login-failure and registration-success tests now verify focus. Added a mismatch case verifying focus, retained editable values, and no API submission. All eight auth integration tests and production build passed; outputs in artifacts/frontend_design/checks-20261013-128.json.
- No browser control tool is available this turn; no new Chrome rendering or screen-reader speech validation claimed.


## Iteration 129 — one pending authentication submission

- Source inspection found login relied on React submitting state, while enrollment/verification lacked entry guards. A batched two-submit test failed with two login API calls.
- Added one synchronous ref lock shared by login, MFA enrollment and MFA verification. Each path releases it in finally; visible disabled/busy behavior remains. Added a delayed enrollment/verification regression proving only one request per pending phase and recovery after failed verification.
- Nine authentication integration tests and production build passed; before/after logs in artifacts/frontend_design/checks-20261013-129.json. This fixes duplicate requests and is not evidence for precise 15-minute session expiry.
- Browser tool remains unavailable; no new browser interaction or screenshot claimed.


## Iteration 130 — single pending account application

- Inspected current Register.jsx. Its submitting state allowed two synchronous batched submissions before rerender. A deferred-response integration test reproduced two API calls.
- Added a synchronous submission ref lock after password validation and released it in finally. Existing submitted confirmation still prevents another application. Regression also proves failure retains editable credentials, focuses feedback and permits a successful retry without automatically signing in.
- Full regression passed 168 tests across 26 files; production build passed. Before/after output recorded in artifacts/frontend_design/checks-20261013-130.json. No live account creation performed. Browser visual/interaction validation remains outstanding due to current tool availability.


## Iteration 131 — keyboard access to the network scroll region

- Inspected current DiseaseNetwork.jsx/css. Mobile graph already has a contained horizontal scroll area and alternative domain controls, but the scroll container lacked a keyboard focus stop and accessible region name.
- Added role=region, descriptive accessible name and tabIndex=0 to the existing graph container. Updated mobile guidance to include left/right arrow scrolling. Preserved SVG node keyboard activation and all domain/data semantics.
- Existing disease network tests and production build passed; outputs in artifacts/frontend_design/checks-20261013-131.json. No tests added for this reversible markup change. Browser arrow-scroll behavior and current rendered layout remain unverified because browser tools are unavailable this turn.


## Iteration 132 — domain controls identify their detail target

- Current disease-network integration tests already verify Enter selection, connection navigation and detail-heading focus. Connections lead to other domains, so no unsupported same-domain failure is asserted.
- Added a per-instance React useId for the detail aside and linked SVG node buttons, alternative domain buttons, and extension-exploration buttons through aria-controls. Existing pressed state and focus behavior are preserved.
- Both existing network tests and production build passed; outputs in artifacts/frontend_design/checks-20261013-132.json. No new test added for this reversible semantic annotation. Browser rendering and assistive-technology interaction remain unverified this turn.


## Iteration 133 — research request/review feedback

- Inspected report-page source and all current report tests. Empty queues and list errors already differ; no new failure claimed there. Mutation feedback lacked focus handling and the request form lacked an accessible name.
- Named the report request form, linked SBP/HbA1c units to inputs, focused request feedback after mutation completion and dialog errors after fields unlock. Success feedback uses status.
- Extended existing failure/recovery assertions for focus and accessible description; all ten report tests and production build passed. Logs in artifacts/frontend_design/checks-20261013-133.json.
- New live-render/focus behavior remains unverified in Chrome due to current browser tool availability. No real report application or approval executed.


## Iteration 134 — report dialog motion preference

- Inspected current report dialog declarations; unlike workspace menu and patient dialog, neither report approval nor artifact preview set a JS transition duration for reduced motion. CSS-wide reductions do not control MUI transition lifecycle timing.
- Both dialogs now read prefers-reduced-motion through MUI useMediaQuery and use zero transition duration when enabled. Default motion and artifact focus-restoration callback remain intact.
- Ten existing report tests and production build passed. Logs in artifacts/frontend_design/checks-20261013-134.json. No mirror test added for this reversible preference mapping. Live reduced-motion animation and focus restoration still await browser validation.


## Iteration 135 — defer disease network assets

- Inspected App.jsx, Navigation.jsx and build config: routes and authenticated navigation are already lazy. RiskAnalysis still eagerly imported DiseaseNetwork and its stylesheet for ordinary model-list use.
- Moved DiseaseNetwork to React.lazy with a local Suspense status around its network-only output. Patient controls and completed analysis remain outside this boundary.
- Build now emits DiseaseNetwork JS (8.41kB / gzip 3.29kB) and CSS (6.46kB / gzip 1.63kB) separately. RiskAnalysis chunk moved from prior 38.59kB / gzip 14.35kB to 30.84kB / gzip 12.04kB. This is build dependency evidence, not a measured runtime latency/Core Web Vitals improvement.
- Seven existing risk-workspace/network tests and production build passed; outputs in artifacts/frontend_design/checks-20261013-135.json. Existing tests cover risk state and direct graph behavior, not the actual lazy-loading network route handoff. That branch still requires integration/browser acceptance.


## Iteration 136 — real lazy network integration

- Inspected current RiskWorkspace tests: all prior scenarios used model-list mode. Added a synthetic network-mode integration test with the real lazy DiseaseNetwork module, real patient selector resolution, mocked backend analysis and two connected clinical systems.
- Test verifies loaded patient identity, two graph node controls, Enter selection/pressed state, aria-controls linking to detail, the patient-scoped model-results link and the focusable graph scroll region. No graph or module loader mock is used.
- All six risk-workspace tests passed; output in artifacts/frontend_design/checks-20261013-136.json. Product source unchanged this turn; prior production build remains relevant. This closes automated module/data handoff coverage, but not live browser loading timing or rendering evidence.


## Iteration 137 — current production brand asset audit

- Inspected Brand.jsx, LandingPage.jsx, index.html, index.css and manifest. Brand SVG is decorative with visible brand text; landing process diagram has its own image description. HTML and manifest both declare zh-Hant.
- Checked all current dist/index.html script/link references and manifest icons against actual build files, and read PNG dimensions from their headers. Results recorded in artifacts/frontend_design/brand-assets-20261013-137.json; missing references: 0.
- No product change was warranted by these checks; no build rerun or tests added. These are current artifact/path/metadata checks, not fresh visual acceptance, font-rendering validation, installability or runtime loading performance. Next work should focus on unverified browser behavior rather than replacing already consistent brand assets.


## Iteration 138 — auditable production dependency manifest

- Reinspected current Vite config and prior evidence. Added build.manifest=true per official Vite build options (https://vite.dev/config/build-options.html#build-manifest), generating dist/.vite/manifest.json separately from the public installation manifest.
- Production build passed. Traversed manifest static imports from index.html: six initial chunks; DiseaseNetwork is absent from this closure and is a dynamic import of RiskAnalysis. All manifest-referenced chunks, CSS and assets exist.
- Output/dependency evidence preserved in artifacts/frontend_design/build-dependencies-20261013-138.json. No tests added for the reversible build-output option. Runtime caching/loading timings and Core Web Vitals remain unmeasured, and broader browser acceptance is still outstanding.


## Iteration 139 — contain graph loading/render failure

- Current network lazy subtree previously depended on the full-route error boundary. Added a patient-keyed local RouteErrorBoundary around only the network Suspense subtree. Failure preserves patient controls and analysis state, with a patient-scoped model-list recovery link.
- Added a graph-throw integration test, separate from the real-module handoff test, verifying retained patient, enabled re-analysis and correct recovery link without raw exception text. Initial assertion expected the pre-analysis button label; corrected to actual completed-state Reanalyze label.
- Seven focused integration tests and production build passed, outputs in artifacts/frontend_design/checks-20261013-139.json. Browser download-failure behavior remains unverified; test covers render failure handled by the same local boundary.


## Iteration 140 — preserve analysis across paired views

- RouteExperience keyed both Suspense and error boundary by full pathname, remounting risk workspace during network/model view changes. Shared a lifecycle key for these two paths only; page title, focus and scroll still follow actual pathname. Other routes remain independently keyed.
- Added real-router integration spanning both views with the real lazy graph: completed result survives return to model list, patient retained, analysis API called once, titles update and main focus moves. Test initial ambiguity from patient name displayed in both identity and graph was corrected by scoping to graph; jsdom scrollTo is mocked.
- Sixteen focused route/risk tests and production build passed; outputs in artifacts/frontend_design/checks-20261013-140.json. Live browser acceptance remains outstanding.


## Iteration 141 — preserve a locally selected patient across views

- Extended paired-view test to select patient 74 within a URL initially scoped to patient 73, then analyze and switch. It failed because URL synchronization cleared completed data.
- Route patient synchronization now preserves state when the requested id matches the currently selected patient; genuine context changes continue to abort/clear old analysis. The integration test waits for the selected identity to finish reloading before checking it.
- Seven risk-workspace tests and production build passed; before/after output in artifacts/frontend_design/checks-20261013-141.json. No medical data persisted, and live browser acceptance remains outstanding.


## Iteration 142 — retain pending analysis across same-patient view changes

- Audited the previous route synchronization guard: its effect cleanup still aborted a pending request when URL synchronized to the locally selected patient. Moved unmount abortion into its own effect; genuine requested-patient changes still abort and reset.
- Added delayed-response paired-route test proving same-patient view change does not abort, renders the resulting real graph and unlocks re-analysis with one API call. Eight risk-workspace tests passed; build exit 0. Outputs in artifacts/frontend_design/checks-20261013-142.json. Live browser evidence remains outstanding.


## Iteration 143 — integrated regression after workspace lifecycle changes

- Rechecked current tool inventory: browser/computer UI tools remain unavailable. Ran the default full frontend regression after paired-view retention, pending-request lifecycle changes, local graph failure recovery and lazy graph loading.
- All 172 tests in 27 files passed in 26.95 seconds with empty stderr. Logs and SHA-256 fingerprints of 74 current source/config/package files preserved in artifacts/frontend_design/regression-20261013-143.json.
- No source change or redundant build this turn; previous build succeeded on unchanged product code. This verifies current automated scope, not full visual accessibility, performance or production-grade acceptance. Outstanding browser evidence is still required for the actual goal.


## Iteration 144 — explicit missing signal summaries

- Inspected current signal report and tests. Available reports with empty/omitted waveform_signals or numeric_signals rendered blank content grids, despite having a distinct overall unavailable state.
- Added concise missing-summary messages to each grid while preserving absent-versus-zero metrics and existing retry/abort behavior. Extended the existing sparse successful response/retry case to verify both messages.
- Three signal-report tests and production build passed; logs in artifacts/frontend_design/checks-20261013-144.json. No fabricated signal data introduced. Live rendering remains unverified this turn.


## Iteration 145 — missing coverage is not zero

- Current coverage rendering coerced null/empty/nonfinite coverage to a zero-width bar. Replaced this with explicit unavailable text; measured coverage in 0–100 uses a named meter with numeric and textual values. Actual zero remains 0%.
- Four signal tests and production build passed; output in artifacts/frontend_design/checks-20261013-145.json. Test covers zero versus missing; browser layout and screen-reader speech remain unverified. An incorrect source replacement produced a parse failure; restored the original surrounding source and replaced the exact map block. Final verification passed.


## Iteration 146 — truthful cohort coverage meters

- Inspected current cohort coverage logic: present-but-null coverage passed its filter and rendered as 0%. Kept measured zeros, rendered unavailable coverage explicitly, and added named meter semantics for finite 0–1 ratios. Percent fill now reflects the measured ratio while displayed text stays rounded.
- Seven research-state tests and production build passed; output in artifacts/frontend_design/checks-20261013-146.json. Regression includes null versus zero coverage. Browser and assistive-technology speech acceptance remains outstanding.
- Asked user to reattach @Chrome to localhost because current tool inventory lacks a browser-control interface; source work continued independently.


## Iteration 147 — identify separate FHIR report populations

- Inspected current FhirReportSummary. Multi-group reports lacked group labels and reports without groups left only status/date. Added headings from provided group text/display or ordered fallback for multiple groups, plus explicit absent-group text.
- Unnamed numeric metrics now have a readable fallback and nonfinite numbers are unavailable rather than NaN/Infinity. Existing zero and suppression behavior preserved.
- Twelve FHIR-summary/report tests and production build passed; outputs in artifacts/frontend_design/checks-20261013-147.json. New regression covers multiple named/unnamed groups and no groups; it does not establish full FHIR conformance. Live visual acceptance remains outstanding.


## Iteration 148 — requirement fidelity and current regression

- Inspected current design tokens, theme, App.css, RouteExperience and RiskAnalysis source. Recorded a requirement-by-requirement internal acceptance audit in artifacts/frontend_design/acceptance-audit-20261013-148.json; full goal remains unproven.
- Default full regression passed 175 tests in 27 files, 25.99 seconds, empty stderr. Output in artifacts/frontend_design/regression-20261013-148.json. Latest product source build already passed in iteration 147. No redundant build or product edit this turn.
- Main gaps: current cross-size visual review, real app navigation acceptance after lifecycle changes, new feedback/meter/population rendering, assistive-technology interaction and runtime performance. Browser reconnect request remains pending; no approval or answer inferred from elapsed time.


## Iteration 149 — paired-view patient isolation invariant

- Revalidated current route/patient lifecycle source and tool inventory. No browser control currently available. Added a real-router integration case for navigating from a completed first-patient model view to a second-patient network view through the shared workspace lifecycle.
- Verified old model and graph are absent, state returns to not analyzed, second patient controls become enabled, recovery link targets patient 74 and no new analysis is silently submitted. This complements same-patient result retention and pending-analysis continuity.
- Eighteen focused risk/route tests passed, empty stderr; outputs in artifacts/frontend_design/checks-20261013-149.json. Product source unchanged; no redundant build. Real app protected-route wrappers and browser visuals still require direct acceptance.


## Iteration 150 — actual App protected-route integration

- Inspected actual App test coverage and ProtectedRoute. Existing App smoke tests render Login only. Added a separate integration using actual App, BrowserRouter, lazy pages, ProtectedRoute, RouteExperience and graph. Only auth state/session service and backend responses are mocked.
- Verified model→network→model retains a single completed analysis through actual wrappers, correct URLs and graph identity; an auth-change removes model/patient content and renders Login.
- Integration passed, empty stderr; output in artifacts/frontend_design/checks-20261014-150.json. Product source unchanged, no redundant build. This closes automated actual-App wrapper coverage; Chrome screenshots and real auth/transport performance still remain unverified.


## Iteration 151 — current local transport and served source

- Read-only probes: frontend root 200 HTML; backend root 401 JSON. Both services respond, so no restart initiated. Backend root response does not prove authenticated API operation.
- Inspected served frontend HTML and, for Vite dev serving, requested three known source-module paths to check recent workspace lifecycle, local network recovery and missing signal coverage markers. Evidence in artifacts/frontend_design/local-service-20261014-151.json.
- HTTP transport/source checks are not browser interaction, screenshot or visual acceptance. Browser control tools still absent; reconnect request remains pending.


## Iteration 152 — clear patient search without losing input focus

- Inspected current risk patient-search UI. Added an explicit inline clear button with 44px hit area and a descriptive name; clearing resets selection/results and focuses the search input.
- Added search API recovery integration confirming blank query reloads the full list, input stays focused, no patient silently selects and no analysis submits. Ten risk-workspace tests and production build passed; output in artifacts/frontend_design/checks-20261014-152.json.
- Current browser rendering of the additional adornment, especially narrow input width, still needs acceptance. No browser tools are available this turn.


## Iteration 153 — researched keyboard search recovery

- Read official Raycast Search Bar documentation (https://manual.raycast.com/search-bar) and Linear Search documentation (https://linear.app/docs/search), accessed 2026-10-14. Raycast documents Escape clearing search; Linear provides contextual search entry. Applied only the local recovery pattern, not global shortcuts or copied layout.
- Risk patient search now clears on Escape, keeps focus, advertises aria-keyshortcuts and a concise visible hint. It ignores IME composition and pending analysis. Existing clear-button path remains.
- Extended search-recovery integration to verify composition does not clear, normal Escape does and input focus remains. Ten risk tests and production build passed; output in artifacts/frontend_design/checks-20261014-153.json. Browser/real IME behavior still needs live acceptance.


## Iteration 154 — focus after empty-result recovery

- Inspected current risk result filtering. Displayed result count already has role=status, so no change there. Clearing filters removes its empty-result action button, without an explicit focus destination.
- Clear now focuses the model-search input while restoring query/status. Existing filtered-result integration asserts focus alongside restored counts and overall summary.
- Ten risk-workspace tests and production build passed; output in artifacts/frontend_design/checks-20261014-154.json. No new test added; browser keyboard behavior remains unverified this turn.


## Iteration 155 — compact narrow cohort demographics

- Inspected actual four demographic fields and current mobile CSS; earlier Chrome screenshots showed a long one-column run before the table. Changed only narrow (<=760px) demographics to two columns with existing quiet dividing lines. Other filter/summary grids retain their layout.
- Added min-width and text wrapping to allow unusually long values to remain within cells. No statistical values or labels changed.
- Seven research-state tests and production build passed; output in artifacts/frontend_design/checks-20261014-155.json. No new CSS mirror test added. Two-column visual acceptance at 320/360px, text zoom and long values remains outstanding due to unavailable Chrome tooling.


## Iteration 156 — explicit empty patient search

- Inspected risk patient-search states. Loading and error already have messages; successful empty results lacked a visible explanation. Added distinct empty-search and empty-available-patient messages, guarded against loading/errors.
- Existing search recovery regression now waits for the empty-search message before clearing, in addition to full-list recovery/focus checks. Ten risk tests and production build passed; output in artifacts/frontend_design/checks-20261014-156.json. No real patient query performed; live presentation remains outstanding.


## Iteration 157 — chart context does not pollute active search

- Revalidated patient-list source: requested chart patient was appended to every search result if absent, even after search intentionally cleared the selected patient. Extended recovery test to begin with chart patient context; it failed because unmatched search was not empty.
- Exact-patient supplementation now occurs only without an active search. Chart-context initial resolution remains, while active search reflects backend matches and clearing search reloads the full list without silently selecting.
- Eleven risk/actual-App tests and production build passed; before/after output in artifacts/frontend_design/checks-20261014-157.json. Live search results still need browser acceptance.


## Iteration 158 — patient-list failure recovery

- Current loading/error source clears stale list and error on retry, but failed-list selector remained operable with no options. Disabled that selector during patient errors, preserving retry.
- Added failed-response/retry integration: error differs from empty state, analysis disabled, retry restores exact chart patient and enabled selector, no analysis silently submitted. Eleven risk tests and production build passed; output in artifacts/frontend_design/checks-20261014-158.json. Browser acceptance remains outstanding.


## Iteration 159 — graph render-error retry recovery

- Inspected current graph boundary and analysis reset: analysis sets riskData null, unmounting old boundary, before a new response. No product correction needed.
- Extended failure integration with a controlled render failure followed by the real graph module after a fresh analysis. Verified fallback disappears, real graph renders, re-analysis enabled and exactly two analysis calls.
- Thirteen network-failure/risk tests passed, empty stderr; output in artifacts/frontend_design/checks-20261014-159.json. Product source unchanged, no redundant build. A cached rejected lazy-module import may require page reload and is not covered by this render-error recovery case; browser download failure remains unverified.


## Iteration 160 — explicit reload option for network load failure

- Consulted React official lazy reference (https://react.dev/reference/react/lazy, accessed 2026-10-14): lazy caches load promise and rejects to nearest boundary. Render-error retry differs from module-load failure.
- Network fallback now offers both patient-scoped model-list navigation and explicit page reload, with a concise note that reload requires re-analysis. Actions are stacked on narrow viewports inside the message rather than squeezing its side action area.
- Three graph-failure/actual-App integration tests and production build passed; outputs in artifacts/frontend_design/checks-20261014-160.json. Tests verify recovery actions appear and render retry still works; actual browser download failure/reload remains unverified.


## Iteration 161 — analysis failure focus and retry

- Inspected calculateRisk failure and message rendering. Patient is retained and loading releases, but feedback had no focus destination. Added focus for error feedback after loading completes; successful feedback now uses status.
- New failure→retry integration verifies focused explanation, same patient retained, operation available again, successful retry clears old error and uses the same patient id. Thirteen risk/actual-App tests and production build passed; output in artifacts/frontend_design/checks-20261014-161.json.
- Real browser focus and screen-reader behavior remain unverified; no actual clinical analysis requested.


## Iteration 162 — full regression on current recovery workflows

- Default frontend regression after search, partial-error recovery and focus changes passed all 181 tests in 28 files, 21.65 seconds, empty stderr. Command output and SHA-256 fingerprints of 75 source/config/package files preserved in artifacts/frontend_design/regression-20261014-162.json.
- Product source unchanged this turn; prior successful build in iteration 161 still applies. No redundant build. Browser tools remain absent, so current cross-size visual review, actual IME/screen-reader use and runtime performance remain outstanding. The full design goal is not complete.


## Iteration 163 — consistent report timestamps

- Inspected HistoryRecords and PatientChart dates, and searched all frontend date conversions. Screening dates display directly, so no timezone-shift defect found or changed. Only ResearchReports formats record timestamps.
- Report timestamps now explicitly use zh-TW with minute precision and 24-hour notation, preserving browser local timezone. Absent/invalid timestamps show unavailable instead of Invalid Date.
- Existing report/import-history/chart tests and production build passed; outputs in artifacts/frontend_design/checks-20261014-163.json. No new mirror test added for reversible display formatting. These tests do not establish real browser locale/timezone rendering acceptance.


## Iteration 164 — single pending risk computation

- Inspected calculateRisk entry: React loading state allowed two batched clicks and aborted the first request only after both were sent. Added regression which failed with two API calls.
- Guard the synchronously stored non-aborted request controller before initiating another calculation. Clear the controller in finally only if it remains the current request; failed calculation can retry, while aborted old request cannot clear a newer handle.
- Fourteen risk/actual-App tests and production build passed; before/after output in artifacts/frontend_design/checks-20261014-164.json. Same-patient pending navigation and cross-patient abort tests remain covered. Browser fast-click interaction remains unverified.


## Iteration 165 — distinguish input from automatic scrolling for idle time

- Inspected actual session manager and tests: new login resets activity and idle expiry uses 15 minutes, but scroll events extended activity even when focus restoration/programmatic scrolling triggered them.
- Track wheel/touchmove instead of scroll, retaining pointerdown/keydown/mousemove/touchstart. Input-driven scrolling remains activity; automatic scroll alone no longer extends deadline.
- Twenty-five session/auth tests and production build passed; output in artifacts/frontend_design/checks-20261014-165.json. New cases cover automatic scroll not extending and wheel extending. Timer/event unit tests are not proof of a real 15-minute browser session or device input behavior.


## Iteration 166 — consistent reduced-motion rule for risk workspace

- Inspected all animation/reduced-motion declarations. Global App.css already disables animation, but RiskAnalysis scoped reduction used near-zero durations. No active whole-App animation defect asserted.
- Scoped risk rule now explicitly sets animation/transition none, matching the global policy and supporting isolated use; visible operation text remains.
- Fourteen risk/actual-App tests and production build passed; output in artifacts/frontend_design/checks-20261014-166.json. No new mirror test; actual computed animation and reduced-motion browser behavior remain unverified.


## Iteration 167 — long report text and population hierarchy

- Inspected ResearchReports.css: artifact context and mobile table rows already wrap, but desktop cells and FHIR metric terms lacked anywhere wrapping. Flex metric children retained automatic minimum widths.
- Added scoped wrapping to table cells and FHIR terms/paragraphs, zero minimum flex widths with balanced term/value columns, and explicit population-heading typography/spacing. Existing mobile stacked metric rules remain.
- Twelve FHIR/report tests and production build passed; output in artifacts/frontend_design/checks-20261014-167.json. No CSS mirror test added. Actual narrow/zoom/long-value rendering remains unverified without browser tooling.


## Iteration 168 — full regression and real-App test scope

- Initial full suite had 183 passes and one actual-App integration failure at the first wait for analysis button; isolated actual-App test passed. Preloaded three real module imports in beforeAll while retaining actual components, lazy boundaries, route wrappers and all assertions. The test targets state/navigation integration, not cold module transform timing.
- Full suite then passed all 184 tests in 28 files, 29.19 seconds, empty stderr. Initial, isolated and final results preserved in artifacts/frontend_design/regression-20261014-168.json.
- Product source unchanged this turn, no redundant build. Browser cold loading/runtime performance, cross-size visuals and actual assistive-technology use remain outstanding.


## Iteration 169 — valid inputs for displayed derived BMI

- Inspected current BMI display calculation; truthiness rejected zero but accepted negative height/weight. Now requires positive input and a finite computed result; formula and payload fields unchanged.
- Extended existing decimal-measure intake scenario: 170cm/62.5kg displays 21.6, negative height hides output, valid height restored before submission. Eight intake tests and production build passed; output in artifacts/frontend_design/checks-20261014-169.json. This is a numerical display guard, not full clinical range validation or a risk interpretation. Live rendering remains unverified.


## Iteration 170 — network result text can wrap

- Inspected current network model rows. Model names wrap but result strong elements forced nowrap, allowing long results to monopolize the detail width.
- Results now wrap, allow shrinking and use at most 45% of row width; names flex to remaining space. Retained right alignment and tabular numerals; no result truncation or data changes.
- Five graph/failure/actual-App tests and production build passed; output in artifacts/frontend_design/checks-20261014-170.json. No CSS mirror test added. Long-value, narrow and zoomed visual acceptance remains outstanding without browser tools.


## Iteration 171 — remove individual selected FHIR files

- Inspected existing multi-file chooser/list. Added per-file remove controls (44px hit area), wrapping filenames and stable focus back to FHIR chooser. Removal invalidates preview/result and resets native chooser value; upload uses remaining selected File objects. Controls remain disabled while busy.
- Integration proves preview invalidates, confirmation disables, remaining list stays intact, chooser focus restores, and next preview uploads only remaining file. Initial test fixture lacked required preview fields; corrected to existing contract. Focus regression also caught a ref bound to CSV chooser; corrected to FHIR chooser.
- Fourteen import/history tests and final production build passed; outputs in artifacts/frontend_design/checks-20261014-171.json. Browser chooser, narrow list and actual uploads still require acceptance.


## Iteration 172 — announce selected files and recover from empty selection

- Revalidated removal/ready logic. Added an accessible status with selected FHIR file count or explicit no-selection text, so removal feedback is available after focus returns to picker.
- Extended existing removal integration through last-file deletion (preview/confirm disabled, list gone) and reselecting the same File object (preview enabled, no upload sent automatically). Fourteen import/history tests and production build passed; output in artifacts/frontend_design/checks-20261014-172.json.
- Scripted file-change test proves frontend state behavior, not native browser same-file chooser change events; real chooser/accessibility speech remains outstanding.

- Follow-up: wrapped removal actions in async act to flush the focus/ripple interaction; focused suite passed again with empty stderr.


## Iteration 173 — native keyboard-capable file picker triggers

- Inspected installed MUI ButtonBase implementation: non-native Enter activation invokes onClick when provided. Existing label-based file pickers had no onClick and hidden input, leaving keyboard activation unsupported by that handler.
- Converted CSV/FHIR pickers to native type=button with explicit input.click handlers, and moved hidden inputs outside buttons. FHIR picker ref remains on its native button, preserving removal focus.
- Fifteen import/history tests and production build passed; output in artifacts/frontend_design/checks-20261014-173.json. Initial test used a shorthand mode name; corrected to actual accessible FHIR primary label. Tests verify native button structure and correct input activation, not browser-native file dialog or key default behavior. Those remain outstanding.


## Iteration 174 — integrated regression after native file picker changes

- Default full frontend suite passed 186 tests in 28 files, 30.66 seconds, empty stderr. Logs and SHA-256 fingerprints of 75 source/config/package files in artifacts/frontend_design/regression-20261014-174.json.
- Product source unchanged this turn; latest successful build in iteration 173 applies. No redundant build. Tool inventory still lacks Chrome control.
- Original goal remains incomplete: native chooser keyboard/reselection, current narrow/zoom visuals, true assistive-technology behavior, runtime performance and broader studio-quality visual judgment require direct evidence. No partial success substituted for completion.


## Iteration 175 — quiet selected spreadsheet metadata

- Inspected import alerts: selected CSV/Excel filename used an outlined info alert. Replaced only that selection metadata with a named group containing filename and size, a quiet divider and wrapping behavior.
- Operational messages/warnings unchanged. Fifteen import/history tests and production build passed; outputs in artifacts/frontend_design/checks-20261014-175.json. No new presentation-mirror test added. Current narrow visual acceptance remains outstanding.


## Iteration 176 — named import format input region

- Revalidated source-switch handlers: they already clear preview/result; no change to correct reset behavior. Added one per-instance useId for active format input region, distinct accessible FHIR/spreadsheet names and aria-controls on format buttons.
- Fifteen import/history tests and production build passed; output in artifacts/frontend_design/checks-20261014-176.json. No annotation-mirror test added. Actual assistive-technology navigation and focus remain unverified.


## Iteration 177 — keyboard-focusable import preview scroll regions

- Inspected current preview table containers: tables had accessible names, containers lacked keyboard focus stops. Added named region/tabIndex=0 to spreadsheet sample and FHIR resource-summary containers while retaining table semantics.
- Fifteen import/history tests and production build passed; output in artifacts/frontend_design/checks-20261014-177.json. No annotation-mirror test added. Native arrow scrolling and narrow preview layout remain unverified without Chrome tooling.


## Iteration 178 — browser capability discovery through plugin management

- Read plugin-management skill and inspected current connector metadata. Queried actual plugin directory; exact Chrome search returned no plugins. Broader capability search returned Opera/TinyFish and unrelated tools; browser alternatives were not installed.
- No permission changes, installation, alternative browser activation or external data transmission performed. No generic remote browser assumed to reach localhost. Evidence in artifacts/frontend_design/chrome-tool-discovery-20261014-178.json.
- Directory is not exhaustive and this does not diagnose the internal cause of absent Chrome tools. Restoring original Chrome binding remains necessary for actual visual/keyboard/native-file acceptance; pending reconnect request remains unanswered. Product source unchanged and no repeated tests/build.


## Iteration 179 — synchronous import request guard

- Inspected actual four preview/import handlers; entry guards depended on React busy state. Added one synchronous operation ref shared by spreadsheet/FHIR preview and import. Acquire after existing readiness checks; release in finally.
- Added parameterized delayed-confirmation integration for both formats: two batched clicks produce one write after preview, failed write retains retry, successful retry completes with expected request count.
- Seventeen import/history tests and production build passed, empty stderr; outputs in artifacts/frontend_design/checks-20261014-179.json. No live clinical writes performed. Browser rapid input/native chooser acceptance remains outstanding.


## Iteration 180 — source controls share immediate import lock

- Inspected newly added operation lock and existing reset/source-change guards. Network handlers guarded synchronously, but reset/file removal/format changes still relied on React busy state alone.
- Added same ref guard to reset/file handling/removal, format/source switching and chooser activation. Added batched confirm→format-change regression: FHIR input region stays active during import, and switching works again after failure with stale preview removed.
- Eighteen import/history tests and production build passed; outputs in artifacts/frontend_design/checks-20261014-180.json. No real import performed. Native browser rapid-event acceptance remains outstanding.


## Iteration 181 — align controls independently of helper text

- Inspected risk-patient control grid and recently added Escape helper text. Center alignment includes helper height in the search cell, offsetting other controls relative to actual input. Changed only that grid to start alignment; narrow single-column rule unchanged.
- Fourteen risk/actual-App tests and production build passed; output in artifacts/frontend_design/checks-20261014-181.json. No CSS mirror test added. Layout improvement is inferred from current style structure, not verified by a fresh screenshot; desktop/narrow visual acceptance remains outstanding.


## Iteration 182 — preview intent and report action context

- Searched preview/download icon usage. Template download is correct; report view action opens a preview but used Download. Changed it to Visibility.
- Assigned per-instance title ids and aria-describedby to view/approve/reject row actions, keeping visible labels and functionality. Existing artifact/approval cases verify accessible report-title descriptions.
- Ten report tests and production build passed; outputs in artifacts/frontend_design/checks-20261014-182.json. Browser visual icon recognition and screen-reader announcement remain unverified.


## Iteration 183 — review dialog names its target report

- Inspected current approval/rejection dialog: target title was visible but not linked to dialog description. Added per-instance describedby context id and wrapping for long titles.
- Existing approval failure integration verifies the target report description alongside retained note and focused error. Ten report tests and production build passed; output in artifacts/frontend_design/checks-20261014-183.json. No real review executed; assistive-technology speech/long-title visuals remain unverified.

## Iteration 184 — integrated frontend regression

Confirmed iteration 183 report dialog checks and production build both exited 0 with empty stderr. Ran the complete frontend suite after the recent import operation locks, report context descriptions and risk control alignment changes: 189 tests across 28 files passed in 28.73 seconds with empty stderr. Evidence: artifacts/frontend_design/regression-20261014-184.json. This validates automated interaction coverage, not visual rendering or live 15-minute idle expiry. Chrome/CUA tools remain absent from the current exposed tool catalog; real browser acceptance remains outstanding and the overall goal remains active.

## Iteration 185 — import completion announcement priority

BulkHealthDataImport explicitly uses role=status for successful parsing and import feedback, retaining role=alert for errors and partial-import warnings. This avoids asserting urgency for normal completion while preserving immediate failure feedback. Existing error focus and import result heading focus remain unchanged. Eighteen import interaction tests and production build passed, both with empty stderr; evidence: artifacts/frontend_design/checks-20261014-185.json. Actual screen reader announcement order still requires browser/assistive technology acceptance.

## Iteration 186 — distinguish preview from persistence

Import waiting status now names the actual operation: reading a CSV/Excel file or FHIR source to establish preview, versus writing the confirmed data to the system. The label is set by each of the four existing handlers before busy state is entered, and is rendered only while busy. Operation locks and confirmation requirements remain intact. Eighteen import interaction tests and production build passed with empty stderr. Evidence: artifacts/frontend_design/checks-20261014-186.json. No invented percentage or claim of server progress; real browser announcement and layout acceptance remain pending.

## Iteration 187 — semantic import result summary

Replaced three nested Paper wrappers with a named definition list pairing success, error and total counts. Kept displayValue handling of zero and unavailable values. Scoped CSS retains three columns with fine separators and a single-column layout below 600px; long values can wrap and numeric glyphs use tabular spacing. Removed the superseded import-only surface-grid overrides. Eighteen import tests and production build passed with empty stderr. Evidence: artifacts/frontend_design/checks-20261014-187.json. Responsive visual and assistive technology behavior are not yet browser-verified.

## Iteration 188 — readable expandable import errors

Detailed import failures now render as a semantic unordered list inside a named warning group. The global partial-import warning remains the immediate notification; expanding details no longer exposes a second alert container. The expand/collapse button reports aria-expanded and controls a unique per-instance list ID. Long diagnostic text wraps within list items. Existing partial-error expansion integration and all 18 import tests passed; production build passed, stderr empty. Evidence: artifacts/frontend_design/checks-20261014-188.json. Browser keyboard/announcement acceptance remains outstanding.

## Iteration 189 — native navigation after import

Import result analysis action now renders a RouterLink anchor instead of imperative button navigation. Preserves the existing exact patient_id destination and general risk-analysis fallback, while exposing native link actions such as opening another tab. Removed unused useNavigate. Existing successful FHIR and partial CSV import tests now assert actual link destinations. All 18 import tests and production build passed with empty stderr. Evidence: artifacts/frontend_design/checks-20261014-189.json. Native browser context menu/modifier behavior remains subject to live browser acceptance.

## Iteration 190 — prevent fabricated zero in signal report

Current report inspection found Number coercion converted whitespace and boolean fields into numeric measurements, including apparent zero/one coverage. Added a shared local numericValue parser accepting finite numbers and nonblank numeric strings, rejecting other types. Both numeric formatting and coverage meters use it; genuine zero remains measured. New synthetic integration covers whitespace duration, boolean sample count/coverage, valid numeric count string and zero coverage string. Five continuous-signal tests and production build passed with empty stderr; artifacts/frontend_design/checks-20261014-190.json. No medical threshold or backend data changed; live rendered acceptance remains incomplete.

## Iteration 191 — consistent bounded percentage display

Unified coverage summary, coverage meters and numeric signal validity using percentageValue: only finite numeric values from 0 through 100 are displayed as percentages. Previously meters rejected out-of-range values but top SCG metric and validity captions displayed them. Missing/invalid validity now explicitly says 有效率未提供. Zero remains measured. New synthetic integration checks out-of-range SCG coverage, negative/missing validity and genuine zero validity. Six report tests and production build passed with empty stderr. Evidence: artifacts/frontend_design/checks-20261014-191.json. This is a display-domain guard, not a clinical threshold or source data correction. Browser visual acceptance remains incomplete.

## Iteration 192 — restore stopped local development services

Read-only requests to localhost and 127.0.0.1:3000 failed with ECONNREFUSED and netstat showed neither 3000 nor 8000 listening. Started existing Vite directly, hidden and bound to loopback with strict port 3000. Root and both recently changed import/signal modules now return HTTP 200 and contain current source markers. Started existing venv Django runserver on loopback 8000 without running migrations. Backend root response: {"status":401,"contentType":"application/json"}. No clinical records or credentials retrieved. Current tool catalog still lacks Chrome/CUA control; these HTTP checks do not prove browser rendering or authenticated workflows. Evidence: artifacts/frontend_design/local-service-20261014-192.json.

## Iteration 193 — consistent AO output narrative

Current-state inspection found boolean true reported existing AO output while numeric display rejected it; a numeric string zero displayed zero but narrative treated it as unavailable. Normalize AO output once through numericValue and require a nonnegative safe integer, then use the same value in both count displays and the narrative. Parameterized integration covers boolean, numeric-string zero, negative and fractional values. Ten signal report tests and production build passed, empty stderr. Evidence: artifacts/frontend_design/checks-20261014-193.json. This changes display interpretation only, not stored results, model performance or medical validation. Real browser acceptance remains outstanding.

## Iteration 194 — integrated regression after import and signal changes

Complete frontend suite passed: 195 tests in 28 files, 31.22 seconds, exit 0 and empty stderr. Captured SHA256 fingerprints of the changed import/signal source and tests, shared CSS and package manifest before execution and confirmed they remained unchanged afterward. Evidence: artifacts/frontend_design/regression-20261014-194.json. Latest production build passed in iteration 193. This is an automated baseline; real desktop/mobile rendering, assistive technology and authenticated workflows remain unproven, so the full goal remains active.

## Iteration 195 — focus failed signal report recovery

Signal report errors were visible with a retry action but lacked programmatic focus. Added an error notice ref and focus after loading completes with an error; tabIndex -1 keeps the container outside normal tab order while making its adjacent retry action reachable. Extended existing failure/retry integration to assert notice focus before successful recovery. Ten signal report tests and production build passed with empty stderr. Evidence: artifacts/frontend_design/checks-20261014-195.json. Live keyboard and assistive technology acceptance remain unverified.

## Iteration 196 — remove signal report intrinsic width constraints

Source CSS review found two-column analysis/bottom grids used automatic minimum track sizes and coverage meter imposed a 100px middle-track minimum. Changed outer tracks to minmax(0, fraction), meter middle track to minmax(0, 1fr), allowed coverage labels and metric values to wrap, and removed intrinsic minimum widths on signal surfaces/metrics. Existing breakpoints, labels and numeric logic unchanged. Production build passed with empty stderr; artifacts/frontend_design/checks-20261014-196.json. This addresses identified CSS overflow mechanisms; actual viewport rendering is not verified and remains a required gate. No mirror CSS tests added.

## Iteration 197 — sequential data route semantics

Data route overview now uses a named ordered list with five native list items. Arrow-only items are hidden and presentational; visual numbers are hidden to avoid duplicating sequential list numbering. List default padding/margins are explicitly reset to retain current grid geometry. Ten signal report tests and production build passed, stderr empty. Evidence: artifacts/frontend_design/checks-20261014-197.json. Actual screen-reader list enumeration and visual layout remain pending browser acceptance.

## Iteration 198 — official typography research and acceptance decision

Inspected Apple WWDC20 session 10175 official transcript, particularly hierarchy through size/weight/leading and adapting spacing for larger text. Direct current HIG layout/typography pages returned JavaScript-required responses; full HIG inspection is not claimed. Compared the guidance with current signal report CSS: primary 32–48px heading, section 18–22px headings, explanatory 14px/1.8-leading text and 13px supporting details. These rules show a designed hierarchy but do not prove rendered readability. Decision: preserve the product typography rather than copy native Apple fonts or point sizes; next acceptance should compare actual reading density and enlarged-text behavior before further typography overrides. Evidence: artifacts/frontend_design/typography-research-20261014-198.json. No source mutation or repeated regression was needed.

## Iteration 199 — distinguish empty history page from empty registry

HistoryRecords already cleared prior rows during page requests. Found later empty pages reused the global 尚無健檢紀錄 state and add/import guidance despite existing earlier records. Pages beyond the first now say 本頁沒有健檢紀錄 and offer previous-page/refresh guidance; new-import shortcut is limited to the initial empty page. Extended existing page-2 integration to verify contextual heading and enabled previous-page action, retaining first-page retry/empty checks. Eighteen import/history tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-199.json. Live pagination rendering remains unverified.

## Iteration 200 — keyboard entry to history scroll container

History CSS already switches to record rows on mobile and retains overflow:auto for table layouts. Added a named region with tabIndex 0 on TableContainer so keyboard users can reach the scroll surface. Extended the existing history navigation integration to verify the region entry while retaining real patient links and page context assertions. Eighteen import/history tests and production build passed, empty stderr. Evidence: artifacts/frontend_design/checks-20261014-200.json. Actual keyboard scrolling and responsive screenshots remain required; this iteration is not a completion claim.

## Iteration 201 — verify history date ordering contract

Inspected HealthScreeningViewSet.get_queryset: order_by(-screening_date, -created_at) within the clinical access policy. HistoryRecords renders response order unchanged. This supports the date-based copy and avoids a misleading client-side sort of one paginated subset. Exact ties on both fields lack a unique-key tie breaker, so complete deterministic tie ordering is not claimed. No private records queried or source changed. Evidence with backend source SHA256: artifacts/frontend_design/history-ordering-20261014-201.json. Initial global rg timed out; narrowed API-directory search succeeded. Next acceptance remains live pagination and responsive rendering.

## Iteration 202 — unique tie breaker for history pagination

Added -id after descending screening_date and created_at in HealthScreeningViewSet so exact timestamp ties have a unique deterministic order. Added synthetic API test creating three same-date records and forcing identical creation timestamps, asserting descending IDs across repeated requests. Ran all four HealthScreeningAPITest cases against settings_security_tests and the explicitly named isolated PostgreSQL test database with keepdb; all passed (2.532s test execution), system checks clean. Evidence: artifacts/frontend_design/checks-20261014-202.json. This does not prevent page shifts when new records are inserted and does not prove live browser pagination. Current development backend was launched with --noreload in iteration 192, so this backend source change requires restart before live acceptance.

## Iteration 203 — launch updated history backend

CIM/tasklist process introspection was denied, so no process was killed. netstat showed no 8000 listener. Launched existing venv Django runserver on loopback 8000 without migrations, loading current source with unique history sorting. Root returned {"status":401,"contentType":"application/json"}. Evidence: artifacts/frontend_design/local-service-20261014-203.json. No credentials or clinical records retrieved. Authenticated history acceptance and browser rendering remain outstanding.

## Iteration 204 — history error recovery focus

History errors already retained retry and avoided false empty records. Added programmatic focus to the error notice after failed loading, with tabIndex -1 to keep the container outside normal keyboard tab order. Extended existing failure/retry integration to assert focus before retrying and recovering to the actual empty registry. Eighteen import/history tests and production build passed, empty stderr. Evidence: artifacts/frontend_design/checks-20261014-204.json. Actual keyboard and screen-reader acceptance remain outstanding.

## Iteration 205 — inspect brand loading cost

Verified actual home is LandingPage (Launch is the SMART authorization route). Home uses a CSS orbit illustration and inline SVG Brand rather than a hero bitmap. Public icon files: logo512 4722 bytes, logo192 944 bytes, favicon.svg 335 bytes, apple-touch-icon 906 bytes. Source search found no external font URL or @font-face dependency. Decision: image compression/font replacement offers no evidenced first-screen benefit here; preserve the existing original mark and focus the next performance acceptance on real resource waterfall/layout shift. Evidence: artifacts/frontend_design/brand-loading-20261014-205.json. These source checks do not prove runtime performance; no code change or redundant tests performed.

## Iteration 206 — scoped home workflow keyboard control

Home keyboard tab activation used global document.getElementById with fixed IDs. Switched to per-instance useId relationships and scoped button refs, retaining role filtering, automatic selection and arrow/Home/End behavior. Existing thirteen navigation tests cover matching content/focus, account routes, role-filtered tabs and selected-workflow validity when permissions change; all passed. Production build passed, stderr empty. Evidence: artifacts/frontend_design/checks-20261014-206.json. Real keyboard/rendered acceptance remains outstanding.

## Iteration 207 — align SMART page title and verify unknown route recovery

Inspected App catch-all and PageNotFound: unknown URL retains an explicit not-found page and directs authenticated users to dashboard, public users to home. Existing tests cover both recovery destinations and document title. Found /launch title still called 啟動工作空間 while real page heading/task is 連接醫療系統; aligned the route title with the task. Fourteen route/SMART tests and production build passed with empty stderr. Evidence: artifacts/frontend_design/checks-20261014-207.json. Browser tab presentation and actual authorization remain separately unverified.

## Iteration 208 — restore frontend acceptance environment

Current HTTP checks found backend 8000 returned 401, frontend 3000 refused connections. Started Vite on loopback with strict port 3000. Eight main route URLs now return 200 with the SPA document. Current tool metadata exposes no Chrome/CUA/browser controller or tool-search entry, so screenshots and live UI behavior cannot be asserted. Evidence: artifacts/frontend_design/local-service-20261014-208.json. These checks verify server routing availability only. The full objective remains active; this is not a substitute for rendered acceptance.

## Iteration 209 — integrated regression after home/history/routing updates

Complete frontend suite passed after iterations 195–207: 195 tests in 28 files, 32.21 seconds, exit 0 and empty stderr. Evidence: artifacts/frontend_design/regression-20261014-209.json. Latest production build passed in iteration 207. Backend unique history-order test separately passed in iteration 202. These are automated/synthetic checks; recent responsive screenshots, live authenticated workflows, screen-reader behavior and runtime performance remain required before full goal completion.

## Iteration 210 — inspect unfinished entrance markers

Scoped rg scan of executable JSX/JS excluding tests found no mock/coming-soon/development placeholder marker in current source. Actual demo matches are API-provided is_demo_patient and labels in PatientChart/RiskAnalysis; ResearchCohorts demographics matches are unrelated field names. Confirmed RiskAnalysis fetches patient API rather than creating a local demonstration fallback. Preserve clearly labeled synthetic patients for requested Golden Patient workflows. No removal warranted by this scan. Evidence: artifacts/frontend_design/placeholder-audit-20261014-210.json. Keyword checks do not prove all features finished; live rendered inventory remains pending.

## Iteration 211 — reject invalid cohort numeric values

ResearchCohorts displayNumber previously rendered booleans/nonfinite values and whitespace directly. It now renders unavailable for invalid types, nonfinite numbers and blank strings while preserving finite zero and meaningful backend text (including release notes). Added a synthetic cohort demographics case. Initial assertion matched the always-present similar-profile age label before cohort completion; scoped the assertion to the loaded cohort summary. Eight research-state tests passed after correction, empty stderr; production build passed. Evidence: checks-20261014-211.json retains initial failure/build, checks-20261014-211-retry.json final success. Actual rendering acceptance remains pending.

## Iteration 212 — strict research ratio display

Research coverage and average similarity previously coerced booleans/blank strings into false percentages. Added local ratioValue accepting finite numeric values/nonblank numeric strings in 0–1, shared by both displays. Invalid coverage remains unavailable and has no meter; invalid similarity remains unreleased. Genuine numeric-string zero remains a measured meter and existing zero-similarity coverage remains passing. New synthetic integration verifies both invalid types and zero preservation. Nine research-state tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-212.json. No clinical model or stored research data changed. Live visual acceptance remains outstanding.

## Iteration 213 — shared numeric display normalization

Consolidated duplicated signal/research source normalization into frontend/src/utils/numericDisplay.js: finite numeric value, bounded 0–100 percentage and bounded 0–1 ratio. Kept component-specific wording, formatting and AO count constraints. The helper is explicitly display-only and does not alter clinical ingestion validation or source data. Existing 19 integration tests across both report areas passed; production build passed, stderr empty. Evidence: artifacts/frontend_design/checks-20261014-213.json. No mirror utility tests added; current integration cases cover zero, invalid types, bounds and rendered states. Browser acceptance remains pending.

## Iteration 214 — identify risk execution summary coercion

Inspected current RiskAnalysis counts/completion source following shared display normalization. Four model counters still use unrestricted Number and can turn booleans/blank strings into counts or invalid text into NaN; completion text depends on these values. Also identified existing riskCards.length fallback as requiring status-aware interpretation, not an assumed completed-model count. Evidence: artifacts/frontend_design/risk-summary-audit-20261014-214.json. Next implementation must validate nonnegative integer counts and preserve unknown counts/completion explicitly; do not broaden shared helpers into clinical score calculations. No source change or unnecessary test rerun in this inspection.

## Iteration 215 — truthful risk execution counts

Added shared countValue requiring nonnegative safe integers. Risk execution counts no longer coerce booleans/blanks or infer scored/resolved counts from result-row length. Missing/invalid counters display 未提供; completion percentage requires valid positive total and resolved count within total. All-resolved styling requires explicit true and matching valid counts. Unknown catalog count uses a general analysis prompt. New synthetic integration checks invalid counters and false all-resolved claim. Seventeen risk workspace/real-App/network-failure tests and production build passed, stderr empty. Evidence: artifacts/frontend_design/checks-20261014-215.json. This affects summary display only; clinical scores unchanged. Live browser acceptance remains incomplete.

## Iteration 216 — preserve valid zero-count completion and share AO count rules

Reused countValue for AO output display instead of duplicating its safe-integer rule. Added risk integration with valid numeric-string totals/resolved counts, zero scored models and two not-applicable models; verifies 100% resolution without inventing scored output. Existing ordinary numeric completion tests remain covered, along with invalid AO types. Twenty-five risk/signal interaction tests and production build passed, empty stderr. Evidence: artifacts/frontend_design/checks-20261014-216.json. Runtime rendering and medical model validation remain separate unproven gates.

## Iteration 217 — allow risk summary text reflow

Current CSS forced risk completion text onto one line, conflicting with longer explicit unknown-state copy and enlarged text. Changed white-space to normal, removed flex child intrinsic minimum width, constrained summary width and enabled wrapping. Kept current alignment breakpoints and added tabular numeric glyphs. Production build passed, empty stderr; artifacts/frontend_design/checks-20261014-217.json. This addresses source-level overflow constraints; no real viewport/zoom screenshot is claimed. No mirror CSS tests added.

## Iteration 218 — integrated regression for shared display rules

Complete frontend regression after shared numeric/count normalization and risk summary reflow passed: 199 tests across 28 files, 31.60 seconds, exit 0, empty stderr. Evidence: artifacts/frontend_design/regression-20261014-218.json. Latest production build passed in iteration 217. Current test evidence covers synthetic interactions; live authenticated behavior, responsive screenshots and runtime accessibility/performance are still outstanding. Overall design goal remains active.

## Iteration 219 — unambiguous model library title

Registry source uses runtime_approved as execution governance status; this is not itself evidence of external approval. Replaced pre-analysis 已核准模型庫 heading with task-based 風險模型庫. Preserved runtime rules and source details. Fifteen risk workspace tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-219.json. This wording change does not assert clinical certification or alter model availability. Live visual acceptance remains pending.

## Iteration 220 — patient chart recovery from network exploration

Verified chart→intake/risk/network and saved intake→risk links preserve patient_id. Network exploration exposed data gaps but only linked to model results; added a same-patient chart link labeled 核對病患資料 in a named navigation group alongside model results. Retains native links, 44px targets, wrapping and reader access without introducing write permissions. Existing graph exploration test now asserts exact chart destination. Seventeen graph/risk tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-220.json. Live cross-page navigation remains pending acceptance.

## Iteration 221 — disease network summary reflow

Confirmed network-count already has a later white-space:normal rule; avoided adding a redundant override. Network-totals still had a nonwrapping flex row. Added wrapping with row/column gaps, constrained child width and wrapping for large values, and tabular numeric glyphs. Keeps all four summary labels and existing order. Production build passed, empty stderr; artifacts/frontend_design/checks-20261014-221.json. Actual text zoom and mobile rendering remain unverified, so this is a source-level reflow improvement only.

## Iteration 222 — actionable empty disease network

DiseaseNetwork previously returned an instruction to execute analysis when no graph nodes existed, even after an analysis response. Replaced it with a named empty network state explaining no available model graph, retaining patient identity and exact chart/model recovery destinations. No illustrative/fabricated nodes added. New synthetic integration verifies heading, identity, links and absence of old instruction. Eighteen graph/risk tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-222.json. Live rendering remains pending.

## Iteration 223 — primary-source Stripe workflow research

Inspected official Stripe Dashboard basics and search documentation. Relevant workflow principles: separate primary resource work from products/settings; navigate search results to resource details; keep scope explicit and permission-aware. Product interpretation: retain authorized care/data/research grouping and patient-specific chart destinations; avoid adding unsupported advanced search grammar or cross-resource search just to imitate a reference. Evidence: artifacts/frontend_design/stripe-workflow-research-20261014-223.json. These are documentation-based workflow observations, not a visual Stripe case study or proof of clinical UI completion. No source change or redundant tests needed.

## Iteration 224 — nonurgent empty cohort statistics

Confirmed StatsTable already has a named focusable scroll region and named sticky-header table. Empty rows previously rendered an informational Alert with default assertive alert role; changed to quiet body text with role=status, distinguishing a normal absent aggregate from query failure. Existing failure handling unchanged. Nine research-state tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-224.json. Real announcement order and rendered hierarchy remain unverified.

## Iteration 225 — measure shared text token contrast

Inspected current designTokens and calculated twelve solid-color combinations of ink/green/muted/success against paper/surface/wash using sRGB luminance. Lowest displayed ratio is muted on wash, 4.558:1; all twelve exceed the ordinary-text 4.5:1 baseline in W3C SC1.4.3 guidance. Source: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html. Evidence: artifacts/frontend_design/core-contrast-20261014-225.json. Preserve core palette; prioritize rendered inline/state-specific colors next. This does not cover opacity, actual cascade, chart strokes or all WCAG requirements, and does not complete browser acceptance. No color change or redundant regression needed.

## Iteration 226 — visible disease network relationships

Calculated the old nonselected edge opacity composite against paper: approximately 1.15:1. Replaced low-opacity edge colors with full-opacity shared muted/green tokens; source contrast is approximately 4.82:1/7.85:1. Increased inactive/active strokes from 0.7/1.5 to 1/2 viewBox units, preserving solid/dashed data semantics. W3C SC1.4.11 guidance informed the contrast review; actual aliasing and graph visual density still require browser inspection. Three graph tests and production build passed, empty stderr. Evidence: artifacts/frontend_design/checks-20261014-226.json. No claim of whole-site WCAG conformance.

## Iteration 227 — measure risk status/section text pairs

Calculated ten declared risk level text/background pairs and eight section accent/wash pairs from RiskAnalysis. All exceed 4.5:1 using unrounded calculations; the lowest is missing-data text at approximately 4.548:1. Retain these semantic colors; no evidence justifies palette replacement in this scope. Evidence with full ratios: artifacts/frontend_design/risk-contrast-20261014-227.json. Reference: W3C SC1.4.3 understanding guidance. This evaluates declared solid pairs, not actual rendered cascade, opacity or all page states. Browser acceptance remains outstanding; no source mutation or redundant tests needed.

## Iteration 228 — inspect visual evidence freshness

Listed frontend_design artifacts: no local PNG/JPG/WebP files or screenshot subdirectories. Iteration 123 explicitly records an inline tool screenshot of scrolled cohort headers and makes no local-file claim. Historical rendered evidence remains valid for that earlier state, but source changes since then require fresh capture. Next browser pass must save images with route/viewport/revision and synthetic normal/empty/error/long-content states. Evidence: artifacts/frontend_design/visual-evidence-audit-20261014-228.json. No claim of new screenshots or current visual completion.

## Iteration 229 — verify pending model cards are not rendered

Reviewed 模型準備中 references beyond earlier keyword scan. normalizeRiskResults excludes clinical_review_required records, and normalized results drive formal rows/network groups. Scoped search found normalizePendingModels only at its export definition in executable frontend source, no callsite; its placeholder helper is not a rendered entrance. Preserve backend source states and avoid unsupported removal. Evidence: artifacts/frontend_design/pending-model-ui-audit-20261014-229.json. This static inspection does not prove every backend module complete or replace live DOM inventory. No code mutation or redundant regression.

## Iteration 230 — integrated regression after disease network refinements

Complete frontend suite passed after chart recovery links, empty network state, summary reflow, status copy and network edge contrast changes: 200 tests in 28 files, 31.37 seconds, exit 0 and empty stderr. Evidence: artifacts/frontend_design/regression-20261014-230.json. Latest production build passed in iteration 226. This establishes automated coverage for current source; no fresh browser rendering, live private workflows or runtime performance evidence was collected. Full goal remains active.

## Iteration 231 — current live login and refresh contract

Used the previously authorized development account against current local backend: login returned HTTP 200 with access/refresh credentials, token refresh returned 200, authenticated profile using refreshed access returned 200. Recorded only status/presence metadata; no credentials, tokens or profile body saved/output. Cleared payload/token variables after check. Evidence: artifacts/frontend_design/auth-live-20261014-231.json. This validates immediate API login/refresh compatibility, not browser storage, actual 15-minute idle expiry or visual workflow. No source mutation or redundant unit suite.

## Iteration 232 — current authenticated FHIR preview

Used existing generated Golden Patient JSON/XML files against local authenticated fhir-preview API, format:auto. Both returned HTTP 200, 44 resources and normalized Bundle with 44 entries: 1 Patient, 1 Encounter, 40 Observation, 1 Condition, 1 QuestionnaireResponse. Metadata-only evidence: artifacts/frontend_design/fhir-preview-live-20261014-232.json. No import endpoint called and no clinical database records written; credential/payload variables cleared after checking. This verifies parser/preview response compatibility, not full FHIR conformance, real browser file selection or risk prediction.

## Iteration 233 — live multipart and content-based FHIR detection

Authenticated local multipart preview accepted Golden Patient JSON+XML together, returning HTTP 200 and 44 normalized resources (duplicates did not double the count). The same JSON content under .fhir extension also returned HTTP 200/44 resources. Initial Node environment lacked FormData, so constructed standard multipart bytes in memory without extra dependencies/files. Credentials/payload variables cleared; only aggregate metadata saved. Evidence: artifacts/frontend_design/fhir-multipart-live-20261014-233.json. No import/database writes; no browser file dialog or rendered UI acceptance claimed.

## Iteration 234 — one patient-scoped network action group

Extracted identical normal/empty network navigation into local NetworkActions, preserving exact destinations, labels and CSS. This keeps patient chart/model recovery behavior consistent across states. Existing three graph interaction tests cover both normal exploration and empty recovery links; all passed, production build passed, stderr empty. Evidence: artifacts/frontend_design/checks-20261014-234.json. No new feature or clinical behavior; live browser acceptance remains pending.

## Iteration 235 — live conflicting FHIR source rejection

Created an in-memory clone of generated Golden Patient data with one numeric Observation changed while retaining the same fullUrl, then multipart-previewed original plus conflicting clone. Local service returned HTTP 400, no normalized fhir_data, and detail matched the frontend 衝突的 fullUrl recovery condition. No source files edited or import endpoint called; credential/clinical payload variables cleared. Metadata-only evidence: artifacts/frontend_design/fhir-conflict-live-20261014-235.json. This verifies service conflict gating/recovery contract, not actual browser message focus or whole FHIR conformance.

## Iteration 236 — current browser acceptance readiness

Rechecked tool catalog: no Chrome/CUA/browser controller or tool-search capability currently exposed. Local service states saved in artifacts/frontend_design/browser-readiness-20261014-236.json. Recent real HTTP checks establish login/refresh/profile and FHIR preview normal/conflict paths, but desktop/mobile screenshots, native file dialog, keyboard/zoom and runtime performance still require actual browser control. Keep original goal active and do not treat these narrower gates as completion.

## Iteration 237 — live response matches frontend auth fields

Inspected auth.js requirements and current authorized local login response without saving credentials or identity details. Response has a three-part token, numeric unexpired exp, accepted user/profile field, role information and refresh field. Remaining access lifetime at inspection: 599 seconds. Evidence: artifacts/frontend_design/auth-contract-live-20261014-237.json. Cleared token/claims/user variables after check. This rules out missing response fields or immediately expired access in this request; browser storage/events and real idle behavior remain unverified.

## Iteration 238 — browser-origin CORS preflight

Sent OPTIONS preflight for login, refresh and FHIR preview with Origin http://localhost:3000, POST method and content-type/authorization headers. All returned HTTP 200, exact allowed origin, POST in allowed methods and both requested headers allowed; credentials true. Evidence: artifacts/frontend_design/cors-live-20261014-238.json. No credentials or clinical data sent. This verifies current preflight configuration only; actual browser requests, storage and rendered workflows remain pending. No configuration change needed.

## Iteration 239 — actual unauthorized responses retain CORS

Requested profile and FHIR preview without credentials using the exact frontend backend hostname localhost:8000 and Origin localhost:3000. Both returned 401 with exact Access-Control-Allow-Origin and credentials headers, so source-level/browser protocol handling can distinguish unauthorized from network failure. Evidence: artifacts/frontend_design/cors-error-live-20261014-239.json. No user/clinical data retrieved; this does not execute browser Fetch/storage behavior. No configuration change or redundant tests.

## Iteration 240 — patient-scoped recovery for empty model results

Model list already warned about an empty analysis response but offered no direct record check. Added a same-patient chart link to the warning and concrete retry-after-check guidance. Extended existing empty-result/patient-selection test to assert exact chart destination and removal when switching patients. Fifteen workspace tests and production build passed, empty stderr. Evidence: artifacts/frontend_design/checks-20261014-240.json. Live browser navigation remains pending.

## Iteration 241 — readable risk descriptions and snapshot labels

Extended contrast review beyond status/accent pairs to actual caption colors. Group descriptions #73838b on section washes computed approximately 3.62–3.70:1; snapshot labels #7a8992 on #fbfcfc computed 3.51:1. Replaced both with shared atlas-muted, raising source ratios to at least 4.70:1 and 4.95:1 respectively. Production build passed, empty stderr; artifacts/frontend_design/checks-20261014-241.json. Text/data/routes unchanged. Actual cascade, rendering and visual acceptance remain pending. No mirror color tests added.

## Iteration 242 — verify card-level reading styles

Inspected RiskResultCard and current CSS: titles/missing notices use ink; English names/outcomes/detail headings use muted; disclosure controls/source links use green on a declared white surface. Source solid contrasts approximately 14.32/5.09/8.30:1. Disclosure/link targets have 44px minimum heights and visible outlines, long text wraps. No extra palette change warranted. Evidence: artifacts/frontend_design/risk-card-readability-20261014-242.json. Actual inherited detail text/cascade, typography and disclosure behavior remain pending rendered verification. No source change or redundant tests performed.

## Iteration 243 — browser/install brand metadata and delivery

Confirmed manifest uses AllCare365/zh-Hant and shared green/paper colors, matching brand constants. All four listed icon assets return 200 from localhost:3000 with image content types; PNG headers confirm actual 192×192 and 512×512 dimensions. No template name or broken icon resource found in this scope. Evidence: artifacts/frontend_design/install-brand-live-20261014-243.json. Installation UI, maskable cropping and rendered branding remain unverified; no source change or redundant tests needed.

## Iteration 244 — wrap risk patient identity

Risk patient identity flex container already wrapped rows, but text children retained intrinsic minimum width and lacked long-string wrapping. Added min-width:0, max-width:100% and overflow-wrap:anywhere to direct Typography children, preserving complete names/MRNs rather than truncating. Kept identity icon from shrinking. Production build passed, empty stderr; artifacts/frontend_design/checks-20261014-244.json. No data or selection logic changed. Actual narrow-screen and zoom rendering remain unverified; no mirror CSS tests added.

## Iteration 245 — clear assessment disclosure action

Reworded risk card disclosure from 檢視資料與模型限制 to 查看評估細節, a concise task label matching its varying contents (missing inputs, model applicability/details, recommendation, reference/version). Preserved all actual evidence and constraints; no medical information removed. Updated existing interaction selectors while retaining assertions on real displayed details. Fifteen risk workspace tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-245.json. Actual disclosure and typography acceptance remain pending browser control.

## Iteration 246 — integrated regression after risk page readability/recovery changes

Complete frontend suite passed after network navigation extraction, empty model recovery, caption contrast, identity wrapping and disclosure wording: 200 tests across 28 files, 31.58 seconds, exit 0 and empty stderr. Evidence: artifacts/frontend_design/regression-20261014-246.json. Latest production build passed in iteration 245. Recent HTTP auth/FHIR/CORS evidence remains separate from synthetic frontend tests. Current desktop/mobile rendering, browser storage/idle behavior and runtime performance remain outstanding, so the complete original goal is still active.

## Iteration 247 — inspect current brand raster visually

Viewed actual logo192.png using local image tool: green field, paper-colored four-arm cross with square centre cutout and substantial outer padding. Geometry matches shared brand direction; no extra decorative/template content. Retain this 192px icon variant. Evidence includes exact asset SHA256: artifacts/frontend_design/brand-visual-20261014-247.json. This is real local asset inspection only, not browser page/installed maskable icon or 16px favicon acceptance. No source change or redundant tests.

## Iteration 249 — inspect original 16px favicon frame

Verified ICO has original PNG frames at 16/32/48/64px. Extracted exact 16px PNG resource bytes without resizing/editing and viewed at original resolution: four-arm mark and centre cutout remain visible. Saved inspectable source-frame artifact and metadata in frontend_design. No source asset correction identified. Evidence: favicon-original-16px-20261014-249.png and favicon-visual-20261014-249.json. This is local frame inspection, not actual browser favicon selection/scaling; Chrome connection request remains pending.

## Iteration 250 — use shared font for risk section codes

Found one remaining IBM Plex Sans override on risk section code labels with no project font-face/external loading rule. Replaced it with atlas-sans, retaining letter spacing, size and layout so this detail uses the same explicit fallback stack as the workspace. Production build passed, empty stderr; artifacts/frontend_design/checks-20261014-250.json. No new font download/dependency or runtime behavior change. Actual glyph metrics remain pending browser inspection; no mirror style tests added.

## Iteration 251 — current model catalogue response contract

Authenticated local risk-algorithms API returned 200 with system/count metadata. Verified executable_models is a nonnegative safe integer matching frontend countValue expectations. Metadata-only evidence: artifacts/frontend_design/risk-catalog-live-20261014-251.json. No patient data or scores queried; tokens cleared. Catalogue availability/counts do not prove model accuracy or actual risk execution. Browser result presentation remains pending.

## Iteration 252 — health product workflow reference

Attempted fresh Awwwards Function Health case fetch; timed out, domain image query empty. Inspected official Function Health public page text as a scoped fallback: explanatory navigation separated from sign-in/start actions and a testing→explanation→follow-up sequence. Product interpretation: preserve professional records→assessment→patient-specific follow-up paths; do not copy consumer purchase or promotional/medical claims. Evidence: artifacts/frontend_design/health-reference-research-20261014-252.json. No fresh visual Awwwards case review, local browser rendering or medical validation claimed. No source mutation or redundant tests.

## Iteration 253 — reset search for explicit patient route changes

Found different-patient URL synchronization preserved the prior patientSearch. Since list loading correctly applies the search and avoids supplementing mismatched searched results, the new route patient could remain unresolved. Reset search only when explicit requested patient differs from current selection; existing early return retains same-patient paired view state. Added integration with a first-patient-only search followed by second-patient route, verifying search clears, new identity resolves and no automatic risk POST occurs. Nineteen risk/real-App/failure tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-253.json. Live browser navigation still requires acceptance.

## Iteration 254 — clear external patient context before paint

Moved the short requested-patient context reset from useEffect to useLayoutEffect so state clearing is processed before browser repaint. Kept same-selected-patient early return, asynchronous fetching and abort behavior. React official useLayoutEffect documentation supports this timing guarantee and warns against broad use; change is limited to route-bound local resets. Nineteen risk/real-App/failure tests and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-254.json. Reference: https://react.dev/reference/react/useLayoutEffect. Actual frame timing and rendered transitions still require browser acceptance.

## Iteration 255 — reset intake draft before patient route paint

Existing intake effect resets form/search/saved-result/message and advances saveContext on cleanup, protecting against old asynchronous save responses. Moved only this short route-bound reset to useLayoutEffect, matching risk context timing so previous draft clears before repaint. Patient fetching remains passive/asynchronous. Eight intake tests (including route draft clearing and late save success/failure isolation) and production build passed, empty stderr; artifacts/frontend_design/checks-20261014-255.json. Actual visual transitions remain pending browser acceptance; no new mirror lifecycle test added.

## Iteration 256 — preserve chart context safeguards without extra paint blocking

Confirmed patient chart routes have distinct pathname workspace keys, and PatientChart independently gates rendering on result.patientId === current patientId. Fetch also rejects mismatched payload IDs and ignores aborted responses. Unlike query-driven shared intake/risk pages, no new layout effect is needed here. Evidence: artifacts/frontend_design/chart-context-audit-20261014-256.json. This source inspection does not replace live browser transitions; no source changes or redundant tests performed.

## Iteration 257 — full regression of patient context timing

Complete frontend regression passed after explicit route-search clearing and pre-paint risk/intake resets: 201 tests in 28 files, 27.70 seconds, exit 0, empty stderr. Evidence: artifacts/frontend_design/regression-20261014-257.json. Latest production build passed in iteration 255. This verifies current synthetic interaction coverage, including late saves and paired risk views; no frame-level browser or actual idle timeout evidence is claimed. Full original goal remains active.

## Iteration 258 — original-goal completion audit remains incomplete

Re-read current evidence files for complete regression/build, live auth/FHIR/CORS, token contrast and original raster/icon inspection. Engineering compilation and synthetic interaction coverage have current passing evidence; selected live HTTP contracts and original asset visuals also have evidence. These scopes do not prove the requested production-grade rendered experience. The original requirements still lack current desktop/mobile screenshots, real keyboard/native upload/idle workflows, rendered contrast/zoom and runtime performance measurements, plus complete visual reference-case comparison. Branding/source tokens and documentation research are partial evidence, not proof of studio-quality design. Do not mark the overall goal complete or redefine it around passed tests. Browser reconnect request remains pending; no further blanket restyling is justified by this audit.
