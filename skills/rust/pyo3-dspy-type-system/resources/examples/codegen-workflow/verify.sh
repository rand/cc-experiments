#!/bin/bash
# Verification script for codegen-workflow example
# Tests that all components are present and functional

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Codegen Workflow Verification ==="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

if command -v cargo &> /dev/null; then
    pass "Cargo found: $(cargo --version)"
else
    fail "Cargo not found. Install Rust toolchain."
fi

if command -v python3 &> /dev/null; then
    pass "Python3 found: $(python3 --version)"
else
    fail "Python3 not found. Install Python 3.8+."
fi

echo ""

# Check required files
echo "Checking required files..."

required_files=(
    "Cargo.toml"
    "build.rs"
    "signatures.txt"
    "src/main.rs"
    "src/generated.rs"
    "README.md"
    "QUICKSTART.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        pass "Found: $file"
    else
        fail "Missing: $file"
    fi
done

echo ""

# Check signature_codegen.py location
echo "Checking codegen script..."

CODEGEN_SCRIPT="../../signature_codegen.py"
if [ -f "$CODEGEN_SCRIPT" ]; then
    pass "Found: signature_codegen.py"
else
    fail "Missing: signature_codegen.py at $CODEGEN_SCRIPT"
fi

echo ""

# Verify signatures.txt format
echo "Verifying signatures.txt..."

signature_count=$(grep -v "^#" signatures.txt | grep -v "^$" | wc -l | tr -d ' ')
if [ "$signature_count" -gt 0 ]; then
    pass "Found $signature_count signatures"
else
    fail "No signatures found in signatures.txt"
fi

# Check signature format
if grep -q " -> " signatures.txt; then
    pass "Signatures use correct format (->)"
else
    warn "No signatures with '->' found"
fi

echo ""

# Test manual code generation
echo "Testing manual code generation..."

python3 "$CODEGEN_SCRIPT" signatures.txt /tmp/test_codegen.rs
if [ -f "/tmp/test_codegen.rs" ]; then
    struct_count=$(grep -c "pub struct" /tmp/test_codegen.rs)
    pass "Generated $struct_count structs manually"

    # Verify generated code has required elements
    if grep -q "#\[derive(Debug, Clone, serde::Serialize, serde::Deserialize)\]" /tmp/test_codegen.rs; then
        pass "Generated code includes proper derives"
    else
        fail "Generated code missing proper derives"
    fi

    rm /tmp/test_codegen.rs
else
    fail "Code generation failed"
fi

echo ""

# Build the project
echo "Building project (triggers automatic codegen)..."

if cargo build 2>&1 | tee /tmp/build_output.log; then
    pass "Build successful"

    # Check if generated.rs was created/updated
    if [ -f "src/generated.rs" ]; then
        generated_structs=$(grep -c "pub struct" src/generated.rs || echo "0")
        if [ "$generated_structs" -gt 0 ]; then
            pass "Generated $generated_structs types in src/generated.rs"
        else
            warn "src/generated.rs exists but has no structs"
        fi
    else
        fail "src/generated.rs not found after build"
    fi
else
    fail "Build failed. Check /tmp/build_output.log"
fi

echo ""

# Run the example
echo "Running example..."

if cargo run --quiet > /tmp/run_output.txt 2>&1; then
    pass "Example ran successfully"

    # Verify output contains expected content
    if grep -q "Automated Rust Type Generation Workflow" /tmp/run_output.txt; then
        pass "Output contains expected header"
    else
        warn "Output missing expected header"
    fi

    if grep -q "Type Safety Demonstration" /tmp/run_output.txt; then
        pass "Output demonstrates type safety"
    else
        warn "Output missing type safety section"
    fi

    # Count examples in output
    example_count=$(grep -c "^\([0-9]\+\)\." /tmp/run_output.txt || echo "0")
    if [ "$example_count" -ge 8 ]; then
        pass "Found $example_count examples in output"
    else
        warn "Expected at least 8 examples, found $example_count"
    fi
else
    fail "Example execution failed"
fi

echo ""

# Check documentation quality
echo "Verifying documentation..."

if [ -s "README.md" ]; then
    readme_lines=$(wc -l < README.md | tr -d ' ')
    if [ "$readme_lines" -gt 100 ]; then
        pass "README.md is comprehensive ($readme_lines lines)"
    else
        warn "README.md seems short ($readme_lines lines)"
    fi
else
    fail "README.md is empty or missing"
fi

if [ -s "QUICKSTART.md" ]; then
    pass "QUICKSTART.md exists"
else
    warn "QUICKSTART.md is empty or missing"
fi

echo ""

# Check Makefile targets
echo "Verifying Makefile..."

if [ -f "Makefile" ]; then
    targets=$(grep "^[a-z-]*:" Makefile | wc -l | tr -d ' ')
    pass "Makefile has $targets targets"

    # Test make help
    if make help &> /dev/null; then
        pass "make help works"
    else
        warn "make help failed"
    fi
else
    warn "Makefile not found"
fi

echo ""

# Verify incremental build
echo "Testing incremental build..."

touch signatures.txt
if cargo build 2>&1 | grep -q "Compiling codegen-workflow"; then
    pass "Build system detects signature changes"
else
    warn "Incremental build may not detect changes properly"
fi

echo ""

# Final summary
echo "=== Verification Summary ==="
echo ""
echo "Project structure: ✓"
echo "Dependencies: ✓"
echo "Code generation: ✓"
echo "Build process: ✓"
echo "Example execution: ✓"
echo "Documentation: ✓"
echo ""
echo -e "${GREEN}All checks passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Read README.md for comprehensive documentation"
echo "  2. Follow QUICKSTART.md to explore the example"
echo "  3. Modify signatures.txt and rebuild"
echo "  4. Integrate into your own projects"
echo ""
echo "Quick commands:"
echo "  make build      - Build and generate types"
echo "  make run        - Run the example"
echo "  make help       - Show all available commands"
echo ""

# Cleanup
rm -f /tmp/build_output.log /tmp/run_output.txt

exit 0
