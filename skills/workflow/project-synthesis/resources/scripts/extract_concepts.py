#!/usr/bin/env python3
"""
Extract key concepts from project files for synthesis.

Scans markdown, code files, and Beads issues to identify:
- Section headers and topics
- Class/function/type names  
- Architectural patterns
- Key decisions and constraints

Output: concepts.json in synthesis directory
"""

import json
import re
import glob
import os
import sys
from pathlib import Path
from collections import defaultdict

def extract_from_markdown(filepath):
    """Extract headers and important terms from markdown files."""
    concepts = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Extract headers (## and ###)
            headers = re.findall(r'^#{2,3}\s+(.+)$', content, re.MULTILINE)
            concepts.extend([('header', h.strip()) for h in headers])
            
            # Extract bold terms (likely important)
            bold_terms = re.findall(r'\*\*(.+?)\*\*', content)
            concepts.extend([('term', t.strip()) for t in bold_terms if len(t) < 50])
            
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    
    return concepts

def extract_from_code(filepath, lang):
    """Extract classes, functions, types from code files."""
    concepts = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Python
            if lang == 'py':
                classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
                functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
                concepts.extend([('class', c) for c in classes])
                concepts.extend([('function', f) for f in functions])
            
            # TypeScript/JavaScript
            elif lang in ['ts', 'js']:
                classes = re.findall(r'class\s+(\w+)', content)
                interfaces = re.findall(r'interface\s+(\w+)', content)
                functions = re.findall(r'function\s+(\w+)', content)
                concepts.extend([('class', c) for c in classes])
                concepts.extend([('interface', i) for i in interfaces])
                concepts.extend([('function', f) for f in functions])
            
            # Go
            elif lang == 'go':
                types = re.findall(r'type\s+(\w+)\s+(?:struct|interface)', content)
                functions = re.findall(r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)', content)
                concepts.extend([('type', t) for t in types])
                concepts.extend([('function', f) for f in functions])
            
            # Rust
            elif lang == 'rs':
                structs = re.findall(r'struct\s+(\w+)', content)
                traits = re.findall(r'trait\s+(\w+)', content)
                functions = re.findall(r'fn\s+(\w+)', content)
                concepts.extend([('struct', s) for s in structs])
                concepts.extend([('trait', t) for t in traits])
                concepts.extend([('function', f) for f in functions])
            
            # Zig
            elif lang == 'zig':
                structs = re.findall(r'const\s+(\w+)\s+=\s+struct', content)
                functions = re.findall(r'pub\s+fn\s+(\w+)', content)
                functions.extend(re.findall(r'fn\s+(\w+)', content))
                concepts.extend([('struct', s) for s in structs])
                concepts.extend([('function', f) for f in functions])
                
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    
    return concepts

def extract_from_beads(beads_file):
    """Extract issue descriptions from Beads JSONL."""
    concepts = []
    try:
        with open(beads_file, 'r') as f:
            for line in f:
                if line.strip():
                    issue = json.loads(line)
                    if 'description' in issue:
                        # Extract key terms from description
                        desc = issue['description']
                        # Simple word extraction (could be more sophisticated)
                        words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', desc)
                        concepts.extend([('issue_term', w) for w in words])
    except FileNotFoundError:
        print("Warning: No .beads/issues.jsonl found", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not read Beads file: {e}", file=sys.stderr)
    
    return concepts

def main():
    """Main extraction logic."""
    
    # Get synthesis directory from environment or use default
    synthesis_dir = os.environ.get('SYNTHESIS_DIR', '.claude/synthesis/current')
    output_file = os.path.join(synthesis_dir, 'concepts.json')
    
    # Ensure synthesis directory exists
    Path(synthesis_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting concepts to {output_file}")
    
    all_concepts = defaultdict(list)
    
    # Scan markdown files
    print("Scanning markdown files...")
    for md_file in glob.glob('**/*.md', recursive=True):
        if 'node_modules' in md_file or '.git' in md_file:
            continue
        concepts = extract_from_markdown(md_file)
        for concept_type, concept_value in concepts:
            all_concepts[concept_type].append({
                'value': concept_value,
                'source': md_file
            })
    
    # Scan code files
    print("Scanning code files...")
    extensions = {
        'py': '**/*.py',
        'ts': '**/*.ts',
        'js': '**/*.js',
        'go': '**/*.go',
        'rs': '**/*.rs',
        'zig': '**/*.zig'
    }
    
    for lang, pattern in extensions.items():
        for code_file in glob.glob(pattern, recursive=True):
            if 'node_modules' in code_file or '.git' in code_file or 'dist' in code_file:
                continue
            concepts = extract_from_code(code_file, lang)
            for concept_type, concept_value in concepts:
                all_concepts[concept_type].append({
                    'value': concept_value,
                    'source': code_file
                })
    
    # Scan Beads issues
    print("Scanning Beads issues...")
    beads_file = '.beads/issues.jsonl'
    if os.path.exists(beads_file):
        concepts = extract_from_beads(beads_file)
        for concept_type, concept_value in concepts:
            all_concepts[concept_type].append({
                'value': concept_value,
                'source': beads_file
            })
    
    # Deduplicate and count occurrences
    deduplicated = {}
    for concept_type, concepts_list in all_concepts.items():
        value_counts = defaultdict(lambda: {'count': 0, 'sources': []})
        for concept in concepts_list:
            value = concept['value']
            value_counts[value]['count'] += 1
            if concept['source'] not in value_counts[value]['sources']:
                value_counts[value]['sources'].append(concept['source'])
        
        deduplicated[concept_type] = [
            {
                'value': value,
                'count': data['count'],
                'sources': data['sources']
            }
            for value, data in value_counts.items()
        ]
        
        # Sort by count (most common first)
        deduplicated[concept_type].sort(key=lambda x: x['count'], reverse=True)
    
    # Write output
    with open(output_file, 'w') as f:
        json.dump(deduplicated, f, indent=2)
    
    # Print summary
    total_concepts = sum(len(concepts) for concepts in deduplicated.values())
    print(f"\n✅ Extracted {total_concepts} unique concepts")
    print(f"   Output: {output_file}")
    
    for concept_type, concepts_list in sorted(deduplicated.items()):
        print(f"   - {concept_type}: {len(concepts_list)}")

if __name__ == '__main__':
    main()
