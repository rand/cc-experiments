"""
Multi-Agent RAG System

Hierarchical multi-agent system with specialized retrieval agents.
"""

import dspy
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# ============================================================================
# SIGNATURES
# ============================================================================

class RouteSignature(dspy.Signature):
    """Route query to appropriate specialist agents."""

    question: str = dspy.InputField(desc="User question")
    available_agents: str = dspy.InputField(desc="Available specialist agents")

    agents: str = dspy.OutputField(desc="Comma-separated list of agents to query")
    reasoning: str = dspy.OutputField(desc="Why these agents were chosen")


class SpecialistRAGSignature(dspy.Signature):
    """Specialist agent retrieval and answer generation."""

    question: str = dspy.InputField(desc="User question")
    context: str = dspy.InputField(desc="Retrieved context from specialist domain")
    domain: str = dspy.InputField(desc="Specialist domain (technical/business/general)")

    answer: str = dspy.OutputField(desc="Answer from specialist perspective")
    confidence: str = dspy.OutputField(desc="Confidence level (high/medium/low)")
    sources: str = dspy.OutputField(desc="Source passages used")


class SynthesizeSignature(dspy.Signature):
    """Synthesize multiple agent answers into final answer."""

    question: str = dspy.InputField(desc="Original question")
    agent_answers: str = dspy.InputField(desc="Answers from all agents")

    final_answer: str = dspy.OutputField(desc="Synthesized final answer")
    confidence: str = dspy.OutputField(desc="Overall confidence")
    sources: str = dspy.OutputField(desc="Combined sources")


# ============================================================================
# SPECIALIST AGENTS
# ============================================================================

class SpecialistAgent(dspy.Module):
    """Specialist agent with domain-specific retrieval."""

    def __init__(self, domain: str, k: int = 5):
        """Initialize specialist agent.

        Args:
            domain: Agent domain (technical/business/general)
            k: Number of passages to retrieve
        """
        super().__init__()
        self.domain = domain
        self.retrieve = dspy.Retrieve(k=k)
        self.generate = dspy.ChainOfThought(SpecialistRAGSignature)

    def forward(self, question: str) -> dspy.Prediction:
        """Process question in specialist domain.

        Args:
            question: User question

        Returns:
            Specialist answer with confidence and sources
        """
        # Retrieve from domain-specific context
        domain_query = f"[{self.domain}] {question}"
        retrieval = self.retrieve(domain_query)
        context = "\n".join(retrieval.passages)

        # Generate answer
        result = self.generate(
            question=question,
            context=context,
            domain=self.domain
        )

        # Validate
        dspy.Assert(
            len(result.answer) > 0,
            "Answer cannot be empty"
        )

        dspy.Suggest(
            result.confidence in ["high", "medium", "low"],
            "Confidence should be high/medium/low",
            target_module=self.generate
        )

        return result


# ============================================================================
# COORDINATOR
# ============================================================================

class CoordinatorAgent(dspy.Module):
    """Coordinator that routes queries to specialists."""

    def __init__(self):
        """Initialize coordinator."""
        super().__init__()
        self.route = dspy.ChainOfThought(RouteSignature)

        self.agent_descriptions = {
            "technical": "Code, APIs, programming, software architecture",
            "business": "Business strategy, finance, operations, management",
            "general": "Broad topics, history, culture, general knowledge"
        }

    def forward(self, question: str) -> List[str]:
        """Route question to appropriate agents.

        Args:
            question: User question

        Returns:
            List of agent names to query
        """
        available = "\n".join(
            f"- {name}: {desc}"
            for name, desc in self.agent_descriptions.items()
        )

        result = self.route(
            question=question,
            available_agents=available
        )

        # Parse agent list
        agents = [
            agent.strip().lower()
            for agent in result.agents.split(",")
        ]

        # Validate
        valid_agents = [
            agent for agent in agents
            if agent in self.agent_descriptions
        ]

        return valid_agents if valid_agents else ["general"]


# ============================================================================
# SYNTHESIZER
# ============================================================================

class SynthesizerAgent(dspy.Module):
    """Synthesize answers from multiple agents."""

    def __init__(self):
        """Initialize synthesizer."""
        super().__init__()
        self.synthesize = dspy.ChainOfThought(SynthesizeSignature)

    def forward(
        self,
        question: str,
        agent_results: Dict[str, dspy.Prediction]
    ) -> dspy.Prediction:
        """Synthesize multiple agent answers.

        Args:
            question: Original question
            agent_results: Dictionary of agent_name -> prediction

        Returns:
            Synthesized answer with confidence and sources
        """
        # Format agent answers
        answers_text = []
        all_sources = []

        for agent_name, result in agent_results.items():
            answers_text.append(
                f"[{agent_name.upper()} AGENT]:\n"
                f"Answer: {result.answer}\n"
                f"Confidence: {result.confidence}\n"
            )
            all_sources.extend(result.sources.split("\n"))

        agent_answers = "\n\n".join(answers_text)

        # Synthesize
        result = self.synthesize(
            question=question,
            agent_answers=agent_answers
        )

        # Validate
        dspy.Assert(
            len(result.final_answer) > 0,
            "Final answer cannot be empty"
        )

        return dspy.Prediction(
            answer=result.final_answer,
            confidence=result.confidence,
            sources=result.sources,
            agent_contributions=agent_results
        )


# ============================================================================
# MULTI-AGENT RAG SYSTEM
# ============================================================================

class MultiAgentRAG(dspy.Module):
    """Multi-agent RAG with hierarchical coordination.

    Architecture:
    1. Coordinator routes query to specialist(s)
    2. Specialists retrieve and answer in parallel
    3. Synthesizer combines answers into final response

    Example:
        ```python
        system = MultiAgentRAG()
        result = system(question="How to implement OAuth?")
        print(result.answer)
        ```
    """

    def __init__(self, k: int = 5, verbose: bool = False):
        """Initialize multi-agent system.

        Args:
            k: Passages per agent
            verbose: Print intermediate steps
        """
        super().__init__()

        # Coordinator
        self.coordinator = CoordinatorAgent()

        # Specialist agents
        self.agents = {
            "technical": SpecialistAgent("technical", k=k),
            "business": SpecialistAgent("business", k=k),
            "general": SpecialistAgent("general", k=k),
        }

        # Synthesizer
        self.synthesizer = SynthesizerAgent()

        self.verbose = verbose

    def forward(self, question: str) -> dspy.Prediction:
        """Process question through multi-agent system.

        Args:
            question: User question

        Returns:
            Final synthesized answer with metadata

        Example:
            ```python
            result = system(question="What is OAuth?")
            print(f"Answer: {result.answer}")
            print(f"Confidence: {result.confidence}")
            print(f"Agents used: {list(result.agent_contributions.keys())}")
            ```
        """
        # Step 1: Route to agents
        selected_agents = self.coordinator(question=question)

        if self.verbose:
            print(f"Routing to agents: {selected_agents}")

        # Step 2: Query specialists in parallel (simulated)
        agent_results = {}
        for agent_name in selected_agents:
            if agent_name in self.agents:
                if self.verbose:
                    print(f"Querying {agent_name} agent...")

                result = self.agents[agent_name](question=question)
                agent_results[agent_name] = result

        # Step 3: Synthesize answers
        if not agent_results:
            # Fallback to general agent
            agent_results["general"] = self.agents["general"](question=question)

        if self.verbose:
            print(f"Synthesizing {len(agent_results)} answers...")

        final_result = self.synthesizer(
            question=question,
            agent_results=agent_results
        )

        return final_result


# ============================================================================
# SETUP AND UTILITIES
# ============================================================================

def setup_retrieval():
    """Setup retrieval with sample documents.

    This should be replaced with your actual document loading logic.
    """
    try:
        from dspy.retrieve.chromadb_rm import ChromadbRM

        # Sample documents per domain
        documents = {
            "technical": [
                "OAuth is an open standard for access delegation...",
                "REST APIs use HTTP methods like GET, POST, PUT, DELETE...",
                "Python decorators are functions that modify other functions...",
            ],
            "business": [
                "ROI (Return on Investment) measures profitability...",
                "Agile methodology emphasizes iterative development...",
                "Market segmentation divides customers into groups...",
            ],
            "general": [
                "The Python programming language was created by Guido van Rossum...",
                "Machine learning is a subset of artificial intelligence...",
                "Cloud computing provides on-demand computing resources...",
            ]
        }

        # Initialize retriever
        rm = ChromadbRM(collection_name="multi_agent_docs", k=5)

        # Note: In production, load documents into ChromaDB here
        print("✓ Retrieval configured (ChromaDB)")

        dspy.settings.configure(rm=rm)

    except ImportError:
        print("⚠ ChromaDB not available, using mock retrieval")


def create_optimized_system(trainset: List[dspy.Example]) -> MultiAgentRAG:
    """Optimize multi-agent system with COPRO.

    Args:
        trainset: Training examples

    Returns:
        Optimized system
    """
    from dspy.teleprompt import COPRO

    system = MultiAgentRAG()

    def accuracy(example, prediction, trace=None):
        return float(
            example.answer.lower() in prediction.answer.lower()
        )

    optimizer = COPRO(
        metric=accuracy,
        breadth=10,
        depth=3,
        verbose=True
    )

    optimized = optimizer.compile(system, trainset=trainset)

    return optimized


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Example usage."""
    # Configure LM
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Setup retrieval
    setup_retrieval()

    # Create system
    system = MultiAgentRAG(verbose=True)

    # Example queries
    queries = [
        "How do I implement OAuth in Python?",  # Technical
        "What is a good ROI for a SaaS startup?",  # Business
        "What is machine learning?",  # General
        "How can I optimize my API for better performance and reduce costs?",  # Multi-domain
    ]

    print("\n" + "=" * 60)
    print("MULTI-AGENT RAG SYSTEM")
    print("=" * 60)

    for question in queries:
        print(f"\n\nQuestion: {question}")
        print("-" * 60)

        result = system(question=question)

        print(f"\nAnswer: {result.answer}")
        print(f"Confidence: {result.confidence}")
        print(f"Agents consulted: {list(result.agent_contributions.keys())}")
        print(f"Sources: {result.sources[:200]}...")


if __name__ == "__main__":
    main()
