#!/usr/bin/env python3
"""
Standalone test demonstrating the custom converter concepts without requiring
the Rust extension to be built. This shows what the converters enable.
"""

from datetime import datetime
from typing import Dict, List, Optional

def create_sample_document() -> Dict:
    """Create a sample document dictionary."""
    return {
        "title": "Sample Document",
        "content": "This is a sample document demonstrating custom type conversion in PyO3.",
        "source": "https://example.com/doc1",
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "author": "John Doe",
            "category": "example",
            "language": "en"
        }
    }

def create_citation_from_doc(doc: Dict) -> Dict:
    """Create a citation from a document."""
    return {
        "text": f"See {doc['title']} for more information.",
        "documents": [doc],
        "citation_style": "APA",
        "page_numbers": [42, 43, 44]
    }

def merge_documents(docs: List[Dict]) -> Dict:
    """Merge multiple documents."""
    if not docs:
        raise ValueError("Cannot merge empty document list")

    merged_title = " + ".join(d["title"] for d in docs)
    merged_content = "\n\n---\n\n".join(d["content"] for d in docs)
    sources = ", ".join(d["source"] for d in docs)

    merged_metadata = {}
    for doc in docs:
        merged_metadata.update(doc.get("metadata", {}))

    return {
        "title": merged_title,
        "content": merged_content,
        "source": sources,
        "timestamp": datetime.now().isoformat(),
        "metadata": merged_metadata
    }

def validate_citation(citation: Dict) -> bool:
    """Validate citation format."""
    if not citation.get("text"):
        raise ValueError("Citation text cannot be empty")

    if not citation.get("documents"):
        raise ValueError("Citation must reference at least one document")

    valid_styles = ["APA", "MLA", "Chicago", "IEEE", "Harvard"]
    if citation.get("citation_style") not in valid_styles:
        raise ValueError(
            f"Invalid citation style '{citation.get('citation_style')}'. "
            f"Must be one of: {', '.join(valid_styles)}"
        )

    return True

def main():
    print("Custom Type Converters Example (Python)")
    print("=" * 50)

    # Create sample document
    print("\n1. Creating sample document...")
    doc = create_sample_document()
    print(f"   Title: {doc['title']}")
    print(f"   Source: {doc['source']}")
    print(f"   Metadata: {doc['metadata']}")

    # Create citation
    print("\n2. Creating citation from document...")
    citation = create_citation_from_doc(doc)
    print(f"   Text: {citation['text']}")
    print(f"   Style: {citation['citation_style']}")
    print(f"   Documents: {len(citation['documents'])}")
    print(f"   Pages: {citation['page_numbers']}")

    # Validate citation
    print("\n3. Validating citation...")
    try:
        is_valid = validate_citation(citation)
        print(f"   Citation is valid: {is_valid}")
    except ValueError as e:
        print(f"   Validation error: {e}")

    # Merge documents
    print("\n4. Merging documents...")
    doc2 = {
        "title": "Second Document",
        "content": "Additional content for merging.",
        "source": "https://example.com/doc2",
        "timestamp": datetime.now().isoformat(),
        "metadata": {"author": "Jane Smith"}
    }
    merged = merge_documents([doc, doc2])
    print(f"   Merged title: {merged['title']}")
    print(f"   Merged sources: {merged['source']}")
    print(f"   Merged metadata: {merged['metadata']}")

    print("\n" + "=" * 50)
    print("All operations completed successfully!")
    print("\nKey concepts demonstrated:")
    print("  ✓ Document type with metadata")
    print("  ✓ Citation type with nested documents")
    print("  ✓ DateTime handling")
    print("  ✓ Type validation")
    print("  ✓ Collection operations")
    print("\nIn the Rust version, these conversions happen between")
    print("Rust types and Python objects bidirectionally with full")
    print("type safety and performance!")

if __name__ == "__main__":
    main()
