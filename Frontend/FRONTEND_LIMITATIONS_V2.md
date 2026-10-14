# EduSphere Frontend — Remaining Limitations After UX Refactor

This list is scoped to the Vue frontend and to capabilities exposed by the current Django API. It does not imply a defect in the normalized Oracle schema.

## Improved in this version

- Course Catalog now recognizes the logged-in student's existing offerings and does not offer duplicate enrollment.
- Manual numeric IDs were removed from normal user workflows wherever the current APIs expose enough relational context.
- OfferingWorkspaceView is now an orchestration shell; individual tabs are separate components.
- Student Performance and Admin Reports use structured tables, cards, charts and calendars instead of raw JSON.
- Mutating actions have disabled/busy states and confirmations for important irreversible operations.
- Quiz attempts have an advisory countdown, progress, unanswered navigation, local drafts, and edit-before-final-submit behavior.
- Data tables provide client-side search, sorting and pagination.
- URL-backed file fields now include drag/drop local-file selection for metadata/validation and clear capability messaging.
- Session/exam views and performance/report pages include calendar and chart views.

## Remaining/new limitations

1. **Persistent direct file upload is not available.** The current backend stores `material_url` and `file_url`; it does not expose a multipart/binary upload endpoint. The frontend can validate a local file but must still submit a hosted/shared URL.
2. **Quiz countdown is advisory after a fresh reload/device switch.** Quiz content returns `attempt_id` and duration but not the authoritative `STARTED_AT`. The frontend stores a start timestamp in `sessionStorage`; Oracle remains authoritative for expiry.
3. **Open-attempt answers cannot be reloaded or updated from the server.** The current API creates responses/options but has no endpoint to fetch/edit an in-progress attempt's responses. Draft editing therefore remains browser-session local until final submission. Partial network failures can leave already-transmitted questions locked.
4. **Admin student discovery is roster-derived.** With no general Admin `GET /students/` directory endpoint, the frontend builds its student selector by reading offering rosters. A student with no enrollment will not appear, and large datasets would cause many requests.
5. **Question-bank quiz discovery is multi-request.** There is no single instructor/admin quiz directory endpoint, so the frontend discovers offerings -> grading components -> quizzes. This is fine for the course-project dataset but is an N+1-style scaling limitation.
6. **Tables are client-side.** Search, sorting and pagination operate on rows already returned by the API. Very large datasets should use server-side query/search/pagination.
7. **Calendar is display-oriented.** It does not support drag-to-reschedule, recurring events, timezone configuration, or collision visualization.
8. **Charts are lightweight CSS visualizations.** They do not provide advanced tooltips, zooming, export, statistical overlays or accessible data-sonification.
9. **Edit/delete workflows remain limited by current API coverage.** Many modules primarily expose create/list/read operations; the frontend cannot safely invent update/delete capabilities that are not in the backend contract.
10. **No real-time synchronization.** Another user's changes appear after refresh/reload; there is no WebSocket/SSE notification layer.
11. **General forms do not have persistent drafts.** Quiz answers are session-drafted, but assignment/announcement/quiz-authoring forms can still be lost on refresh/navigation.
12. **Authentication uses sessionStorage tokens.** This is simple for the course project, but a production deployment should review cookie/token strategy, CSRF/XSS threat models and session revocation.
13. **Accessibility is improved but not formally audited.** Keyboard behavior, focus trapping, contrast and screen-reader semantics still need a dedicated WCAG pass.
14. **No automated browser E2E suite yet.** Static smoke checks exist, but Playwright/Cypress-style end-to-end coverage is not part of this frontend package.
