# Anti-Slop: AI Content Quality Toolkit

A comprehensive Claude Code skill for detecting and eliminating generic AI-generated patterns ("AI slop") in natural language, code, and design.

## What You Get

### 1. Anti-Slop Skill (`anti-slop.skill`)
A complete Claude Code skill package containing:

- **SKILL.md**: Main skill documentation with workflows and best practices
- **3 Comprehensive Reference Guides**:
  - `text-patterns.md`: Natural language slop patterns (5.5KB)
  - `code-patterns.md`: Programming antipatterns (9.5KB)
  - `design-patterns.md`: Visual/UX design slop patterns (10KB)
- **2 Python Scripts**:
  - `detect_slop.py`: Automated slop detection for text files
  - `clean_slop.py`: Automated slop cleanup with safety features

### 2. CLAUDE.md Updates (`CLAUDE_MD_UPDATES.md`)
Proposed system-level integration updates including:
- Core behavior modifications to prevent slop generation
- Quality standards for text, code, and design
- Proactive trigger patterns for the anti-slop skill
- Integration with existing Claude workflows

## What is AI Slop?

"AI slop" refers to telltale patterns that signal generic, low-quality AI-generated content:

### Text Slop
- Overused phrases: "delve into", "navigate the complexities", "in today's fast-paced world"
- Excessive buzzwords: "leverage", "synergistic", "paradigm shift"
- Meta-commentary: "In this article, we will discuss..."
- Generic hedging: "may or may not", "could potentially"

### Code Slop
- Generic variable names: `data`, `result`, `temp`, `item`
- Obvious comments that restate code
- Unnecessary abstraction layers
- Over-engineered solutions for simple problems

### Design Slop
- Cookie-cutter layouts and generic templates
- Purple/pink/cyan gradient backgrounds
- Generic marketing copy: "Empower Your Business"
- Overuse of trendy effects without purpose

## Quick Start

### Installation

1. **Install the skill in Claude Code:**
   ```bash
   # Download anti-slop.skill from outputs
   # Import it into Claude Code via the Skills menu
   ```

2. **Test the detection script:**
   ```bash
   python scripts/detect_slop.py your_file.txt
   ```

3. **Preview cleanup:**
   ```bash
   python scripts/clean_slop.py your_file.txt
   ```

### Basic Usage

**Detect slop in a text file:**
```bash
python scripts/detect_slop.py article.md --verbose
```

**Clean up slop (with backup):**
```bash
python scripts/clean_slop.py article.md --save
```

**Ask Claude to use the skill:**
```
"Can you review this article for AI slop patterns?"
"Help me clean up generic AI patterns in my code"
"Does this design look too generic?"
```

## Detailed Usage

### Text Analysis

The `detect_slop.py` script analyzes text files and provides:

**Slop Score (0-100):**
- 0-20: Low slop (authentic writing)
- 20-40: Moderate slop (some patterns present)
- 40-60: High slop (many patterns found)
- 60+: Severe slop (heavily generic)

**Pattern Categories:**
- High-risk phrases (nearly always slop)
- Buzzwords and jargon
- Meta-commentary
- Excessive hedging
- Structural issues

**Example output:**
```
Overall Slop Score: 85/100
Assessment: 🚨 High slop detected

🔴 HIGH-RISK PHRASES (6 found):
  Line 1: 'delve into' in: In this article, we will delve into...
  Line 3: 'it's important to note that' in: ...

📢 BUZZWORDS (10 found):
  leverage, synergistic, paradigm shift, empower...

💡 RECOMMENDATIONS:
  • Replace high-risk phrases with direct, specific language
  • Remove buzzwords and use concrete, specific terms
  • Delete meta-commentary; lead with actual content
```

### Text Cleanup

The `clean_slop.py` script automatically removes common patterns:

**Preview mode (default):**
```bash
python scripts/clean_slop.py article.md
# Shows what would change without modifying file
```

**Save mode (creates backup):**
```bash
python scripts/clean_slop.py article.md --save
# Creates article.md.backup and overwrites original
```

**Aggressive mode:**
```bash
python scripts/clean_slop.py article.md --save --aggressive
# More aggressive cleanup, may slightly change meaning
```

**Custom output:**
```bash
python scripts/clean_slop.py article.md --output cleaned_article.md
```

**What it cleans:**
- High-risk phrases → removed or simplified
- Wordy constructions → replaced with concise alternatives
- Meta-commentary → removed entirely
- Excessive hedging → reduced to single qualifiers
- Buzzwords → replaced with specific terms
- Redundant qualifiers → fixed
- Empty intensifiers → removed

### Code Review

For code, the skill provides manual review guidance:

```bash
# Read the reference first
view references/code-patterns.md

# Then manually review code against patterns:
# - Generic variable names
# - Obvious comments
# - Over-engineering
# - Unnecessary abstractions
```

**Common fixes:**
- `data` → `userPreferences`, `transactionHistory`, `searchResults`
- `result` → `parsedDocument`, `filteredItems`, `validationError`
- Remove comments like `# Create a user` before `user = User()`
- Simplify complex implementations of simple tasks

### Design Review

For design work, consult the design patterns reference:

```bash
view references/design-patterns.md
```

**Key checks:**
- Is the color palette generic (purple/pink/cyan)?
- Does layout follow a template or serve content?
- Is copy specific or generic marketing speak?
- Are visual effects purposeful or decorative?
- Does design reflect brand or look like any AI startup?

## Reference Guides

### text-patterns.md
Comprehensive guide to natural language slop:
- Overused transition phrases
- Generic hedge language
- Unnecessary meta-commentary
- Corporate buzzword clusters
- Redundant qualifiers
- Empty intensifiers
- Filler constructions
- Detection patterns and cleanup strategies

### code-patterns.md
Programming antipatterns across languages:
- Naming antipatterns
- Comment antipatterns
- Structure antipatterns
- Implementation antipatterns
- Documentation antipatterns
- Language-specific slop (Python, JS, Java)
- Detection signals and refactoring strategies

### design-patterns.md
Visual and UX design slop patterns:
- Visual design slop (gradients, effects, motifs)
- Color and typography issues
- Layout antipatterns
- Component overuse
- UX writing slop
- Animation and interaction patterns
- Platform-specific issues
- Quality improvement strategies

## Integration with CLAUDE.md

The `CLAUDE_MD_UPDATES.md` file contains proposed system-level changes that would make Claude naturally avoid slop patterns.

**Key updates:**
1. **Anti-slop awareness** - Core patterns to avoid
2. **Quality principles** - Direct, specific, authentic writing
3. **Code quality standards** - Meaningful names, appropriate comments
4. **Design quality standards** - Content-first, intentional choices
5. **Proactive triggers** - When to use anti-slop skill automatically

**Implementation approaches:**

**Option 1: Gradual Integration**
- Start by making Claude aware the skill exists
- Add proactive triggers for common scenarios
- Integrate quality principles over time
- Monitor and refine based on usage

**Option 2: Full Integration**
- Add all updates to CLAUDE.md at once
- Claude becomes naturally anti-slop in all outputs
- Skill becomes both prevention and cure tool

**Option 3: User-Controlled**
- Keep skill as opt-in tool
- Users explicitly invoke when needed
- No changes to core Claude behavior

## Best Practices

### For Prevention

**When creating content:**
1. Write with specific audience in mind
2. Use concrete examples over abstractions
3. Lead with the point, skip preambles
4. Choose words for precision, not impression
5. Review against slop patterns before finalizing

### For Detection

**Run detection when:**
- Content feels generic or "AI-like"
- Before delivering client work
- During content review processes
- Establishing quality standards
- Training teams on quality

### For Cleanup

**Cleanup workflow:**
1. Run detection to understand scope
2. Preview automated cleanup
3. Apply safe automated changes
4. Manually review and refine
5. Verify meaning preserved

**Safety notes:**
- Always preview before saving
- Review automated changes carefully
- Use non-aggressive mode for important content
- Keep backups of originals
- Exercise judgment on context-dependent patterns

## Common Scenarios

### Scenario 1: Content Review
```
User: "Can you review this article for AI slop?"

Claude:
1. Reads text-patterns.md for reference
2. Runs detect_slop.py script
3. Reviews findings manually
4. Optionally runs clean_slop.py
5. Provides manual cleanup recommendations
6. Verifies final content quality
```

### Scenario 2: Code Cleanup
```
User: "Help me remove generic patterns from my code"

Claude:
1. Reads code-patterns.md
2. Reviews code files manually
3. Identifies generic names to rename
4. Spots over-engineering to simplify
5. Suggests removing obvious comments
6. Provides refactoring guidance
```

### Scenario 3: Design Audit
```
User: "Does this design look too generic?"

Claude:
1. Reads design-patterns.md
2. Checks against high-confidence indicators
3. Identifies specific issues
4. Provides concrete recommendations
5. Suggests alternatives
6. Focuses on user needs over templates
```

### Scenario 4: Quality Standards
```
User: "Help me create quality standards for our team"

Claude:
1. Reviews all reference files
2. Identifies relevant patterns for user's domain
3. Creates project-specific guidelines
4. Sets up detection in pipeline
5. Documents acceptable exceptions
6. Provides training materials
```

## Limitations

**Current scope:**
- Detection scripts only work on text files
- Code slop detection is manual process
- Design slop detection is manual process
- Patterns optimized for English
- Code patterns focus on Python, JS, Java

**Context sensitivity:**
- Scripts can't understand all contexts
- Some "slop" may be appropriate in specific domains
- Always review automated changes
- Exercise judgment on recommendations

**Not a replacement for:**
- Domain expertise
- Human judgment
- Editorial review
- Code review process
- Design critique

## Technical Details

### Script Requirements
- Python 3.6+
- No external dependencies
- Works on Linux, macOS, Windows

### Script Architecture

**detect_slop.py:**
- Pattern-based text analysis
- Multiple slop categories
- Configurable scoring
- Detailed reporting

**clean_slop.py:**
- Regex-based pattern replacement
- Safe/aggressive modes
- Backup creation
- Preview functionality

### Performance
- Detection: ~50ms per 1000 words
- Cleanup: ~100ms per 1000 words
- Memory: Minimal (loads file once)
- Output: Detailed reports or cleaned text

## Examples

### Example 1: Before/After Text

**Before (Score: 85/100):**
```
In this article, we will delve into the complexities of modern AI. 
In today's fast-paced world, it's important to note that leveraging 
cutting-edge solutions can empower businesses to drive innovation.
```

**After (Score: 15/100):**
```
Modern AI systems balance accuracy, speed, and cost. This article 
examines practical trade-offs with examples from production deployments.
```

### Example 2: Before/After Code

**Before:**
```python
# Process the data
def process_data(data):
    result = []
    # Loop through items
    for item in data:
        result.append(item)
    return result
```

**After:**
```python
def filter_completed_transactions(transactions):
    return [t for t in transactions if t.status == 'completed']
```

### Example 3: Before/After Design

**Before:**
```
Purple gradient background
"Empower Your Business"
"Transform your workflow with cutting-edge solutions"
[Get Started] button
Generic 3D shapes floating
```

**After:**
```
Brand color background
"Automate Invoice Processing"
"Extract line items from PDFs, sync to QuickBooks"
[Try 50 invoices free] button
Screenshot of actual interface
```

## Contributing

To extend the skill:

1. **Add new patterns** to reference files
2. **Update detection regex** in detect_slop.py
3. **Add cleanup rules** to clean_slop.py
4. **Test thoroughly** with real examples
5. **Document patterns** with examples

## Support

For issues or questions:
- Review the comprehensive reference guides
- Check example scenarios in SKILL.md
- Test with the provided scripts
- Consider context when applying rules

## License

See LICENSE.txt for complete terms.

---

## Summary

The Anti-Slop skill provides:

✅ **Detection**: Automated scanning for slop patterns in text
✅ **Cleanup**: Safe automated removal of common patterns
✅ **Prevention**: Reference guides for all content types
✅ **Integration**: System-level updates for Claude
✅ **Flexibility**: Use as tool or integrate into behavior

The goal: Create authentic, high-quality content that serves users rather than following generic AI patterns.
