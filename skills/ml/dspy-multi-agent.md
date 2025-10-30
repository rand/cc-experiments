---
name: dspy-multi-agent
description: Multi-agent systems with DSPy including orchestration, GEPA optimization, and inter-agent communication
---

# DSPy Multi-Agent Systems

**Scope**: Multi-agent architectures, orchestration, GEPA, agent communication, coordination
**Lines**: ~490
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Building systems with multiple specialized agents
- Implementing hierarchical agent architectures (manager-worker)
- Creating collaborative agent networks
- Optimizing multi-agent systems with GEPA
- Designing domain-specific agent teams (research, customer service, etc.)
- Implementing agent communication and coordination protocols

## Core Concepts

### Multi-Agent Systems

**Definition**: Multiple autonomous agents working together to solve complex tasks

**Purpose**:
- **Specialization**: Each agent focuses on specific domain/skill
- **Scalability**: Distribute workload across agents
- **Robustness**: System continues if one agent fails
- **Modularity**: Easy to add/remove/update agents

**Key insight**: Divide complex problems among specialized agents with clear roles

### Agent Architectures

**Hierarchical**: Manager agent coordinates worker agents
- Manager: Plans, delegates, synthesizes
- Workers: Execute specialized tasks
- Clear command structure

**Peer-to-Peer**: Agents collaborate as equals
- Distributed decision making
- Consensus-based coordination
- No single point of failure

**Pipeline**: Sequential agent chain
- Each agent processes and passes to next
- Clear data flow
- Easy to debug

**Network**: Agents communicate freely
- Dynamic collaboration
- Complex coordination
- Maximum flexibility

### GEPA Optimization

**GEPA**: General-to-specific Evolutionary Prompt Augmentation

**Purpose**: Optimize multi-agent systems jointly
- Co-evolves agent prompts
- Considers inter-agent dependencies
- Improves system-wide performance

**When to use**:
- Multiple agents with interdependencies
- Need to optimize entire system (not just individual agents)
- Complex multi-step workflows

---

## Patterns

### Pattern 1: Hierarchical Multi-Agent System

```python
import dspy

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Define worker agents
class ResearchAgent(dspy.Module):
    """Research agent specialized in information gathering."""

    def __init__(self):
        super().__init__()
        self.search = dspy.Retrieve(k=5)
        self.synthesize = dspy.ChainOfThought("topic, sources -> summary")

    def forward(self, topic):
        sources = self.search(topic).passages
        return self.synthesize(topic=topic, sources="\n".join(sources))

class AnalysisAgent(dspy.Module):
    """Analysis agent specialized in data interpretation."""

    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought("data, question -> analysis, insights: list[str]")

    def forward(self, data, question):
        return self.analyze(data=data, question=question)

class WritingAgent(dspy.Module):
    """Writing agent specialized in content creation."""

    def __init__(self):
        super().__init__()
        self.write = dspy.ChainOfThought("topic, content, style -> article")

    def forward(self, topic, content, style="professional"):
        return self.write(topic=topic, content=content, style=style)

# Manager agent
class ManagerAgent(dspy.Module):
    """Manager that coordinates worker agents."""

    def __init__(self):
        super().__init__()

        # Worker agents
        self.researcher = ResearchAgent()
        self.analyst = AnalysisAgent()
        self.writer = WritingAgent()

        # Planning and synthesis
        self.planner = dspy.ChainOfThought("task -> plan: list[str], agents_needed: list[str]")
        self.synthesizer = dspy.ChainOfThought("task, results -> final_answer")

    def forward(self, task):
        # Plan task decomposition
        plan = self.planner(task=task)

        # Parse plan
        if isinstance(plan.plan, str):
            steps = [s.strip() for s in plan.plan.split(',')]
        else:
            steps = plan.plan

        # Execute with appropriate agents
        results = []

        for step in steps[:5]:  # Limit steps
            step_lower = step.lower()

            if 'research' in step_lower or 'search' in step_lower:
                result = self.researcher(topic=step)
                results.append(f"Research: {result.summary}")

            elif 'analyz' in step_lower or 'interpret' in step_lower:
                # Use previous results as data
                data = "\n".join(results) if results else "No prior data"
                result = self.analyst(data=data, question=step)
                results.append(f"Analysis: {result.analysis}")

            elif 'write' in step_lower or 'draft' in step_lower:
                content = "\n".join(results) if results else "No content"
                result = self.writer(topic=task, content=content)
                results.append(f"Article: {result.article}")

            else:
                # Default to research
                result = self.researcher(topic=step)
                results.append(f"Info: {result.summary}")

        # Synthesize final answer
        all_results = "\n\n".join(results)
        final = self.synthesizer(task=task, results=all_results)

        return dspy.Prediction(
            answer=final.final_answer,
            steps=steps,
            results=results
        )

# Use manager agent
manager = ManagerAgent()
result = manager(task="Write a report about AI trends in 2025")

print(result.answer)
print(f"\nSteps executed: {len(result.steps)}")
```

**Benefits**:
- Clear separation of concerns
- Specialized agents for different tasks
- Centralized coordination
- Easy to add new worker agents

### Pattern 2: Peer-to-Peer Agent Collaboration

```python
import dspy

class CollaborativeAgent(dspy.Module):
    """Agent that can consult peers."""

    def __init__(self, name, specialty, peers=None):
        super().__init__()
        self.name = name
        self.specialty = specialty
        self.peers = peers or []

        self.decide = dspy.ChainOfThought(
            "task, specialty -> can_handle: bool, needs_peer: bool, peer_name"
        )
        self.execute = dspy.ChainOfThought(f"task, context -> result")

    def add_peer(self, peer):
        """Add peer agent."""
        if peer not in self.peers:
            self.peers.append(peer)

    def forward(self, task, context="", visited=None):
        if visited is None:
            visited = set()

        # Prevent infinite loops
        if self.name in visited:
            return dspy.Prediction(result="Already consulted this agent")

        visited.add(self.name)

        # Decide if this agent can handle task
        decision = self.decide(task=task, specialty=self.specialty)

        can_handle = str(decision.can_handle).lower() in ['true', 'yes', '1']
        needs_peer = str(decision.needs_peer).lower() in ['true', 'yes', '1']

        # Execute if can handle
        if can_handle:
            result = self.execute(task=task, context=context)
            agent_result = f"[{self.name}] {result.result}"

            # Consult peer if needed
            if needs_peer and self.peers:
                peer_name = decision.peer_name
                peer = next((p for p in self.peers if p.name == peer_name), None)

                if peer:
                    peer_result = peer(task=task, context=agent_result, visited=visited)
                    combined = f"{agent_result}\n\n{peer_result.result}"
                    return dspy.Prediction(result=combined)

            return dspy.Prediction(result=agent_result)

        # Delegate to peer
        elif needs_peer and self.peers:
            peer_name = decision.peer_name
            peer = next((p for p in self.peers if p.name == peer_name), None)

            if peer:
                return peer(task=task, context=context, visited=visited)

        return dspy.Prediction(result=f"[{self.name}] Cannot handle task")

# Create specialized agents
search_agent = CollaborativeAgent("SearchAgent", "information retrieval and web search")
code_agent = CollaborativeAgent("CodeAgent", "writing and debugging code")
writing_agent = CollaborativeAgent("WritingAgent", "content creation and editing")

# Connect agents as peers
search_agent.add_peer(code_agent)
search_agent.add_peer(writing_agent)
code_agent.add_peer(search_agent)
code_agent.add_peer(writing_agent)
writing_agent.add_peer(search_agent)
writing_agent.add_peer(code_agent)

# Use peer network
result = search_agent(task="Find information about DSPy and write a code example")
print(result.result)
```

**Benefits**:
- No single point of failure
- Agents can route tasks dynamically
- Flexible collaboration
- Emergent behavior

### Pattern 3: Sequential Pipeline

```python
import dspy

class PipelineStage(dspy.Module):
    """Base class for pipeline stages."""

    def __init__(self, name):
        super().__init__()
        self.name = name

    def forward(self, input_data):
        raise NotImplementedError

class ExtractionStage(PipelineStage):
    """Extract structured data."""

    def __init__(self):
        super().__init__("Extraction")
        self.extract = dspy.ChainOfThought(
            "text -> entities: list[str], facts: list[str]"
        )

    def forward(self, input_data):
        result = self.extract(text=input_data)
        return {
            'entities': result.entities,
            'facts': result.facts,
            'source': input_data
        }

class EnrichmentStage(PipelineStage):
    """Enrich data with additional context."""

    def __init__(self):
        super().__init__("Enrichment")
        self.retrieve = dspy.Retrieve(k=3)
        self.enrich = dspy.ChainOfThought("entities, sources -> enriched_data")

    def forward(self, input_data):
        entities = input_data['entities']

        # Retrieve context for entities
        all_sources = []
        for entity in entities[:3]:  # Limit entities
            sources = self.retrieve(entity).passages
            all_sources.extend(sources)

        # Enrich data
        enriched = self.enrich(
            entities=", ".join(entities),
            sources="\n".join(all_sources[:5])
        )

        return {
            **input_data,
            'enriched': enriched.enriched_data
        }

class SynthesisStage(PipelineStage):
    """Synthesize final output."""

    def __init__(self):
        super().__init__("Synthesis")
        self.synthesize = dspy.ChainOfThought(
            "facts, enriched_data -> summary, key_points: list[str]"
        )

    def forward(self, input_data):
        result = self.synthesize(
            facts=", ".join(input_data['facts']),
            enriched_data=input_data['enriched']
        )

        return {
            **input_data,
            'summary': result.summary,
            'key_points': result.key_points
        }

class MultiAgentPipeline(dspy.Module):
    """Sequential multi-agent pipeline."""

    def __init__(self, stages):
        super().__init__()
        self.stages = stages

    def forward(self, input_data):
        data = input_data

        # Execute stages sequentially
        for stage in self.stages:
            print(f"Executing {stage.name}...")
            data = stage(data)

        return dspy.Prediction(**data)

# Create pipeline
pipeline = MultiAgentPipeline(stages=[
    ExtractionStage(),
    EnrichmentStage(),
    SynthesisStage()
])

# Use pipeline
result = pipeline(input_data="DSPy is a framework for programming language models.")
print(f"Summary: {result.summary}")
print(f"Key points: {result.key_points}")
```

**Benefits**:
- Clear data flow
- Easy to debug
- Modular stages
- Predictable execution

### Pattern 4: Multi-Agent RAG with Specialization

```python
import dspy

class SpecializedRAGAgent(dspy.Module):
    """RAG agent specialized for a domain."""

    def __init__(self, domain, collection_name):
        super().__init__()
        self.domain = domain
        self.retrieve = dspy.Retrieve(k=5)  # Would be domain-specific
        self.generate = dspy.ChainOfThought(f"context, question -> answer, confidence: float")

    def forward(self, question):
        # Retrieve from domain-specific collection
        passages = self.retrieve(question).passages
        context = "\n\n".join(passages)

        # Generate answer
        result = self.generate(context=context, question=question)

        try:
            conf = float(result.confidence)
        except:
            conf = 0.5

        return dspy.Prediction(
            answer=result.answer,
            confidence=conf,
            domain=self.domain
        )

class MultiDomainRAG(dspy.Module):
    """Multi-agent RAG system with domain routing."""

    def __init__(self):
        super().__init__()

        # Domain-specific agents
        self.agents = {
            'technical': SpecializedRAGAgent('technical', 'tech_docs'),
            'business': SpecializedRAGAgent('business', 'business_docs'),
            'legal': SpecializedRAGAgent('legal', 'legal_docs'),
        }

        # Router
        self.router = dspy.Predict("question -> domain, confidence: float")

        # Aggregator
        self.aggregate = dspy.ChainOfThought(
            "question, answers -> final_answer"
        )

    def forward(self, question):
        # Route question to domain
        routing = self.router(question=question)
        domain = routing.domain.lower()

        # Try primary domain
        if domain in self.agents:
            primary = self.agents[domain](question)

            try:
                route_conf = float(routing.confidence)
            except:
                route_conf = 0.5

            # If confident in routing, return primary answer
            if route_conf > 0.7 and primary.confidence > 0.6:
                return primary

        # Query multiple domains and aggregate
        answers = []
        for domain_name, agent in self.agents.items():
            result = agent(question)
            answers.append(f"[{domain_name}] {result.answer} (confidence: {result.confidence})")

        # Aggregate answers
        all_answers = "\n\n".join(answers)
        final = self.aggregate(question=question, answers=all_answers)

        return dspy.Prediction(
            answer=final.final_answer,
            sources=answers
        )

# Use multi-domain RAG
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

rag = MultiDomainRAG()
result = rag(question="What are the compliance requirements for data storage?")
print(result.answer)
```

**Benefits**:
- Domain-specific expertise
- Better retrieval quality
- Intelligent routing
- Fallback to multiple domains

### Pattern 5: GEPA-Optimized Multi-Agent System

```python
import dspy

# Define specialized agents
class Agent1(dspy.Module):
    """First agent in pipeline."""

    def __init__(self):
        super().__init__()
        self.process = dspy.ChainOfThought("input -> intermediate_output")

    def forward(self, input):
        return self.process(input=input)

class Agent2(dspy.Module):
    """Second agent that depends on Agent1."""

    def __init__(self):
        super().__init__()
        self.refine = dspy.ChainOfThought("input, previous_output -> refined_output")

    def forward(self, input, previous_output):
        return self.refine(input=input, previous_output=previous_output)

class Agent3(dspy.Module):
    """Final agent that synthesizes."""

    def __init__(self):
        super().__init__()
        self.synthesize = dspy.ChainOfThought("input, context -> final_answer")

    def forward(self, input, context):
        return self.synthesize(input=input, context=context)

# Multi-agent system
class MultiAgentSystem(dspy.Module):
    """System with three dependent agents."""

    def __init__(self):
        super().__init__()
        self.agent1 = Agent1()
        self.agent2 = Agent2()
        self.agent3 = Agent3()

    def forward(self, question):
        # Sequential execution with dependencies
        result1 = self.agent1(input=question)
        result2 = self.agent2(input=question, previous_output=result1.intermediate_output)
        result3 = self.agent3(input=question, context=result2.refined_output)

        return dspy.Prediction(answer=result3.final_answer)

# Prepare training data
trainset = [
    dspy.Example(
        question="What is DSPy?",
        answer="A framework for programming language models"
    ).with_inputs("question"),
    # ... more examples
]

# Define metric
def accuracy(example, pred, trace=None):
    return example.answer.lower() in pred.answer.lower()

# GEPA optimization
# Note: GEPA is experimental and may require specific DSPy version
from dspy.teleprompt import GEPA

optimizer = GEPA(
    metric=accuracy,
    breadth=5,  # Number of prompt variations per agent
    depth=2,    # Optimization iterations
    init_temperature=1.0
)

# Compile multi-agent system
system = MultiAgentSystem()
optimized_system = optimizer.compile(
    student=system,
    trainset=trainset,
    max_bootstrapped_demos=3,
)

# Use optimized system
result = optimized_system(question="What is DSPy?")
print(result.answer)
```

**GEPA Benefits**:
- Co-optimizes all agents jointly
- Considers inter-agent dependencies
- Better than optimizing agents independently
- Evolutionary approach to prompt generation

### Pattern 6: Agent Communication Protocol

```python
import dspy
from dataclasses import dataclass
from typing import Optional

@dataclass
class Message:
    """Message passed between agents."""
    sender: str
    recipient: str
    content: str
    message_type: str  # 'request', 'response', 'broadcast'
    context: Optional[dict] = None

class CommunicatingAgent(dspy.Module):
    """Agent with messaging capability."""

    def __init__(self, name, role):
        super().__init__()
        self.name = name
        self.role = role
        self.inbox = []

        self.process_message = dspy.ChainOfThought(
            "message, role -> response, action"
        )

    def send_message(self, recipient, content, message_type='request', context=None):
        """Send message to another agent."""
        return Message(
            sender=self.name,
            recipient=recipient,
            content=content,
            message_type=message_type,
            context=context
        )

    def receive_message(self, message: Message):
        """Receive message from another agent."""
        self.inbox.append(message)

    def process_inbox(self):
        """Process all messages in inbox."""
        responses = []

        for msg in self.inbox:
            result = self.process_message(
                message=msg.content,
                role=self.role
            )

            responses.append(
                self.send_message(
                    recipient=msg.sender,
                    content=result.response,
                    message_type='response',
                    context={'action': result.action}
                )
            )

        self.inbox = []  # Clear inbox
        return responses

    def forward(self, task):
        """Main agent execution."""
        result = self.process_message(message=task, role=self.role)
        return dspy.Prediction(
            response=result.response,
            action=result.action
        )

class MessageBroker:
    """Central message broker for agent communication."""

    def __init__(self):
        self.agents = {}

    def register_agent(self, agent: CommunicatingAgent):
        """Register agent with broker."""
        self.agents[agent.name] = agent

    def deliver_message(self, message: Message):
        """Deliver message to recipient."""
        if message.recipient == 'broadcast':
            # Broadcast to all agents except sender
            for name, agent in self.agents.items():
                if name != message.sender:
                    agent.receive_message(message)
        elif message.recipient in self.agents:
            self.agents[message.recipient].receive_message(message)
        else:
            print(f"Recipient {message.recipient} not found")

    def process_all(self):
        """Process all agent inboxes."""
        all_responses = []

        for agent in self.agents.values():
            responses = agent.process_inbox()
            all_responses.extend(responses)

            # Deliver responses
            for response in responses:
                self.deliver_message(response)

        return all_responses

# Create agents
researcher = CommunicatingAgent("Researcher", "information gathering")
analyst = CommunicatingAgent("Analyst", "data analysis")
writer = CommunicatingAgent("Writer", "content creation")

# Create broker and register agents
broker = MessageBroker()
broker.register_agent(researcher)
broker.register_agent(analyst)
broker.register_agent(writer)

# Send initial message
msg = researcher.send_message(
    recipient="Analyst",
    content="Analyze the trend of AI adoption in 2025",
    message_type='request'
)
broker.deliver_message(msg)

# Process messages
responses = broker.process_all()
print(f"Processed {len(responses)} messages")
```

**Benefits**:
- Structured communication
- Broadcast capability
- Message routing
- Clear message types

### Pattern 7: Consensus-Based Multi-Agent

```python
import dspy

class VotingAgent(dspy.Module):
    """Agent that can vote on proposals."""

    def __init__(self, name, expertise):
        super().__init__()
        self.name = name
        self.expertise = expertise
        self.vote = dspy.ChainOfThought(
            "proposal, expertise -> vote: bool, confidence: float, reasoning"
        )

    def forward(self, proposal):
        result = self.vote(proposal=proposal, expertise=self.expertise)

        vote_bool = str(result.vote).lower() in ['true', 'yes', '1']

        try:
            conf = float(result.confidence)
        except:
            conf = 0.5

        return dspy.Prediction(
            vote=vote_bool,
            confidence=conf,
            reasoning=result.reasoning,
            agent=self.name
        )

class ConsensusSystem(dspy.Module):
    """Multi-agent system using consensus voting."""

    def __init__(self, agents, threshold=0.6):
        super().__init__()
        self.agents = agents
        self.threshold = threshold

        self.proposer = dspy.ChainOfThought("question -> proposal")
        self.synthesizer = dspy.ChainOfThought(
            "question, proposal, votes -> final_answer"
        )

    def forward(self, question):
        # Generate proposal
        proposal_result = self.proposer(question=question)
        proposal = proposal_result.proposal

        # Collect votes from all agents
        votes = []
        for agent in self.agents:
            vote_result = agent(proposal)
            votes.append({
                'agent': vote_result.agent,
                'vote': vote_result.vote,
                'confidence': vote_result.confidence,
                'reasoning': vote_result.reasoning
            })

        # Calculate consensus
        positive_votes = sum(1 for v in votes if v['vote'])
        consensus_score = positive_votes / len(votes)

        # Synthesize based on votes
        votes_summary = "\n".join([
            f"{v['agent']}: {'Yes' if v['vote'] else 'No'} (confidence: {v['confidence']}) - {v['reasoning']}"
            for v in votes
        ])

        final = self.synthesizer(
            question=question,
            proposal=proposal,
            votes=votes_summary
        )

        return dspy.Prediction(
            answer=final.final_answer,
            proposal=proposal,
            consensus_score=consensus_score,
            reached_consensus=consensus_score >= self.threshold,
            votes=votes
        )

# Create voting agents
agents = [
    VotingAgent("TechnicalExpert", "software engineering and architecture"),
    VotingAgent("SecurityExpert", "cybersecurity and data protection"),
    VotingAgent("UXExpert", "user experience and interface design"),
]

# Create consensus system
consensus = ConsensusSystem(agents, threshold=0.66)

# Use system
result = consensus(question="Should we implement feature X?")
print(f"Answer: {result.answer}")
print(f"Consensus: {result.consensus_score:.1%}")
print(f"Reached: {result.reached_consensus}")
```

**Benefits**:
- Democratic decision making
- Multiple perspectives
- Transparent reasoning
- Configurable thresholds

### Pattern 8: Adaptive Multi-Agent System

```python
import dspy

class AdaptiveMultiAgent(dspy.Module):
    """System that dynamically selects and coordinates agents."""

    def __init__(self, agent_pool):
        super().__init__()
        self.agent_pool = agent_pool  # Dict of {name: agent}

        self.selector = dspy.ChainOfThought(
            "task, available_agents -> selected_agents: list[str], strategy"
        )
        self.coordinator = dspy.ChainOfThought(
            "task, strategy, agent_results -> final_answer"
        )

    def forward(self, task):
        # Describe available agents
        agents_desc = ", ".join([
            f"{name}: {agent.__doc__ or 'No description'}"
            for name, agent in self.agent_pool.items()
        ])

        # Select agents for this task
        selection = self.selector(task=task, available_agents=agents_desc)

        # Parse selected agents
        if isinstance(selection.selected_agents, str):
            selected = [a.strip() for a in selection.selected_agents.split(',')]
        else:
            selected = selection.selected_agents

        # Execute selected agents
        results = []
        for agent_name in selected[:5]:  # Limit agents
            if agent_name in self.agent_pool:
                agent = self.agent_pool[agent_name]
                try:
                    result = agent(task)
                    results.append(f"{agent_name}: {result}")
                except Exception as e:
                    results.append(f"{agent_name}: Error - {e}")

        # Coordinate results
        all_results = "\n\n".join(results)
        final = self.coordinator(
            task=task,
            strategy=selection.strategy,
            agent_results=all_results
        )

        return dspy.Prediction(
            answer=final.final_answer,
            agents_used=selected,
            strategy=selection.strategy
        )

# Define agent pool
agent_pool = {
    'search': dspy.Predict("query -> results"),
    'analyze': dspy.ChainOfThought("data -> analysis"),
    'summarize': dspy.ChainOfThought("text -> summary"),
    'classify': dspy.Predict("text -> category"),
}

# Create adaptive system
adaptive = AdaptiveMultiAgent(agent_pool)

# Use system - it selects appropriate agents
result = adaptive(task="Research and summarize AI trends")
print(f"Answer: {result.answer}")
print(f"Agents used: {result.agents_used}")
```

**Benefits**:
- Dynamic agent selection
- Task-specific configuration
- Resource efficient
- Flexible architecture

---

## Quick Reference

### Multi-Agent Architectures

```python
# Hierarchical
manager = ManagerAgent(workers=[agent1, agent2, agent3])

# Peer-to-peer
agent1.add_peer(agent2)
agent2.add_peer(agent1)

# Pipeline
pipeline = Sequential([stage1, stage2, stage3])

# Adaptive
adaptive = AdaptiveSystem(agent_pool={name: agent, ...})
```

### GEPA Optimization

```python
from dspy.teleprompt import GEPA

optimizer = GEPA(
    metric=metric_fn,
    breadth=5,
    depth=2,
)

optimized = optimizer.compile(
    student=multi_agent_system,
    trainset=trainset,
)
```

### Best Practices

```
✅ DO: Specialize agents for distinct roles
✅ DO: Limit number of agents (5-10 max)
✅ DO: Define clear communication protocols
✅ DO: Handle agent failures gracefully
✅ DO: Optimize system jointly with GEPA
✅ DO: Log inter-agent communications

❌ DON'T: Create too many similar agents
❌ DON'T: Allow circular dependencies
❌ DON'T: Optimize agents independently (use GEPA)
❌ DON'T: Ignore agent failures
❌ DON'T: Forget to set max iterations
```

---

## Anti-Patterns

❌ **Too many agents**: Coordination overhead
```python
# Bad - 50 agents
system = MultiAgent(agents=list_of_50_agents)
```
✅ 5-10 focused agents:
```python
# Good
system = MultiAgent(agents=[search, analyze, write, validate])
```

❌ **Circular dependencies**: Infinite loops
```python
# Bad
agent1 → agent2 → agent3 → agent1  # Loop!
```
✅ Acyclic flow or loop detection:
```python
# Good
def forward(self, task, visited=None):
    if visited is None:
        visited = set()
    if self.name in visited:
        return
    visited.add(self.name)
```

❌ **No error handling**: System crashes
```python
# Bad
result = agent1(task)
result2 = agent2(result.output)  # May fail!
```
✅ Handle errors:
```python
# Good
try:
    result = agent1(task)
    result2 = agent2(result.output)
except Exception as e:
    return fallback_response()
```

---

## Related Skills

- `dspy-agents.md` - Single agent patterns
- `dspy-optimizers.md` - GEPA and other optimizers
- `dspy-production.md` - Deploying multi-agent systems
- `dspy-debugging.md` - Debugging agent interactions
- `dspy-testing.md` - Testing multi-agent systems
- `dspy-rag.md` - Multi-agent RAG patterns

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
