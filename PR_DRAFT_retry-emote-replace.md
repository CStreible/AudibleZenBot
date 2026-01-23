Title: Fix broken Twitch emote renders with UI-side data-URI fallback and onload-swap

Branch: tests/persistence-additions

Summary
- Detect and replace broken `file:///` emote images in the WebEngine DOM by
  building a `data:` URI (manager first, disk fallback) and performing a safe
  onload swap using a newly-loaded `Image()` so the DOM is only updated if the
  replacement actually decodes.

Files changed (high level)
- `ui/chat_page.py`: added `build_data_uri_for_emote`, probe callbacks, and
  modified replacement JS to use onload-swap. Emits `RETRY_EMOTE_REPLACE` logs
  when the UI performs replacements.
- `tests/`: added unit tests and an integration test exercising the onload-swap:
  - `tests/test_emote_fallback_disk.py`
  - `tests/test_emote_manager_none_fallback.py`
  - `tests/test_emote_additional_units.py`
  - `tests/test_emote_integration_onload.py`
  - several other test skeletons for future cases
- `.github/workflows/ci.yml`: CI workflow to run tests under Xvfb with
  `PyQt6-QtWebEngine` on Ubuntu runners.
- `docs/HEADLESS_QT_CI.md`: instructions for CI/local setup for headless Qt.

Selected log excerpts (from a 10-minute tail capture saved to `artifacts/integration-logs/tail_capture.txt`)

RENDER_PROBE entries showing data: URIs successfully decoding (naturalWidth>0):

```
1769191245.868 RENDER_PROBE message_id=65578893-32db-46c4-808e-615a0c369b18 probe=[{"complete": true, "currentSrc": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAIA...", "dataEmoteId": "emotesv2_7d062a...", "naturalHeight": 28, "naturalWidth": 28, "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAIA..."}]

1769191245.868 RENDER_PROBE message_id=65578893-32db-46c4-808e-615a0c369b18 probe=[{"complete": true, "currentSrc": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAYAAAByDd+U...", "dataEmoteId": "emotesv2_1adf4c4...", "naturalHeight": 28, "naturalWidth": 28, "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAYAAAByDd+U..."}]
```

Earlier probes showed broken `file:///` renders (reproduced in prod prior to this change), and the new retry flow emits `RETRY_EMOTE_REPLACE` when replacements are applied. The CI and local tests exercise the disk fallback (unit) and the JS onload-swap (integration, requires headless Qt).

How to open the PR from this branch
1. Create the branch locally and push it:

```bash
git checkout -b tests/persistence-additions
git add -A
git commit -m "UI: retry emote replace using data-URI disk fallback + onload swap; tests + CI"
git push origin tests/persistence-additions
```

2. Open a PR using GitHub CLI (recommended):

```bash
gh pr create --base main --head tests/persistence-additions --title "Fix broken Twitch emote renders" --body-file PR_DRAFT_retry-emote-replace.md
```

If you prefer, I can open the PR for you if you provide push access or run the `git push`/`gh pr create` steps locally.
