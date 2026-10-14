# EduSphere Frontend — Limitations After Error-Handling Hardening

This document is scoped to the Vue frontend. It distinguishes limitations that were fixed in this revision from limitations that still require backend/API changes or a larger production-grade frontend architecture.

## Fixed in this revision

1. **Raw Oracle/ODBC errors no longer appear in the UI.**
   - Technical strings such as `HY000`, `ODBC`, `SQLExecDirectW`, `ORA-06512`, schema/procedure names and Django debug HTML are sanitized before display.
   - Known Oracle business-rule codes are translated into user-facing messages.
   - Example: ORA-20113 now displays **“You have used all attempts allowed for this quiz.”**

2. **Quiz startup no longer treats every HTTP 400 as “start a new attempt”.**
   - The frontend now starts an attempt only when the backend specifically reports that an attempt must be started before quiz content can be loaded.
   - Maximum-attempt, closed-quiz, not-enrolled and other business errors remain errors instead of triggering another start request.

3. **Quiz fatal errors now use a dedicated error state.**
   - Friendly title/message.
   - Retry appears only for retryable failures.
   - Business-rule failures such as no attempts remaining do not misleadingly show a retry action.

4. **Network/offline/timeout handling is clearer.**
   - API requests have a configurable timeout.
   - Offline/network failures show a clear message instead of `Failed to fetch`.
   - The application shell shows an Offline indicator when the browser reports loss of network connectivity.

5. **JWT refresh is single-flight.**
   - Multiple requests receiving 401 at the same time reuse one refresh request instead of starting several competing refreshes.

6. **Duplicate error toasts are suppressed.**
   - The same error is not repeatedly stacked while an identical toast is already visible.

7. **Unhandled promise errors are surfaced as safe frontend notifications.**
   - Technical details are normalized before display.

## Remaining/new limitations

1. **The backend can still transmit technical database text over HTTP.**
   - This revision hides it from normal UI rendering, but browser DevTools can still inspect the raw network response.
   - Fully eliminating that information disclosure requires backend-side sanitization/classification before sending the response.

2. **Some database business rules still arrive under broad backend error categories.**
   - The frontend recognizes known Oracle codes/messages, but it cannot perfectly infer every future database rule.
   - A structured backend error contract such as `error_code: QUIZ_MAX_ATTEMPTS` would be more stable than phrase/code mapping.

3. **No submitted-attempt history endpoint.**
   - When a student has exhausted quiz attempts, the frontend can explain the condition but cannot automatically show the most recent attempt/result because there is no “my attempts for this quiz” endpoint.

4. **Open-attempt answer recovery remains browser-local.**
   - The backend still has no endpoint to fetch/edit in-progress answers.
   - Refreshing on another browser/device cannot reconstruct local drafts.
   - Partial submission/network failure can leave some responses already stored server-side while unsent answers remain local.

5. **Persistent file upload is still unavailable.**
   - Material and assignment APIs accept URLs rather than multipart/binary uploads.
   - The frontend cannot provide real persistent upload without backend storage/upload support.

6. **Admin student discovery is still roster-derived.**
   - No general Admin student-directory endpoint exists.
   - Students with no enrollment do not appear in the derived selector.
   - Large datasets cause many roster requests.

7. **Question-bank quiz discovery still uses multiple API calls.**
   - Offerings -> grading components -> quizzes is an N+1-style discovery path.

8. **Tables still paginate/search/sort client-side.**
   - Good for the project dataset, but not for very large datasets.

9. **No automatic retry for mutating requests.**
   - This is intentional: automatically retrying POST/PATCH can duplicate writes unless the backend supports idempotency keys.
   - The UI therefore asks the user to retry after failures rather than replaying writes automatically.

10. **No request cancellation on every route transition.**
    - Long-running fetches may finish after navigation. The transport supports abort signals, but pages do not yet attach a controller to every load request.

11. **No real-time synchronization.**
    - Instructor/admin changes made in another browser appear only after refresh/reload.

12. **No persistent drafts for most authoring forms.**
    - Quiz answer drafts are session-backed, but assignment/announcement/question/exam forms are not.

13. **Calendar/timezone handling is basic.**
    - The UI assumes backend-provided dates/times are appropriate for local display and does not expose timezone controls.

14. **Charts remain lightweight visual components.**
    - No advanced tooltip/export/zoom or formal accessibility audit.

15. **No formal browser E2E test suite.**
    - Static smoke tests exist, including the new error-sanitization smoke check, but Playwright/Cypress tests are not included.

16. **Frontend error boundaries are partial.**
    - Promise failures are normalized globally, but Vue component-render exceptions do not yet have a dedicated recovery boundary/screen.

17. **No optimistic undo/rollback UI.**
    - Successful creates/updates are refreshed from the server, but there is no “Undo” workflow for supported mutations.

18. **Accessibility still needs a dedicated WCAG pass.**
    - Error states use semantic alerts, but keyboard/focus/contrast/screen-reader behavior across the whole application has not been formally audited.
