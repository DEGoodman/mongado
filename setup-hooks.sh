#!/bin/bash
# Setup script to install git hooks

set -e

echo "🪝 Setting up git hooks..."

# Configure git to use .githooks directory
git config core.hooksPath .githooks

echo "✓ Git hooks configured successfully!"
echo ""
echo "The following hooks are now active:"
echo "  • commit-msg: Adds DCO Signed-off-by trailer automatically"
echo "  • pre-push: Runs quality checks and DCO verification before pushing"
echo ""
echo "To skip hooks temporarily, use: git push --no-verify"
