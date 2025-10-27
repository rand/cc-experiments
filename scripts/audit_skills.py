#!/usr/bin/env python3
"""
Comprehensive Skills Quality Audit Script

Analyzes all 355 skills for:
- Code examples (languages, count, complexity)
- External references (URLs, RFCs, tools)
- Configuration snippets
- Existing Resources
- Quality metrics
- Improvement opportunities

Outputs: skills-audit-report.json
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("Warning: PyYAML not installed, using simple frontmatter parser")


class SkillAuditor:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.results = []

        # Patterns for detection
        self.code_fence_pattern = re.compile(r'```(\w+)\n(.*?)```', re.DOTALL)
        self.url_pattern = re.compile(r'https?://[^\s\)]+')
        self.rfc_pattern = re.compile(r'RFC\s*\d+', re.IGNORECASE)
        self.tool_pattern = re.compile(r'`(\w+)`')

        # High-impact categories
        self.high_priority_categories = {
            'distributed-systems', 'api', 'database', 'security',
            'cryptography', 'protocols', 'engineering', 'frontend',
            'testing', 'infrastructure', 'observability'
        }

    def audit_all_skills(self) -> List[Dict[str, Any]]:
        """Audit all skills in the directory"""
        skill_files = list(self.skills_dir.glob('**/*.md'))
        skill_files = [f for f in skill_files if f.name not in ['INDEX.md', 'README.md']
                      and 'discover-' not in str(f)]

        print(f"Found {len(skill_files)} skills to audit...")

        for skill_file in skill_files:
            try:
                result = self.audit_skill(skill_file)
                self.results.append(result)
            except Exception as e:
                print(f"Error auditing {skill_file}: {e}")

        return self.results

    def audit_skill(self, skill_file: Path) -> Dict[str, Any]:
        """Comprehensive audit of a single skill"""
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter
        frontmatter = self.extract_frontmatter(content)

        # Get category and name
        rel_path = skill_file.relative_to(self.skills_dir)
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else 'root'
        skill_name = skill_file.stem

        # Check for existing Resources
        skill_dir = skill_file.parent
        has_resources_dir = (skill_dir / 'resources').exists()
        has_scripts_dir = (skill_dir / 'scripts').exists()

        # Analyze content
        code_examples = self.find_code_examples(content)
        external_refs = self.find_external_references(content)
        tools_mentioned = self.find_tools(content)
        config_snippets = self.find_config_snippets(content)

        # Calculate metrics
        line_count = len(content.split('\n'))
        code_line_count = sum(len(ex['code'].split('\n')) for ex in code_examples)

        # Determine improvement opportunities
        opportunities = self.identify_opportunities(
            code_examples, external_refs, tools_mentioned, config_snippets,
            has_resources_dir, has_scripts_dir
        )

        # Calculate priority score
        priority_score = self.calculate_priority(
            category, len(code_examples), len(external_refs),
            len(tools_mentioned), has_resources_dir
        )

        return {
            'file_path': str(skill_file.relative_to(self.skills_dir)),
            'category': category,
            'skill_name': skill_name,
            'frontmatter': frontmatter,
            'metrics': {
                'line_count': line_count,
                'code_line_count': code_line_count,
                'code_examples': len(code_examples),
                'external_refs': len(external_refs),
                'tools_mentioned': len(tools_mentioned),
                'config_snippets': len(config_snippets),
            },
            'code_examples': code_examples,
            'external_refs': external_refs,
            'tools_mentioned': list(tools_mentioned),
            'config_snippets': config_snippets,
            'has_resources': {
                'resources_dir': has_resources_dir,
                'scripts_dir': has_scripts_dir,
            },
            'opportunities': opportunities,
            'priority_score': priority_score,
            'priority_tier': self.get_priority_tier(priority_score),
        }

    def extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            if HAS_YAML:
                try:
                    return yaml.safe_load(match.group(1))
                except:
                    return {}
            else:
                # Simple key: value parser
                result = {}
                for line in match.group(1).split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result[key.strip()] = value.strip()
                return result
        return {}

    def find_code_examples(self, content: str) -> List[Dict[str, Any]]:
        """Find all code examples with language and complexity"""
        examples = []
        for match in self.code_fence_pattern.finditer(content):
            lang = match.group(1)
            code = match.group(2)

            # Estimate complexity
            complexity = 'simple'
            if len(code.split('\n')) > 20:
                complexity = 'medium'
            if len(code.split('\n')) > 50 or 'class ' in code or 'import ' in code:
                complexity = 'complex'

            examples.append({
                'language': lang,
                'line_count': len(code.split('\n')),
                'complexity': complexity,
                'code': code[:200]  # Store first 200 chars for reference
            })

        return examples

    def find_external_references(self, content: str) -> List[Dict[str, str]]:
        """Find all external URLs and RFCs"""
        refs = []

        # Find URLs
        for match in self.url_pattern.finditer(content):
            url = match.group(0).rstrip('.,;)')
            ref_type = self.classify_url(url)
            refs.append({
                'type': ref_type,
                'url': url
            })

        # Find RFCs
        for match in self.rfc_pattern.finditer(content):
            refs.append({
                'type': 'rfc',
                'reference': match.group(0)
            })

        return refs

    def classify_url(self, url: str) -> str:
        """Classify URL by type"""
        if 'github.com' in url:
            return 'github'
        elif 'docs.' in url or 'documentation' in url:
            return 'documentation'
        elif 'rfc-editor.org' in url or 'ietf.org' in url:
            return 'rfc'
        elif 'mozilla.org' in url or 'w3.org' in url:
            return 'standard'
        elif 'example.com' in url or 'localhost' in url:
            return 'example'
        else:
            return 'external'

    def find_tools(self, content: str) -> set:
        """Find mentioned tools and technologies"""
        tools = set()

        # Common tools to detect
        tool_keywords = [
            'postgres', 'postgresql', 'mysql', 'redis', 'mongodb',
            'docker', 'kubernetes', 'nginx', 'apache', 'envoy', 'traefik',
            'etcd', 'consul', 'vault', 'terraform', 'ansible',
            'pytest', 'jest', 'go test', 'cargo test',
            'webpack', 'vite', 'rollup', 'esbuild',
            'jwt', 'oauth', 'openssl', 'tls', 'ssl',
            'prometheus', 'grafana', 'datadog', 'sentry',
        ]

        content_lower = content.lower()
        for tool in tool_keywords:
            if tool in content_lower:
                tools.add(tool)

        return tools

    def find_config_snippets(self, content: str) -> List[str]:
        """Find configuration file snippets (nginx, yaml, json, etc.)"""
        config_langs = ['nginx', 'yaml', 'json', 'toml', 'ini', 'apache', 'sql']
        snippets = []

        for match in self.code_fence_pattern.finditer(content):
            lang = match.group(1)
            if lang.lower() in config_langs:
                snippets.append(lang)

        return snippets

    def identify_opportunities(
        self, code_examples, external_refs, tools_mentioned,
        config_snippets, has_resources_dir, has_scripts_dir
    ) -> List[Dict[str, str]]:
        """Identify improvement opportunities"""
        opportunities = []

        if not has_resources_dir and (len(code_examples) > 5 or len(external_refs) > 10):
            opportunities.append({
                'type': 'create_resources_dir',
                'reason': 'Many examples/references could be extracted to Resources',
                'priority': 'high'
            })

        if not has_scripts_dir and len(config_snippets) > 0:
            opportunities.append({
                'type': 'add_validation_scripts',
                'reason': f'Config snippets found ({", ".join(set(config_snippets))}), could add validators',
                'priority': 'medium'
            })

        if len(code_examples) > 3 and not has_resources_dir:
            opportunities.append({
                'type': 'extract_examples',
                'reason': f'{len(code_examples)} code examples could be extracted to standalone files',
                'priority': 'medium'
            })

        if any(tool in tools_mentioned for tool in ['docker', 'postgres', 'redis', 'nginx']):
            opportunities.append({
                'type': 'add_test_scripts',
                'reason': 'Mentions testable tools, could add Docker-based integration tests',
                'priority': 'high'
            })

        if len([ref for ref in external_refs if ref['type'] not in ['example']]) > 5:
            opportunities.append({
                'type': 'create_reference_file',
                'reason': 'Many external references, could create REFERENCE.md',
                'priority': 'low'
            })

        # Check for complex examples that should be validated
        complex_examples = [ex for ex in code_examples if ex['complexity'] in ['medium', 'complex']]
        if len(complex_examples) > 0 and not has_scripts_dir:
            opportunities.append({
                'type': 'validate_examples',
                'reason': f'{len(complex_examples)} complex examples should be validated',
                'priority': 'high'
            })

        return opportunities

    def calculate_priority(
        self, category, num_examples, num_refs, num_tools, has_resources
    ) -> float:
        """Calculate priority score (0-100)"""
        score = 0.0

        # Category priority (40 points)
        if category in self.high_priority_categories:
            score += 40
        elif category != 'root':
            score += 20

        # Examples weight (25 points)
        score += min(num_examples * 3, 25)

        # External references (15 points)
        score += min(num_refs * 1.5, 15)

        # Tools mentioned (10 points)
        score += min(num_tools * 2, 10)

        # Penalize if already has Resources (less urgent) (-10 points)
        if has_resources:
            score -= 10

        # Boost if missing Resources but has content (+10 points)
        if not has_resources and (num_examples > 3 or num_refs > 5):
            score += 10

        return min(score, 100)

    def get_priority_tier(self, score: float) -> str:
        """Convert priority score to tier"""
        if score >= 70:
            return 'HIGH'
        elif score >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'

    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_skills = len(self.results)
        high_priority = len([r for r in self.results if r['priority_tier'] == 'HIGH'])
        medium_priority = len([r for r in self.results if r['priority_tier'] == 'MEDIUM'])
        low_priority = len([r for r in self.results if r['priority_tier'] == 'LOW'])

        with_resources = len([r for r in self.results if r['has_resources']['resources_dir']])
        with_scripts = len([r for r in self.results if r['has_resources']['scripts_dir']])

        total_code_examples = sum(r['metrics']['code_examples'] for r in self.results)
        total_external_refs = sum(r['metrics']['external_refs'] for r in self.results)

        # Count opportunities by type
        opportunity_counts = defaultdict(int)
        for result in self.results:
            for opp in result['opportunities']:
                opportunity_counts[opp['type']] += 1

        # Category breakdown
        category_counts = defaultdict(int)
        for result in self.results:
            category_counts[result['category']] += 1

        return {
            'total_skills': total_skills,
            'priority_distribution': {
                'high': high_priority,
                'medium': medium_priority,
                'low': low_priority
            },
            'resources_status': {
                'with_resources_dir': with_resources,
                'with_scripts_dir': with_scripts,
                'without_resources': total_skills - with_resources
            },
            'content_metrics': {
                'total_code_examples': total_code_examples,
                'total_external_refs': total_external_refs,
                'avg_examples_per_skill': round(total_code_examples / total_skills, 2),
                'avg_refs_per_skill': round(total_external_refs / total_skills, 2)
            },
            'opportunity_counts': dict(opportunity_counts),
            'category_counts': dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))
        }

    def save_report(self, output_file: Path):
        """Save audit report as JSON"""
        report = {
            'summary': self.generate_summary(),
            'skills': sorted(self.results, key=lambda x: x['priority_score'], reverse=True)
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"\nAudit report saved to: {output_file}")
        self.print_summary(report['summary'])

    def print_summary(self, summary: Dict[str, Any]):
        """Print summary to console"""
        print("\n" + "="*60)
        print("SKILLS QUALITY AUDIT SUMMARY")
        print("="*60)

        print(f"\nTotal Skills Audited: {summary['total_skills']}")

        print("\nPriority Distribution:")
        for tier, count in summary['priority_distribution'].items():
            pct = (count / summary['total_skills']) * 100
            print(f"  {tier.upper()}: {count} ({pct:.1f}%)")

        print("\nResources Status:")
        for status, count in summary['resources_status'].items():
            print(f"  {status.replace('_', ' ').title()}: {count}")

        print("\nContent Metrics:")
        for metric, value in summary['content_metrics'].items():
            print(f"  {metric.replace('_', ' ').title()}: {value}")

        print("\nTop Improvement Opportunities:")
        sorted_opps = sorted(summary['opportunity_counts'].items(),
                           key=lambda x: x[1], reverse=True)
        for opp_type, count in sorted_opps[:5]:
            print(f"  {opp_type.replace('_', ' ').title()}: {count} skills")

        print("\nTop Categories (by skill count):")
        for cat, count in list(summary['category_counts'].items())[:10]:
            print(f"  {cat}: {count} skills")

        print("\n" + "="*60)


def main():
    """Main entry point"""
    script_dir = Path(__file__).parent
    skills_dir = script_dir.parent / 'skills'
    output_file = script_dir.parent / 'skills-audit-report.json'

    print("Starting comprehensive skills quality audit...")
    print(f"Skills directory: {skills_dir}")

    auditor = SkillAuditor(skills_dir)
    auditor.audit_all_skills()
    auditor.save_report(output_file)

    print("\nAudit complete! Review skills-audit-report.json for full details.")


if __name__ == '__main__':
    main()
