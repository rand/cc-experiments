---
name: research-synthesis
description: Master information synthesis, literature review, meta-analysis, and knowledge integration across sources
---

# Research Synthesis Skill

## When to Use This Skill

Use this skill when you need to:
- Conduct systematic literature reviews
- Synthesize findings across multiple studies
- Perform meta-analysis of quantitative research
- Integrate qualitative findings across sources
- Identify research gaps and trends
- Create knowledge maps and frameworks
- Write comprehensive review papers
- Evaluate evidence quality and strength

## Core Synthesis Approaches

### 1. Narrative Synthesis

**Purpose**: Qualitative integration of findings using words and text

**Process**:
```
1. Define scope and research questions
2. Search and select studies systematically
3. Extract key findings and themes
4. Organize by theoretical framework or chronology
5. Identify patterns, contradictions, gaps
6. Synthesize into coherent narrative
```

**Example Structure**:
```markdown
## Research Question
How does X influence Y in Z contexts?

## Synthesis Findings

### Theme 1: Direct Effects
- Study A (2023): Found positive correlation (r=0.65, p<0.01)
- Study B (2022): Confirmed effect in different population
- Study C (2021): Mixed results, moderated by factor Q

### Theme 2: Mediating Mechanisms
- Study D identifies pathway through M
- Study E challenges this, proposes alternative

### Theme 3: Contextual Factors
- Effect stronger in setting X
- No effect observed in setting Y

## Synthesis Conclusion
Evidence suggests X→Y relationship is robust but context-dependent...
```

### 2. Meta-Analysis

**Purpose**: Statistical integration of quantitative results

**Python Implementation**:
```python
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

class MetaAnalysis:
    """Fixed and random effects meta-analysis"""

    def __init__(self, effect_sizes, standard_errors, study_labels):
        self.effects = np.array(effect_sizes)
        self.se = np.array(standard_errors)
        self.labels = study_labels
        self.weights = None
        self.pooled_effect = None

    def fixed_effects(self):
        """Fixed effects meta-analysis"""
        # Inverse variance weighting
        self.weights = 1 / (self.se ** 2)
        self.pooled_effect = np.sum(self.weights * self.effects) / np.sum(self.weights)
        pooled_se = np.sqrt(1 / np.sum(self.weights))

        # 95% CI
        ci_lower = self.pooled_effect - 1.96 * pooled_se
        ci_upper = self.pooled_effect + 1.96 * pooled_se

        # Heterogeneity statistics
        Q = np.sum(self.weights * (self.effects - self.pooled_effect) ** 2)
        df = len(self.effects) - 1
        I2 = max(0, ((Q - df) / Q) * 100)

        return {
            'pooled_effect': self.pooled_effect,
            'se': pooled_se,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'Q': Q,
            'I2': I2,
            'p_heterogeneity': 1 - stats.chi2.cdf(Q, df)
        }

    def random_effects(self, tau2_method='DL'):
        """Random effects meta-analysis (DerSimonian-Laird)"""
        # First get fixed effects for Q statistic
        fixed = self.fixed_effects()
        Q = fixed['Q']
        df = len(self.effects) - 1

        # Estimate between-study variance (tau^2)
        C = np.sum(self.weights) - np.sum(self.weights ** 2) / np.sum(self.weights)
        tau2 = max(0, (Q - df) / C)

        # Random effects weights
        re_weights = 1 / (self.se ** 2 + tau2)
        pooled_effect = np.sum(re_weights * self.effects) / np.sum(re_weights)
        pooled_se = np.sqrt(1 / np.sum(re_weights))

        ci_lower = pooled_effect - 1.96 * pooled_se
        ci_upper = pooled_effect + 1.96 * pooled_se

        return {
            'pooled_effect': pooled_effect,
            'se': pooled_se,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'tau2': tau2,
            'I2': fixed['I2']
        }

    def forest_plot(self, results, title='Meta-Analysis Forest Plot'):
        """Create forest plot visualization"""
        fig, ax = plt.subplots(figsize=(10, len(self.effects) + 2))

        # Calculate CIs for individual studies
        ci_lower = self.effects - 1.96 * self.se
        ci_upper = self.effects + 1.96 * self.se

        # Plot individual studies
        y_pos = np.arange(len(self.effects))
        ax.errorbar(self.effects, y_pos,
                   xerr=[self.effects - ci_lower, ci_upper - self.effects],
                   fmt='s', markersize=8, capsize=5, label='Studies')

        # Plot pooled effect
        pooled_y = len(self.effects) + 0.5
        ax.errorbar([results['pooled_effect']], [pooled_y],
                   xerr=[[results['pooled_effect'] - results['ci_lower']],
                         [results['ci_upper'] - results['pooled_effect']]],
                   fmt='D', markersize=12, capsize=8,
                   color='red', label='Pooled Effect')

        # Styling
        ax.axvline(x=0, color='black', linestyle='--', linewidth=1)
        ax.set_yticks(list(y_pos) + [pooled_y])
        ax.set_yticklabels(list(self.labels) + ['Pooled'])
        ax.set_xlabel('Effect Size')
        ax.set_title(title)
        ax.legend()
        ax.grid(axis='x', alpha=0.3)

        return fig

# Example usage
studies = [
    ('Study A', 0.45, 0.12),
    ('Study B', 0.62, 0.15),
    ('Study C', 0.38, 0.10),
    ('Study D', 0.51, 0.14),
    ('Study E', 0.55, 0.11)
]

labels = [s[0] for s in studies]
effects = [s[1] for s in studies]
ses = [s[2] for s in studies]

meta = MetaAnalysis(effects, ses, labels)
fixed_results = meta.fixed_effects()
random_results = meta.random_effects()

print(f"Fixed Effects: {fixed_results['pooled_effect']:.3f} "
      f"[{fixed_results['ci_lower']:.3f}, {fixed_results['ci_upper']:.3f}]")
print(f"I² = {fixed_results['I2']:.1f}%")
print(f"\nRandom Effects: {random_results['pooled_effect']:.3f} "
      f"[{random_results['ci_lower']:.3f}, {random_results['ci_upper']:.3f}]")

# Create forest plot
fig = meta.forest_plot(random_results)
plt.savefig('forest_plot.png', dpi=300, bbox_inches='tight')
```

### 3. Thematic Synthesis

**Purpose**: Integrate qualitative findings across studies

**Process**:
```python
from collections import defaultdict
import pandas as pd

class ThematicSynthesis:
    """Synthesize themes across qualitative studies"""

    def __init__(self):
        self.studies = []
        self.themes = defaultdict(list)

    def add_study(self, study_id, findings):
        """Add study findings

        Args:
            study_id: Study identifier
            findings: List of (finding, theme) tuples
        """
        self.studies.append(study_id)
        for finding, theme in findings:
            self.themes[theme].append({
                'study': study_id,
                'finding': finding
            })

    def get_theme_matrix(self):
        """Create study x theme presence matrix"""
        themes = list(self.themes.keys())
        matrix = []

        for study in self.studies:
            row = []
            for theme in themes:
                has_theme = any(f['study'] == study for f in self.themes[theme])
                row.append(1 if has_theme else 0)
            matrix.append(row)

        return pd.DataFrame(matrix,
                          index=self.studies,
                          columns=themes)

    def synthesize_theme(self, theme_name):
        """Synthesize findings for a specific theme"""
        findings = self.themes[theme_name]

        synthesis = {
            'theme': theme_name,
            'n_studies': len(set(f['study'] for f in findings)),
            'n_findings': len(findings),
            'findings_by_study': defaultdict(list)
        }

        for finding in findings:
            synthesis['findings_by_study'][finding['study']].append(
                finding['finding']
            )

        return synthesis

    def generate_report(self):
        """Generate synthesis report"""
        report = []
        report.append("# Thematic Synthesis Report\n")
        report.append(f"Total Studies: {len(self.studies)}\n")
        report.append(f"Total Themes: {len(self.themes)}\n\n")

        # Theme frequency
        report.append("## Theme Prevalence\n")
        for theme, findings in sorted(self.themes.items(),
                                    key=lambda x: len(x[1]),
                                    reverse=True):
            n_studies = len(set(f['study'] for f in findings))
            report.append(f"- **{theme}**: {n_studies} studies, "
                        f"{len(findings)} findings\n")

        report.append("\n## Detailed Synthesis\n")
        for theme in sorted(self.themes.keys()):
            synthesis = self.synthesize_theme(theme)
            report.append(f"\n### {theme}\n")
            report.append(f"Present in {synthesis['n_studies']} studies\n\n")

            for study, findings in synthesis['findings_by_study'].items():
                report.append(f"**{study}**:\n")
                for finding in findings:
                    report.append(f"- {finding}\n")
                report.append("\n")

        return ''.join(report)

# Example usage
synth = ThematicSynthesis()

synth.add_study('Smith2023', [
    ('Participants valued flexibility', 'Flexibility'),
    ('Trust was essential for engagement', 'Trust'),
    ('Time constraints were barrier', 'Barriers')
])

synth.add_study('Jones2022', [
    ('Flexibility enabled participation', 'Flexibility'),
    ('Communication breakdowns reduced trust', 'Trust'),
    ('Technology issues created frustration', 'Barriers')
])

synth.add_study('Lee2023', [
    ('Schedule flexibility was key benefit', 'Flexibility'),
    ('Clear expectations built trust', 'Trust')
])

# Generate outputs
matrix = synth.get_theme_matrix()
print(matrix)
print("\n" + synth.generate_report())
```

### 4. Evidence Mapping

**Purpose**: Visualize research landscape and gaps

**Approach**:
```python
import networkx as nx
import matplotlib.pyplot as plt

class EvidenceMap:
    """Create evidence map of research domain"""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_study(self, study_id, population, intervention,
                 outcome, quality='medium'):
        """Add study to evidence map"""
        # Create nodes
        pop_node = f"POP: {population}"
        int_node = f"INT: {intervention}"
        out_node = f"OUT: {outcome}"

        self.graph.add_node(pop_node, type='population')
        self.graph.add_node(int_node, type='intervention')
        self.graph.add_node(out_node, type='outcome')

        # Create edges
        self.graph.add_edge(pop_node, int_node,
                          study=study_id, quality=quality)
        self.graph.add_edge(int_node, out_node,
                          study=study_id, quality=quality)

    def identify_gaps(self):
        """Identify under-researched areas"""
        gaps = {
            'populations': [],
            'interventions': [],
            'outcomes': [],
            'combinations': []
        }

        # Find nodes with few connections
        for node in self.graph.nodes():
            degree = self.graph.degree(node)
            node_type = self.graph.nodes[node]['type']

            if degree < 2:
                gaps[f"{node_type}s"].append(node)

        return gaps

    def visualize(self):
        """Create evidence map visualization"""
        pos = nx.spring_layout(self.graph, k=2, iterations=50)

        # Color by node type
        colors = []
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node]['type']
            if node_type == 'population':
                colors.append('lightblue')
            elif node_type == 'intervention':
                colors.append('lightgreen')
            else:
                colors.append('lightyellow')

        plt.figure(figsize=(12, 8))
        nx.draw(self.graph, pos, node_color=colors,
               with_labels=True, node_size=3000,
               font_size=8, arrows=True)

        plt.title('Evidence Map')
        return plt.gcf()
```

## Synthesis Quality Assessment

### GRADE Framework

**Criteria for Evidence Quality**:
1. **Risk of bias**: Study design and execution quality
2. **Inconsistency**: Heterogeneity across studies
3. **Indirectness**: Relevance to question
4. **Imprecision**: Sample size and confidence intervals
5. **Publication bias**: Missing studies

**Rating System**:
```
High:     Further research unlikely to change confidence
Moderate: Further research likely important to confidence
Low:      Further research very likely important
Very Low: Very uncertain about the estimate
```

## Synthesis Patterns

### Effective Synthesis
```
✓ Systematic search strategy documented
✓ Inclusion/exclusion criteria clear
✓ Quality assessment of each study
✓ Appropriate synthesis method for data type
✓ Heterogeneity acknowledged and explored
✓ Limitations discussed
✓ Practical implications stated
✓ Research gaps identified
```

### Ineffective Synthesis
```
✗ Cherry-picking favorable studies
✗ Mixing apples and oranges without justification
✗ Ignoring study quality differences
✗ Over-generalizing from limited evidence
✗ Failing to report null findings
✗ Missing recent relevant studies
✗ Synthesis method unclear or inappropriate
```

## Best Practices

### 1. Planning Phase
- Register protocol (PROSPERO for systematic reviews)
- Define clear research questions (PICO framework)
- Specify inclusion/exclusion criteria a priori
- Plan synthesis approach before seeing results

### 2. Search Strategy
- Use multiple databases
- Include grey literature
- Hand-search key journals
- Contact experts for unpublished work
- Document search terms and results

### 3. Data Extraction
- Use standardized extraction forms
- Dual extraction for quality control
- Extract both results and methods details
- Contact authors for missing data
- Track extraction decisions

### 4. Synthesis Execution
- Choose method appropriate for data type
- Test for heterogeneity before pooling
- Explore sources of heterogeneity
- Conduct sensitivity analyses
- Assess publication bias (funnel plots)

### 5. Reporting
- Follow PRISMA guidelines
- Create PRISMA flow diagram
- Report all included studies
- Present individual study details
- Discuss quality and limitations

## Common Pitfalls

1. **Scope Creep**: Question becomes too broad during review
   - Solution: Return to original PICO, create separate reviews if needed

2. **Data Overload**: Drowning in extracted information
   - Solution: Use structured extraction tools, focus on key variables

3. **Apples to Oranges**: Pooling incomparable studies
   - Solution: Narrative synthesis or subgroup meta-analysis

4. **Publication Bias**: Missing negative results
   - Solution: Grey literature search, contact authors, funnel plots

5. **Cherry Picking**: Selective reporting of themes
   - Solution: Systematic coding, frequency analysis, audit trail

## Related Skills

- **research-design**: Formulating synthesis research questions
- **data-analysis**: Statistical techniques for meta-analysis
- **quantitative-methods**: Understanding primary study methods
- **qualitative-methods**: Synthesizing qualitative findings
- **research-writing**: Writing synthesis reports and reviews
- **data-collection**: Systematic search and extraction protocols

## Templates and Tools

### PRISMA Flow Diagram Template
```
Records identified through database searching (n=)
  ↓
Records after duplicates removed (n=)
  ↓
Records screened (n=) → Records excluded (n=)
  ↓
Full-text assessed (n=) → Full-text excluded, with reasons (n=)
  ↓
Studies included in synthesis (n=)
  ↓
Studies included in meta-analysis (n=)
```

### Synthesis Summary Table
```markdown
| Study | Year | Design | N | Population | Outcome | Effect Size | Quality |
|-------|------|--------|---|------------|---------|-------------|---------|
| A     | 2023 | RCT    |100| Adults     | Anxiety | d=-0.45     | High    |
| B     | 2022 | Cohort |250| Teens      | Anxiety | d=-0.32     | Medium  |
```
