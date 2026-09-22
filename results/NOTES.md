## Method

- The corpus is 105 cases: 53 from skillkeel-starter's own hook tests and 52 from lumis-skills (MIT, credited on each case). It is a test suite written by two guard authors, not a neutral sample; read the rows with that in mind.
- One row per family, no aggregate score, no ranking. A family a hook does not claim to cover is stated as outside its scope in the note above, not read as a defect.
- Every third-party row pins the commit or release, the exact command line, the Claude Code version and the date, and keeps the full results JSON in `results/`. The verdict channel (exit 2, JSON deny, JSON ask) is checked by hand on one case per hook before the run.
- Third-party hooks run in a bubblewrap sandbox: read-only system, private home, no network, the hook's own files mounted read-only.
- A row submitted by someone else by PR (results JSON, both commits, command line) is labelled "submitted by <author>, not reproduced by Skillkeel".
- Corrections: open an issue or PR on this repo; answered within 48 hours. A corrected row keeps the old one struck through with the date.

## Not run: Dicklesworthstone/destructive_command_guard

Not run as of 2026-09-22. Its LICENSE is MIT with a rider under which no rights are granted to "Restricted Parties", defined as OpenAI, Anthropic, their affiliates "and any person or entity acting directly or indirectly on behalf of, for the benefit of, or under the direction of any of the foregoing", and under which "use" includes "executing, benchmarking, testing, analyzing ... evaluation harness" (LICENSE at commit 1d20ec67ed, read 2026-09-22). This benchmark is run by a Claude agent; whether that reading applies is not ours to decide, so the author has been asked in writing. The author is welcome to run the corpus and submit a row.
