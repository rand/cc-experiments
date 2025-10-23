#!/usr/bin/env python3
"""
AI Slop Detector - Analyzes text files for common AI-generated content patterns.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict


# High-risk phrases that nearly always indicate AI slop
HIGH_RISK_PHRASES = [
    r"delve into",
    r"dive deep into",
    r"unpack",
    r"navigate the complexit(?:y|ies)",
    r"in the ever-evolving landscape",
    r"in today's fast-paced world",
    r"in today's digital age",
    r"at the end of the day",
    r"it'?s important to note that",
    r"it'?s worth noting that",
]

# Medium-risk phrases - context dependent
MEDIUM_RISK_PHRASES = [
    r"however,? it is important to",
    r"furthermore",
    r"moreover",
    r"in essence",
    r"essentially",
    r"fundamentally",
    r"ultimately",
    r"that being said",
]

# Buzzwords and corporate jargon
BUZZWORDS = [
    r"synergistic",
    r"holistic approach",
    r"paradigm shift",
    r"game-changer",
    r"revolutionary",
    r"cutting-edge",
    r"next-generation",
    r"world-class",
    r"best-in-class",
    r"leverage",
    r"utilize",
    r"empower",
    r"unlock potential",
    r"drive innovation",
]

# Meta-commentary patterns
META_COMMENTARY = [
    r"in this (?:article|post|document|section)",
    r"as we (?:explore|examine|discuss|delve)",
    r"let'?s take a (?:closer )?look",
    r"now that we'?ve covered",
    r"before we proceed",
    r"it'?s crucial to understand",
]

# Excessive hedging
HEDGE_WORDS = [
    r"may or may not",
    r"could potentially",
    r"might possibly",
    r"it appears that",
    r"it seems that",
    r"one could argue",
    r"some might say",
    r"to a certain extent",
    r"generally speaking",
]


class SlopDetector:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.text = self._load_file()
        self.lines = self.text.split('\n')
        self.findings = defaultdict(list)
        
    def _load_file(self) -> str:
        """Load and return file contents."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _find_patterns(self, patterns: List[str], category: str):
        """Find all occurrences of patterns in text."""
        for i, line in enumerate(self.lines, 1):
            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    self.findings[category].append({
                        'line': i,
                        'text': line.strip(),
                        'match': match.group(),
                        'position': match.start()
                    })
    
    def analyze(self) -> Dict:
        """Run all analyses and return findings."""
        # Find pattern categories
        self._find_patterns(HIGH_RISK_PHRASES, 'high_risk')
        self._find_patterns(MEDIUM_RISK_PHRASES, 'medium_risk')
        self._find_patterns(BUZZWORDS, 'buzzwords')
        self._find_patterns(META_COMMENTARY, 'meta_commentary')
        self._find_patterns(HEDGE_WORDS, 'hedging')
        
        # Analyze document structure
        self._analyze_structure()
        
        # Calculate overall score
        score = self._calculate_slop_score()
        
        return {
            'findings': dict(self.findings),
            'score': score,
            'summary': self._generate_summary(score)
        }
    
    def _analyze_structure(self):
        """Analyze document-level structure for slop patterns."""
        # Check for meta-commentary in opening
        if len(self.lines) > 0:
            first_para = ' '.join(self.lines[:5])
            if re.search(r'in this .+ (?:will|we)', first_para, re.IGNORECASE):
                self.findings['structure'].append({
                    'issue': 'Opening meta-commentary',
                    'description': 'Document starts with meta-commentary instead of content'
                })
        
        # Check for excessive transition words at paragraph starts
        transition_starters = 0
        transitions = ['however', 'furthermore', 'moreover', 'additionally', 
                      'nevertheless', 'consequently', 'therefore']
        
        for line in self.lines:
            line = line.strip()
            if line and any(line.lower().startswith(t) for t in transitions):
                transition_starters += 1
        
        if len(self.lines) > 0:
            transition_ratio = transition_starters / len([l for l in self.lines if l.strip()])
            if transition_ratio > 0.3:
                self.findings['structure'].append({
                    'issue': 'Excessive transitions',
                    'description': f'{transition_ratio:.0%} of paragraphs start with transition words'
                })
    
    def _calculate_slop_score(self) -> int:
        """Calculate overall slop score (0-100, higher is worse)."""
        score = 0
        
        # Weight different categories
        score += len(self.findings['high_risk']) * 15
        score += len(self.findings['medium_risk']) * 8
        score += len(self.findings['buzzwords']) * 5
        score += len(self.findings['meta_commentary']) * 10
        score += len(self.findings['hedging']) * 6
        score += len(self.findings['structure']) * 20
        
        # Normalize by document length (per 1000 words)
        word_count = len(self.text.split())
        if word_count > 0:
            score = int((score / word_count) * 1000)
        
        return min(score, 100)  # Cap at 100
    
    def _generate_summary(self, score: int) -> str:
        """Generate a human-readable summary."""
        if score < 20:
            return "✅ Low slop detected - Writing appears authentic and purposeful"
        elif score < 40:
            return "⚠️  Moderate slop detected - Some generic patterns present"
        elif score < 60:
            return "🚨 High slop detected - Many AI-generated patterns found"
        else:
            return "💀 Severe slop detected - Document heavily relies on generic AI patterns"
    
    def print_report(self, verbose: bool = False):
        """Print a formatted report of findings."""
        results = self.analyze()
        
        print(f"\n{'='*70}")
        print(f"AI Slop Detection Report: {self.filepath.name}")
        print(f"{'='*70}\n")
        
        print(f"Overall Slop Score: {results['score']}/100")
        print(f"Assessment: {results['summary']}\n")
        
        findings = results['findings']
        
        if findings['high_risk']:
            print(f"🔴 HIGH-RISK PHRASES ({len(findings['high_risk'])} found):")
            for f in findings['high_risk'][:5 if not verbose else None]:
                print(f"  Line {f['line']}: '{f['match']}' in: {f['text'][:60]}...")
            if len(findings['high_risk']) > 5 and not verbose:
                print(f"  ... and {len(findings['high_risk']) - 5} more")
            print()
        
        if findings['buzzwords']:
            print(f"📢 BUZZWORDS & JARGON ({len(findings['buzzwords'])} found):")
            if not verbose:
                unique_buzzwords = set(f['match'] for f in findings['buzzwords'])
                print(f"  {', '.join(list(unique_buzzwords)[:10])}")
                if len(unique_buzzwords) > 10:
                    print(f"  ... and {len(unique_buzzwords) - 10} more unique buzzwords")
            else:
                for f in findings['buzzwords']:
                    print(f"  Line {f['line']}: '{f['match']}'")
            print()
        
        if findings['meta_commentary']:
            print(f"📝 META-COMMENTARY ({len(findings['meta_commentary'])} found):")
            for f in findings['meta_commentary'][:3 if not verbose else None]:
                print(f"  Line {f['line']}: {f['text'][:70]}...")
            if len(findings['meta_commentary']) > 3 and not verbose:
                print(f"  ... and {len(findings['meta_commentary']) - 3} more")
            print()
        
        if findings['structure']:
            print(f"🏗️  STRUCTURAL ISSUES:")
            for f in findings['structure']:
                print(f"  • {f['issue']}: {f['description']}")
            print()
        
        if findings['hedging']:
            print(f"🤔 EXCESSIVE HEDGING ({len(findings['hedging'])} found)")
            if not verbose:
                print(f"  Found in {len(set(f['line'] for f in findings['hedging']))} lines")
            else:
                for f in findings['hedging'][:5]:
                    print(f"  Line {f['line']}: '{f['match']}'")
            print()
        
        # Recommendations
        if results['score'] > 20:
            print("💡 RECOMMENDATIONS:")
            if findings['high_risk']:
                print("  • Replace high-risk phrases with direct, specific language")
            if findings['buzzwords']:
                print("  • Remove buzzwords and use concrete, specific terms")
            if findings['meta_commentary']:
                print("  • Delete meta-commentary; lead with actual content")
            if findings['hedging']:
                print("  • Reduce hedging; be direct and confident in statements")
            if findings['structure']:
                print("  • Restructure document to avoid generic AI patterns")
            print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python detect_slop.py <file> [--verbose]")
        print("Analyzes text files for AI-generated content patterns")
        sys.exit(1)
    
    filepath = sys.argv[1]
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    if not Path(filepath).exists():
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    
    detector = SlopDetector(filepath)
    detector.print_report(verbose=verbose)


if __name__ == '__main__':
    main()
