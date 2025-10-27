---
name: research-research-design
description: Master research study design including hypothesis formation, validity, sampling strategies, and experimental control
---

# Research Design Skill

## When to Use This Skill

Use this skill when you need to:
- Plan a research study from scratch
- Choose appropriate research methodology
- Formulate testable hypotheses
- Design sampling strategies
- Ensure validity and reliability
- Control for confounding variables
- Balance internal and external validity
- Navigate ethical considerations

## Core Design Elements

### 1. Research Questions and Hypotheses

**FINER Criteria for Research Questions**:
```
F - Feasible: Can you actually do this?
I - Interesting: Does it matter?
N - Novel: Is it new?
E - Ethical: Is it responsible?
R - Relevant: Will it impact the field?
```

**Question to Hypothesis Framework**:
```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class HypothesisType(Enum):
    DIRECTIONAL = "directional"
    NON_DIRECTIONAL = "non-directional"
    NULL = "null"

@dataclass
class ResearchQuestion:
    """Structure a research question"""
    question: str
    population: str
    variables: List[str]
    relationship_type: str  # 'difference', 'relationship', 'prediction'

    def to_hypothesis(self, hypothesis_type: HypothesisType,
                     expected_direction: Optional[str] = None):
        """Convert research question to testable hypothesis"""

        if hypothesis_type == HypothesisType.NULL:
            return f"There is no {self.relationship_type} between " \
                   f"{' and '.join(self.variables)} in {self.population}."

        elif hypothesis_type == HypothesisType.DIRECTIONAL:
            if not expected_direction:
                raise ValueError("Directional hypothesis requires expected_direction")
            return f"There is a {expected_direction} {self.relationship_type} " \
                   f"between {' and '.join(self.variables)} in {self.population}."

        else:  # NON_DIRECTIONAL
            return f"There is a {self.relationship_type} between " \
                   f"{' and '.join(self.variables)} in {self.population}."

# Example
rq = ResearchQuestion(
    question="Does exercise frequency affect anxiety levels in college students?",
    population="college students",
    variables=["exercise frequency", "anxiety levels"],
    relationship_type="relationship"
)

print("Null:", rq.to_hypothesis(HypothesisType.NULL))
print("Directional:", rq.to_hypothesis(HypothesisType.DIRECTIONAL,
                                       "negative"))
print("Non-directional:", rq.to_hypothesis(HypothesisType.NON_DIRECTIONAL))
```

### 2. Validity Considerations

**Validity Framework**:
```python
from typing import List, Dict
from enum import Enum

class ValidityThreat(Enum):
    # Internal validity
    HISTORY = "history"
    MATURATION = "maturation"
    TESTING = "testing"
    INSTRUMENTATION = "instrumentation"
    REGRESSION = "regression_to_mean"
    SELECTION = "selection_bias"
    ATTRITION = "attrition"

    # External validity
    INTERACTION_SELECTION = "selection_treatment_interaction"
    SETTING = "setting_effects"
    HISTORY_TREATMENT = "history_treatment_interaction"

    # Construct validity
    HYPOTHESIS_GUESSING = "hypothesis_guessing"
    EVALUATION_APPREHENSION = "evaluation_apprehension"
    EXPERIMENTER_EFFECTS = "experimenter_effects"
    MONO_OPERATION = "mono_operation_bias"
    MONO_METHOD = "mono_method_bias"

class ValidityAnalysis:
    """Analyze validity threats and controls"""

    def __init__(self, study_design: str):
        self.design = study_design
        self.threats = []
        self.controls = {}

    def add_threat(self, threat: ValidityThreat, description: str,
                  severity: str):
        """Identify potential validity threat"""
        self.threats.append({
            'threat': threat.value,
            'description': description,
            'severity': severity  # 'low', 'medium', 'high'
        })

    def add_control(self, threat: ValidityThreat, control: str):
        """Document how threat is controlled"""
        self.controls[threat.value] = control

    def generate_validity_table(self):
        """Create validity threat and control matrix"""
        import pandas as pd

        data = []
        for threat_info in self.threats:
            threat_name = threat_info['threat']
            data.append({
                'Threat': threat_name,
                'Description': threat_info['description'],
                'Severity': threat_info['severity'],
                'Control': self.controls.get(threat_name, 'None specified')
            })

        return pd.DataFrame(data)

# Example
validity = ValidityAnalysis("Pre-post intervention with control group")

validity.add_threat(
    ValidityThreat.HISTORY,
    "External events during study period may affect outcomes",
    severity="medium"
)
validity.add_control(
    ValidityThreat.HISTORY,
    "Control group experiencing same time period"
)

validity.add_threat(
    ValidityThreat.ATTRITION,
    "Differential dropout between treatment and control",
    severity="high"
)
validity.add_control(
    ValidityThreat.ATTRITION,
    "Intent-to-treat analysis; track and report attrition rates; "
    "compare completers vs dropouts on baseline characteristics"
)

print(validity.generate_validity_table())
```

### 3. Sampling Strategies

**Sampling Design Framework**:
```python
from enum import Enum
import numpy as np
from typing import Optional

class SamplingMethod(Enum):
    # Probability sampling
    SIMPLE_RANDOM = "simple_random"
    SYSTEMATIC = "systematic"
    STRATIFIED = "stratified"
    CLUSTER = "cluster"
    MULTISTAGE = "multistage"

    # Non-probability sampling
    CONVENIENCE = "convenience"
    PURPOSIVE = "purposive"
    QUOTA = "quota"
    SNOWBALL = "snowball"

class SamplingDesign:
    """Design and document sampling strategy"""

    def __init__(self, method: SamplingMethod, population_size: int,
                 target_sample_size: int):
        self.method = method
        self.N = population_size
        self.n = target_sample_size
        self.sampling_frame = None
        self.strata = None

    def simple_random_sample(self, population_ids: list, seed: int = 42):
        """Draw simple random sample"""
        np.random.seed(seed)
        return np.random.choice(population_ids, size=self.n, replace=False)

    def stratified_sample(self, strata_dict: dict, proportional: bool = True):
        """Draw stratified sample

        Args:
            strata_dict: {stratum_name: [ids in stratum]}
            proportional: If True, proportional allocation; else equal
        """
        samples = []

        if proportional:
            # Proportional to stratum size
            for stratum_name, stratum_ids in strata_dict.items():
                stratum_n = int(self.n * len(stratum_ids) / self.N)
                stratum_sample = np.random.choice(stratum_ids,
                                                 size=stratum_n,
                                                 replace=False)
                samples.extend(stratum_sample)
        else:
            # Equal allocation
            n_per_stratum = self.n // len(strata_dict)
            for stratum_ids in strata_dict.values():
                stratum_sample = np.random.choice(stratum_ids,
                                                 size=n_per_stratum,
                                                 replace=False)
                samples.extend(stratum_sample)

        return samples

    def calculate_sampling_error(self, std_dev: float,
                                 finite_correction: bool = True):
        """Calculate standard error of the mean"""
        if finite_correction and self.N > 0:
            fpc = np.sqrt((self.N - self.n) / (self.N - 1))
            se = (std_dev / np.sqrt(self.n)) * fpc
        else:
            se = std_dev / np.sqrt(self.n)

        return se

    def required_sample_size(self, std_dev: float, margin_error: float,
                           confidence_level: float = 0.95,
                           finite_correction: bool = True):
        """Calculate required sample size for desired precision"""
        from scipy import stats

        # Z-score for confidence level
        z = stats.norm.ppf((1 + confidence_level) / 2)

        # Required n without finite population correction
        n_0 = (z * std_dev / margin_error) ** 2

        if finite_correction and self.N > 0:
            # Adjust for finite population
            n = n_0 / (1 + (n_0 - 1) / self.N)
        else:
            n = n_0

        return int(np.ceil(n))

    def document_sampling(self):
        """Generate sampling documentation"""
        doc = f"""
# Sampling Design Documentation

## Method
{self.method.value}

## Population and Sample
- Population size (N): {self.N if self.N else 'Unknown'}
- Target sample size (n): {self.n}
- Sampling fraction: {(self.n/self.N)*100:.1f}% (if N known)

## Sampling Procedure
[Describe step-by-step how sampling was conducted]

## Rationale
[Justify why this method is appropriate for research question]

## Limitations
[Discuss potential sampling biases and limitations]
"""
        return doc

# Example
design = SamplingDesign(
    method=SamplingMethod.STRATIFIED,
    population_size=10000,
    target_sample_size=400
)

# Calculate required n for desired precision
required_n = design.required_sample_size(
    std_dev=15,
    margin_error=2,
    confidence_level=0.95
)
print(f"Required sample size: {required_n}")

# Draw stratified sample
strata = {
    'stratum_A': list(range(0, 5000)),
    'stratum_B': list(range(5000, 10000))
}
sample = design.stratified_sample(strata, proportional=True)
print(f"Sample drawn: {len(sample)} participants")
```

### 4. Experimental Control

**Control Strategies**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class ControlMethod(Enum):
    RANDOMIZATION = "randomization"
    MATCHING = "matching"
    BLOCKING = "blocking"
    STATISTICAL_CONTROL = "statistical_control"
    STANDARDIZATION = "standardization"

@dataclass
class ConfoundingVariable:
    """Define potential confounding variable"""
    name: str
    relationship_to_iv: str
    relationship_to_dv: str
    control_method: ControlMethod
    control_procedure: str

class ExperimentalControl:
    """Design experimental controls"""

    def __init__(self):
        self.confounds = {}
        self.design_features = []

    def identify_confound(self, confound: ConfoundingVariable):
        """Add confounding variable with control plan"""
        self.confounds[confound.name] = confound

    def add_design_feature(self, feature: str, purpose: str):
        """Document design feature for control"""
        self.design_features.append({
            'feature': feature,
            'purpose': purpose
        })

    def random_assignment(self, participants: list,
                         n_groups: int, seed: int = 42):
        """Randomly assign participants to groups"""
        np.random.seed(seed)
        shuffled = np.random.permutation(participants)
        groups = np.array_split(shuffled, n_groups)
        return [list(g) for g in groups]

    def matched_assignment(self, participants_df,
                          matching_vars: List[str],
                          n_groups: int):
        """Create matched groups based on variables"""
        import pandas as pd
        from sklearn.preprocessing import StandardScaler

        # Standardize matching variables
        scaler = StandardScaler()
        X = scaler.fit_transform(participants_df[matching_vars])

        # Cluster into n_groups using K-means
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_groups, random_state=42)
        participants_df['match_group'] = kmeans.fit_predict(X)

        # Assign one from each cluster to each condition
        groups = [[] for _ in range(n_groups)]
        for cluster in range(n_groups):
            cluster_members = participants_df[
                participants_df['match_group'] == cluster
            ].index.tolist()

            np.random.shuffle(cluster_members)
            for i, member in enumerate(cluster_members):
                groups[i % n_groups].append(member)

        return groups

    def generate_control_plan(self):
        """Create documented control plan"""
        plan = "# Experimental Control Plan\n\n"
        plan += "## Identified Confounding Variables\n\n"

        for name, confound in self.confounds.items():
            plan += f"### {name}\n"
            plan += f"- **Relationship to IV**: {confound.relationship_to_iv}\n"
            plan += f"- **Relationship to DV**: {confound.relationship_to_dv}\n"
            plan += f"- **Control Method**: {confound.control_method.value}\n"
            plan += f"- **Procedure**: {confound.control_procedure}\n\n"

        plan += "## Design Features for Control\n\n"
        for feature in self.design_features:
            plan += f"- **{feature['feature']}**: {feature['purpose']}\n"

        return plan

# Example
control = ExperimentalControl()

# Identify confounds
control.identify_confound(ConfoundingVariable(
    name='Prior Experience',
    relationship_to_iv='More experienced participants may seek treatment',
    relationship_to_dv='Experience directly affects performance',
    control_method=ControlMethod.RANDOMIZATION,
    control_procedure='Random assignment to conditions distributes experience equally'
))

control.identify_confound(ConfoundingVariable(
    name='Time of Day',
    relationship_to_iv='Treatment sessions at different times',
    relationship_to_dv='Cognitive performance varies by time',
    control_method=ControlMethod.STANDARDIZATION,
    control_procedure='All sessions conducted between 9-11am'
))

# Add design features
control.add_design_feature(
    'Double-blind procedure',
    'Prevent experimenter bias and demand characteristics'
)
control.add_design_feature(
    'Standardized protocols',
    'Ensure consistent treatment delivery'
)

print(control.generate_control_plan())
```

## Design Patterns

### Strong Research Design
```
✓ Clear, testable hypotheses
✓ Appropriate methodology for question
✓ Threats to validity identified and controlled
✓ Adequate sample size (power analysis)
✓ Random sampling or assignment when possible
✓ Multiple measures/methods (triangulation)
✓ Pilot testing conducted
✓ Pre-registration of hypotheses and methods
```

### Weak Research Design
```
✗ Vague or non-testable hypotheses
✗ Method-question mismatch
✗ Uncontrolled confounds
✗ Convenience sample assumed representative
✗ Underpowered study
✗ Single method/measure
✗ Post-hoc hypothesizing (HARKing)
✗ P-hacking through multiple analyses
```

## Research Design Types

### 1. Experimental Designs

**True Experiment**:
```
- Random assignment to conditions
- Manipulation of IV
- Control group
- Maximum internal validity
```

**Quasi-Experiment**:
```
- No random assignment
- Manipulation of IV or natural variation
- Comparison group
- Moderate internal validity
```

**Single-Case Design**:
```
- Individual as own control
- Repeated measures over time
- Experimental control through replication
- Good for clinical intervention research
```

### 2. Non-Experimental Designs

**Correlational**:
```
- Examine relationships between variables
- No manipulation
- Cannot infer causation
- Useful for prediction
```

**Survey**:
```
- Describe population characteristics
- No manipulation
- Generalization to population
- Good for attitudes, beliefs, behaviors
```

**Observational**:
```
- Observe naturally occurring behavior
- No manipulation
- High ecological validity
- Good for exploratory research
```

## Best Practices

### 1. Planning Phase
- Start with clear research question
- Review literature thoroughly
- Choose design matching question and resources
- Conduct power analysis
- Create detailed protocol
- Pre-register study
- Get IRB approval

### 2. Design Phase
- Map causal model (DAG)
- Identify all confounds
- Choose appropriate controls
- Balance internal and external validity
- Plan for attrition
- Build in manipulation checks
- Design pilot study

### 3. Ethical Considerations
- Assess risk-benefit ratio
- Ensure informed consent
- Protect participant privacy
- Plan for adverse events
- Consider vulnerable populations
- Ensure equitable participant selection
- Plan data security

### 4. Documentation
- Write detailed protocol
- Create decision tree for procedures
- Document all changes from protocol
- Maintain audit trail
- Archive all materials
- Enable reproducibility

## Common Design Mistakes

1. **Confusing Correlation and Causation**
   - Problem: Inferring causation from correlational design
   - Solution: Use causal language only with experimental designs

2. **Insufficient Power**
   - Problem: Sample too small to detect real effects
   - Solution: Conduct a priori power analysis

3. **Unmeasured Confounds**
   - Problem: Alternative explanations not ruled out
   - Solution: Create comprehensive causal diagram

4. **Convenience Sampling Generalization**
   - Problem: Assuming convenience sample represents population
   - Solution: Acknowledge limitations; use probability sampling

5. **Demand Characteristics**
   - Problem: Participants guess hypothesis and act accordingly
   - Solution: Use blind procedures; cover story; implicit measures

6. **Experimenter Bias**
   - Problem: Researcher expectations influence results
   - Solution: Double-blind design; automated procedures

## Related Skills

- **quantitative-methods**: Statistical analysis for designed studies
- **qualitative-methods**: Alternative research approaches
- **data-collection**: Implementing research protocols
- **research-synthesis**: Learning from existing research
- **research-writing**: Documenting research design

## Quick Reference

### Design Selection Matrix
```
Question Type        → Design
-------------------------------------
Causation           → True experiment
Association         → Correlational
Prevalence          → Cross-sectional survey
Change over time    → Longitudinal
Lived experience    → Phenomenology
Process/meaning     → Grounded theory
Bounded system      → Case study
```

### Internal Validity Hierarchy
```
Highest:  Randomized controlled trial
          Quasi-experiment with matching
          Pre-post with control
          Post-only with control
Lowest:   One-group pre-post
          Cross-sectional correlation
```

### Sample Size Quick Rules
```
Simple comparison:     50-100 per group
Multiple regression:   104 + k (k=predictors)
Factor analysis:       300+ or 10× variables
Structural equation:   200+ minimum
Qualitative:          Until saturation (varies)
```
