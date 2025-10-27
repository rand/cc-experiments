---
name: research-qualitative-methods
description: Master qualitative research methods including interviews, ethnography, case studies, grounded theory, and thematic analysis
---

# Qualitative Research Methods Skill

## When to Use This Skill

Use this skill when you need to:
- Explore phenomena in depth
- Understand lived experiences and meanings
- Generate theory from data
- Study context and complexity
- Investigate "how" and "why" questions
- Capture participant perspectives
- Analyze textual or visual data
- Conduct case studies or ethnographic research

## Core Qualitative Approaches

### 1. In-Depth Interviews

**Purpose**: Explore individual perspectives and experiences

**Interview Protocol Template**:
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class InterviewProtocol:
    """Structure for interview guide"""
    research_question: str
    introduction: str
    opening_questions: List[str]
    main_questions: List[str]
    probes: dict  # question -> list of probes
    closing_questions: List[str]
    estimated_duration: int  # minutes

    def generate_guide(self):
        """Generate formatted interview guide"""
        guide = f"""
# Interview Guide

## Research Question
{self.research_question}

## Introduction ({estimated_duration} minutes)
{self.introduction}

## Opening Questions (5-10 minutes)
"""
        for i, q in enumerate(self.opening_questions, 1):
            guide += f"{i}. {q}\n"

        guide += "\n## Main Questions (30-40 minutes)\n"
        for i, q in enumerate(self.main_questions, 1):
            guide += f"{i}. {q}\n"
            if q in self.probes:
                for probe in self.probes[q]:
                    guide += f"   - Probe: {probe}\n"

        guide += "\n## Closing Questions (5-10 minutes)\n"
        for i, q in enumerate(self.closing_questions, 1):
            guide += f"{i}. {q}\n"

        return guide

# Example protocol
protocol = InterviewProtocol(
    research_question="How do remote workers maintain work-life balance?",
    introduction="""
Thank you for participating. This interview will take about 60 minutes.
I'm interested in understanding your experiences with remote work.
There are no right or wrong answers. Everything you share will be kept
confidential. Do you have any questions before we begin?
""",
    opening_questions=[
        "Can you tell me about your current remote work situation?",
        "How long have you been working remotely?"
    ],
    main_questions=[
        "Walk me through a typical workday. What does it look like?",
        "How do you separate work time from personal time?",
        "What challenges have you faced with work-life balance?",
        "What strategies have you found helpful?"
    ],
    probes={
        "Walk me through a typical workday. What does it look like?": [
            "What time do you typically start?",
            "How do you structure your day?",
            "Where do you work from?"
        ],
        "What challenges have you faced with work-life balance?": [
            "Can you give me a specific example?",
            "How did that make you feel?",
            "What did you do about it?"
        ]
    },
    closing_questions=[
        "Is there anything else you'd like to share?",
        "What advice would you give to new remote workers?"
    ],
    estimated_duration=60
)

print(protocol.generate_guide())
```

### 2. Thematic Analysis

**Purpose**: Identify patterns and themes in qualitative data

**Six-Phase Process**:
```python
import pandas as pd
from collections import defaultdict
from typing import List, Dict, Set

class ThematicAnalysis:
    """Conduct rigorous thematic analysis"""

    def __init__(self):
        self.transcripts = {}
        self.codes = defaultdict(list)
        self.themes = {}
        self.codebook = {}

    # Phase 1: Familiarization
    def add_transcript(self, participant_id: str, text: str):
        """Add transcript and initial notes"""
        self.transcripts[participant_id] = {
            'text': text,
            'initial_notes': []
        }

    def add_initial_note(self, participant_id: str, note: str):
        """Record initial observations"""
        self.transcripts[participant_id]['initial_notes'].append(note)

    # Phase 2: Generate initial codes
    def code_segment(self, participant_id: str, segment: str,
                    code: str, line_numbers: tuple):
        """Apply code to text segment"""
        self.codes[code].append({
            'participant': participant_id,
            'segment': segment,
            'lines': line_numbers
        })

    def get_code_frequency(self):
        """Count code applications"""
        return {code: len(instances)
                for code, instances in self.codes.items()}

    # Phase 3: Search for themes
    def create_theme(self, theme_name: str, codes: List[str],
                    description: str):
        """Group codes into themes"""
        self.themes[theme_name] = {
            'codes': codes,
            'description': description,
            'subthemes': []
        }

    def add_subtheme(self, theme_name: str, subtheme_name: str,
                    codes: List[str]):
        """Add subtheme to existing theme"""
        self.themes[theme_name]['subthemes'].append({
            'name': subtheme_name,
            'codes': codes
        })

    # Phase 4: Review themes
    def get_theme_excerpts(self, theme_name: str):
        """Extract all coded excerpts for a theme"""
        excerpts = []
        theme = self.themes[theme_name]

        for code in theme['codes']:
            if code in self.codes:
                excerpts.extend(self.codes[code])

        return excerpts

    def check_theme_coherence(self, theme_name: str):
        """Assess internal homogeneity of theme"""
        excerpts = self.get_theme_excerpts(theme_name)

        report = {
            'theme': theme_name,
            'n_excerpts': len(excerpts),
            'n_participants': len(set(e['participant'] for e in excerpts)),
            'codes': self.themes[theme_name]['codes'],
            'excerpts_sample': excerpts[:5]  # First 5 for review
        }

        return report

    # Phase 5: Define and name themes
    def define_theme(self, theme_name: str, definition: str,
                    essence: str):
        """Provide clear theme definition"""
        self.themes[theme_name]['definition'] = definition
        self.themes[theme_name]['essence'] = essence

    # Phase 6: Produce report
    def generate_codebook(self):
        """Create detailed codebook"""
        codebook = []

        for theme_name, theme_data in self.themes.items():
            entry = {
                'Theme': theme_name,
                'Definition': theme_data.get('definition', ''),
                'Codes': ', '.join(theme_data['codes']),
                'N_Excerpts': len(self.get_theme_excerpts(theme_name))
            }
            codebook.append(entry)

        return pd.DataFrame(codebook)

    def generate_theme_report(self):
        """Generate thematic analysis report"""
        report = "# Thematic Analysis Report\n\n"
        report += f"Total Participants: {len(self.transcripts)}\n"
        report += f"Total Codes: {len(self.codes)}\n"
        report += f"Total Themes: {len(self.themes)}\n\n"

        for theme_name, theme_data in self.themes.items():
            report += f"## Theme: {theme_name}\n\n"
            report += f"**Definition**: {theme_data.get('definition', 'N/A')}\n\n"
            report += f"**Essence**: {theme_data.get('essence', 'N/A')}\n\n"
            report += f"**Codes**: {', '.join(theme_data['codes'])}\n\n"

            excerpts = self.get_theme_excerpts(theme_name)
            report += f"**Prevalence**: {len(excerpts)} coded segments "
            report += f"across {len(set(e['participant'] for e in excerpts))} participants\n\n"

            # Sample excerpts
            report += "**Representative Excerpts**:\n\n"
            for i, excerpt in enumerate(excerpts[:3], 1):
                report += f"{i}. *{excerpt['participant']}*: "
                report += f'"{excerpt["segment"]}"\n\n'

            # Subthemes
            if theme_data.get('subthemes'):
                report += "**Subthemes**:\n\n"
                for subtheme in theme_data['subthemes']:
                    report += f"- *{subtheme['name']}*: "
                    report += f"{', '.join(subtheme['codes'])}\n"
                report += "\n"

        return report

# Example usage
analysis = ThematicAnalysis()

# Add data
analysis.add_transcript('P001', "I find it hard to stop working...")
analysis.add_initial_note('P001', "Struggles with boundaries")

# Code data
analysis.code_segment('P001',
    "I find it hard to stop working at 5pm",
    'boundary_difficulty',
    (23, 25))
analysis.code_segment('P001',
    "My laptop is always open on the kitchen table",
    'physical_workspace_integration',
    (45, 47))

# Create themes
analysis.create_theme(
    'Blurred Boundaries',
    codes=['boundary_difficulty', 'work_intrusion', 'always_on'],
    description='Difficulty maintaining clear work-life boundaries'
)

analysis.define_theme(
    'Blurred Boundaries',
    definition='The challenge of creating and maintaining separation between work and personal life in remote settings',
    essence='Work and life become entangled'
)

# Generate report
print(analysis.generate_theme_report())
```

### 3. Grounded Theory

**Purpose**: Generate theory from data inductively

**Coding Approach**:
```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum

class CodingLevel(Enum):
    OPEN = "open"
    AXIAL = "axial"
    SELECTIVE = "selective"

@dataclass
class GroundedTheoryCode:
    """Represent a grounded theory code"""
    code: str
    level: CodingLevel
    definition: str
    properties: List[str]
    dimensions: Dict[str, tuple]  # property -> (min, max) dimensions
    memos: List[str]
    examples: List[str]

class GroundedTheoryAnalysis:
    """Conduct grounded theory analysis"""

    def __init__(self):
        self.codes = {}
        self.categories = {}
        self.core_category = None
        self.theoretical_memos = []

    def open_coding(self, code_name: str, definition: str):
        """Initial open coding"""
        self.codes[code_name] = GroundedTheoryCode(
            code=code_name,
            level=CodingLevel.OPEN,
            definition=definition,
            properties=[],
            dimensions={},
            memos=[],
            examples=[]
        )

    def axial_coding(self, category_name: str, codes: List[str],
                    conditions: List[str], actions: List[str],
                    consequences: List[str]):
        """Relate categories to subcategories (paradigm model)"""
        self.categories[category_name] = {
            'codes': codes,
            'conditions': conditions,  # When/why
            'actions_interactions': actions,  # What strategies
            'consequences': consequences,  # With what results
            'level': CodingLevel.AXIAL
        }

    def selective_coding(self, core_category: str, storyline: str):
        """Identify core category and integrate theory"""
        self.core_category = {
            'category': core_category,
            'storyline': storyline,
            'level': CodingLevel.SELECTIVE
        }

    def add_memo(self, memo: str, code: Optional[str] = None):
        """Write theoretical memo"""
        if code and code in self.codes:
            self.codes[code].memos.append(memo)
        else:
            self.theoretical_memos.append(memo)

    def constant_comparison(self, code1: str, code2: str):
        """Compare two codes"""
        c1 = self.codes.get(code1)
        c2 = self.codes.get(code2)

        if not c1 or not c2:
            return "Code(s) not found"

        comparison = f"## Constant Comparison: {code1} vs {code2}\n\n"
        comparison += f"**{code1}**: {c1.definition}\n"
        comparison += f"**{code2}**: {c2.definition}\n\n"
        comparison += "**Similarities**:\n- [Identify similarities]\n\n"
        comparison += "**Differences**:\n- [Identify differences]\n\n"
        comparison += "**Theoretical Insight**:\n[What does this tell us?]\n"

        return comparison

    def theoretical_sampling_guide(self):
        """Generate guide for next theoretical sampling"""
        guide = "# Theoretical Sampling Guide\n\n"
        guide += "## Current Theory State\n"
        if self.core_category:
            guide += f"Core Category: {self.core_category['category']}\n"
            guide += f"Storyline: {self.core_category['storyline']}\n\n"

        guide += "## Gaps to Address\n"
        guide += "1. [Identify underdeveloped categories]\n"
        guide += "2. [Identify missing relationships]\n"
        guide += "3. [Identify negative cases needed]\n\n"

        guide += "## Next Sampling Criteria\n"
        guide += "- Participants who... [specific characteristics]\n"
        guide += "- Settings that... [specific conditions]\n"
        guide += "- Events that... [specific situations]\n"

        return guide

# Example
gt = GroundedTheoryAnalysis()

# Open coding
gt.open_coding('seeking_flexibility',
    'Actions to gain control over work schedule and location')
gt.open_coding('managing_expectations',
    'Negotiating others\' expectations about availability')

# Axial coding
gt.axial_coding(
    category_name='Boundary Work',
    codes=['seeking_flexibility', 'managing_expectations', 'creating_rituals'],
    conditions=['Work from home', 'High autonomy', 'Family present'],
    actions=['Set physical boundaries', 'Communicate availability', 'Use transitional rituals'],
    consequences=['Reduced conflict', 'Better focus', 'Improved wellbeing']
)

# Selective coding
gt.selective_coding(
    core_category='Continuous Boundary Negotiation',
    storyline='Remote workers engage in ongoing negotiation of boundaries '
              'between work and life, using spatial, temporal, and communicative '
              'strategies to manage competing demands and maintain wellbeing.'
)

# Memos
gt.add_memo('Flexibility appears to be double-edged sword - enables control '
            'but also creates expectation of constant availability',
            code='seeking_flexibility')
```

### 4. Case Study Research

**Purpose**: In-depth examination of bounded system

**Case Study Protocol**:
```python
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class CaseType(Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    EMBEDDED = "embedded"

class DataSource(Enum):
    INTERVIEW = "interview"
    OBSERVATION = "observation"
    DOCUMENT = "document"
    ARTIFACT = "artifact"
    ARCHIVAL = "archival"

@dataclass
class CaseStudyDesign:
    """Define case study parameters"""
    case_type: CaseType
    research_questions: List[str]
    propositions: List[str]
    units_of_analysis: str
    case_selection_logic: str
    data_sources: List[DataSource]

    def generate_protocol(self):
        """Generate case study protocol"""
        protocol = f"""
# Case Study Protocol

## Overview
Type: {self.case_type.value}
Unit of Analysis: {self.units_of_analysis}

## Research Questions
"""
        for i, q in enumerate(self.research_questions, 1):
            protocol += f"{i}. {q}\n"

        protocol += "\n## Propositions\n"
        for i, p in enumerate(self.propositions, 1):
            protocol += f"{i}. {p}\n"

        protocol += f"\n## Case Selection\n{self.case_selection_logic}\n"

        protocol += "\n## Data Collection\n"
        for source in self.data_sources:
            protocol += f"- {source.value}\n"

        return protocol

class CaseStudyDatabase:
    """Organize case study evidence"""

    def __init__(self):
        self.evidence = defaultdict(list)
        self.chain_of_evidence = []

    def add_evidence(self, source: DataSource, content: str,
                    date: str, related_rq: str):
        """Add piece of evidence"""
        evidence_id = f"{source.value}_{len(self.evidence[source])}"
        self.evidence[source].append({
            'id': evidence_id,
            'content': content,
            'date': date,
            'research_question': related_rq
        })
        return evidence_id

    def link_evidence(self, evidence_ids: List[str], finding: str):
        """Create chain of evidence"""
        self.chain_of_evidence.append({
            'finding': finding,
            'evidence': evidence_ids
        })

    def generate_evidence_table(self):
        """Create evidence summary table"""
        rows = []
        for source, items in self.evidence.items():
            for item in items:
                rows.append({
                    'ID': item['id'],
                    'Source': source.value,
                    'Date': item['date'],
                    'Research Question': item['research_question']
                })
        return pd.DataFrame(rows)

# Example
design = CaseStudyDesign(
    case_type=CaseType.SINGLE,
    research_questions=[
        'How does the organization implement remote work policy?',
        'What challenges emerge in the transition?'
    ],
    propositions=[
        'Remote work adoption requires cultural change',
        'Technology alone is insufficient'
    ],
    units_of_analysis='Organization-level remote work transition',
    case_selection_logic='Selected for being early adopter with documented transition',
    data_sources=[DataSource.INTERVIEW, DataSource.DOCUMENT, DataSource.OBSERVATION]
)

print(design.generate_protocol())
```

## Qualitative Patterns

### Rigorous Qualitative Research
```
✓ Reflexivity acknowledged
✓ Thick description provided
✓ Triangulation of data sources
✓ Member checking conducted
✓ Negative cases sought
✓ Audit trail maintained
✓ Saturation documented
✓ Context richly described
```

### Weak Qualitative Research
```
✗ Researcher bias unacknowledged
✗ Thin description (anecdotes only)
✗ Single data source
✗ Cherry-picking quotes
✗ Ignoring disconfirming evidence
✗ Unclear analysis process
✗ Sample too small for claims
✗ Decontextualized findings
```

## Best Practices

### 1. Data Collection
- Build rapport before deep questions
- Use open-ended questions
- Practice active listening
- Follow up on interesting points
- Record with permission
- Take field notes immediately after
- Continue until saturation

### 2. Analysis
- Start analysis during collection
- Code systematically
- Write analytic memos frequently
- Check codes with second coder
- Seek negative cases
- Connect to existing theory
- Ground findings in data

### 3. Quality Criteria
- **Credibility**: Prolonged engagement, triangulation, member checks
- **Transferability**: Thick description, context detail
- **Dependability**: Audit trail, clear methods
- **Confirmability**: Reflexivity, raw data available

## Related Skills

- **research-design**: Planning qualitative studies
- **data-collection**: Interview and observation protocols
- **data-analysis**: Qualitative data analysis software
- **research-synthesis**: Synthesizing qualitative findings
- **research-writing**: Writing qualitative reports

## Quick Reference

### Sample Sizes
```
Interviews:        5-25 for phenomenology
                   20-30 for grounded theory
                   1-3 for case study
Focus Groups:      3-5 groups of 6-10 participants
Ethnography:       Extended engagement (months to years)
```

### When to Stop Collecting Data
```
✓ Theoretical saturation reached
✓ No new themes emerging
✓ Negative cases explored
✓ All research questions addressed
✓ Rich description achieved
```
