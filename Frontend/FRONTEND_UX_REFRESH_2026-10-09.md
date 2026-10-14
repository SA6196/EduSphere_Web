# EduSphere Frontend UX Refresh — 9 October 2026

This update is a Vue 3 frontend-only pass based on the latest saved EduSphere project package.

## Changes

- Refined the shared visual system across student, instructor, and administrator views: consistent spacing, cards, borders, shadows, typography, focus rings, form controls, button states, and responsive layouts.
- Added reduced-motion support and clearer keyboard focus visibility.
- Improved sidebar interaction and active navigation semantics, including an accessible mobile-menu label and `aria-current` on the active route.
- Improved reusable data-table accessibility by exposing the current sort direction to assistive technology.
- Added question-bank search by question text or ID, filtering by question type, per-type counts, result counts, and clearer selected-question actions.
- Added student-dashboard quick access to quiz attempts, performance, and the course catalog.
- Surfaced upcoming exams directly on the student dashboard instead of showing only an exam count.
- Improved quiz-taking accessibility with an announced progress bar, completion percentage, descriptive question navigation labels, and descriptive matching-select labels.
- Made the grading review call out attempts containing LONG_TEXT questions so instructors are reminded to review written answers manually.

## Compatibility and safety boundaries

- No backend files were intentionally changed.
- No database scripts, relations, columns, constraints, or API contracts were changed.
- Auto-grading logic and marks/answer visibility rules were not changed.
- Existing Vue 3 and Vue Router structure was retained; no new UI framework or runtime dependency was introduced.

## Verification

- JavaScript syntax checks passed for the `<script>` blocks extracted from all Vue single-file components.
- A full Vite production build could not be run in this environment because npm dependencies were not fully available locally and the package registry was unreachable. Run `npm ci` followed by `npm run build` in the frontend directory on a machine with package-registry access before deployment.
