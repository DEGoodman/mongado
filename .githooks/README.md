# Git Hooks

This directory contains git hooks that run automated checks before certain git operations.

## Setup

Run the setup script from the repository root to enable hooks:

```bash
./setup-hooks.sh
```

This configures git to use the `.githooks` directory for all hooks.

## Available Hooks

### pre-push

Runs before `git push` to catch issues before they reach CI.

**Checks performed:**

Backend:
- ✓ Linting (ruff)
- ⚠ Type checking (mypy) - warnings only, doesn't block
- ✓ Security scanning (bandit)

Frontend:
- ✓ Linting (eslint)
- ✓ Type checking (tsc)
- ✓ Code formatting (prettier)

**What's NOT checked:**
- Unit tests (run in CI)
- Integration tests (run in CI)
- E2E tests (run in CI)
- Coverage reports (run in CI)

These longer-running tests remain in CI to keep the pre-push hook fast (typically < 10 seconds).

## Skipping Hooks

If you need to bypass the hooks temporarily (not recommended):

```bash
git push --no-verify
```

## Troubleshooting

If hooks aren't running:
1. Verify hooks are configured: `git config core.hooksPath`
2. Should return: `.githooks`
3. If not, run `./setup-hooks.sh` again

If hooks fail:
1. Read the error messages - they tell you how to fix the issues
2. Run the suggested commands to see details
3. Fix the issues and try pushing again
