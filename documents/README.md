# Technical Documentation for RAG

This directory contains comprehensive technical documentation for all project dependencies and patterns.

## Directory Structure

```
documents/
├── docker/
│   └── docker-compose-networking.md     # Docker Compose networking and troubleshooting
├── chatwoot/
│   ├── docker-deployment.md             # Chatwoot Docker deployment guide
│   └── api-reference.md                 # Complete Chatwoot API reference
├── waha/
│   └── api-reference.md                 # WAHA (WhatsApp API) complete reference
├── langgraph/
│   └── state-management.md              # LangGraph state management guide
├── anthropic/
│   └── claude-api-best-practices.md     # Anthropic Claude API best practices
├── rag/
│   └── agentic-rag-patterns.md          # RAG and Agentic RAG patterns
└── supabase/
    └── pgvector-guide.md                # Supabase pgvector vector search guide
```

## Documentation Coverage

### 1. **Infrastructure & Deployment**
- Docker Compose networking patterns
- Container service discovery
- Network troubleshooting
- Chatwoot deployment (Docker)
- Database setup and migrations

### 2. **API Integration**
- **Chatwoot API**: Contacts, conversations, messages, labels, webhooks
- **WAHA API**: WhatsApp message sending/receiving, sessions, webhooks
- **Anthropic Claude**: Model selection, prompting, token management, cost optimization

### 3. **AI & ML Frameworks**
- **LangGraph**: Multi-agent workflows, state management, conditional routing
- **RAG Patterns**: Retrieval-augmented generation, agentic RAG, query reformulation
- **Vector Search**: Supabase pgvector, similarity search, hybrid search

### 4. **Best Practices**
- Claude API usage (model selection, prompting, error handling)
- LangGraph state management (reducers, checkpointing, error handling)
- RAG optimization (chunking, reranking, metadata filtering)
- Vector search performance (indexing, query optimization)

## Usage

These documents are indexed by the RAG system and provide context for:

1. **Development**
   - API references for integration
   - Code examples and patterns
   - Best practices and optimization

2. **Troubleshooting**
   - Common errors and solutions
   - Performance issues
   - Network and connectivity problems

3. **Architecture**
   - Multi-agent workflow patterns
   - Vector search implementation
   - Webhook integration

## Adding New Documentation

When adding new documentation:

1. Create a new markdown file in the appropriate subdirectory
2. Include clear section headers
3. Add practical code examples
4. Include troubleshooting sections with:
   - Problem description
   - Root cause
   - Step-by-step solution
5. Add best practices section
6. Include source URL at the bottom

## Documentation Standards

### Structure
```markdown
# Title

## Overview
Brief description and use cases

## API/Feature Reference
Detailed API endpoints or feature descriptions

## Examples
Practical code examples

## Best Practices
Recommended patterns and approaches

## Troubleshooting
Common issues and solutions

## Source
Documentation source links
```

### Code Examples
- Use Python by default (primary project language)
- Include both sync and async examples where applicable
- Add comments for clarity
- Show error handling patterns

## Future Additions

Potential documentation to add:
- [ ] PostgreSQL advanced queries
- [ ] Redis caching patterns
- [ ] FastAPI best practices
- [ ] Celery task management
- [ ] Prometheus monitoring
- [ ] CI/CD deployment
- [ ] Security patterns
- [ ] Testing strategies

## RAG Integration

All documentation in this directory is automatically:
1. **Chunked** into semantic sections
2. **Embedded** using OpenAI text-embedding-3-small
3. **Stored** in Supabase pgvector database
4. **Retrieved** during agent workflows when needed

**Retrieval Triggers:**
- API integration questions
- Error troubleshooting
- Architecture decisions
- Code implementation
- Performance optimization

## Maintenance

Documentation should be:
- **Updated** when APIs change
- **Reviewed** quarterly for accuracy
- **Expanded** when new patterns emerge
- **Versioned** with source dates

Last updated: 2025-01-15
