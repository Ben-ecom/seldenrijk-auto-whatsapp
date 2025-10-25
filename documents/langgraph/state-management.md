# LangGraph State Management Guide

Complete guide for managing state in LangGraph multi-agent workflows.

## Overview

LangGraph uses a **StateGraph** to orchestrate multi-agent workflows with typed state management.

**Key Concepts:**
- **State:** Shared data structure passed between agents
- **Nodes:** Individual agent functions that process state
- **Edges:** Connections between nodes (conditional or direct)
- **Reducers:** Functions that merge state updates

## State Definition

### Basic State Schema

```python
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """State passed between agents."""
    messages: Annotated[List[Dict], add_messages]  # Messages with reducer
    user_input: str
    agent_output: str
    metadata: Dict[str, Any]
```

### State with Reducers

Reducers control how state fields are updated:

```python
from operator import add

class AgentState(TypedDict):
    # Append to list (don't replace)
    messages: Annotated[List[Dict], add_messages]

    # Add numbers together
    token_count: Annotated[int, add]

    # Replace with latest value (default)
    current_agent: str

    # Custom reducer
    tags: Annotated[List[str], lambda x, y: list(set(x + y))]
```

**Built-in Reducers:**
- `add_messages`: Append messages to conversation history
- `add`: Sum numeric values
- `operator.or_`: Boolean OR
- Custom function: `lambda old, new: merged_value`

### Complex State Example

```python
class ConversationState(TypedDict):
    # Input
    message_id: str
    conversation_id: str
    contact_id: str
    content: str
    sender_name: str
    sender_phone: str

    # History
    conversation_history: Annotated[List[Dict], add_messages]

    # Agent outputs
    router_output: Dict[str, Any]
    extraction_output: Dict[str, Any]
    conversation_output: Dict[str, Any]

    # Metadata
    intent: str
    confidence: float
    processing_time_s: float
    total_cost_usd: Annotated[float, add]
    total_tokens_used: Annotated[int, add]

    # Control flow
    escalate_to_human: bool
    error_occurred: bool
    source: str  # "chatwoot", "waha", "360dialog"
```

## State Updates

### Returning State Updates

Agents return **partial state updates** that get merged:

```python
def router_agent(state: AgentState) -> Dict[str, Any]:
    """Route message to appropriate intent."""

    intent = classify_message(state["content"])

    # Return only changed fields
    return {
        "intent": intent,
        "router_output": {
            "intent": intent,
            "confidence": 0.95
        },
        "total_tokens_used": 100  # Will be added to existing value
    }
```

### State Access Patterns

```python
def agent_function(state: AgentState) -> Dict[str, Any]:
    # Read from state
    user_message = state["content"]
    history = state.get("conversation_history", [])

    # Process
    response = generate_response(user_message, history)

    # Return updates (partial state)
    return {
        "agent_output": response,
        "total_tokens_used": 150
    }
```

### Conditional Updates

```python
def extraction_agent(state: AgentState) -> Dict[str, Any]:
    intent = state["intent"]

    if intent == "general_inquiry":
        # No extraction needed
        return {}  # No state changes

    if intent == "car_search":
        extracted = extract_car_preferences(state["content"])
        return {"extraction_output": extracted}

    return {"error_occurred": True}
```

## Graph Construction

### Basic Graph Setup

```python
from langgraph.graph import StateGraph, END

# Define state
class MyState(TypedDict):
    input: str
    output: str

# Create graph
workflow = StateGraph(MyState)

# Add nodes (agents)
workflow.add_node("agent1", agent1_function)
workflow.add_node("agent2", agent2_function)

# Set entry point
workflow.set_entry_point("agent1")

# Add edges
workflow.add_edge("agent1", "agent2")
workflow.add_edge("agent2", END)

# Compile
app = workflow.compile()
```

### Conditional Routing

```python
def router(state: MyState) -> str:
    """Decide next node based on state."""
    if state.get("needs_extraction"):
        return "extraction_agent"
    elif state.get("needs_conversation"):
        return "conversation_agent"
    else:
        return END

# Add conditional edge
workflow.add_conditional_edges(
    "router_agent",
    router,  # Function returns next node name
    {
        "extraction_agent": "extraction_agent",
        "conversation_agent": "conversation_agent",
        END: END
    }
)
```

### Multiple Exit Paths

```python
def route_after_extraction(state: MyState) -> str:
    """Route based on extraction results."""
    if state.get("error_occurred"):
        return "error_handler"

    if state.get("escalate_to_human"):
        return END  # Stop workflow

    return "conversation_agent"

workflow.add_conditional_edges(
    "extraction_agent",
    route_after_extraction,
    {
        "error_handler": "error_handler",
        "conversation_agent": "conversation_agent",
        END: END
    }
)
```

## Execution

### Running the Graph

```python
# Create initial state
initial_state = {
    "input": "I want to buy a car",
    "metadata": {}
}

# Execute workflow
final_state = await app.ainvoke(initial_state)

# Access results
print(final_state["output"])
```

### Streaming Results

```python
async for event in app.astream(initial_state):
    node_name = list(event.keys())[0]
    node_output = event[node_name]
    print(f"{node_name}: {node_output}")
```

### Synchronous Execution

```python
# Async (recommended)
final_state = await app.ainvoke(initial_state)

# Sync (blocking)
final_state = app.invoke(initial_state)
```

## State Persistence (Checkpointing)

### Memory Checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver

# Create checkpointer
checkpointer = MemorySaver()

# Compile with checkpointing
app = workflow.compile(checkpointer=checkpointer)

# Execute with thread_id
config = {"configurable": {"thread_id": "conversation_123"}}
final_state = await app.ainvoke(initial_state, config)

# Resume from checkpoint
resumed_state = await app.ainvoke(
    {"input": "Follow-up question"},
    config  # Same thread_id
)
```

### Postgres Checkpointer

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create Postgres checkpointer
checkpointer = PostgresSaver(
    connection_string="postgresql://user:pass@localhost/db"
)

# Compile
app = workflow.compile(checkpointer=checkpointer)

# State automatically saved/restored per thread_id
```

### Checkpoint Usage

```python
# Get checkpoint history
history = checkpointer.list(config)

# Load specific checkpoint
checkpoint = checkpointer.get(config)

# Resume from checkpoint
state = await app.ainvoke(new_input, config)
```

## Error Handling

### Try-Catch in Agents

```python
def safe_agent(state: AgentState) -> Dict[str, Any]:
    try:
        result = risky_operation(state["input"])
        return {"output": result}

    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {
            "error_occurred": True,
            "error_message": str(e)
        }
```

### Error Routing

```python
def error_router(state: AgentState) -> str:
    if state.get("error_occurred"):
        return "error_handler"
    return "next_agent"

workflow.add_conditional_edges(
    "risky_agent",
    error_router,
    {
        "error_handler": "error_handler",
        "next_agent": "next_agent"
    }
)
```

### Global Error Handler

```python
def error_handler(state: AgentState) -> Dict[str, Any]:
    """Handle all errors."""
    error_msg = state.get("error_message", "Unknown error")

    return {
        "escalate_to_human": True,
        "agent_output": f"Error occurred: {error_msg}",
        "error_occurred": False  # Reset flag
    }
```

## Best Practices

### 1. Minimal State Updates

```python
# ❌ Bad - returning entire state
def agent(state: AgentState) -> AgentState:
    return {**state, "output": "new value"}

# ✅ Good - return only changes
def agent(state: AgentState) -> Dict[str, Any]:
    return {"output": "new value"}
```

### 2. Type Safety

```python
# ✅ Use TypedDict for state
class MyState(TypedDict):
    field1: str
    field2: int

# ✅ Type agent returns
def agent(state: MyState) -> Dict[str, Any]:
    ...
```

### 3. Default Values

```python
def agent(state: AgentState) -> Dict[str, Any]:
    # Use .get() with defaults
    history = state.get("conversation_history", [])
    metadata = state.get("metadata", {})

    # Safe dictionary access
    intent = state.get("router_output", {}).get("intent", "unknown")
```

### 4. Reducers for Accumulation

```python
# ✅ Use reducers for accumulation
class MyState(TypedDict):
    total_tokens: Annotated[int, add]  # Auto-sum
    total_cost: Annotated[float, add]  # Auto-sum
    messages: Annotated[List, add_messages]  # Auto-append
```

### 5. Clear Naming

```python
# ✅ Descriptive state fields
class MyState(TypedDict):
    # Input fields
    user_message: str
    user_id: str

    # Agent outputs
    router_output: Dict
    extraction_output: Dict
    conversation_output: Dict

    # Control flow
    escalate_to_human: bool
    error_occurred: bool

    # Metrics
    total_cost_usd: Annotated[float, add]
```

## Common Patterns

### Multi-Agent Pipeline

```python
workflow = StateGraph(AgentState)

# Sequential pipeline
workflow.add_node("router", router_agent)
workflow.add_node("extractor", extraction_agent)
workflow.add_node("responder", conversation_agent)

workflow.set_entry_point("router")
workflow.add_edge("router", "extractor")
workflow.add_edge("extractor", "responder")
workflow.add_edge("responder", END)
```

### Conditional Branching

```python
def route_by_intent(state: AgentState) -> str:
    intent = state["intent"]

    if intent == "car_search":
        return "search_agent"
    elif intent == "appointment":
        return "booking_agent"
    else:
        return "general_agent"

workflow.add_conditional_edges(
    "router",
    route_by_intent,
    {
        "search_agent": "search_agent",
        "booking_agent": "booking_agent",
        "general_agent": "general_agent"
    }
)
```

### Loop Until Complete

```python
def check_completion(state: AgentState) -> str:
    if state.get("task_complete"):
        return END
    return "processor"  # Loop back

workflow.add_node("processor", process_agent)
workflow.add_conditional_edges(
    "processor",
    check_completion,
    {
        "processor": "processor",  # Loop
        END: END
    }
)
```

### Parallel Processing

```python
# Create subgraph for parallel execution
from langgraph.graph import Graph

def parallel_processor(state: AgentState) -> Dict[str, Any]:
    # Launch parallel tasks
    task1 = agent1(state)
    task2 = agent2(state)

    # Merge results
    return {
        "result1": task1["output"],
        "result2": task2["output"]
    }
```

## Performance Tips

1. **Minimize State Size:** Only include necessary data
2. **Use Reducers:** Automatic merging is faster
3. **Checkpoint Strategically:** Only save at key points
4. **Async Execution:** Use `ainvoke` for better performance
5. **Lazy Loading:** Don't fetch data until needed

## Debugging

### Print State

```python
def debug_agent(state: AgentState) -> Dict[str, Any]:
    print(f"Current state: {state}")
    return {}  # No changes

# Add debug nodes
workflow.add_node("debug1", debug_agent)
workflow.add_edge("router", "debug1")
workflow.add_edge("debug1", "next_agent")
```

### State Logging

```python
import logging

def logged_agent(state: AgentState) -> Dict[str, Any]:
    logging.info(f"Agent input: {state.get('input')}")

    result = process(state)

    logging.info(f"Agent output: {result}")
    return result
```

## Source

Documentation compiled from:
- https://langchain-ai.github.io/langgraph/
- LangGraph Python API reference
- LangGraph tutorials and examples
