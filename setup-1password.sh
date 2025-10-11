#!/bin/bash
# Setup script for 1Password service account token
# This script helps you add the OP_SERVICE_ACCOUNT_TOKEN to your shell profile

echo "🔐 1Password Service Account Setup"
echo "=================================="
echo ""

# Detect shell
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    echo "⚠️  Could not detect shell type. Please manually add to your shell profile."
    exit 1
fi

echo "Detected shell: $SHELL_NAME"
echo "Profile file: $SHELL_RC"
echo ""

# Check if already configured
if grep -q "OP_SERVICE_ACCOUNT_TOKEN" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  OP_SERVICE_ACCOUNT_TOKEN already exists in $SHELL_RC"
    echo ""
    echo "To update it:"
    echo "  1. Open $SHELL_RC in your editor"
    echo "  2. Find the line with OP_SERVICE_ACCOUNT_TOKEN"
    echo "  3. Update the token value"
    echo "  4. Run: source $SHELL_RC"
    exit 0
fi

# Prompt for token
echo "Please paste your 1Password service account token:"
echo "(It should start with 'ops_')"
echo ""
read -r -p "Token: " TOKEN

# Validate token format
if [[ ! "$TOKEN" =~ ^ops_ ]]; then
    echo ""
    echo "⚠️  Warning: Token doesn't start with 'ops_'"
    echo "   Make sure you're using a service account token"
    echo ""
    read -r -p "Continue anyway? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Add to shell profile
echo "" >> "$SHELL_RC"
echo "# 1Password Service Account for mongado project" >> "$SHELL_RC"
echo "export OP_SERVICE_ACCOUNT_TOKEN=\"$TOKEN\"" >> "$SHELL_RC"

echo ""
echo "✅ Token added to $SHELL_RC"
echo ""
echo "Next steps:"
echo "  1. Reload your shell configuration:"
echo "     source $SHELL_RC"
echo ""
echo "  2. Verify it's set:"
echo "     echo \$OP_SERVICE_ACCOUNT_TOKEN"
echo ""
echo "  3. Start the application:"
echo "     docker compose up"
echo ""
echo "Note: The token will be available in all new terminal windows automatically."
