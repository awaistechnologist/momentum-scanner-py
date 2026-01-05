#!/bin/bash
# Verify repository is safe to publish to GitHub
# Run this before pushing to GitHub

echo "🔍 Running safety checks before GitHub publication..."
echo ""

errors=0
warnings=0

# Check 1: Verify .gitignore exists and contains sensitive files
echo "1️⃣ Checking .gitignore..."
if [ ! -f ".gitignore" ]; then
    echo "   ❌ .gitignore not found!"
    errors=$((errors + 1))
else
    if grep -q "^\.env$" .gitignore && grep -q "^config\.json$" .gitignore; then
        echo "   ✅ .gitignore properly configured"
    else
        echo "   ❌ .gitignore missing .env or config.json"
        errors=$((errors + 1))
    fi
fi

# Check 2: Verify no sensitive files are tracked by git
echo ""
echo "2️⃣ Checking for tracked sensitive files..."
tracked_sensitive=$(git ls-files | grep -E '^\.env$|^config\.json$' || true)
if [ -z "$tracked_sensitive" ]; then
    echo "   ✅ No sensitive files tracked by git"
else
    echo "   ❌ DANGER: Sensitive files are tracked!"
    echo "$tracked_sensitive"
    errors=$((errors + 1))
fi

# Check 3: Verify .env.example exists and contains no real keys
echo ""
echo "3️⃣ Checking .env.example..."
if [ ! -f ".env.example" ]; then
    echo "   ⚠️  .env.example not found"
    warnings=$((warnings + 1))
else
    if grep -qE '[A-Z0-9]{20,}' .env.example; then
        echo "   ⚠️  WARNING: .env.example may contain real API keys!"
        grep -E '[A-Z0-9]{20,}' .env.example
        warnings=$((warnings + 1))
    else
        echo "   ✅ .env.example looks safe"
    fi
fi

# Check 4: Verify config.example.json exists
echo ""
echo "4️⃣ Checking config.example.json..."
if [ -f "scanner/config/config.example.json" ]; then
    echo "   ✅ config.example.json exists"
else
    echo "   ⚠️  config.example.json not found"
    warnings=$((warnings + 1))
fi

# Check 5: Check for API keys in staged files
echo ""
echo "5️⃣ Checking staged files for API keys..."
if git diff --cached --quiet; then
    echo "   ℹ️  No files staged for commit"
else
    if git diff --cached | grep -qiE '(api[_-]?key|api[_-]?secret|token|password).*=.*[A-Za-z0-9]{20,}'; then
        echo "   ⚠️  WARNING: Potential API keys in staged files!"
        warnings=$((warnings + 1))
    else
        echo "   ✅ No obvious API keys in staged files"
    fi
fi

# Check 6: Verify documentation exists
echo ""
echo "6️⃣ Checking documentation..."
missing_docs=""
[ ! -f "README.md" ] && missing_docs="$missing_docs README.md"
[ ! -f "SECURITY.md" ] && missing_docs="$missing_docs SECURITY.md"
[ ! -f "CONTRIBUTING.md" ] && missing_docs="$missing_docs CONTRIBUTING.md"
[ ! -f "LICENSE" ] && missing_docs="$missing_docs LICENSE"

if [ -z "$missing_docs" ]; then
    echo "   ✅ All documentation files present"
else
    echo "   ⚠️  Missing documentation:$missing_docs"
    warnings=$((warnings + 1))
fi

# Check 7: Verify .env and config.json exist locally
echo ""
echo "7️⃣ Checking local configuration files..."
if [ -f ".env" ] && [ -f "config.json" ]; then
    echo "   ✅ Local .env and config.json exist"
else
    echo "   ⚠️  Missing local config files (you'll need to create them after cloning)"
    warnings=$((warnings + 1))
fi

# Summary
echo ""
echo "======================================"
if [ $errors -eq 0 ]; then
    echo "✅ Safety check PASSED"
    echo ""
    if [ $warnings -gt 0 ]; then
        echo "⚠️  $warnings warning(s) found (review recommended)"
    else
        echo "🚀 Repository is safe to publish to GitHub!"
    fi
    echo ""
    echo "Next steps:"
    echo "  1. Create a new repository on GitHub"
    echo "  2. git remote add origin <your-repo-url>"
    echo "  3. git add ."
    echo "  4. git commit -m 'Initial commit'"
    echo "  5. git push -u origin main"
    exit 0
else
    echo "❌ Safety check FAILED"
    echo ""
    echo "🛑 $errors error(s) and $warnings warning(s) found"
    echo ""
    echo "DO NOT push to GitHub until errors are fixed!"
    exit 1
fi
