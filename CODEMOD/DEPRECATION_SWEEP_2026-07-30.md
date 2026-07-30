Deprecation sweep report (2026-07-30)

Summary
-------
I scanned the codebase for high-confidence deprecated patterns and mechanical replacements:
- `ugettext`, `ugettext_lazy` -> `gettext`, `gettext_lazy`
- `force_text` -> `force_str`
- `datetime.now(` -> `django.utils.timezone.now()`
- `from django.conf.urls import url` -> `django.urls.re_path` or `path`

Result
------
No occurrences of `ugettext`, `ugettext_lazy`, or `force_text` were found.
All instances of `datetime.now(` were already replaced with `timezone.now()` earlier.
No `from django.conf.urls import url` imports were found.

Actions taken
-------------
- Created this report file under `CODEMOD/DEPRECATION_SWEEP_2026-07-30.md` on branch `codemod/deprecations`.
- No code changes were necessary for the patterns we searched for.

How to proceed
--------------
- If you want me to perform additional, lower-confidence codemods (e.g., automatically converting `url()` calls to `re_path()` across the repo), I can run them, but they may require manual review.
- To open a PR: push the branch (already done) and create a PR from `codemod/deprecations` into `development` on GitHub. If you want, I can attempt to create the PR using the `gh` CLI if it's installed and authenticated in this environment.
