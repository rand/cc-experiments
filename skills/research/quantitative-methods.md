---
name: research-quantitative-methods
description: Master quantitative research methods including statistical analysis, surveys, experiments, and hypothesis testing
---

# Quantitative Research Methods Skill

## When to Use This Skill

Use this skill when you need to:
- Design quantitative research studies
- Conduct statistical hypothesis testing
- Analyze survey data
- Run experiments and measure effects
- Perform correlation and regression analyses
- Test causal relationships
- Validate measurement instruments
- Report quantitative findings

## Core Quantitative Approaches

### 1. Experimental Design

**Purpose**: Test causal relationships through controlled manipulation

**Design Types**:
```python
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np
from scipy import stats

@dataclass
class ExperimentDesign:
    """Define experimental design parameters"""
    design_type: str  # 'between', 'within', 'mixed', 'factorial'
    independent_vars: List[str]
    dependent_vars: List[str]
    n_per_group: int
    random_assignment: bool = True
    blocking_var: Optional[str] = None

    def calculate_power(self, effect_size, alpha=0.05):
        """Calculate statistical power"""
        from statsmodels.stats.power import TTestIndPower

        if self.design_type == 'between':
            analysis = TTestIndPower()
            power = analysis.power(effect_size=effect_size,
                                  nobs1=self.n_per_group,
                                  alpha=alpha,
                                  alternative='two-sided')
            return power
        else:
            raise NotImplementedError(f"{self.design_type} power calculation")

    def required_n(self, effect_size, power=0.80, alpha=0.05):
        """Calculate required sample size"""
        from statsmodels.stats.power import TTestIndPower

        if self.design_type == 'between':
            analysis = TTestIndPower()
            n = analysis.solve_power(effect_size=effect_size,
                                   power=power,
                                   alpha=alpha,
                                   alternative='two-sided')
            return int(np.ceil(n))
        else:
            raise NotImplementedError(f"{self.design_type} sample size")

# Example: Between-subjects experiment
design = ExperimentDesign(
    design_type='between',
    independent_vars=['treatment_condition'],
    dependent_vars=['outcome_score'],
    n_per_group=50
)

print(f"Power for d=0.5: {design.calculate_power(0.5):.3f}")
print(f"Required N for 80% power: {design.required_n(0.5)}")
```

### 2. Survey Methods

**Purpose**: Collect self-report data from samples or populations

**Survey Design Implementation**:
```python
import pandas as pd
import numpy as np
from scipy import stats

class SurveyAnalysis:
    """Analyze survey data with proper weighting and missing data"""

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.weights = None

    def set_weights(self, weight_col: str):
        """Set sampling weights"""
        self.weights = self.data[weight_col]

    def weighted_mean(self, var: str):
        """Calculate weighted mean"""
        if self.weights is None:
            return self.data[var].mean()

        weighted_sum = (self.data[var] * self.weights).sum()
        return weighted_sum / self.weights.sum()

    def weighted_proportion(self, var: str, value):
        """Calculate weighted proportion"""
        if self.weights is None:
            return (self.data[var] == value).mean()

        matches = (self.data[var] == value).astype(int)
        weighted_sum = (matches * self.weights).sum()
        return weighted_sum / self.weights.sum()

    def cronbach_alpha(self, items: List[str]):
        """Calculate reliability (internal consistency)"""
        item_data = self.data[items].dropna()
        n_items = len(items)

        # Variance of each item
        item_vars = item_data.var(axis=0, ddof=1)

        # Variance of total score
        total_var = item_data.sum(axis=1).var(ddof=1)

        # Cronbach's alpha
        alpha = (n_items / (n_items - 1)) * (1 - item_vars.sum() / total_var)
        return alpha

    def response_rate_bias(self, response_indicator: str,
                          demographic_vars: List[str]):
        """Test for response bias"""
        results = {}

        for var in demographic_vars:
            # Compare respondents vs non-respondents
            respondents = self.data[self.data[response_indicator] == 1][var]
            non_respondents = self.data[self.data[response_indicator] == 0][var]

            # T-test or chi-square depending on variable type
            if self.data[var].dtype in ['int64', 'float64']:
                stat, p = stats.ttest_ind(respondents, non_respondents,
                                         nan_policy='omit')
                test = 't-test'
            else:
                # Chi-square for categorical
                contingency = pd.crosstab(self.data[response_indicator],
                                        self.data[var])
                stat, p, _, _ = stats.chi2_contingency(contingency)
                test = 'chi-square'

            results[var] = {
                'test': test,
                'statistic': stat,
                'p_value': p,
                'biased': p < 0.05
            }

        return results

# Example usage
survey = SurveyAnalysis(pd.DataFrame({
    'satisfaction': [4, 5, 3, 4, 5, 2, 4, 5, 3, 4],
    'loyalty': [5, 5, 4, 4, 5, 3, 4, 5, 4, 4],
    'recommend': [4, 5, 3, 5, 5, 2, 4, 5, 3, 5],
    'weight': [1.2, 0.8, 1.0, 1.1, 0.9, 1.3, 1.0, 0.9, 1.1, 1.0]
}))

survey.set_weights('weight')
print(f"Weighted mean satisfaction: {survey.weighted_mean('satisfaction'):.2f}")

# Calculate scale reliability
alpha = survey.cronbach_alpha(['satisfaction', 'loyalty', 'recommend'])
print(f"Cronbach's alpha: {alpha:.3f}")
```

### 3. Hypothesis Testing

**Purpose**: Make statistical inferences about populations

**Common Tests Implementation**:
```python
import pandas as pd
import numpy as np
from scipy import stats
from typing import Tuple

class HypothesisTests:
    """Common hypothesis tests with effect sizes"""

    @staticmethod
    def t_test_independent(group1, group2, alpha=0.05):
        """Independent samples t-test with Cohen's d"""
        # Remove NaN values
        g1 = np.array(group1)[~np.isnan(group1)]
        g2 = np.array(group2)[~np.isnan(group2)]

        # T-test
        t_stat, p_value = stats.ttest_ind(g1, g2)

        # Cohen's d
        pooled_std = np.sqrt(((len(g1)-1)*np.var(g1, ddof=1) +
                             (len(g2)-1)*np.var(g2, ddof=1)) /
                            (len(g1) + len(g2) - 2))
        cohens_d = (np.mean(g1) - np.mean(g2)) / pooled_std

        # Confidence interval
        se_diff = pooled_std * np.sqrt(1/len(g1) + 1/len(g2))
        df = len(g1) + len(g2) - 2
        t_crit = stats.t.ppf(1 - alpha/2, df)
        ci = (np.mean(g1) - np.mean(g2) - t_crit * se_diff,
              np.mean(g1) - np.mean(g2) + t_crit * se_diff)

        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'mean_diff': np.mean(g1) - np.mean(g2),
            'ci_95': ci,
            'significant': p_value < alpha
        }

    @staticmethod
    def t_test_paired(before, after, alpha=0.05):
        """Paired samples t-test with Cohen's d"""
        differences = np.array(after) - np.array(before)
        differences = differences[~np.isnan(differences)]

        # T-test
        t_stat, p_value = stats.ttest_1samp(differences, 0)

        # Cohen's d for paired samples
        cohens_d = np.mean(differences) / np.std(differences, ddof=1)

        # Confidence interval
        se = stats.sem(differences)
        df = len(differences) - 1
        t_crit = stats.t.ppf(1 - alpha/2, df)
        ci = (np.mean(differences) - t_crit * se,
              np.mean(differences) + t_crit * se)

        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'mean_diff': np.mean(differences),
            'ci_95': ci,
            'significant': p_value < alpha
        }

    @staticmethod
    def anova_oneway(groups, alpha=0.05):
        """One-way ANOVA with eta-squared"""
        # F-test
        f_stat, p_value = stats.f_oneway(*groups)

        # Effect size (eta-squared)
        grand_mean = np.mean([x for group in groups for x in group])
        ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2
                        for g in groups)
        ss_total = sum((x - grand_mean)**2
                      for group in groups for x in group)
        eta_squared = ss_between / ss_total

        return {
            'f_statistic': f_stat,
            'p_value': p_value,
            'eta_squared': eta_squared,
            'significant': p_value < alpha
        }

    @staticmethod
    def chi_square_test(observed_freq, expected_freq=None, alpha=0.05):
        """Chi-square goodness of fit or independence"""
        if expected_freq is None:
            # Equal expected frequencies
            expected_freq = np.ones_like(observed_freq) * np.mean(observed_freq)

        chi2_stat, p_value = stats.chisquare(observed_freq, expected_freq)

        # Effect size (Cramer's V for 2x2 table)
        n = np.sum(observed_freq)
        cramers_v = np.sqrt(chi2_stat / n)

        return {
            'chi2_statistic': chi2_stat,
            'p_value': p_value,
            'cramers_v': cramers_v,
            'significant': p_value < alpha
        }

# Example usage
control = [23, 25, 21, 24, 22, 20, 23, 24, 22, 21]
treatment = [28, 30, 26, 29, 31, 27, 30, 28, 29, 30]

result = HypothesisTests.t_test_independent(control, treatment)
print(f"t({len(control)+len(treatment)-2}) = {result['t_statistic']:.3f}, "
      f"p = {result['p_value']:.3f}, d = {result['cohens_d']:.3f}")
```

### 4. Regression Analysis

**Purpose**: Model relationships between variables

**Implementation**:
```python
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
from scipy import stats

class RegressionAnalysis:
    """Multiple regression with diagnostics"""

    def __init__(self, data: pd.DataFrame, outcome: str, predictors: List[str]):
        self.data = data.dropna(subset=[outcome] + predictors)
        self.outcome = outcome
        self.predictors = predictors
        self.model = None
        self.results = {}

    def fit(self):
        """Fit regression model"""
        X = self.data[self.predictors]
        y = self.data[self.outcome]

        self.model = LinearRegression()
        self.model.fit(X, y)

        # Predictions
        y_pred = self.model.predict(X)
        residuals = y - y_pred

        # Model fit statistics
        self.results['r_squared'] = r2_score(y, y_pred)
        self.results['adj_r_squared'] = 1 - (1 - self.results['r_squared']) * \
                                       (len(y) - 1) / (len(y) - len(self.predictors) - 1)
        self.results['rmse'] = np.sqrt(mean_squared_error(y, y_pred))

        # Coefficients with significance tests
        n = len(y)
        k = len(self.predictors)
        mse = np.sum(residuals**2) / (n - k - 1)

        X_with_intercept = np.column_stack([np.ones(n), X])
        var_coef = mse * np.linalg.inv(X_with_intercept.T @ X_with_intercept).diagonal()
        se_coef = np.sqrt(var_coef)

        t_stats = np.concatenate([[self.model.intercept_], self.model.coef_]) / se_coef
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - k - 1))

        self.results['coefficients'] = pd.DataFrame({
            'Variable': ['Intercept'] + self.predictors,
            'B': np.concatenate([[self.model.intercept_], self.model.coef_]),
            'SE': se_coef,
            't': t_stats,
            'p': p_values
        })

        return self

    def standardized_coefficients(self):
        """Calculate standardized (beta) coefficients"""
        X = self.data[self.predictors]
        y = self.data[self.outcome]

        # Standardize variables
        X_std = (X - X.mean()) / X.std()
        y_std = (y - y.mean()) / y.std()

        model_std = LinearRegression()
        model_std.fit(X_std, y_std)

        return pd.DataFrame({
            'Variable': self.predictors,
            'Beta': model_std.coef_
        })

    def vif(self):
        """Calculate variance inflation factors (multicollinearity)"""
        from statsmodels.stats.outliers_influence import variance_inflation_factor

        X = self.data[self.predictors]
        vif_data = pd.DataFrame({
            'Variable': self.predictors,
            'VIF': [variance_inflation_factor(X.values, i)
                   for i in range(len(self.predictors))]
        })
        return vif_data

    def diagnostics(self):
        """Run regression diagnostics"""
        X = self.data[self.predictors]
        y = self.data[self.outcome]
        y_pred = self.model.predict(X)
        residuals = y - y_pred

        diagnostics = {
            'normality': stats.shapiro(residuals)[1],  # p-value
            'durbin_watson': self._durbin_watson(residuals),
            'homoscedasticity': self._breusch_pagan(residuals, y_pred)
        }

        return diagnostics

    @staticmethod
    def _durbin_watson(residuals):
        """Durbin-Watson test for autocorrelation"""
        diff_resid = np.diff(residuals)
        return np.sum(diff_resid**2) / np.sum(residuals**2)

    @staticmethod
    def _breusch_pagan(residuals, fitted):
        """Breusch-Pagan test for heteroscedasticity"""
        # Simplified version
        aux_model = LinearRegression()
        aux_model.fit(fitted.reshape(-1, 1), residuals**2)
        r2 = r2_score(residuals**2, aux_model.predict(fitted.reshape(-1, 1)))
        lm = len(residuals) * r2
        p_value = 1 - stats.chi2.cdf(lm, 1)
        return p_value

# Example usage
data = pd.DataFrame({
    'sales': [100, 150, 120, 180, 200, 160, 140, 190, 170, 155],
    'advertising': [10, 15, 12, 18, 20, 16, 14, 19, 17, 15],
    'price': [50, 45, 48, 42, 40, 44, 46, 41, 43, 45],
    'competition': [5, 3, 4, 2, 1, 3, 4, 2, 3, 3]
})

regression = RegressionAnalysis(
    data=data,
    outcome='sales',
    predictors=['advertising', 'price', 'competition']
).fit()

print(f"R² = {regression.results['r_squared']:.3f}")
print(regression.results['coefficients'])
```

## Quantitative Patterns

### Effective Quantitative Research
```
✓ Clear hypotheses stated a priori
✓ Appropriate sample size (power analysis)
✓ Random sampling or assignment when possible
✓ Valid and reliable measures
✓ Assumptions checked before analysis
✓ Effect sizes reported alongside p-values
✓ Multiple testing corrections when needed
✓ Confidence intervals provided
```

### Ineffective Quantitative Research
```
✗ P-hacking (trying tests until significant)
✗ HARKing (hypothesizing after results known)
✗ Ignoring violated assumptions
✗ Confusing significance with importance
✗ Cherry-picking analyses to report
✗ Insufficient sample size
✗ Measurement without validity evidence
```

## Best Practices

### 1. Study Design
- Conduct power analysis before data collection
- Use random assignment for causal inference
- Control for confounding variables
- Pilot test instruments
- Pre-register analysis plan

### 2. Measurement
- Use validated instruments when available
- Report reliability (Cronbach's alpha, test-retest)
- Assess validity (construct, criterion, content)
- Check for measurement invariance across groups
- Consider multiple methods to measure constructs

### 3. Analysis
- Check assumptions before running tests
- Report descriptive statistics first
- Use appropriate tests for data type and design
- Report effect sizes, not just p-values
- Provide confidence intervals
- Correct for multiple comparisons
- Conduct sensitivity analyses

### 4. Reporting
- Follow APA or journal guidelines
- Report all tested hypotheses
- Provide sufficient detail for replication
- Share data and code when possible
- Discuss practical significance
- Acknowledge limitations

## Related Skills

- **research-design**: Planning quantitative studies
- **data-collection**: Survey and experiment implementation
- **data-analysis**: Advanced statistical techniques
- **research-synthesis**: Meta-analysis of quantitative studies
- **research-writing**: Reporting quantitative results

## Quick Reference

### Sample Size Rules of Thumb
```
Correlation: N ≥ 30 for detection, N ≥ 85 for stable estimates
T-test: N ≥ 50 per group for d=0.5, 80% power
ANOVA: N ≥ 30 per group minimum
Regression: N ≥ 104 + k (k = predictors) for R²
            N ≥ 50 + 8k for individual coefficients
```

### Effect Size Interpretation (Cohen's benchmarks)
```
Cohen's d:      Small = 0.2,  Medium = 0.5,  Large = 0.8
Correlation r:  Small = 0.1,  Medium = 0.3,  Large = 0.5
Eta-squared:    Small = 0.01, Medium = 0.06, Large = 0.14
```

### Assumption Checks
```
Normality:         Shapiro-Wilk test, Q-Q plot
Homogeneity:       Levene's test, residual plots
Independence:      Durbin-Watson statistic
Linearity:         Scatterplots, residual plots
Multicollinearity: VIF < 10, tolerance > 0.1
```
