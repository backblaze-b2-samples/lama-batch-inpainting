# Tech debt

## 2026-07-16 — verify

- Dashboard (/) first-time empty state — the sole prominent CTA is "New job" (→ /jobs/new) while the true first step for a zero-image user is Upload → a first-timer may detour through an empty New Job screen; not a dead-end (jobs/new offers an "Upload images" button) (.local/verify/A/A2-01-dashboard.png)
- Job detail (/jobs/[id]) after "Approve all" — a transient toast confirms approval but the page keeps the Approve buttons enabled and the badge reads "Completed" (not "Approved") → once the toast fades the user can't tell from the page whether they already approved (only the Dashboard "Approved" counter reflects it) (.local/verify/A/A2-10-approved.png)
- Job detail (/jobs/[id]) during a single-image run — the determinate progress bar stays pinned at 0% for the whole model-load+inpaint (~8–16s) then jumps to 100%, and the stage text reads "0/1 pair done (0%)" through the model-load phase; the animated spinner + "this can take a moment per image" copy keep it from reading as frozen and the bar does advance per-pair for N>1, so it's cosmetic on the single-image path (.local/verify/B/B2-09b-H1-inpaint-inflight.png)
- Job detail (/jobs/[id]) after a mid-run page reload — the source/mask triptych cells render briefly blank while presigned asset URLs re-fetch, self-healing within ~1s (edge case only; the app stays usable) (.local/verify/B/B2-11b-H6-reload-midrun.png)
- Job detail (/jobs/[id]) batch mid-run — a pair still Pending renders a broken-image glyph in its "Inpainted output" cell instead of a "pending/awaiting output" placeholder, so it momentarily looks like an error; self-resolves on completion (.local/verify/C/C2-15-job2-completed-batch-triptych.png)
- Dashboard (/) storage-amplification tile — shows 1.29× with the formula "(output + masks) relative to source bytes" while the README markets "~3× its input volume"; the metric excludes the retained source from the numerator so it understates the 3× storytelling (still > 1 and reflects the runs — a definition/wording mismatch, not a flow defect) (.local/verify/C/C2-19-dashboard-after.png)

## 2026-07-17 — verify

Resolved this run (both were 2026-07-16 nitpicks; the 3-lens funnel + adversarial gate escalated them to friction and they were fixed): the storage-amplification tile now leads with an honest object-count amplification (~3×+ — every source retains its mask and gains an output) alongside a clearly-labeled byte ratio; the Job detail page now shows a persistent per-pair "Approved" badge plus an "N/total approved" header instead of a toast-only signal. The two-pass source/mask Upload was confirmed by-design (a source and its mask share the same base filename, so a mixed drop can't be auto-split) and now offers a one-click "Upload masks next" step after the source pass.

Surviving nitpicks:

- Job detail (/jobs/[id]) pending pair — the "Inpainted output" cell of a not-yet-processed pair renders the generic ImageOff broken-image glyph with no caption → indistinguishable from a failed image load; only the per-pair "Pending" badge and the top progress panel disambiguate. A "not generated yet — run inpainting" placeholder would remove the ambiguity (.local/verify-r4/A/08-pending-job-detail.png)
- Sidebar (all screens) — nav order Dashboard, Jobs, Library, Upload, Files, Settings puts the mandatory first step (Upload) third, counter to the task order Upload → Library → New Job → Run → Review; mitigated because empty-state CTAs chain the user correctly, so never a dead-end (.local/verify-r4/A/01-dashboard.png)
- Library (/library) — an unpaired source shows a "No mask" badge but no per-card "add mask" affordance → the user must go to Upload and re-upload a matching mask by exact base filename, away from where the gap is surfaced (.local/verify-r4/A/07-library.png)
- Job not-found (/jobs/[bad-id]) — the "Job '<id>' not found" state offers no inline "back to Jobs" link or button; recovery relies solely on the persistent sidebar (.local/verify-r3/A/10-bogus-job-id.png)
- Backend (services/api/app/service/jobs.py) — a code comment asserts the byte-amplification ratio "can never show the ~3× story," but after multiple runs it reads 3.45× because output PNG bytes dominate; align the comment with the shipped object + byte amplification metrics (code, no shot)
