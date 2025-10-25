# Anthropic Claude API Best Practices

Guide for building production-ready applications with Claude AI.

## Models

### Available Models (2025)

**Claude 3.5 Sonnet** (Recommended)
- Model: `claude-3-5-sonnet-20241022`
- Best balance of intelligence, speed, and cost
- Excellent for complex reasoning
- Context: 200K tokens
- Use for: Routing, classification, complex tasks

**Claude 3.5 Haiku** (Fast & Cheap)
- Model: `claude-3-5-haiku-20241022`
- Ultra-fast responses
- Cost-effective for high-volume
- Context: 200K tokens
- Use for: Simple tasks, high-volume generation

**Claude 3 Opus** (Most Capable)
- Model: `claude-3-opus-20240229`
- Highest intelligence
- Slower and more expensive
- Context: 200K tokens
- Use for: Critical decisions, complex analysis

### Model Selection Strategy

```python
def select_model(task_complexity: str) -> str:
    """Select appropriate model based on task."""
    if task_complexity == "simple":
        return "claude-3-5-haiku-20241022"  # Fast, cheap
    elif task_complexity == "medium":
        return "claude-3-5-sonnet-20241022"  # Balanced
    elif task_complexity == "complex":
        return "claude-3-opus-20240229"  # Most capable
```

## API Basics

### Making API Calls

```python
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)

print(response.content[0].text)
```

### Async API Calls

```python
import anthropic

client = anthropic.AsyncAnthropic(api_key="your-api-key")

response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)
```

### Response Structure

```python
{
    "id": "msg_01...",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "Response text here"
        }
    ],
    "model": "claude-3-5-sonnet-20241022",
    "stop_reason": "end_turn",
    "usage": {
        "input_tokens": 15,
        "output_tokens": 25
    }
}
```

## Prompt Engineering

### System Prompts

```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system="You are a helpful automotive sales assistant. Always be professional and concise.",
    messages=[
        {"role": "user", "content": "I'm looking for a car."}
    ]
)
```

### Conversation History

```python
messages = [
    {"role": "user", "content": "What cars do you have?"},
    {"role": "assistant", "content": "We have many options. What's your budget?"},
    {"role": "user", "content": "Around €25,000"}
]

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=messages
)
```

### Structured Output with JSON

```python
system_prompt = """You are a JSON API. Always respond with valid JSON.

Output format:
{
    "intent": "string",
    "confidence": float,
    "entities": {}
}"""

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system=system_prompt,
    messages=[
        {"role": "user", "content": "I want to buy a Golf 8 diesel"}
    ]
)

import json
result = json.loads(response.content[0].text)
```

### Few-Shot Examples

```python
system_prompt = """Classify customer intent.

Examples:
User: "I'm looking for a car" -> Intent: general_inquiry
User: "I want to test drive a Golf" -> Intent: test_drive
User: "What's your address?" -> Intent: information

Now classify the following:"""

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system=system_prompt,
    messages=[
        {"role": "user", "content": "Can I come by tomorrow?"}
    ]
)
```

## Temperature & Sampling

### Temperature Settings

```python
# Deterministic (low temperature)
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    temperature=0.0,  # Most deterministic
    messages=[{"role": "user", "content": "Extract data from: ..."}]
)

# Creative (high temperature)
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    temperature=1.0,  # Most creative
    messages=[{"role": "user", "content": "Write a creative description"}]
)
```

**Temperature Recommendations:**
- **0.0-0.3:** Data extraction, classification, JSON output
- **0.5-0.7:** Conversations, customer support (recommended)
- **0.8-1.0:** Creative writing, brainstorming

### Top-P Sampling

```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    top_p=0.9,  # Nucleus sampling
    messages=[{"role": "user", "content": "..."}]
)
```

## Token Management

### Counting Tokens (Approximate)

```python
def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 characters"""
    return len(text) // 4

# More accurate: use tokenizer
from anthropic import Anthropic
client = Anthropic()

token_count = client.count_tokens(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": text}]
)
```

### Managing Context Window

```python
def truncate_history(messages: list, max_tokens: int = 150000) -> list:
    """Keep only recent messages that fit in context."""
    total_tokens = 0
    truncated = []

    # Keep messages from newest to oldest
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg["content"])
        if total_tokens + msg_tokens > max_tokens:
            break
        truncated.insert(0, msg)
        total_tokens += msg_tokens

    return truncated
```

### Cost Calculation

```python
# Pricing (2025 estimates)
PRICING = {
    "claude-3-5-sonnet-20241022": {
        "input": 0.003 / 1000,   # $3 per million tokens
        "output": 0.015 / 1000,  # $15 per million tokens
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.0008 / 1000,  # $0.80 per million
        "output": 0.004 / 1000,  # $4 per million
    }
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate API call cost."""
    pricing = PRICING[model]
    cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
    return cost

# From response
cost = calculate_cost(
    model="claude-3-5-sonnet-20241022",
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens
)
```

## Error Handling

### Retry with Exponential Backoff

```python
import time
from anthropic import APIError, RateLimitError

async def call_claude_with_retry(
    client: anthropic.AsyncAnthropic,
    **kwargs
) -> anthropic.types.Message:
    """Call Claude API with automatic retries."""
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            return await client.messages.create(**kwargs)

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

        except APIError as e:
            logger.error(f"API error: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
```

### Handling Timeouts

```python
import asyncio

async def call_with_timeout(
    client: anthropic.AsyncAnthropic,
    timeout: int = 30,
    **kwargs
) -> anthropic.types.Message:
    """Call API with timeout."""
    try:
        return await asyncio.wait_for(
            client.messages.create(**kwargs),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("API call timed out")
        raise
```

### Graceful Degradation

```python
async def call_with_fallback(
    client: anthropic.AsyncAnthropic,
    primary_model: str,
    fallback_model: str,
    **kwargs
) -> anthropic.types.Message:
    """Try primary model, fall back to cheaper model on error."""
    try:
        return await client.messages.create(
            model=primary_model,
            **kwargs
        )
    except (APIError, RateLimitError) as e:
        logger.warning(f"Primary model failed, using fallback: {e}")
        return await client.messages.create(
            model=fallback_model,
            max_tokens=kwargs.get("max_tokens", 1024) // 2,  # Reduce tokens
            **{k: v for k, v in kwargs.items() if k != "max_tokens"}
        )
```

## Performance Optimization

### Caching (Prompt Caching)

```python
# Cache system prompt for repeated use
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "Long system prompt here...",
            "cache_control": {"type": "ephemeral"}  # Cache this
        }
    ],
    messages=[
        {"role": "user", "content": "User message"}
    ]
)

# Subsequent calls reuse cached prompt (90% cost reduction)
```

### Batch Processing

```python
async def batch_process(
    client: anthropic.AsyncAnthropic,
    messages: list[str],
    model: str = "claude-3-5-haiku-20241022"
) -> list[str]:
    """Process multiple messages in parallel."""
    tasks = [
        client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": msg}]
        )
        for msg in messages
    ]

    responses = await asyncio.gather(*tasks)
    return [r.content[0].text for r in responses]
```

### Streaming Responses

```python
async def stream_response(
    client: anthropic.AsyncAnthropic,
    **kwargs
):
    """Stream response as it's generated."""
    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            yield text  # Yield chunks as they arrive

# Usage
async for chunk in stream_response(
    client=client,
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Tell me a story"}]
):
    print(chunk, end="", flush=True)
```

## Best Practices

### 1. Use Appropriate Models

```python
# ✅ Good - use Haiku for simple tasks
def classify_intent(message: str) -> str:
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",  # Fast & cheap
        max_tokens=100,
        messages=[{"role": "user", "content": f"Classify: {message}"}]
    )
    return response.content[0].text

# ✅ Good - use Sonnet for complex tasks
def generate_response(message: str, context: str) -> str:
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",  # Better reasoning
        max_tokens=1024,
        system=context,
        messages=[{"role": "user", "content": message}]
    )
    return response.content[0].text
```

### 2. Structured Prompts

```python
# ✅ Good - clear structure
system_prompt = """You are a car sales assistant.

Your task:
1. Understand customer needs
2. Recommend suitable cars
3. Provide pricing information

Guidelines:
- Be concise
- Always ask for budget
- Mention available test drives

Output format: Plain text, 2-3 sentences max."""
```

### 3. Error Recovery

```python
# ✅ Good - handle errors gracefully
try:
    response = await client.messages.create(...)
except RateLimitError:
    # Wait and retry
    await asyncio.sleep(60)
    response = await client.messages.create(...)
except APIError as e:
    # Log and use fallback
    logger.error(f"API error: {e}")
    return fallback_response()
```

### 4. Monitor Usage

```python
# ✅ Good - track costs and tokens
def log_usage(response: anthropic.types.Message):
    """Log token usage and cost."""
    usage = response.usage
    cost = calculate_cost(
        model=response.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens
    )

    logger.info(
        "API call completed",
        extra={
            "model": response.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": cost
        }
    )
```

### 5. Async for Scalability

```python
# ✅ Good - use async client
async def process_messages(messages: list[str]):
    client = anthropic.AsyncAnthropic()

    tasks = [
        client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": msg}]
        )
        for msg in messages
    ]

    return await asyncio.gather(*tasks)
```

## Common Pitfalls

### ❌ Avoid These

```python
# ❌ Don't use Opus for simple tasks (expensive)
response = client.messages.create(
    model="claude-3-opus-20240229",  # Overkill
    messages=[{"role": "user", "content": "Hello"}]
)

# ❌ Don't ignore token limits
long_message = "..." * 100000  # Will fail
response = client.messages.create(...)

# ❌ Don't hardcode API keys
client = anthropic.Anthropic(api_key="sk-ant-...")  # Bad

# ✅ Use environment variables
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

## Testing

### Mock API Responses

```python
from unittest.mock import AsyncMock, MagicMock

# Mock response
mock_response = MagicMock()
mock_response.content = [MagicMock(text="Mocked response")]
mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)

# Mock client
mock_client = AsyncMock()
mock_client.messages.create.return_value = mock_response

# Test
response = await mock_client.messages.create(...)
assert response.content[0].text == "Mocked response"
```

## Source

Documentation compiled from:
- https://docs.anthropic.com/en/api/
- Anthropic API reference
- Claude best practices guide
- Production deployment examples
