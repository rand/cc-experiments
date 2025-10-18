---
name: math-probability-statistics
description: Statistical hypothesis testing (t-test, chi-square, ANOVA)
---



# Probability and Statistics

## Metadata
- **Skill ID**: probability-statistics
- **Category**: Mathematics/Statistics
- **Complexity**: Advanced
- **Last Updated**: 2025-10-18

## Overview
Computational statistics and probability using SciPy, NumPy, and statsmodels. Covers distributions, hypothesis testing, confidence intervals, Bayesian inference, and statistical modeling for data analysis and decision making.

## When to Use This Skill
- Statistical hypothesis testing (t-test, chi-square, ANOVA)
- A/B testing and experiment analysis
- Probability distributions and random sampling
- Confidence intervals and parameter estimation
- Bayesian inference and MCMC
- Time series analysis
- Regression and statistical modeling
- Monte Carlo simulation

## When NOT to Use This Skill
- Machine learning model training (use scikit-learn)
- Deep learning (use PyTorch/TensorFlow)
- Causal inference without domain knowledge
- When sample size is too small for statistical validity
- Pure probability theory (use SymPy for symbolic)

## Prerequisites
- Probability basics (distributions, expectation, variance)
- Statistics fundamentals (hypothesis testing, p-values)
- NumPy array operations
- Basic data manipulation (pandas helpful)

## Core Concepts

### 1. Probability Distributions

**Common Continuous Distributions**
```python
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# Normal (Gaussian) distribution
mu, sigma = 0, 1
normal = stats.norm(loc=mu, scale=sigma)

# PDF (probability density function)
x = np.linspace(-4, 4, 1000)
pdf = normal.pdf(x)

# CDF (cumulative distribution function)
cdf = normal.cdf(x)

# Inverse CDF (quantile function)
p = 0.95
quantile = normal.ppf(p)  # 95th percentile
print(f"95th percentile: {quantile:.4f}")  # ~1.645

# Random sampling
samples = normal.rvs(size=10000, random_state=42)
print(f"Sample mean: {samples.mean():.4f}")
print(f"Sample std: {samples.std():.4f}")

# Other continuous distributions
exponential = stats.expon(scale=2.0)  # λ = 1/2
gamma = stats.gamma(a=2.0, scale=2.0)  # shape, scale
beta = stats.beta(a=2.0, b=5.0)
uniform = stats.uniform(loc=0, scale=10)  # [0, 10]
lognormal = stats.lognorm(s=1.0)  # s is shape parameter
```

**Common Discrete Distributions**
```python
# Binomial: n trials, probability p
n, p = 10, 0.3
binomial = stats.binom(n=n, p=p)

# PMF (probability mass function)
k = np.arange(0, n+1)
pmf = binomial.pmf(k)

# Probability of exactly 3 successes
prob_3 = binomial.pmf(3)
print(f"P(X=3) = {prob_3:.4f}")

# Probability of at most 5 successes
prob_le_5 = binomial.cdf(5)
print(f"P(X≤5) = {prob_le_5:.4f}")

# Poisson distribution (events in fixed interval)
lambda_rate = 5.0
poisson = stats.poisson(mu=lambda_rate)

# Geometric (number of trials until first success)
geometric = stats.geom(p=0.3)

# Negative binomial (trials until r successes)
neg_binomial = stats.nbinom(n=5, p=0.3)
```

**Multivariate Distributions**
```python
# Multivariate normal
mean = [0, 0]
cov = [[1, 0.5], [0.5, 2]]  # Covariance matrix
mvn = stats.multivariate_normal(mean=mean, cov=cov)

# Sample
samples = mvn.rvs(size=1000, random_state=42)

# PDF at a point
point = [0.5, 1.0]
density = mvn.pdf(point)

# Marginal distributions
# X ~ N(0, 1), Y ~ N(0, 2)
# Conditional: X|Y=y ~ N(ρσ_x/σ_y * y, σ_x^2(1-ρ^2))
```

### 2. Hypothesis Testing

**t-tests**
```python
from scipy.stats import ttest_1samp, ttest_ind, ttest_rel

# One-sample t-test: test if mean equals hypothesized value
data = np.random.randn(100) + 0.5
t_stat, p_value = ttest_1samp(data, 0)  # H0: μ = 0

print(f"t-statistic: {t_stat:.4f}")
print(f"p-value: {p_value:.4f}")

if p_value < 0.05:
    print("Reject H0: mean is significantly different from 0")
else:
    print("Fail to reject H0")

# Two-sample t-test (independent samples)
group1 = np.random.randn(50) + 0.5
group2 = np.random.randn(60)

# Equal variance assumed
t_stat, p_value = ttest_ind(group1, group2)

# Unequal variance (Welch's t-test)
t_stat, p_value = ttest_ind(group1, group2, equal_var=False)

# Paired t-test (dependent samples)
before = np.random.randn(30) + 5
after = before + np.random.randn(30) * 0.5 + 0.3
t_stat, p_value = ttest_rel(before, after)

print(f"Paired t-test p-value: {p_value:.4f}")
```

**Chi-Square Tests**
```python
from scipy.stats import chi2_contingency, chisquare

# Chi-square goodness-of-fit test
# H0: observed frequencies match expected distribution
observed = np.array([50, 45, 55])
expected = np.array([50, 50, 50])

chi2_stat, p_value = chisquare(observed, expected)
print(f"Chi-square goodness-of-fit p-value: {p_value:.4f}")

# Chi-square test of independence (contingency table)
# Example: relationship between gender and preference
observed = np.array([
    [30, 20, 10],  # Male: A, B, C
    [15, 25, 35]   # Female: A, B, C
])

chi2, p_value, dof, expected = chi2_contingency(observed)
print(f"Chi-square independence test:")
print(f"χ² = {chi2:.4f}, p = {p_value:.4f}, dof = {dof}")

if p_value < 0.05:
    print("Reject H0: variables are not independent")
```

**ANOVA (Analysis of Variance)**
```python
from scipy.stats import f_oneway, kruskal

# One-way ANOVA: compare means of 3+ groups
group1 = np.random.randn(30) + 0
group2 = np.random.randn(30) + 0.5
group3 = np.random.randn(30) + 1.0

f_stat, p_value = f_oneway(group1, group2, group3)
print(f"ANOVA F-statistic: {f_stat:.4f}, p-value: {p_value:.4f}")

# Kruskal-Wallis test (non-parametric alternative)
h_stat, p_value = kruskal(group1, group2, group3)
print(f"Kruskal-Wallis H: {h_stat:.4f}, p-value: {p_value:.4f}")
```

**Non-Parametric Tests**
```python
from scipy.stats import mannwhitneyu, wilcoxon, kstest

# Mann-Whitney U test (independent samples, non-parametric)
u_stat, p_value = mannwhitneyu(group1, group2, alternative='two-sided')

# Wilcoxon signed-rank test (paired samples, non-parametric)
w_stat, p_value = wilcoxon(before, after)

# Kolmogorov-Smirnov test (goodness-of-fit)
# Test if data comes from standard normal
data = np.random.randn(100)
ks_stat, p_value = kstest(data, 'norm')
print(f"KS test p-value: {p_value:.4f}")
```

### 3. Confidence Intervals

**Mean Confidence Intervals**
```python
from scipy import stats

def confidence_interval_mean(data, confidence=0.95):
    """
    Compute confidence interval for mean.
    """
    n = len(data)
    mean = np.mean(data)
    sem = stats.sem(data)  # Standard error of mean

    # t-distribution (for unknown population variance)
    ci = stats.t.interval(confidence, df=n-1, loc=mean, scale=sem)

    return ci

data = np.random.randn(50) + 5
ci = confidence_interval_mean(data, confidence=0.95)
print(f"95% CI for mean: [{ci[0]:.4f}, {ci[1]:.4f}]")

# Proportion confidence interval (Wilson score interval)
def confidence_interval_proportion(successes, n, confidence=0.95):
    """Confidence interval for proportion."""
    p_hat = successes / n
    z = stats.norm.ppf((1 + confidence) / 2)

    # Wilson score interval (better for small samples)
    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2*n)) / denominator
    margin = z * np.sqrt((p_hat * (1 - p_hat) / n + z**2 / (4*n**2))) / denominator

    return (center - margin, center + margin)

ci_prop = confidence_interval_proportion(60, 100, confidence=0.95)
print(f"95% CI for proportion: [{ci_prop[0]:.4f}, {ci_prop[1]:.4f}]")
```

**Bootstrap Confidence Intervals**
```python
from scipy.stats import bootstrap

def median_statistic(data, axis):
    """Statistic function for bootstrap"""
    return np.median(data, axis=axis)

data = np.random.lognormal(size=100)

# Bootstrap resampling
result = bootstrap(
    (data,),
    median_statistic,
    n_resamples=10000,
    confidence_level=0.95,
    random_state=42
)

print(f"95% CI for median: [{result.confidence_interval.low:.4f}, "
      f"{result.confidence_interval.high:.4f}]")

# Manual bootstrap
def bootstrap_ci(data, statistic, n_bootstrap=10000, confidence=0.95):
    """Manual bootstrap confidence interval"""
    bootstrap_stats = []
    n = len(data)

    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=n, replace=True)
        bootstrap_stats.append(statistic(sample))

    bootstrap_stats = np.array(bootstrap_stats)
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

    return lower, upper

ci_boot = bootstrap_ci(data, np.median, n_bootstrap=10000)
```

### 4. A/B Testing

**Two-Proportion Z-Test**
```python
from statsmodels.stats.proportion import proportions_ztest

def ab_test(conversions_a, visitors_a, conversions_b, visitors_b, alpha=0.05):
    """
    A/B test for conversion rates.
    """
    # Conversion rates
    rate_a = conversions_a / visitors_a
    rate_b = conversions_b / visitors_b

    # Z-test
    count = np.array([conversions_a, conversions_b])
    nobs = np.array([visitors_a, visitors_b])

    z_stat, p_value = proportions_ztest(count, nobs)

    # Relative improvement
    relative_improvement = (rate_b - rate_a) / rate_a * 100

    # Effect size (Cohen's h)
    h = 2 * (np.arcsin(np.sqrt(rate_b)) - np.arcsin(np.sqrt(rate_a)))

    print(f"Control rate: {rate_a:.4f}")
    print(f"Treatment rate: {rate_b:.4f}")
    print(f"Relative improvement: {relative_improvement:.2f}%")
    print(f"p-value: {p_value:.4f}")
    print(f"Effect size (h): {h:.4f}")

    if p_value < alpha:
        print("Result is statistically significant")
    else:
        print("Result is not statistically significant")

    return {
        'rate_a': rate_a,
        'rate_b': rate_b,
        'p_value': p_value,
        'relative_improvement': relative_improvement,
        'effect_size': h
    }

# Example
result = ab_test(conversions_a=120, visitors_a=1000,
                 conversions_b=150, visitors_b=1000)

# Sample size calculation for A/B test
from statsmodels.stats.power import zt_ind_solve_power

def calculate_sample_size(baseline_rate, mde, alpha=0.05, power=0.8):
    """
    Calculate required sample size per group.

    Args:
        baseline_rate: Current conversion rate
        mde: Minimum detectable effect (absolute, e.g., 0.01 for 1pp increase)
        alpha: Significance level
        power: Statistical power
    """
    effect_size = 2 * (np.arcsin(np.sqrt(baseline_rate + mde)) -
                       np.arcsin(np.sqrt(baseline_rate)))

    n = zt_ind_solve_power(effect_size=effect_size, alpha=alpha,
                           power=power, alternative='two-sided')

    return int(np.ceil(n))

n_required = calculate_sample_size(baseline_rate=0.10, mde=0.02)
print(f"Required sample size per group: {n_required}")
```

### 5. Bayesian Inference

**Bayesian Parameter Estimation**
```python
# Example: Estimate success probability from binomial data
# Prior: Beta(alpha, beta)
# Likelihood: Binomial(n, p)
# Posterior: Beta(alpha + successes, beta + failures)

def bayesian_binomial(successes, trials, prior_alpha=1, prior_beta=1):
    """
    Bayesian inference for binomial proportion.
    """
    failures = trials - successes

    # Posterior parameters
    post_alpha = prior_alpha + successes
    post_beta = prior_beta + failures

    # Posterior distribution
    posterior = stats.beta(post_alpha, post_beta)

    # Point estimates
    mean = posterior.mean()
    mode = (post_alpha - 1) / (post_alpha + post_beta - 2) if post_alpha > 1 else 0

    # Credible interval (Bayesian CI)
    credible_interval = posterior.interval(0.95)

    print(f"Posterior mean: {mean:.4f}")
    print(f"Posterior mode: {mode:.4f}")
    print(f"95% credible interval: [{credible_interval[0]:.4f}, {credible_interval[1]:.4f}]")

    return posterior

# Weak prior (uniform)
posterior = bayesian_binomial(successes=60, trials=100, prior_alpha=1, prior_beta=1)

# Informative prior
posterior_informed = bayesian_binomial(successes=60, trials=100,
                                       prior_alpha=30, prior_beta=70)
```

**Bayesian A/B Testing**
```python
def bayesian_ab_test(conversions_a, visitors_a, conversions_b, visitors_b,
                     prior_alpha=1, prior_beta=1):
    """
    Bayesian A/B test: probability that B is better than A.
    """
    # Posterior distributions
    post_a = stats.beta(prior_alpha + conversions_a,
                       prior_beta + visitors_a - conversions_a)
    post_b = stats.beta(prior_alpha + conversions_b,
                       prior_beta + visitors_b - conversions_b)

    # Monte Carlo: sample from posteriors and compare
    n_samples = 100000
    samples_a = post_a.rvs(n_samples, random_state=42)
    samples_b = post_b.rvs(n_samples, random_state=42)

    prob_b_better = (samples_b > samples_a).mean()

    # Expected loss (for decision making)
    expected_loss_a = np.maximum(samples_b - samples_a, 0).mean()
    expected_loss_b = np.maximum(samples_a - samples_b, 0).mean()

    print(f"Probability B > A: {prob_b_better:.4f}")
    print(f"Expected loss if choosing A: {expected_loss_a:.6f}")
    print(f"Expected loss if choosing B: {expected_loss_b:.6f}")

    return prob_b_better, expected_loss_a, expected_loss_b

prob, loss_a, loss_b = bayesian_ab_test(120, 1000, 150, 1000)
```

**MCMC with PyMC**
```python
# Example: Bayesian linear regression
# Requires: pip install pymc arviz

try:
    import pymc as pm
    import arviz as az

    # Generate synthetic data
    np.random.seed(42)
    n = 100
    X = np.random.randn(n)
    true_slope = 2.5
    true_intercept = 1.0
    y = true_intercept + true_slope * X + np.random.randn(n) * 0.5

    with pm.Model() as model:
        # Priors
        intercept = pm.Normal('intercept', mu=0, sigma=10)
        slope = pm.Normal('slope', mu=0, sigma=10)
        sigma = pm.HalfNormal('sigma', sigma=1)

        # Likelihood
        mu = intercept + slope * X
        likelihood = pm.Normal('y', mu=mu, sigma=sigma, observed=y)

        # Inference
        trace = pm.sample(2000, tune=1000, return_inferencedata=True, random_seed=42)

    # Summary
    print(az.summary(trace, var_names=['intercept', 'slope', 'sigma']))

    # Posterior predictive check
    with model:
        ppc = pm.sample_posterior_predictive(trace, random_seed=42)

except ImportError:
    print("PyMC not installed. Install with: pip install pymc arviz")
```

### 6. Statistical Modeling

**Linear Regression**
```python
from scipy.stats import linregress
import statsmodels.api as sm

# Simple linear regression
x = np.random.randn(100)
y = 2 * x + 1 + np.random.randn(100) * 0.5

# SciPy
slope, intercept, r_value, p_value, std_err = linregress(x, y)
print(f"Slope: {slope:.4f} ± {std_err:.4f}")
print(f"R²: {r_value**2:.4f}")
print(f"p-value: {p_value:.4e}")

# Statsmodels (more detailed)
X_with_const = sm.add_constant(x)
model = sm.OLS(y, X_with_const).fit()
print(model.summary())

# Multiple regression
X_multi = np.random.randn(100, 3)
y_multi = 2*X_multi[:, 0] + 3*X_multi[:, 1] - X_multi[:, 2] + np.random.randn(100)

X_multi_const = sm.add_constant(X_multi)
model_multi = sm.OLS(y_multi, X_multi_const).fit()
print(model_multi.summary())
```

**Logistic Regression**
```python
# Binary outcome
X = np.random.randn(200, 2)
z = 1 + 2*X[:, 0] - X[:, 1]
prob = 1 / (1 + np.exp(-z))
y_binary = (np.random.rand(200) < prob).astype(int)

X_const = sm.add_constant(X)
logit_model = sm.Logit(y_binary, X_const).fit()
print(logit_model.summary())

# Predictions
predictions = logit_model.predict(X_const)
```

## Patterns and Best Practices

### Pattern 1: Test Selection Guide
```python
def select_statistical_test(data_type, n_groups, paired, normal):
    """Guide for selecting appropriate test"""
    if data_type == 'continuous':
        if n_groups == 1:
            return 'one-sample t-test' if normal else 'Wilcoxon signed-rank'
        elif n_groups == 2:
            if paired:
                return 'paired t-test' if normal else 'Wilcoxon signed-rank'
            else:
                return 't-test' if normal else 'Mann-Whitney U'
        else:  # n_groups > 2
            return 'ANOVA' if normal else 'Kruskal-Wallis'
    elif data_type == 'categorical':
        if n_groups == 1:
            return 'Chi-square goodness-of-fit'
        else:
            return 'Chi-square independence'
    elif data_type == 'proportion':
        return 'Z-test for proportions'
```

### Pattern 2: Multiple Testing Correction
```python
from statsmodels.stats.multitest import multipletests

# Multiple comparisons: correct for family-wise error rate
p_values = np.array([0.01, 0.04, 0.03, 0.08, 0.005])

# Bonferroni correction
reject_bonf, pvals_corr_bonf, _, _ = multipletests(p_values, method='bonferroni')

# Benjamini-Hochberg (FDR control)
reject_bh, pvals_corr_bh, _, _ = multipletests(p_values, method='fdr_bh')

print(f"Original p-values: {p_values}")
print(f"Bonferroni corrected: {pvals_corr_bonf}")
print(f"FDR corrected: {pvals_corr_bh}")
```

## Anti-Patterns

### Anti-Pattern 1: P-Value Misuse
```python
# WRONG: p=0.06 means "no effect"
# RIGHT: p=0.06 means insufficient evidence against H0 at α=0.05

# WRONG: p=0.001 means "large effect"
# RIGHT: Statistical significance ≠ practical significance
# Always report effect size!
```

### Anti-Pattern 2: Ignoring Assumptions
```python
# WRONG: Using t-test without checking normality
ttest_ind(group1, group2)

# RIGHT: Check assumptions first
from scipy.stats import shapiro
stat, p = shapiro(group1)
if p < 0.05:
    print("Data not normal, use Mann-Whitney U instead")
    mannwhitneyu(group1, group2)
```

### Anti-Pattern 3: Sample Size Too Small
```python
# WRONG: Testing with n=5 per group
small_group1 = np.random.randn(5)
small_group2 = np.random.randn(5) + 0.5
ttest_ind(small_group1, small_group2)  # Low power!

# RIGHT: Calculate required sample size first
# Use power analysis before collecting data
```

## Related Skills
- `linear-algebra-computation.md` - Matrix operations for statistics
- `numerical-methods.md` - Numerical integration, root finding
- `optimization-algorithms.md` - Maximum likelihood estimation

## Learning Resources
- SciPy Stats: https://docs.scipy.org/doc/scipy/reference/stats.html
- Statsmodels: https://www.statsmodels.org/
- Think Stats (Allen Downey)
- Statistical Rethinking (Richard McElreath)
