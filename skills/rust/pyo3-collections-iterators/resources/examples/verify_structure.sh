#!/bin/bash
# Verification script for PyO3 collections-iterators examples

set -e

EXAMPLES_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$EXAMPLES_DIR"

echo "=== PyO3 Collections & Iterators Examples Verification ==="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

errors=0
warnings=0

echo "Checking example directories..."

for i in 01 02 03 04 05 06 07 08 09 10; do
    # Find directory matching pattern
    dir=$(find . -maxdepth 1 -type d -name "${i}_*" | head -1)

    if [ -z "$dir" ]; then
        echo -e "${RED}✗${NC} Example $i directory not found"
        ((errors++))
        continue
    fi

    dir_name=$(basename "$dir")
    echo -e "${GREEN}✓${NC} Found $dir_name"

    # Check required files
    required_files=("src/lib.rs" "Cargo.toml" "pyproject.toml" "test_example.py" "README.md")

    for file in "${required_files[@]}"; do
        if [ ! -f "$dir/$file" ]; then
            echo -e "  ${RED}✗${NC} Missing $file"
            ((errors++))
        fi
    done

    # Check file sizes
    if [ -f "$dir/src/lib.rs" ]; then
        lines=$(wc -l < "$dir/src/lib.rs")
        if [ "$lines" -lt 50 ]; then
            echo -e "  ${YELLOW}⚠${NC} lib.rs seems small ($lines lines)"
            ((warnings++))
        fi
    fi

    if [ -f "$dir/test_example.py" ]; then
        lines=$(wc -l < "$dir/test_example.py")
        if [ "$lines" -lt 20 ]; then
            echo -e "  ${YELLOW}⚠${NC} test_example.py seems small ($lines lines)"
            ((warnings++))
        fi
    fi
done

echo ""
echo "=== Summary ==="
echo "Total examples: 10"
echo "lib.rs files: $(find . -name 'lib.rs' | wc -l | tr -d ' ')"
echo "Test files: $(find . -name 'test_example.py' | wc -l | tr -d ' ')"
echo "README files: $(find . -name 'README.md' | wc -l | tr -d ' ')"
echo ""
echo "Total Rust lines: $(find . -name 'lib.rs' -exec wc -l {} + | tail -1 | awk '{print $1}')"
echo "Total test lines: $(find . -name 'test_example.py' -exec wc -l {} + | tail -1 | awk '{print $1}')"
echo "Total docs lines: $(find . -name 'README.md' -exec wc -l {} + | tail -1 | awk '{print $1}')"
echo ""

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
elif [ $errors -eq 0 ]; then
    echo -e "${YELLOW}⚠ Completed with $warnings warnings${NC}"
    exit 0
else
    echo -e "${RED}✗ Found $errors errors and $warnings warnings${NC}"
    exit 1
fi
