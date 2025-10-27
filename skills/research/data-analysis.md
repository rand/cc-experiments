---
name: research-data-analysis
description: Master data analysis techniques including coding, statistical tests, visualization, interpretation, and reporting findings
---

# Data Analysis Skill

## When to Use This Skill

Use this skill when you need to:
- Analyze quantitative or qualitative data
- Code textual data systematically
- Choose appropriate statistical tests
- Visualize data effectively
- Interpret analysis results
- Check analysis assumptions
- Report findings clearly
- Handle complex or messy data

## Quantitative Data Analysis

### 1. Descriptive Statistics

**Comprehensive Description Framework**:
```python
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

class DescriptiveAnalysis:
    """Comprehensive descriptive statistics"""

    def __init__(self, data: pd.DataFrame):
        self.data = data

    def continuous_summary(self, var: str):
        """Summarize continuous variable"""
        series = self.data[var].dropna()

        summary = {
            'n': len(series),
            'missing': self.data[var].isna().sum(),
            'mean': series.mean(),
            'median': series.median(),
            'std': series.std(),
            'min': series.min(),
            'max': series.max(),
            'q25': series.quantile(0.25),
            'q75': series.quantile(0.75),
            'skewness': stats.skew(series),
            'kurtosis': stats.kurtosis(series)
        }

        # Add confidence interval for mean
        ci = stats.t.interval(0.95, len(series)-1,
                            loc=summary['mean'],
                            scale=stats.sem(series))
        summary['ci_95_lower'] = ci[0]
        summary['ci_95_upper'] = ci[1]

        return summary

    def categorical_summary(self, var: str):
        """Summarize categorical variable"""
        counts = self.data[var].value_counts()
        proportions = self.data[var].value_counts(normalize=True)

        summary = pd.DataFrame({
            'Count': counts,
            'Proportion': proportions,
            'Percentage': proportions * 100
        })

        summary['95% CI Lower'] = summary.apply(
            lambda row: self._proportion_ci(row['Count'], len(self.data))[0],
            axis=1
        )
        summary['95% CI Upper'] = summary.apply(
            lambda row: self._proportion_ci(row['Count'], len(self.data))[1],
            axis=1
        )

        return summary

    @staticmethod
    def _proportion_ci(count, n, confidence=0.95):
        """Wilson score confidence interval for proportion"""
        from statsmodels.stats.proportion import proportion_confint
        return proportion_confint(count, n, alpha=1-confidence, method='wilson')

    def create_descriptive_table(self, continuous_vars: list,
                                categorical_vars: list):
        """Create Table 1 style descriptive statistics"""
        table = []

        for var in continuous_vars:
            summary = self.continuous_summary(var)
            table.append({
                'Variable': var,
                'Type': 'Continuous',
                'Summary': f"{summary['mean']:.2f} ± {summary['std']:.2f}",
                'Range': f"[{summary['min']:.2f}, {summary['max']:.2f}]",
                'N': summary['n']
            })

        for var in categorical_vars:
            summary = self.categorical_summary(var)
            for category, row in summary.iterrows():
                table.append({
                    'Variable': f"{var}: {category}",
                    'Type': 'Categorical',
                    'Summary': f"{row['Count']} ({row['Percentage']:.1f}%)",
                    'Range': f"[{row['95% CI Lower']:.3f}, "
                            f"{row['95% CI Upper']:.3f}]",
                    'N': row['Count']
                })

        return pd.DataFrame(table)

    def visualize_distribution(self, var: str, var_type: str = 'continuous'):
        """Create distribution visualizations"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        if var_type == 'continuous':
            # Histogram with KDE
            axes[0].hist(self.data[var].dropna(), bins=30,
                        density=True, alpha=0.7, edgecolor='black')
            self.data[var].plot.kde(ax=axes[0], color='red', linewidth=2)
            axes[0].set_xlabel(var)
            axes[0].set_ylabel('Density')
            axes[0].set_title(f'Distribution of {var}')

            # Q-Q plot for normality
            stats.probplot(self.data[var].dropna(), dist="norm", plot=axes[1])
            axes[1].set_title('Q-Q Plot (Normality Check)')

        else:  # categorical
            # Bar chart
            counts = self.data[var].value_counts()
            axes[0].bar(range(len(counts)), counts.values)
            axes[0].set_xticks(range(len(counts)))
            axes[0].set_xticklabels(counts.index, rotation=45, ha='right')
            axes[0].set_ylabel('Count')
            axes[0].set_title(f'Frequency of {var}')

            # Proportion with CI
            summary = self.categorical_summary(var)
            x = range(len(summary))
            axes[1].bar(x, summary['Percentage'])
            axes[1].errorbar(x,
                           summary['Percentage'],
                           yerr=[summary['Percentage'] - summary['95% CI Lower']*100,
                                 summary['95% CI Upper']*100 - summary['Percentage']],
                           fmt='none', color='black', capsize=5)
            axes[1].set_xticks(x)
            axes[1].set_xticklabels(summary.index, rotation=45, ha='right')
            axes[1].set_ylabel('Percentage')
            axes[1].set_title(f'Proportion with 95% CI')

        plt.tight_layout()
        return fig

# Example usage
data = pd.DataFrame({
    'age': np.random.normal(35, 10, 100),
    'satisfaction': np.random.choice([1, 2, 3, 4, 5], 100),
    'group': np.random.choice(['Control', 'Treatment'], 100)
})

analysis = DescriptiveAnalysis(data)
print(analysis.continuous_summary('age'))
print(analysis.categorical_summary('group'))
table = analysis.create_descriptive_table(
    continuous_vars=['age'],
    categorical_vars=['group', 'satisfaction']
)
print(table)
```

### 2. Inferential Statistics

**Comprehensive Testing Framework**:
```python
from scipy import stats
import pandas as pd
import numpy as np
from typing import Tuple, Dict

class InferentialAnalysis:
    """Statistical inference with proper reporting"""

    @staticmethod
    def t_test(group1, group2, paired: bool = False,
              alpha: float = 0.05) -> Dict:
        """Conduct t-test with full reporting"""
        g1 = np.array(group1)
        g2 = np.array(group2)

        # Remove NaN
        if paired:
            mask = ~(np.isnan(g1) | np.isnan(g2))
            g1, g2 = g1[mask], g2[mask]
            t_stat, p_value = stats.ttest_rel(g1, g2)
            df = len(g1) - 1
            # Cohen's d for paired
            diff = g1 - g2
            cohens_d = np.mean(diff) / np.std(diff, ddof=1)
        else:
            g1 = g1[~np.isnan(g1)]
            g2 = g2[~np.isnan(g2)]
            t_stat, p_value = stats.ttest_ind(g1, g2)
            df = len(g1) + len(g2) - 2
            # Cohen's d for independent
            pooled_std = np.sqrt(((len(g1)-1)*np.var(g1, ddof=1) +
                                 (len(g2)-1)*np.var(g2, ddof=1)) / df)
            cohens_d = (np.mean(g1) - np.mean(g2)) / pooled_std

        # Effect size interpretation
        if abs(cohens_d) < 0.2:
            effect_size = 'negligible'
        elif abs(cohens_d) < 0.5:
            effect_size = 'small'
        elif abs(cohens_d) < 0.8:
            effect_size = 'medium'
        else:
            effect_size = 'large'

        return {
            'test': 'paired t-test' if paired else 'independent t-test',
            't_statistic': t_stat,
            'df': df,
            'p_value': p_value,
            'significant': p_value < alpha,
            'mean_1': np.mean(g1),
            'mean_2': np.mean(g2),
            'mean_diff': np.mean(g1) - np.mean(g2),
            'cohens_d': cohens_d,
            'effect_size': effect_size,
            'n_1': len(g1),
            'n_2': len(g2)
        }

    @staticmethod
    def anova(groups: list, alpha: float = 0.05) -> Dict:
        """One-way ANOVA with post-hoc tests"""
        # ANOVA
        f_stat, p_value = stats.f_oneway(*groups)
        df_between = len(groups) - 1
        df_within = sum(len(g) for g in groups) - len(groups)

        # Effect size (eta-squared)
        grand_mean = np.mean([x for g in groups for x in g])
        ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2
                        for g in groups)
        ss_total = sum((x - grand_mean)**2 for g in groups for x in g)
        eta_squared = ss_between / ss_total

        result = {
            'test': 'One-way ANOVA',
            'f_statistic': f_stat,
            'df_between': df_between,
            'df_within': df_within,
            'p_value': p_value,
            'significant': p_value < alpha,
            'eta_squared': eta_squared,
            'n_groups': len(groups)
        }

        # Post-hoc pairwise comparisons if significant
        if p_value < alpha:
            from itertools import combinations
            pairwise = []

            for i, j in combinations(range(len(groups)), 2):
                t_result = InferentialAnalysis.t_test(groups[i], groups[j])
                # Bonferroni correction
                adjusted_alpha = alpha / (len(groups) * (len(groups) - 1) / 2)
                pairwise.append({
                    'comparison': f'Group {i+1} vs Group {j+1}',
                    'p_value': t_result['p_value'],
                    'significant_bonferroni': t_result['p_value'] < adjusted_alpha,
                    'mean_diff': t_result['mean_diff']
                })

            result['post_hoc'] = pairwise

        return result

    @staticmethod
    def correlation(x, y, method: str = 'pearson',
                   alpha: float = 0.05) -> Dict:
        """Correlation with confidence interval"""
        # Remove NaN
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean = np.array(x)[mask]
        y_clean = np.array(y)[mask]

        if method == 'pearson':
            r, p_value = stats.pearsonr(x_clean, y_clean)
        elif method == 'spearman':
            r, p_value = stats.spearmanr(x_clean, y_clean)
        else:
            raise ValueError("method must be 'pearson' or 'spearman'")

        n = len(x_clean)

        # Fisher's z transformation for CI
        if method == 'pearson':
            z = 0.5 * np.log((1 + r) / (1 - r))
            se = 1 / np.sqrt(n - 3)
            z_crit = stats.norm.ppf(1 - alpha/2)
            ci_lower = np.tanh(z - z_crit * se)
            ci_upper = np.tanh(z + z_crit * se)
        else:
            ci_lower, ci_upper = None, None

        # Coefficient of determination
        r_squared = r ** 2

        return {
            'test': f'{method.capitalize()} correlation',
            'r': r,
            'r_squared': r_squared,
            'p_value': p_value,
            'significant': p_value < alpha,
            'ci_95_lower': ci_lower,
            'ci_95_upper': ci_upper,
            'n': n
        }

    @staticmethod
    def chi_square(contingency_table, alpha: float = 0.05) -> Dict:
        """Chi-square test of independence"""
        chi2, p_value, df, expected = stats.chi2_contingency(contingency_table)

        # Effect size (Cramer's V)
        n = np.sum(contingency_table)
        min_dim = min(contingency_table.shape[0] - 1,
                     contingency_table.shape[1] - 1)
        cramers_v = np.sqrt(chi2 / (n * min_dim))

        return {
            'test': 'Chi-square test of independence',
            'chi2_statistic': chi2,
            'df': df,
            'p_value': p_value,
            'significant': p_value < alpha,
            'cramers_v': cramers_v,
            'expected_frequencies': expected
        }

    @staticmethod
    def format_apa(result: Dict) -> str:
        """Format result in APA style"""
        test = result['test']

        if 't-test' in test:
            return (f"t({result['df']}) = {result['t_statistic']:.2f}, "
                   f"p = {result['p_value']:.3f}, d = {result['cohens_d']:.2f}")

        elif 'ANOVA' in test:
            return (f"F({result['df_between']}, {result['df_within']}) = "
                   f"{result['f_statistic']:.2f}, p = {result['p_value']:.3f}, "
                   f"η² = {result['eta_squared']:.2f}")

        elif 'correlation' in test:
            return (f"r({result['n']-2}) = {result['r']:.2f}, "
                   f"p = {result['p_value']:.3f}")

        elif 'Chi-square' in test:
            return (f"χ²({result['df']}) = {result['chi2_statistic']:.2f}, "
                   f"p = {result['p_value']:.3f}, V = {result['cramers_v']:.2f}")

        return str(result)

# Example usage
control = np.random.normal(50, 10, 30)
treatment = np.random.normal(55, 10, 30)

result = InferentialAnalysis.t_test(control, treatment)
print(InferentialAnalysis.format_apa(result))
print(f"Interpretation: {result['effect_size']} effect size")
```

## Qualitative Data Analysis

### 1. Coding Process

**Systematic Coding Framework**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict
import pandas as pd

@dataclass
class Code:
    """Represent a qualitative code"""
    name: str
    definition: str
    when_to_use: str
    when_not_to_use: str
    examples: List[str]

@dataclass
class CodedSegment:
    """Represent coded text segment"""
    source: str
    text: str
    codes: List[str]
    line_numbers: tuple
    memo: str = ""

class QualitativeCoding:
    """Systematic qualitative coding"""

    def __init__(self):
        self.codebook = {}
        self.coded_segments = []
        self.memos = []

    def add_code(self, code: Code):
        """Add code to codebook"""
        self.codebook[code.name] = code

    def apply_code(self, segment: CodedSegment):
        """Apply codes to text segment"""
        # Validate codes exist
        for code in segment.codes:
            if code not in self.codebook:
                print(f"Warning: Code '{code}' not in codebook")

        self.coded_segments.append(segment)

    def add_memo(self, memo: str, codes: Optional[List[str]] = None):
        """Write analytical memo"""
        self.memos.append({
            'memo': memo,
            'codes': codes,
            'date': pd.Timestamp.now()
        })

    def get_code_frequency(self):
        """Count code applications"""
        freq = defaultdict(int)
        for segment in self.coded_segments:
            for code in segment.codes:
                freq[code] += 1
        return dict(freq)

    def get_coded_segments(self, code: str) -> List[CodedSegment]:
        """Retrieve all segments with a specific code"""
        return [seg for seg in self.coded_segments if code in seg.codes]

    def co_occurrence_matrix(self):
        """Create code co-occurrence matrix"""
        codes = list(self.codebook.keys())
        matrix = pd.DataFrame(0, index=codes, columns=codes)

        for segment in self.coded_segments:
            seg_codes = segment.codes
            for code1 in seg_codes:
                for code2 in seg_codes:
                    if code1 != code2:
                        matrix.loc[code1, code2] += 1

        return matrix

    def inter_rater_reliability(self, coder2_segments: List[CodedSegment]):
        """Calculate Cohen's Kappa for inter-rater reliability"""
        # Match segments by source and line numbers
        agreements = 0
        total = 0

        for seg1 in self.coded_segments:
            # Find matching segment from coder 2
            matching = [s for s in coder2_segments
                       if s.source == seg1.source and
                          s.line_numbers == seg1.line_numbers]

            if matching:
                seg2 = matching[0]
                # Check if codes match
                if set(seg1.codes) == set(seg2.codes):
                    agreements += 1
                total += 1

        if total == 0:
            return None

        observed_agreement = agreements / total

        # For simplicity, calculate expected agreement assuming random
        # (Full Cohen's Kappa requires more complex calculation)
        code_freq = self.get_code_frequency()
        total_codes = sum(code_freq.values())
        expected_agreement = sum((freq/total_codes)**2
                                for freq in code_freq.values())

        kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)

        return {
            'observed_agreement': observed_agreement,
            'expected_agreement': expected_agreement,
            'cohens_kappa': kappa,
            'interpretation': 'substantial' if kappa > 0.6 else
                            'moderate' if kappa > 0.4 else 'fair'
        }

    def generate_codebook_document(self):
        """Export codebook"""
        doc = "# Qualitative Codebook\n\n"

        for code_name, code in self.codebook.items():
            doc += f"## {code_name}\n\n"
            doc += f"**Definition**: {code.definition}\n\n"
            doc += f"**When to use**: {code.when_to_use}\n\n"
            doc += f"**When NOT to use**: {code.when_not_to_use}\n\n"
            doc += "**Examples**:\n"
            for ex in code.examples:
                doc += f"- {ex}\n"
            doc += "\n"

            # Add frequency
            freq = self.get_code_frequency().get(code_name, 0)
            doc += f"*Applied {freq} times*\n\n"
            doc += "---\n\n"

        return doc

# Example usage
coding = QualitativeCoding()

# Build codebook
coding.add_code(Code(
    name='boundary_work',
    definition='Actions taken to create or maintain work-life boundaries',
    when_to_use='When participant describes specific strategies or behaviors '
                'for separating work and personal life',
    when_not_to_use='When simply mentioning boundaries without action',
    examples=[
        '"I close my laptop at 5pm every day"',
        '"I have a separate room for work"'
    ]
))

coding.add_code(Code(
    name='role_conflict',
    definition='Tension between work and personal role demands',
    when_to_use='When participant describes competing demands or identity conflicts',
    when_not_to_use='When mentioning roles without conflict',
    examples=[
        '"I felt torn between meeting and picking up my kids"',
        '"I can\'t be fully present at home because I\'m thinking about work"'
    ]
))

# Code data
coding.apply_code(CodedSegment(
    source='Interview_P001',
    text='I always close my laptop at 5pm, even if work isn\'t done',
    codes=['boundary_work'],
    line_numbers=(45, 47),
    memo='Strong temporal boundary - clock-based'
))

coding.apply_code(CodedSegment(
    source='Interview_P001',
    text='But then I feel guilty about unfinished tasks',
    codes=['role_conflict'],
    line_numbers=(48, 49),
    memo='Guilt suggests incomplete boundary - work identity bleeds through'
))

# Analyze
print(coding.get_code_frequency())
print(coding.generate_codebook_document())
```

### 2. Thematic Development

**Theme Building Process**:
```python
class ThematicDevelopment:
    """Develop and refine themes from codes"""

    def __init__(self, coding: QualitativeCoding):
        self.coding = coding
        self.themes = {}

    def create_theme(self, theme_name: str, codes: List[str],
                    description: str):
        """Group codes into theme"""
        self.themes[theme_name] = {
            'codes': codes,
            'description': description,
            'definition': '',
            'subthemes': []
        }

    def define_theme(self, theme_name: str, definition: str):
        """Provide clear theme definition"""
        self.themes[theme_name]['definition'] = definition

    def add_subtheme(self, theme_name: str, subtheme_name: str,
                    codes: List[str]):
        """Add subtheme"""
        self.themes[theme_name]['subthemes'].append({
            'name': subtheme_name,
            'codes': codes
        })

    def theme_prevalence(self, theme_name: str):
        """Calculate theme prevalence"""
        theme = self.themes[theme_name]
        segments = []

        for code in theme['codes']:
            segments.extend(self.coding.get_coded_segments(code))

        # Get unique sources
        sources = set(seg.source for seg in segments)

        return {
            'theme': theme_name,
            'n_segments': len(segments),
            'n_sources': len(sources),
            'percentage_sources': (len(sources) /
                                  len(set(s.source for s in self.coding.coded_segments))) * 100
        }

    def generate_theme_map(self):
        """Create visual theme hierarchy"""
        map_str = "# Thematic Map\n\n"

        for theme_name, theme in self.themes.items():
            map_str += f"## {theme_name}\n"
            map_str += f"{theme['description']}\n\n"
            map_str += f"**Codes**: {', '.join(theme['codes'])}\n\n"

            if theme['subthemes']:
                map_str += "**Subthemes**:\n"
                for subtheme in theme['subthemes']:
                    map_str += f"- {subtheme['name']}: "
                    map_str += f"{', '.join(subtheme['codes'])}\n"

            prev = self.theme_prevalence(theme_name)
            map_str += f"\n*{prev['n_sources']} sources "
            map_str += f"({prev['percentage_sources']:.0f}%), "
            map_str += f"{prev['n_segments']} segments*\n\n"

        return map_str

# Example
thematic = ThematicDevelopment(coding)

thematic.create_theme(
    'Negotiating Boundaries',
    codes=['boundary_work', 'role_conflict'],
    description='The ongoing process of creating and maintaining work-life separation'
)

thematic.define_theme(
    'Negotiating Boundaries',
    'Remote workers actively and continuously construct boundaries between work '
    'and personal life through spatial, temporal, and communicative strategies, '
    'while managing guilt and role conflicts that arise from boundary violations.'
)

print(thematic.generate_theme_map())
```

## Data Visualization Best Practices

```python
import matplotlib.pyplot as plt
import seaborn as sns

class VisualizationGuide:
    """Create publication-ready visualizations"""

    @staticmethod
    def set_publication_style():
        """Set consistent style for publication"""
        sns.set_style('whitegrid')
        sns.set_context('paper', font_scale=1.2)
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial']
        plt.rcParams['figure.dpi'] = 300

    @staticmethod
    def comparison_plot(groups: Dict[str, list], ylabel: str, title: str):
        """Create comparison plot with error bars"""
        fig, ax = plt.subplots(figsize=(8, 6))

        x_pos = range(len(groups))
        means = [np.mean(data) for data in groups.values()]
        sems = [stats.sem(data) for data in groups.values()]

        ax.bar(x_pos, means, yerr=sems, capsize=5,
              color='steelblue', alpha=0.8, edgecolor='black')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(groups.keys())
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        return fig

    @staticmethod
    def scatter_with_regression(x, y, xlabel: str, ylabel: str):
        """Scatter plot with regression line"""
        fig, ax = plt.subplots(figsize=(8, 6))

        ax.scatter(x, y, alpha=0.6, s=50)

        # Add regression line
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        ax.plot(x, p(x), 'r--', linewidth=2)

        # Add correlation
        r, p_val = stats.pearsonr(x, y)
        ax.text(0.05, 0.95, f'r = {r:.3f}, p = {p_val:.3f}',
               transform=ax.transAxes, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        return fig
```

## Best Practices

### Quantitative Analysis
- Check assumptions before tests
- Report effect sizes, not just p-values
- Provide confidence intervals
- Correct for multiple comparisons
- Document all analysis decisions
- Report negative results
- Make data and code available

### Qualitative Analysis
- Code systematically with clear definitions
- Calculate inter-rater reliability
- Write analytic memos throughout
- Seek negative cases
- Use software for transparency
- Provide thick description
- Maintain audit trail

### Visualization
- Choose appropriate chart type
- Label axes clearly
- Include error bars or confidence intervals
- Use colorblind-friendly palettes
- Remove chart junk
- Export at high resolution
- Caption thoroughly

## Related Skills

- **quantitative-methods**: Quantitative research approaches
- **qualitative-methods**: Qualitative research approaches
- **research-synthesis**: Analyzing across studies
- **data-collection**: Obtaining analyzable data
- **research-writing**: Reporting analyses

## Quick Reference

### Test Selection Guide
```
Compare 2 groups:        Independent t-test
Compare 2 timepoints:    Paired t-test
Compare 3+ groups:       ANOVA
Relationship:            Correlation
Prediction:              Regression
Categorical association: Chi-square
Non-normal data:         Non-parametric alternatives
```

### Effect Size Interpretation
```
Cohen's d:    0.2 small, 0.5 medium, 0.8 large
Correlation:  0.1 small, 0.3 medium, 0.5 large
Eta-squared:  0.01 small, 0.06 medium, 0.14 large
```

### Coding Reliability Standards
```
Cohen's Kappa:
< 0.20: Poor
0.21-0.40: Fair
0.41-0.60: Moderate
0.61-0.80: Substantial
0.81-1.00: Almost perfect
```
