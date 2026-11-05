## What and why

<!-- One or two sentences. Link the plan item (docs/superpowers/plans/...) if there is one. -->

## Evidence

<!-- Honesty rule: say exactly what you ran. Unit tests only? A VM run? Hardware? Paste command and result. -->

- [ ] `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test`
- [ ] `python -m pytest tests -q` (and the QML tests if you touched QML)
- [ ] ShellCheck clean for changed shell scripts
- [ ] `docs/CLAIMS.md` updated if a feature's status changed (no unverified claims)
- [ ] No secrets, no ISOs/VM disks, no generated files committed
