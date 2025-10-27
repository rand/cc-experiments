---
name: research-research-writing
description: Master academic and research writing including structure, citations, reporting standards, and peer review processes
---

# Research Writing Skill

## When to Use This Skill

Use this skill when you need to:
- Write research papers and reports
- Structure academic arguments
- Report statistical results correctly
- Format citations and references
- Write for peer review
- Respond to reviewer feedback
- Create research proposals
- Write research summaries

## Research Paper Structure

### 1. IMRAD Framework

**Implementation Guide**:
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PaperSection:
    """Define paper section structure"""
    title: str
    purpose: str
    key_elements: List[str]
    common_mistakes: List[str]
    word_count_range: tuple

class IMRADStructure:
    """Standard research paper structure"""

    def __init__(self):
        self.sections = self._define_sections()

    def _define_sections(self):
        return {
            'Title': PaperSection(
                title='Title',
                purpose='Concisely communicate main finding',
                key_elements=[
                    'Specific (not vague)',
                    'Informative (conveys key message)',
                    'Indexable (includes key terms)',
                    '10-15 words typical'
                ],
                common_mistakes=[
                    'Too broad or vague',
                    'Missing key variables',
                    'Clickbait-style teasing'
                ],
                word_count_range=(10, 15)
            ),
            'Abstract': PaperSection(
                title='Abstract',
                purpose='Standalone summary of entire paper',
                key_elements=[
                    'Background (1-2 sentences)',
                    'Objective/hypothesis (1 sentence)',
                    'Methods (2-3 sentences)',
                    'Results (2-3 sentences)',
                    'Conclusions (1-2 sentences)'
                ],
                common_mistakes=[
                    'References or citations',
                    'Unexplained abbreviations',
                    'Vague results (no numbers)',
                    'Overstating conclusions'
                ],
                word_count_range=(150, 250)
            ),
            'Introduction': PaperSection(
                title='Introduction',
                purpose='Establish importance and rationale',
                key_elements=[
                    'Opening: Broad importance of topic',
                    'Narrowing: What is known',
                    'Gap: What is unknown',
                    'Purpose: What this study does',
                    'Hypothesis/Aim: Specific predictions'
                ],
                common_mistakes=[
                    'Starting too broad ("Since ancient times...")',
                    'Missing gap statement',
                    'No clear hypothesis',
                    'Too long or tangential'
                ],
                word_count_range=(500, 1000)
            ),
            'Methods': PaperSection(
                title='Methods',
                purpose='Enable replication',
                key_elements=[
                    'Design overview',
                    'Participants/Sample',
                    'Materials/Measures',
                    'Procedure',
                    'Analysis plan'
                ],
                common_mistakes=[
                    'Insufficient detail for replication',
                    'Missing ethical approval',
                    'No justification for sample size',
                    'Analysis decisions post-hoc'
                ],
                word_count_range=(800, 1500)
            ),
            'Results': PaperSection(
                title='Results',
                purpose='Report findings objectively',
                key_elements=[
                    'Descriptive statistics first',
                    'Each hypothesis tested',
                    'Statistics reported in full',
                    'Figures and tables',
                    'Unexpected findings noted'
                ],
                common_mistakes=[
                    'Interpreting (save for Discussion)',
                    'Incomplete statistics',
                    'Cherry-picking results',
                    'Poor figure quality'
                ],
                word_count_range=(800, 1500)
            ),
            'Discussion': PaperSection(
                title='Discussion',
                purpose='Interpret findings and implications',
                key_elements=[
                    'Summary of key findings',
                    'Interpretation in context of literature',
                    'Theoretical implications',
                    'Practical implications',
                    'Limitations',
                    'Future directions',
                    'Conclusion'
                ],
                common_mistakes=[
                    'Repeating Results verbatim',
                    'Overgeneralizing',
                    'Ignoring limitations',
                    'Introducing new data'
                ],
                word_count_range=(1000, 2000)
            )
        }

    def generate_outline(self):
        """Create paper outline"""
        outline = "# Research Paper Outline (IMRAD)\n\n"

        for section_name, section in self.sections.items():
            outline += f"## {section.title}\n"
            outline += f"**Purpose**: {section.purpose}\n\n"
            outline += f"**Word count**: {section.word_count_range[0]}-"
            outline += f"{section.word_count_range[1]} words\n\n"
            outline += "**Key elements**:\n"
            for elem in section.key_elements:
                outline += f"- [ ] {elem}\n"
            outline += "\n**Avoid**:\n"
            for mistake in section.common_mistakes:
                outline += f"- {mistake}\n"
            outline += "\n---\n\n"

        return outline

    def check_section(self, section_name: str, text: str):
        """Check if section meets requirements"""
        section = self.sections.get(section_name)
        if not section:
            return "Section not found"

        word_count = len(text.split())
        issues = []

        # Check word count
        if word_count < section.word_count_range[0]:
            issues.append(f"Too short: {word_count} words "
                        f"(minimum {section.word_count_range[0]})")
        elif word_count > section.word_count_range[1] * 1.2:
            issues.append(f"Quite long: {word_count} words "
                        f"(typical max {section.word_count_range[1]})")

        return {
            'section': section_name,
            'word_count': word_count,
            'target_range': section.word_count_range,
            'issues': issues if issues else ['Within guidelines']
        }

# Example
structure = IMRADStructure()
print(structure.generate_outline())
```

### 2. Statistical Reporting

**APA Style Statistical Reporting**:
```python
from typing import Dict, Any

class StatisticalReporter:
    """Format statistical results in APA style"""

    @staticmethod
    def t_test(result: Dict[str, Any]) -> str:
        """Format t-test results"""
        # Result should have: t_statistic, df, p_value, mean_1, mean_2, cohens_d

        # Format p-value
        if result['p_value'] < 0.001:
            p_str = "p < .001"
        else:
            p_str = f"p = {result['p_value']:.3f}"

        # Build sentence
        report = (
            f"The {'paired-samples' if result.get('paired') else 'independent-samples'} "
            f"t-test revealed a "
            f"{'significant' if result['significant'] else 'non-significant'} "
            f"difference between groups "
            f"(M₁ = {result['mean_1']:.2f}, M₂ = {result['mean_2']:.2f}), "
            f"t({result['df']}) = {result['t_statistic']:.2f}, "
            f"{p_str}, d = {result['cohens_d']:.2f}."
        )

        return report

    @staticmethod
    def correlation(result: Dict[str, Any]) -> str:
        """Format correlation results"""
        # Result should have: r, p_value, n

        if result['p_value'] < 0.001:
            p_str = "p < .001"
        else:
            p_str = f"p = {result['p_value']:.3f}"

        report = (
            f"There was a {'significant' if result['significant'] else 'non-significant'} "
            f"{'positive' if result['r'] > 0 else 'negative'} correlation "
            f"between the variables, "
            f"r({result['n'] - 2}) = {result['r']:.2f}, {p_str}."
        )

        return report

    @staticmethod
    def regression(result: Dict[str, Any]) -> str:
        """Format regression results"""
        # Result should have: r_squared, f_statistic, df_model, df_resid, p_value

        if result['p_value'] < 0.001:
            p_str = "p < .001"
        else:
            p_str = f"p = {result['p_value']:.3f}"

        report = (
            f"The regression model was "
            f"{'significant' if result['significant'] else 'non-significant'}, "
            f"F({result['df_model']}, {result['df_resid']}) = "
            f"{result['f_statistic']:.2f}, {p_str}, "
            f"R² = {result['r_squared']:.2f}, "
            f"accounting for {result['r_squared']*100:.1f}% of the variance."
        )

        return report

    @staticmethod
    def create_results_table(results: list, table_title: str) -> str:
        """Create APA-style results table"""
        table = f"Table X\n\n{table_title}\n\n"
        table += "| Variable | M | SD | 1 | 2 | 3 |\n"
        table += "|----------|---|----|----|----|\n"

        for i, var in enumerate(results, 1):
            table += f"| {var['name']} | {var['mean']:.2f} | "
            table += f"{var['sd']:.2f} |"

            # Add correlations
            for j in range(len(results)):
                if j < i - 1:
                    table += f" {var['correlations'][j]:.2f} |"
                elif j == i - 1:
                    table += " — |"
                else:
                    table += " |"

            table += "\n"

        table += "\n*Note*. N = XX. * p < .05, ** p < .01, *** p < .001\n"

        return table

# Example
reporter = StatisticalReporter()

t_result = {
    't_statistic': 2.45,
    'df': 58,
    'p_value': 0.017,
    'mean_1': 45.2,
    'mean_2': 40.8,
    'cohens_d': 0.63,
    'significant': True,
    'paired': False
}

print(reporter.t_test(t_result))
```

### 3. Citation Management

**Citation Formatter**:
```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class CitationStyle(Enum):
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"

@dataclass
class Reference:
    """Store reference information"""
    authors: List[str]
    year: int
    title: str
    journal: Optional[str] = None
    volume: Optional[int] = None
    issue: Optional[int] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    book_title: Optional[str] = None
    publisher: Optional[str] = None
    url: Optional[str] = None

class CitationFormatter:
    """Format citations and references"""

    @staticmethod
    def format_authors_apa(authors: List[str], in_text: bool = False) -> str:
        """Format author names in APA style"""
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"
        elif in_text and len(authors) >= 3:
            return f"{authors[0]} et al."
        elif len(authors) <= 20:
            return ", ".join(authors[:-1]) + f", & {authors[-1]}"
        else:
            # 21+ authors
            return ", ".join(authors[:19]) + f", ... {authors[-1]}"

    @staticmethod
    def in_text_citation_apa(ref: Reference, page: Optional[str] = None) -> str:
        """Generate APA in-text citation"""
        author_str = CitationFormatter.format_authors_apa(ref.authors, in_text=True)

        if page:
            return f"({author_str}, {ref.year}, p. {page})"
        else:
            return f"({author_str}, {ref.year})"

    @staticmethod
    def reference_apa(ref: Reference) -> str:
        """Generate APA reference list entry"""
        # Authors
        ref_str = CitationFormatter.format_authors_apa(ref.authors, in_text=False)

        # Year
        ref_str += f" ({ref.year}). "

        # Title
        ref_str += f"{ref.title}. "

        # Journal article
        if ref.journal:
            ref_str += f"*{ref.journal}*"
            if ref.volume:
                ref_str += f", *{ref.volume}*"
            if ref.issue:
                ref_str += f"({ref.issue})"
            if ref.pages:
                ref_str += f", {ref.pages}"
            ref_str += ". "

        # Book
        if ref.book_title:
            ref_str += f"*{ref.book_title}*. "
            if ref.publisher:
                ref_str += f"{ref.publisher}. "

        # DOI or URL
        if ref.doi:
            ref_str += f"https://doi.org/{ref.doi}"
        elif ref.url:
            ref_str += f"{ref.url}"

        return ref_str

    @staticmethod
    def generate_reference_list(refs: List[Reference]) -> str:
        """Create formatted reference list"""
        # Sort alphabetically by first author
        sorted_refs = sorted(refs, key=lambda r: r.authors[0].split()[-1])

        ref_list = "# References\n\n"
        for ref in sorted_refs:
            ref_list += CitationFormatter.reference_apa(ref) + "\n\n"

        return ref_list

# Example
refs = [
    Reference(
        authors=['Smith, J. A.', 'Johnson, B. C.'],
        year=2023,
        title='Remote work and wellbeing: A systematic review',
        journal='Journal of Occupational Health Psychology',
        volume=28,
        issue=3,
        pages='234-256',
        doi='10.1037/ocp0000123'
    ),
    Reference(
        authors=['Lee, K.', 'Chen, M.', 'Park, S.'],
        year=2022,
        title='Work-life balance in the digital age',
        book_title='Organizational Psychology',
        publisher='Academic Press'
    )
]

formatter = CitationFormatter()
print("In-text:", formatter.in_text_citation_apa(refs[0]))
print("\nReference list:")
print(formatter.generate_reference_list(refs))
```

## Writing Quality Guidelines

### 1. Clarity and Precision

**Writing Checklist**:
```
✓ Use active voice when possible
✓ Be specific, not vague
✓ Define technical terms
✓ Use parallel structure
✓ Avoid unnecessary jargon
✓ One idea per sentence
✓ Signpost transitions clearly
✓ Use consistent terminology
```

**Common Issues**:
```
✗ Vague: "The results were interesting"
  → "Contrary to expectations, treatment reduced anxiety by 30%"

✗ Passive: "The survey was administered to participants"
  → "Participants completed the survey"

✗ Jargon: "Leveraging synergistic modalities"
  → "Using multiple complementary approaches"

✗ Wordy: "Due to the fact that"
  → "Because"
```

### 2. Argument Structure

**Building Arguments**:
```python
@dataclass
class ArgumentStructure:
    """Structure for academic argument"""
    claim: str
    evidence: List[str]
    reasoning: str
    counterargument: Optional[str] = None
    rebuttal: Optional[str] = None

    def format_paragraph(self) -> str:
        """Generate well-structured paragraph"""
        para = f"{self.claim} "

        # Evidence
        for i, ev in enumerate(self.evidence, 1):
            para += f"{ev} "

        # Reasoning
        para += f"{self.reasoning} "

        # Address counterargument if present
        if self.counterargument:
            para += f"While some argue that {self.counterargument}, "
            if self.rebuttal:
                para += f"{self.rebuttal} "

        return para

# Example
arg = ArgumentStructure(
    claim="Remote work poses challenges for work-life balance.",
    evidence=[
        "Smith et al. (2023) found that 65% of remote workers reported "
        "difficulty separating work and personal time.",
        "Lee and Chen (2022) observed increased overtime among remote workers."
    ],
    reasoning="The physical proximity of work materials and lack of spatial "
             "boundaries may contribute to this blurring of domains.",
    counterargument="remote work provides flexibility that could improve balance",
    rebuttal="the flexibility paradox shows that autonomy without structure "
             "can increase rather than decrease work-life conflict "
             "(Park et al., 2021)"
)

print(arg.format_paragraph())
```

### 3. Revision Checklist

**Self-Editing Guide**:
```
## Content
[ ] Research question clearly stated
[ ] Literature review comprehensive and focused
[ ] Methods described in sufficient detail
[ ] Results reported completely
[ ] Discussion interprets findings appropriately
[ ] Limitations acknowledged
[ ] Implications stated clearly

## Structure
[ ] Each paragraph has topic sentence
[ ] Paragraphs flow logically
[ ] Transitions connect ideas
[ ] Sections are balanced in length
[ ] Headings are informative

## Style
[ ] Active voice predominates
[ ] Sentences vary in length
[ ] Technical terms defined
[ ] Jargon minimized
[ ] Tone is objective

## Mechanics
[ ] Grammar and spelling correct
[ ] Punctuation proper
[ ] Citations formatted correctly
[ ] All citations in reference list
[ ] All references cited in text
[ ] Figures and tables numbered
[ ] Figures and tables have captions

## Ethics
[ ] Authorship appropriate
[ ] Conflicts of interest disclosed
[ ] Ethical approval noted
[ ] Participants protected
[ ] Data available (when possible)
```

## Responding to Peer Review

### Review Response Framework

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ReviewComment:
    """Represent reviewer comment"""
    reviewer: str
    comment_number: int
    comment: str
    response: str
    action_taken: str
    location: str

class ReviewResponse:
    """Organize response to peer review"""

    def __init__(self, manuscript_title: str):
        self.title = manuscript_title
        self.responses = []

    def add_response(self, response: ReviewComment):
        """Add response to reviewer comment"""
        self.responses.append(response)

    def generate_response_letter(self) -> str:
        """Create point-by-point response letter"""
        letter = f"# Response to Reviewers\n\n"
        letter += f"## Manuscript: {self.title}\n\n"
        letter += "Dear Editor and Reviewers,\n\n"
        letter += ("We thank the editor and reviewers for their thoughtful "
                  "comments. We have carefully addressed each point and "
                  "believe the manuscript is substantially improved. "
                  "Below we provide point-by-point responses.\n\n")

        # Group by reviewer
        by_reviewer = {}
        for resp in self.responses:
            if resp.reviewer not in by_reviewer:
                by_reviewer[resp.reviewer] = []
            by_reviewer[resp.reviewer].append(resp)

        for reviewer, comments in by_reviewer.items():
            letter += f"## {reviewer}\n\n"

            for comment in sorted(comments, key=lambda x: x.comment_number):
                letter += f"### Comment {comment.comment_number}\n\n"
                letter += f"*{comment.comment}*\n\n"
                letter += "**Response**: "
                letter += f"{comment.response}\n\n"
                letter += "**Action taken**: "
                letter += f"{comment.action_taken} "
                letter += f"({comment.location})\n\n"
                letter += "---\n\n"

        letter += ("We hope these revisions address the concerns raised. "
                  "We look forward to your decision.\n\n")
        letter += "Sincerely,\n[Authors]\n")

        return letter

# Example
response = ReviewResponse("Remote Work and Wellbeing Study")

response.add_response(ReviewComment(
    reviewer="Reviewer 1",
    comment_number=1,
    comment="The sample size seems small for the claims made. "
            "Can you justify this?",
    response="We appreciate this concern. We have added a power analysis "
             "to the Methods section demonstrating that our sample of "
             "N=120 provides 80% power to detect medium effects (d=0.5). "
             "We have also softened claims in the Discussion to acknowledge "
             "that replication with larger samples is needed.",
    action_taken="Added power analysis to Methods; revised Discussion claims",
    location="Methods p.8, Discussion p.15"
))

response.add_response(ReviewComment(
    reviewer="Reviewer 1",
    comment_number=2,
    comment="The measure of work-life balance is not validated. "
            "This is a significant limitation.",
    response="We agree this is an important point. We have added a new "
             "section to Methods describing the scale validation process, "
             "including factor analysis (α=0.85) and convergent validity "
             "with established measures (r=0.67, p<.001). We have also "
             "added this as a limitation since the scale has not been "
             "validated in other samples.",
    action_taken="Added validation evidence to Methods; noted limitation",
    location="Methods p.9-10, Discussion p.16"
))

print(response.generate_response_letter())
```

## Best Practices

### 1. Pre-Writing
- Read target journal requirements
- Review similar published papers
- Create detailed outline
- Set writing schedule
- Find writing accountability partner

### 2. Drafting
- Write Methods first (easiest)
- Write Results second (objective)
- Write Introduction and Discussion last
- Don't edit while drafting
- Write regularly, even if brief sessions

### 3. Revising
- Take break before revising
- Read aloud to catch awkward phrasing
- Check that each paragraph makes one point
- Verify all claims have citations
- Ensure figures tell story independently
- Get feedback from colleagues

### 4. Submitting
- Follow journal guidelines exactly
- Write clear cover letter
- Suggest appropriate reviewers
- Prepare for revision
- Don't take rejection personally

## Related Skills

- **research-synthesis**: Synthesizing literature
- **research-design**: Describing methods
- **quantitative-methods**: Reporting quantitative results
- **qualitative-methods**: Reporting qualitative findings
- **data-analysis**: Reporting analyses

## Quick Reference

### APA Reporting Templates

**T-test**:
```
t(df) = X.XX, p = .XXX, d = X.XX
```

**ANOVA**:
```
F(df₁, df₂) = X.XX, p = .XXX, η² = .XX
```

**Correlation**:
```
r(df) = .XX, p = .XXX
```

**Regression**:
```
β = .XX, t(df) = X.XX, p = .XXX
```

### Common Phrases

**Introducing results**:
- "As hypothesized..."
- "Contrary to expectations..."
- "Consistent with prior research..."

**Discussing limitations**:
- "A limitation of this study is..."
- "Findings should be interpreted cautiously given..."
- "Future research should address..."

**Drawing conclusions**:
- "These findings suggest that..."
- "Results provide evidence for..."
- "This study contributes to understanding..."

### Word Count Guidelines

```
Abstract:       150-250 words
Introduction:   500-1000 words
Methods:        800-1500 words
Results:        800-1500 words
Discussion:     1000-2000 words
Total:          4000-7000 words (typical journal article)
```
