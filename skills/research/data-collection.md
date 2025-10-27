---
name: research-data-collection
description: Master data collection methods including survey design, interview protocols, observation techniques, and measurement instruments
---

# Data Collection Skill

## When to Use This Skill

Use this skill when you need to:
- Design surveys and questionnaires
- Create interview protocols
- Plan observation studies
- Develop measurement instruments
- Ensure data quality
- Train data collectors
- Manage fieldwork
- Handle missing data and errors

## Core Collection Methods

### 1. Survey Design

**Survey Construction Framework**:
```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum

class QuestionType(Enum):
    LIKERT = "likert"
    MULTIPLE_CHOICE = "multiple_choice"
    OPEN_ENDED = "open_ended"
    RANKING = "ranking"
    SEMANTIC_DIFFERENTIAL = "semantic_differential"
    MATRIX = "matrix"

@dataclass
class SurveyQuestion:
    """Define a survey question"""
    id: str
    text: str
    type: QuestionType
    required: bool
    options: Optional[List[str]] = None
    scale_range: Optional[tuple] = None
    scale_labels: Optional[Dict[int, str]] = None
    validation: Optional[str] = None
    skip_logic: Optional[Dict] = None

class SurveyInstrument:
    """Build and validate survey instrument"""

    def __init__(self, title: str, instructions: str):
        self.title = title
        self.instructions = instructions
        self.sections = {}
        self.current_section = None

    def add_section(self, section_name: str, description: str):
        """Add survey section"""
        self.sections[section_name] = {
            'description': description,
            'questions': []
        }
        self.current_section = section_name

    def add_question(self, question: SurveyQuestion):
        """Add question to current section"""
        if self.current_section is None:
            raise ValueError("Must create section before adding questions")
        self.sections[self.current_section]['questions'].append(question)

    def validate_survey(self):
        """Check survey for common issues"""
        issues = []

        for section_name, section in self.sections.items():
            questions = section['questions']

            # Check question count
            if len(questions) > 20:
                issues.append(f"Section '{section_name}' has {len(questions)} "
                            "questions (consider splitting)")

            for q in questions:
                # Check question text length
                if len(q.text) > 150:
                    issues.append(f"Question {q.id} is very long "
                                f"({len(q.text)} chars)")

                # Check Likert scale has odd number of points
                if q.type == QuestionType.LIKERT and q.scale_range:
                    n_points = q.scale_range[1] - q.scale_range[0] + 1
                    if n_points % 2 == 0:
                        issues.append(f"Question {q.id}: Even-numbered Likert "
                                    "scale (consider odd for neutral midpoint)")

                # Check multiple choice has reasonable number of options
                if q.type == QuestionType.MULTIPLE_CHOICE and q.options:
                    if len(q.options) > 7:
                        issues.append(f"Question {q.id}: Too many options "
                                    f"({len(q.options)})")

        return issues

    def generate_survey_markdown(self):
        """Generate human-readable survey"""
        output = f"# {self.title}\n\n"
        output += f"{self.instructions}\n\n"

        for section_name, section in self.sections.items():
            output += f"## {section_name}\n"
            output += f"*{section['description']}*\n\n"

            for q in section['questions']:
                output += f"**{q.id}.** {q.text}"
                if q.required:
                    output += " *"
                output += "\n\n"

                if q.type == QuestionType.LIKERT:
                    output += f"Scale: {q.scale_range[0]} to {q.scale_range[1]}\n"
                    if q.scale_labels:
                        for val, label in q.scale_labels.items():
                            output += f"- {val}: {label}\n"
                elif q.type == QuestionType.MULTIPLE_CHOICE:
                    for i, opt in enumerate(q.options, 1):
                        output += f"- [ ] {opt}\n"
                elif q.type == QuestionType.OPEN_ENDED:
                    output += "_" * 50 + "\n"

                output += "\n"

        output += "\n*Required questions marked with *\n"
        return output

# Example survey
survey = SurveyInstrument(
    title="Remote Work Experience Survey",
    instructions="This survey takes approximately 10 minutes. "
                "Your responses are confidential."
)

survey.add_section("Background", "Tell us about your work situation")

survey.add_question(SurveyQuestion(
    id="Q1",
    text="How long have you been working remotely?",
    type=QuestionType.MULTIPLE_CHOICE,
    required=True,
    options=[
        "Less than 6 months",
        "6-12 months",
        "1-2 years",
        "More than 2 years"
    ]
))

survey.add_section("Work-Life Balance", "Rate your agreement with these statements")

survey.add_question(SurveyQuestion(
    id="Q2",
    text="I can easily separate work time from personal time",
    type=QuestionType.LIKERT,
    required=True,
    scale_range=(1, 5),
    scale_labels={
        1: "Strongly Disagree",
        3: "Neutral",
        5: "Strongly Agree"
    }
))

# Validate and generate
issues = survey.validate_survey()
if issues:
    print("Survey Issues:")
    for issue in issues:
        print(f"- {issue}")

print(survey.generate_survey_markdown())
```

### 2. Interview Protocols

**Structured Interview Framework**:
```python
from dataclasses import dataclass
from typing import List, Dict
import json

@dataclass
class InterviewQuestion:
    """Define interview question with probes"""
    question: str
    purpose: str
    probes: List[str]
    max_time_minutes: int
    notes_to_interviewer: str = ""

class InterviewProtocol:
    """Create comprehensive interview protocol"""

    def __init__(self, research_aim: str, duration_minutes: int):
        self.aim = research_aim
        self.duration = duration_minutes
        self.opening = None
        self.questions = []
        self.closing = None
        self.training_notes = []

    def set_opening(self, script: str):
        """Set opening script"""
        self.opening = script

    def add_question(self, question: InterviewQuestion):
        """Add interview question"""
        self.questions.append(question)

    def set_closing(self, script: str):
        """Set closing script"""
        self.closing = script

    def add_training_note(self, note: str):
        """Add note for interviewer training"""
        self.training_notes.append(note)

    def check_timing(self):
        """Verify questions fit in time allotted"""
        total_time = sum(q.max_time_minutes for q in self.questions)
        overhead = 10  # Opening, closing, buffer

        if total_time + overhead > self.duration:
            return {
                'fits': False,
                'planned': total_time + overhead,
                'available': self.duration,
                'overage': (total_time + overhead) - self.duration
            }
        return {
            'fits': True,
            'planned': total_time + overhead,
            'available': self.duration,
            'buffer': self.duration - (total_time + overhead)
        }

    def generate_protocol_document(self):
        """Generate complete protocol document"""
        doc = f"""
# Interview Protocol

## Research Aim
{self.aim}

## Duration
{self.duration} minutes

## Opening Script ({len(self.opening.split())*0.4:.0f} seconds estimated)
{self.opening}

## Interview Questions

"""
        for i, q in enumerate(self.questions, 1):
            doc += f"### Question {i} ({q.max_time_minutes} minutes max)\n\n"
            doc += f"**Question**: {q.question}\n\n"
            doc += f"**Purpose**: {q.purpose}\n\n"
            doc += "**Probes**:\n"
            for probe in q.probes:
                doc += f"- {probe}\n"
            if q.notes_to_interviewer:
                doc += f"\n**Interviewer Notes**: {q.notes_to_interviewer}\n"
            doc += "\n"

        doc += f"## Closing Script\n{self.closing}\n\n"

        if self.training_notes:
            doc += "## Interviewer Training Notes\n\n"
            for note in self.training_notes:
                doc += f"- {note}\n"

        # Add timing check
        timing = self.check_timing()
        doc += f"\n## Timing Analysis\n"
        doc += f"- Planned time: {timing['planned']} minutes\n"
        doc += f"- Available time: {timing['available']} minutes\n"
        if timing['fits']:
            doc += f"- Buffer: {timing['buffer']} minutes\n"
        else:
            doc += f"- **WARNING: Over by {timing['overage']} minutes**\n"

        return doc

    def create_interview_log(self):
        """Create interview tracking log"""
        log = {
            'interviewer': '',
            'participant_id': '',
            'date': '',
            'start_time': '',
            'end_time': '',
            'location': '',
            'recording': {'audio': False, 'video': False},
            'consent_obtained': False,
            'questions_completed': {f"Q{i+1}": False
                                   for i in range(len(self.questions))},
            'technical_issues': [],
            'notes': '',
            'transcription_status': 'pending'
        }
        return log

# Example protocol
protocol = InterviewProtocol(
    research_aim="Understand how remote workers maintain work-life boundaries",
    duration_minutes=60
)

protocol.set_opening("""
Thank you for participating in this study. This interview will take about 60 minutes.
I'll be asking you about your experiences with remote work and work-life balance.
Please answer openly - there are no right or wrong answers. Everything you share
will be kept confidential and your name will not appear in any reports.

Do I have your permission to audio record this interview? You can ask me to
stop recording at any time.

[Start recording]

Do you have any questions before we begin?
""")

protocol.add_question(InterviewQuestion(
    question="Can you walk me through a typical workday? Start from when you wake up.",
    purpose="Understand daily routines and work patterns",
    probes=[
        "What time do you usually start work?",
        "Where do you physically work?",
        "How do you transition into 'work mode'?",
        "When do you typically finish?",
        "How do you signal to yourself and others that work is done?"
    ],
    max_time_minutes=10,
    notes_to_interviewer="Listen for spatial, temporal, and social boundaries"
))

protocol.add_question(InterviewQuestion(
    question="Tell me about a time when work and personal life collided. What happened?",
    purpose="Elicit specific boundary violations and coping strategies",
    probes=[
        "How did you feel in that moment?",
        "What did you do?",
        "Looking back, what would you do differently?",
        "Has this happened more than once?"
    ],
    max_time_minutes=15,
    notes_to_interviewer="Critical incident technique - get detailed narrative"
))

protocol.set_closing("""
Those are all my questions. Is there anything else you'd like to share about
your remote work experience that we didn't cover?

[Answer]

Thank you so much for your time and insights. Your participation is really valuable.
As a reminder, everything you've shared is confidential. I'll send you a summary
of the findings once the study is complete, if you're interested.

[Stop recording]
""")

protocol.add_training_note("Use active listening - paraphrase to confirm understanding")
protocol.add_training_note("Embrace silence - give participants time to think")
protocol.add_training_note("Follow participant's lead when they share something unexpected")

print(protocol.generate_protocol_document())
```

### 3. Observation Methods

**Observation Protocol**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

class ObservationType(Enum):
    PARTICIPANT = "participant"
    NON_PARTICIPANT = "non_participant"
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"

@dataclass
class ObservationCategory:
    """Define what to observe"""
    category: str
    description: str
    indicators: List[str]
    recording_method: str  # 'checklist', 'frequency', 'narrative', 'time_sample'

class ObservationProtocol:
    """Design observation study"""

    def __init__(self, observation_type: ObservationType,
                 setting: str, duration_minutes: int):
        self.type = observation_type
        self.setting = setting
        self.duration = duration_minutes
        self.categories = []
        self.sampling_strategy = None

    def add_category(self, category: ObservationCategory):
        """Add observation category"""
        self.categories.append(category)

    def set_sampling_strategy(self, strategy: str, interval: Optional[int] = None):
        """Define time sampling strategy

        Args:
            strategy: 'continuous', 'time_sampling', 'event_sampling'
            interval: For time_sampling, seconds between observations
        """
        self.sampling_strategy = {
            'strategy': strategy,
            'interval': interval
        }

    def create_observation_sheet(self):
        """Generate observation recording sheet"""
        sheet = f"""
# Observation Recording Sheet

**Observer**: _______________  **Date**: _______________
**Setting**: {self.setting}
**Start Time**: _______________  **End Time**: _______________
**Observation Type**: {self.type.value}

---

"""
        for i, cat in enumerate(self.categories, 1):
            sheet += f"## {i}. {cat.category}\n"
            sheet += f"*{cat.description}*\n\n"

            if cat.recording_method == 'checklist':
                sheet += "**Indicators** (check if observed):\n"
                for indicator in cat.indicators:
                    sheet += f"- [ ] {indicator}\n"
            elif cat.recording_method == 'frequency':
                sheet += "**Frequency Count**:\n"
                for indicator in cat.indicators:
                    sheet += f"- {indicator}: _____\n"
            elif cat.recording_method == 'time_sample':
                sheet += "**Time Samples** (mark X if present):\n"
                sheet += "| Indicator | "
                sheet += " | ".join([f"T{i}" for i in range(1, 11)])
                sheet += " |\n"
                sheet += "| --- | " + " | ".join(["---"]*10) + " |\n"
                for indicator in cat.indicators:
                    sheet += f"| {indicator} | " + " | ".join(["  "]*10) + " |\n"
            else:  # narrative
                sheet += "**Notes**:\n"
                sheet += "_" * 60 + "\n"
                sheet += "_" * 60 + "\n"

            sheet += "\n"

        sheet += """
---

## Field Notes
[Record contextual details, observer reflections, questions]

"""
        return sheet

    def create_field_notes_template(self):
        """Generate field notes template"""
        template = """
# Field Notes Template

## Descriptive Notes
[What did you observe? Be detailed and concrete]
- Physical setting:
- Participants:
- Activities:
- Interactions:
- Temporal flow:

## Reflective Notes
[Your thoughts, feelings, questions, hunches]
- Initial impressions:
- Surprises:
- Patterns emerging:
- Questions raised:

## Methodological Notes
[Notes about the research process]
- What worked well:
- Challenges:
- Adjustments needed:
- Observer effect concerns:

## Analytical Notes
[Preliminary analysis and connections]
- Themes:
- Connections to theory:
- Ideas for follow-up:
"""
        return template

# Example observation protocol
obs_protocol = ObservationProtocol(
    observation_type=ObservationType.NON_PARTICIPANT,
    setting="Open office workspace",
    duration_minutes=120
)

obs_protocol.add_category(ObservationCategory(
    category="Collaboration Behaviors",
    description="Spontaneous interactions between coworkers",
    indicators=[
        "Verbal questions/requests",
        "Screen sharing",
        "Walking to colleague's desk",
        "Impromptu meetings",
        "Shared problem-solving"
    ],
    recording_method='frequency'
))

obs_protocol.add_category(ObservationCategory(
    category="Focus Behaviors",
    description="Individual concentrated work",
    indicators=[
        "Headphones on",
        "Do not disturb sign",
        "Working at desk alone",
        "Note-taking"
    ],
    recording_method='time_sample'
))

obs_protocol.set_sampling_strategy('time_sampling', interval=600)  # Every 10 min

print(obs_protocol.create_observation_sheet())
```

### 4. Data Quality Assurance

**Quality Control Framework**:
```python
import pandas as pd
import numpy as np
from typing import List, Dict

class DataQualityControl:
    """Implement data quality checks"""

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.issues = []

    def check_completeness(self, required_vars: List[str]):
        """Check for missing data"""
        for var in required_vars:
            if var in self.data.columns:
                missing_n = self.data[var].isna().sum()
                missing_pct = (missing_n / len(self.data)) * 100

                if missing_pct > 5:
                    self.issues.append({
                        'type': 'completeness',
                        'variable': var,
                        'issue': f'{missing_pct:.1f}% missing',
                        'severity': 'high' if missing_pct > 20 else 'medium'
                    })

    def check_range(self, var: str, expected_range: tuple):
        """Check values are in expected range"""
        if var in self.data.columns:
            out_of_range = (
                (self.data[var] < expected_range[0]) |
                (self.data[var] > expected_range[1])
            ).sum()

            if out_of_range > 0:
                self.issues.append({
                    'type': 'range',
                    'variable': var,
                    'issue': f'{out_of_range} values out of range '
                            f'{expected_range}',
                    'severity': 'high'
                })

    def check_consistency(self, var1: str, var2: str, rule: str):
        """Check logical consistency between variables"""
        if var1 in self.data.columns and var2 in self.data.columns:
            # Example: age should be <= years_experience + 18
            inconsistent = 0

            if rule == 'age_gt_experience':
                inconsistent = (
                    self.data[var1] < self.data[var2] + 18
                ).sum()

            if inconsistent > 0:
                self.issues.append({
                    'type': 'consistency',
                    'variable': f'{var1}, {var2}',
                    'issue': f'{inconsistent} logically inconsistent values',
                    'severity': 'medium'
                })

    def check_duplicates(self, id_var: str):
        """Check for duplicate records"""
        duplicates = self.data[id_var].duplicated().sum()

        if duplicates > 0:
            self.issues.append({
                'type': 'duplicates',
                'variable': id_var,
                'issue': f'{duplicates} duplicate IDs',
                'severity': 'high'
            })

    def check_outliers(self, var: str, method: str = 'iqr'):
        """Detect outliers"""
        if var in self.data.columns:
            if method == 'iqr':
                Q1 = self.data[var].quantile(0.25)
                Q3 = self.data[var].quantile(0.75)
                IQR = Q3 - Q1
                outliers = (
                    (self.data[var] < Q1 - 3 * IQR) |
                    (self.data[var] > Q3 + 3 * IQR)
                ).sum()

                if outliers > 0:
                    self.issues.append({
                        'type': 'outliers',
                        'variable': var,
                        'issue': f'{outliers} extreme outliers detected',
                        'severity': 'low'
                    })

    def generate_quality_report(self):
        """Create data quality report"""
        report = "# Data Quality Report\n\n"
        report += f"Dataset: {len(self.data)} records, "
        report += f"{len(self.data.columns)} variables\n\n"

        if not self.issues:
            report += "No quality issues detected.\n"
        else:
            report += f"## Issues Detected: {len(self.issues)}\n\n"

            high = [i for i in self.issues if i['severity'] == 'high']
            medium = [i for i in self.issues if i['severity'] == 'medium']
            low = [i for i in self.issues if i['severity'] == 'low']

            if high:
                report += "### High Severity\n"
                for issue in high:
                    report += f"- **{issue['type'].title()}** "
                    report += f"in {issue['variable']}: {issue['issue']}\n"
                report += "\n"

            if medium:
                report += "### Medium Severity\n"
                for issue in medium:
                    report += f"- **{issue['type'].title()}** "
                    report += f"in {issue['variable']}: {issue['issue']}\n"
                report += "\n"

            if low:
                report += "### Low Severity\n"
                for issue in low:
                    report += f"- **{issue['type'].title()}** "
                    report += f"in {issue['variable']}: {issue['issue']}\n"

        return report

# Example
sample_data = pd.DataFrame({
    'id': [1, 2, 3, 4, 5, 2],  # Duplicate
    'age': [25, 35, 150, 45, np.nan, 30],  # Out of range, missing
    'satisfaction': [4, 5, 3, 4, 2, 5]
})

qc = DataQualityControl(sample_data)
qc.check_completeness(['age', 'satisfaction'])
qc.check_range('age', (18, 100))
qc.check_duplicates('id')

print(qc.generate_quality_report())
```

## Best Practices

### 1. Survey Design
- Keep surveys as short as possible
- Use clear, simple language
- Avoid leading questions
- Use validated scales when available
- Pilot test with target population
- Provide progress indicators
- Test on mobile devices

### 2. Interview Execution
- Build rapport before deep questions
- Use active listening techniques
- Allow silence for thinking
- Be flexible with order
- Probe interesting responses
- Record with permission
- Transcribe promptly

### 3. Observation Methods
- Be systematic and consistent
- Record field notes immediately
- Note your potential biases
- Consider observer effects
- Use multiple observers when possible
- Triangulate with other methods
- Distinguish description from interpretation

### 4. Data Quality
- Check data immediately after collection
- Double-enter critical data
- Use validation rules in forms
- Train data collectors thoroughly
- Conduct inter-rater reliability checks
- Document all quality issues
- Create data cleaning log

## Related Skills

- **research-design**: Planning data collection
- **quantitative-methods**: Quantitative data collection
- **qualitative-methods**: Qualitative data collection
- **data-analysis**: Using collected data
- **research-writing**: Reporting collection methods

## Quick Reference

### Survey Length Guidelines
```
Email survey:     5-7 minutes (10-15 questions)
Phone survey:     10-15 minutes
In-person:        20-30 minutes
Longitudinal:     Shorter for repeated measures
```

### Interview Durations
```
Brief interview:     15-30 minutes
Standard:            45-60 minutes
In-depth:            90-120 minutes
Life history:        Multiple sessions
```

### Response Rate Improvement
```
✓ Personalized invitations
✓ Multiple contact attempts
✓ Incentives (when appropriate)
✓ Clear purpose and benefit
✓ Convenient timing
✓ Follow-up reminders
✓ Mobile-friendly format
```
