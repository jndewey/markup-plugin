#!/usr/bin/env bash
# setup.sh — One-time setup for Markup
set -e

echo "============================================"
echo "  Markup — Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found."
    exit 1
fi
echo "✅ Python $(python3 --version 2>&1 | cut -d' ' -f2)"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages -q 2>/dev/null || \
    pip install -r requirements.txt -q
echo "✅ Python dependencies installed"

# Check for Claude Code
if command -v claude &> /dev/null; then
    echo "✅ Claude Code found"
else
    echo "⚠️  Claude Code not found. Install from: https://docs.anthropic.com/en/docs/claude-code"
fi

# Create deals directory
mkdir -p deals
echo "✅ deals/ directory ready"

# Make scripts executable
chmod +x scripts/*.py
echo "✅ Scripts marked executable"

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Quick start:"
echo ""
echo "  # Prepare a deal workspace"
echo "  python scripts/prepare_deal.py /path/to/agreement.docx \\"
echo "      --posture borrower_friendly \\"
echo "      --term-sheet /path/to/term_sheet.docx \\"
echo "      --skill skills/construction-loan-negotiation.md \\"
echo "      --output-dir deals/my_deal"
echo ""
echo "  # Launch Claude Code in the workspace"
echo "  cd deals/my_deal"
echo "  claude"
echo ""
echo "  # Then use slash commands:"
echo "  /review-all"
echo "  /status"
echo "  /apply-redlines"
echo "  /generate-deliverables"
echo ""
