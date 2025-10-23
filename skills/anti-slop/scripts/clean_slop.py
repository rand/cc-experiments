#!/usr/bin/env python3
"""
AI Slop Cleaner - Automatically removes common AI-generated content patterns from text.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class SlopCleaner:
    def __init__(self, filepath: str, aggressive: bool = False):
        self.filepath = Path(filepath)
        self.aggressive = aggressive
        self.text = self._load_file()
        self.changes_made = []
        
    def _load_file(self) -> str:
        """Load and return file contents."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def clean(self) -> str:
        """Apply all cleaning operations and return cleaned text."""
        cleaned = self.text
        
        # Apply cleaning operations in order
        cleaned = self._remove_high_risk_phrases(cleaned)
        cleaned = self._simplify_wordy_phrases(cleaned)
        cleaned = self._remove_meta_commentary(cleaned)
        cleaned = self._reduce_hedging(cleaned)
        cleaned = self._clean_buzzwords(cleaned)
        cleaned = self._fix_redundant_qualifiers(cleaned)
        cleaned = self._remove_empty_intensifiers(cleaned)
        
        if self.aggressive:
            cleaned = self._aggressive_cleanup(cleaned)
        
        # Clean up spacing issues created by deletions
        cleaned = self._normalize_spacing(cleaned)
        
        return cleaned
    
    def _remove_high_risk_phrases(self, text: str) -> str:
        """Remove or replace high-risk AI phrases."""
        replacements = {
            r'\b(?:delve|dive deep) into\b': '',
            r'\bunpack\b(?! (?:the|a|an))': 'examine',  # Keep "unpack the box"
            r'\bnavigate the complexit(?:y|ies) of\b': 'handle',
            r'\bin the ever-evolving landscape of\b': 'in',
            r'\bin today\'s fast-paced world,?\b': '',
            r'\bin today\'s digital age,?\b': '',
            r'\bat the end of the day,?\b': 'ultimately',
            r'\bit\'s important to note that\b': '',
            r'\bit\'s worth noting that\b': '',
        }
        
        for pattern, replacement in replacements.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Removed/replaced: {pattern}")
        
        return text
    
    def _simplify_wordy_phrases(self, text: str) -> str:
        """Replace wordy phrases with simpler alternatives."""
        replacements = {
            r'\bin order to\b': 'to',
            r'\bdue to the fact that\b': 'because',
            r'\bat this point in time\b': 'now',
            r'\bfor the purpose of\b': 'for',
            r'\bhas the ability to\b': 'can',
            r'\bis able to\b': 'can',
            r'\bin spite of the fact that\b': 'although',
            r'\btake into consideration\b': 'consider',
            r'\bmake a decision\b': 'decide',
            r'\bconduct an investigation\b': 'investigate',
            r'\bin the event that\b': 'if',
            r'\bprior to\b': 'before',
            r'\bsubsequent to\b': 'after',
        }
        
        for pattern, replacement in replacements.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Simplified: '{pattern}' → '{replacement}'")
        
        return text
    
    def _remove_meta_commentary(self, text: str) -> str:
        """Remove meta-commentary about the document itself."""
        patterns = [
            r'In this (?:article|post|document|section|guide),? (?:we will|I will|we|I) .*?[.!]\s*',
            r'As we (?:explore|examine|discuss|delve into) .*?,?\s',
            r'Let\'s take a (?:closer )?look at .*?[.!]\s*',
            r'Now that we\'ve covered .*?,?\s',
            r'Before we proceed,?\s.*?[.!]\s*',
        ]
        
        for pattern in patterns:
            old_text = text
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Removed meta-commentary")
        
        return text
    
    def _reduce_hedging(self, text: str) -> str:
        """Reduce excessive hedging language."""
        replacements = {
            r'\bmay or may not\b': 'may',
            r'\bcould potentially\b': 'could',
            r'\bmight possibly\b': 'might',
            r'\bit appears that\b': '',
            r'\bit seems that\b': '',
            r'\bone could argue that\b': '',
            r'\bsome might say that\b': '',
            r'\bto a certain extent,?\b': '',
            r'\bgenerally speaking,?\b': '',
        }
        
        for pattern, replacement in replacements.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Reduced hedging: {pattern}")
        
        return text
    
    def _clean_buzzwords(self, text: str) -> str:
        """Replace or remove corporate buzzwords."""
        replacements = {
            r'\bleverag(?:e|ing)\b': 'use',
            r'\butiliz(?:e|ing)\b': 'use',
            r'\bsynergistic\b': 'cooperative',
            r'\bparadigm shift\b': 'major change',
            r'\bgame-changer\b': 'significant',
            r'\bnext-generation\b': 'new',
            r'\bworld-class\b': 'excellent',
            r'\bbest-in-class\b': 'excellent',
            r'\bcutting-edge\b': 'advanced',
        }
        
        for pattern, replacement in replacements.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Replaced buzzword: {pattern}")
        
        return text
    
    def _fix_redundant_qualifiers(self, text: str) -> str:
        """Remove redundant qualifiers."""
        patterns = [
            r'\bcompletely finish(?:ed)?\b',
            r'\babsolutely essential\b',
            r'\btotally unique\b',
            r'\bvery unique\b',
            r'\bpast history\b',
            r'\bfuture plans\b',
            r'\bend result\b',
            r'\bfinal outcome\b',
        ]
        
        replacements = {
            r'\bcompletely finish(?:ed)?\b': 'finished',
            r'\babsolutely essential\b': 'essential',
            r'\btotally unique\b': 'unique',
            r'\bvery unique\b': 'unique',
            r'\bpast history\b': 'history',
            r'\bfuture plans\b': 'plans',
            r'\bend result\b': 'result',
            r'\bfinal outcome\b': 'outcome',
        }
        
        for pattern, replacement in replacements.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Fixed redundant qualifier: {pattern}")
        
        return text
    
    def _remove_empty_intensifiers(self, text: str) -> str:
        """Remove overused empty intensifiers."""
        # Only remove in specific contexts where they're clearly filler
        patterns = [
            r'\breally important\b',
            r'\bvery important\b',
            r'\bquite literally\b',
            r'\bactually,?\s(?!not|the|a)\b',  # Remove filler "actually"
        ]
        
        replacements = {
            r'\breally important\b': 'important',
            r'\bvery important\b': 'important',
            r'\bquite literally\b': 'literally',
            r'\bactually,?\s(?!not|the|a)\b': '',
        }
        
        for pattern, replacement in replacements.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                self.changes_made.append(f"Removed empty intensifier")
        
        return text
    
    def _aggressive_cleanup(self, text: str) -> str:
        """More aggressive cleanup - may change meaning slightly."""
        # Remove more transition words at sentence starts
        text = re.sub(r'^However,\s', '', text, flags=re.MULTILINE)
        text = re.sub(r'^Furthermore,\s', '', text, flags=re.MULTILINE)
        text = re.sub(r'^Moreover,\s', '', text, flags=re.MULTILINE)
        
        # Remove "It is X that" constructions
        text = re.sub(r'\bIt is (?:important|crucial|essential|vital) (?:that|to)\b', '', text, flags=re.IGNORECASE)
        
        self.changes_made.append("Applied aggressive cleanup")
        return text
    
    def _normalize_spacing(self, text: str) -> str:
        """Clean up spacing issues from deletions."""
        # Fix multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix space before punctuation
        text = re.sub(r' +([.,;:!?])', r'\1', text)
        
        # Fix multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix spaces at start of sentences after deletions
        text = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
        
        # Fix orphaned commas
        text = re.sub(r',\s*,', ',', text)
        
        return text.strip()
    
    def save(self, output_path: str = None):
        """Save cleaned text to file."""
        cleaned = self.clean()
        
        if output_path is None:
            # Create backup and overwrite original
            backup_path = self.filepath.with_suffix(self.filepath.suffix + '.backup')
            self.filepath.rename(backup_path)
            output_path = self.filepath
            print(f"✅ Created backup: {backup_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        
        print(f"✅ Saved cleaned text to: {output_path}")
        print(f"\n📊 Changes made: {len(self.changes_made)}")
        
        if self.changes_made:
            print("\nSummary of changes:")
            # Group similar changes
            change_counts = {}
            for change in self.changes_made:
                category = change.split(':')[0]
                change_counts[category] = change_counts.get(category, 0) + 1
            
            for category, count in change_counts.items():
                print(f"  • {category}: {count} instance(s)")
    
    def preview(self, context_lines: int = 2):
        """Preview changes without saving."""
        cleaned = self.clean()
        
        if cleaned == self.text:
            print("✅ No changes needed - text is already clean!")
            return
        
        print(f"\n{'='*70}")
        print(f"Preview of changes for: {self.filepath.name}")
        print(f"{'='*70}\n")
        
        # Show a diff-like preview
        original_lines = self.text.split('\n')
        cleaned_lines = cleaned.split('\n')
        
        changes_shown = 0
        max_changes_to_show = 10
        
        for i, (orig, clean) in enumerate(zip(original_lines, cleaned_lines), 1):
            if orig != clean and changes_shown < max_changes_to_show:
                print(f"Line {i}:")
                print(f"  - {orig[:80]}")
                print(f"  + {clean[:80]}")
                print()
                changes_shown += 1
        
        if changes_shown == max_changes_to_show:
            print(f"... and more changes (showing first {max_changes_to_show})")
        
        print(f"\n📊 Total changes: {len(self.changes_made)}")
        print("\nRun with --save to apply changes")


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_slop.py <file> [options]")
        print("\nOptions:")
        print("  --save           Save changes (creates backup)")
        print("  --output FILE    Save to different file")
        print("  --aggressive     More aggressive cleanup")
        print("  --preview        Preview changes without saving (default)")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    
    aggressive = '--aggressive' in sys.argv
    save_mode = '--save' in sys.argv
    output_file = None
    
    if '--output' in sys.argv:
        output_idx = sys.argv.index('--output')
        if output_idx + 1 < len(sys.argv):
            output_file = sys.argv[output_idx + 1]
            save_mode = True
    
    cleaner = SlopCleaner(filepath, aggressive=aggressive)
    
    if save_mode:
        cleaner.save(output_file)
    else:
        cleaner.preview()


if __name__ == '__main__':
    main()
