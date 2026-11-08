# Landing viewport regression follow-up - 6 November 2026

## Completed scope

Reviewed the latest context, authentication delivery reports and saved work queue (documentation compilation pages 42-43). The previous Google authentication task was complete, with one explicitly recorded unrelated viewport failure remaining.

Reproduced that landing test failure. The current `Frontend/src/styles/publicLandingLayout.css` deliberately gives public heroes a full viewport minimum height and puts the following search/steps card in normal document flow. The older test incorrectly required the entire booking panel inside the opening viewport.

Updated only the test: verify the booking panel starts after the hero, scroll it into view, then retain checks that the panel and every input/select/button fit inside the viewport with no horizontal page overflow. Reduced motion makes the scroll measurement deterministic. Four desktop and two mobile viewport sizes remain covered. No product layout or behavior changed.

Relevant Final Decisions were consulted from compilation page 8. No API, data or operational module contract change was needed for this test-only correction. No environment values were read or changed.

## Changed files

- `Frontend/tests/browser/auth-viewport-fit.spec.js`
- `docs/validation/google-sign-in-2026-11-05.md` - append follow-up without rewriting historical evidence.
- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`
- This report.

## Tests

`npx.cmd playwright test tests/browser/auth-viewport-fit.spec.js --project=desktop` from `Frontend`: **5 passed (31.0 seconds)** using Chrome. The tests explicitly select desktop/mobile dimensions. Coverage includes desktop auth fit, mobile scrolling, visible validation errors, registration payload and the landing panel after scrolling.

No backend tests or production build were needed for this test-only change.

## Deferred scope, blockers and next dependency

No blocker remains for this viewport follow-up. Live Google provider setup/testing remains separate, requiring a valid configured client and allowed origin. Ride completion, payments/refunds, tracking and remaining dashboard operational modules were not started; the saved work queue requires explicit scope and unresolved business decisions before dependent implementation. Existing worktree changes were preserved.
