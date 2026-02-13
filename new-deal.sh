#!/usr/bin/env bash
# new-deal.sh — Create a new deal review workspace
#
# Usage:
#   ./new-deal.sh <deal_name> <agreement_file> [options]
#
# Examples:
#   ./new-deal.sh centtral-aventura agreement.docx --posture borrower_friendly
#   ./new-deal.sh ocean-bank-construction loan.docx -t term_sheet.docx -k skills/construction-loan-negotiation.md
#   ./new-deal.sh yacht-financing agreement.docx --posture lender_friendly --notes "Marina collateral"
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 2 ]; then
    echo "Usage: ./new-deal.sh <deal_name> <agreement_file> [options]"
    echo ""
    echo "Creates a new deal workspace in deals/<deal_name>/"
    echo ""
    echo "Options (passed through to prepare_deal.py):"
    echo "  --posture, -P    borrower_friendly|lender_friendly|balanced|compliance_only"
    echo "  --term-sheet, -t Path to term sheet"
    echo "  --skill, -k      Path to skill file (repeatable)"
    echo "  --style, -s      Heading style to split on"
    echo "  --pattern, -p    Regex pattern to split on"
    echo "  --notes, -n      Client-specific notes"
    echo ""
    echo "Examples:"
    echo "  ./new-deal.sh my-deal agreement.docx --posture borrower_friendly"
    echo "  ./new-deal.sh my-deal agreement.docx -t term_sheet.docx -k skills/construction-loan-negotiation.md"
    exit 1
fi

DEAL_NAME="$1"
AGREEMENT="$2"
shift 2

OUTPUT_DIR="$SCRIPT_DIR/deals/$DEAL_NAME"

if [ -d "$OUTPUT_DIR" ]; then
    echo "⚠️  Deal workspace already exists: $OUTPUT_DIR"
    echo "   Use 'python scripts/prepare_deal.py --status $OUTPUT_DIR' to check progress."
    exit 1
fi

echo "Creating deal workspace: $OUTPUT_DIR"
echo ""

python3 "$SCRIPT_DIR/scripts/prepare_deal.py" "$AGREEMENT" \
    --output-dir "$OUTPUT_DIR" \
    "$@"

echo ""
echo "Next steps:"
echo "  cd $OUTPUT_DIR"
echo "  claude"
echo "  /review-all"
