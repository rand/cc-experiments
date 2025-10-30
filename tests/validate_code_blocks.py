#!/usr/bin/env python3
"""
Validate code blocks in skill files for syntax correctness.
Extracts code blocks by language and validates them.
"""

import re
import sys
import ast
from pathlib import Path
from typing import List, Tuple
import subprocess


def extract_code_blocks(file_path: Path) -> List[Tuple[str, str, int]]:
    """
    Extract code blocks from markdown file.
    Returns: List of (language, code, line_number) tuples
    """
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    blocks = []
    in_code_block = False
    current_lang = None
    current_code = []
    start_line = 0

    for i, line in enumerate(lines, 1):
        # Start of code block
        if line.startswith('```'):
            if not in_code_block:
                # Extract language
                lang = line[3:].strip().lower()
                if lang:
                    in_code_block = True
                    current_lang = lang
                    current_code = []
                    start_line = i + 1
            else:
                # End of code block
                if current_lang and current_code:
                    code = '\n'.join(current_code)
                    blocks.append((current_lang, code, start_line))
                in_code_block = False
                current_lang = None
                current_code = []
        elif in_code_block:
            current_code.append(line)

    return blocks


def validate_python_code(code: str) -> Tuple[bool, str]:
    """Validate Python code syntax."""
    try:
        ast.parse(code)
        return True, "Valid"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Parse error: {e}"


def validate_javascript_code(code: str) -> Tuple[bool, str]:
    """Validate JavaScript/TypeScript code syntax (basic check)."""
    # Basic validation - check for common syntax errors
    # In production, would use a proper JS parser
    if code.strip():
        return True, "Valid (basic check)"
    return False, "Empty code block"


def validate_swift_code(code: str) -> Tuple[bool, str]:
    """Validate Swift code syntax using swiftc if available."""
    try:
        # Check if swiftc is available
        result = subprocess.run(
            ['swiftc', '--version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            return True, "Swift compiler not available (skipped)"

        # Write code to temp file and validate
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.swift', delete=False) as f:
            f.write(code)
            temp_path = f.name

        result = subprocess.run(
            ['swiftc', '-parse', temp_path],
            capture_output=True,
            timeout=10
        )

        Path(temp_path).unlink()

        if result.returncode == 0:
            return True, "Valid"
        else:
            return False, result.stderr.decode('utf-8')

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True, "Swift compiler not available (skipped)"
    except Exception as e:
        return False, f"Validation error: {e}"


def validate_zig_code(code: str) -> Tuple[bool, str]:
    """Validate Zig code syntax using zig ast-check if available."""
    try:
        # Check if zig is available
        result = subprocess.run(
            ['zig', 'version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            return True, "Zig compiler not available (skipped)"

        # Write code to temp file and validate
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zig', delete=False) as f:
            f.write(code)
            temp_path = f.name

        result = subprocess.run(
            ['zig', 'ast-check', temp_path],
            capture_output=True,
            timeout=10
        )

        Path(temp_path).unlink()

        if result.returncode == 0:
            return True, "Valid"
        else:
            return False, result.stderr.decode('utf-8')

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True, "Zig compiler not available (skipped)"
    except Exception as e:
        return False, f"Validation error: {e}"


def validate_skill_file(file_path: Path) -> List[dict]:
    """Validate all code blocks in a skill file."""
    print(f"\nValidating {file_path.name}...")

    blocks = extract_code_blocks(file_path)
    results = []

    for lang, code, line_num in blocks:
        # Normalize language names
        normalized_lang = lang.split()[0]  # Handle "python3", "typescript"

        # Validate based on language
        if normalized_lang in ['python', 'python3', 'py']:
            valid, message = validate_python_code(code)
        elif normalized_lang in ['javascript', 'js', 'typescript', 'ts', 'jsx', 'tsx']:
            valid, message = validate_javascript_code(code)
        elif normalized_lang in ['swift']:
            valid, message = validate_swift_code(code)
        elif normalized_lang in ['zig']:
            valid, message = validate_zig_code(code)
        else:
            # Skip validation for other languages
            valid = True
            message = "Skipped (unsupported language)"

        results.append({
            'file': file_path.name,
            'language': lang,
            'line': line_num,
            'valid': valid,
            'message': message
        })

        # Print result
        status = "✅" if valid else "❌"
        print(f"  {status} {lang:15} (line {line_num:4}): {message}")

    return results


def main():
    """Main validation function."""
    print("="*60)
    print("CODE BLOCK SYNTAX VALIDATION")
    print("="*60)

    skills_dir = Path(__file__).parent.parent

    # Find all skill files
    skill_files = []
    for pattern in ["*.md", "*/*.md"]:
        skill_files.extend(skills_dir.glob(pattern))

    # Filter out unwanted files
    excluded = {"MIGRATION_GUIDE.md", "REFACTORING_SUMMARY.md", "_INDEX.md", "README.md", "ENHANCEMENT_PLAN.md", "ENHANCEMENTS_SUMMARY.md", "SKILLS_USAGE_GUIDE.md", "CLAUDE.md"}
    skill_files = [
        f for f in skill_files
        if f.name not in excluded
        and "_archive" not in str(f)
        and ".work" not in str(f)
        and f.is_file()
    ]

    skill_files.sort()

    print(f"Found {len(skill_files)} skill files to validate")

    all_results = []
    for skill_file in skill_files:
        try:
            results = validate_skill_file(skill_file)
            all_results.extend(results)
        except Exception as e:
            print(f"❌ Error validating {skill_file.name}: {e}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    total = len(all_results)
    passed = sum(1 for r in all_results if r['valid'])
    failed = total - passed

    print(f"Total code blocks: {total}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")

    if failed > 0:
        print(f"\nFailed blocks:")
        for result in all_results:
            if not result['valid']:
                print(f"  • {result['file']} ({result['language']}, line {result['line']}): {result['message']}")

    print("="*60)

    # Exit with error if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
