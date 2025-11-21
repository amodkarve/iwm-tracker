#!/bin/bash
# Commit and push script for IWM Tracker
# Usage: ./scripts/commit_and_push.sh "commit message"

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Check if commit message is provided
if [ -z "$1" ]; then
    echo "❌ Error: Commit message is required"
    echo "Usage: ./scripts/commit_and_push.sh \"commit message\""
    exit 1
fi

COMMIT_MESSAGE="$1"

echo "📝 Committing and pushing changes"
echo "=================================="
echo ""

# Check if there are any changes to commit
if git diff --quiet && git diff --cached --quiet; then
    echo "ℹ️  No changes to commit"
    exit 0
fi

# Show status
echo "📊 Current status:"
git status --short
echo ""

# Stage all changes
echo "📦 Staging all changes..."
git add -A
echo "✅ Changes staged"
echo ""

# Commit with message
echo "💾 Committing changes..."
git commit -m "$COMMIT_MESSAGE"
echo "✅ Changes committed"
echo ""

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 Current branch: $CURRENT_BRANCH"
echo ""

# Push to remote
echo "🚀 Pushing to remote..."
git push origin "$CURRENT_BRANCH"
echo "✅ Changes pushed to remote"
echo ""

echo "🎉 Done!"

