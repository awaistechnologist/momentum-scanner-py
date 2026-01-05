#!/bin/bash
# Pre-commit hook to prevent committing sensitive data
# Install: ln -s ../../.pre-commit-check.sh .git/hooks/pre-commit

echo "🔍 Checking for sensitive data..."

# Check if .env or config.json are being committed
if git diff --cached --name-only | grep -qE '^\.env$|^config\.json$'; then
    echo "❌ ERROR: Attempting to commit sensitive files!"
    echo ""
    echo "The following files should NOT be committed:"
    git diff --cached --name-only | grep -E '^\.env$|^config\.json$'
    echo ""
    echo "These files contain API keys and are in .gitignore for a reason."
    echo ""
    echo "To fix:"
    echo "  git reset HEAD .env config.json"
    echo ""
    exit 1
fi

# Check for potential API keys in staged files
if git diff --cached | grep -qiE '(api[_-]?key|api[_-]?secret|token|password).*=.*[A-Za-z0-9]{20,}'; then
    echo "⚠️  WARNING: Potential API key detected in staged files!"
    echo ""
    echo "Searching for patterns like API_KEY=xxxxx..."
    git diff --cached | grep -iE '(api[_-]?key|api[_-]?secret|token|password).*=.*[A-Za-z0-9]{20,}'
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Commit aborted."
        exit 1
    fi
fi

echo "✅ Pre-commit check passed"
exit 0
