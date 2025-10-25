# 🧪 Test Suite - WhatsApp Recruitment Platform

Complete test coverage voor alle componenten van het platform.

---

## 📋 Test Overzicht

### Test Files

1. **test_agent_1.py** - Unit tests voor Pydantic AI Extractie Agent
   - Extractie accuracy
   - Scoring systeem (100 punten)
   - Kwalificatie thresholds
   - Missing info detectie
   - Confidence scoring

2. **test_agent_2.py** - Unit tests voor Claude SDK Conversatie Agent
   - Conversatie kwaliteit
   - Tool gebruik (agentic RAG)
   - Context behoud
   - Response formatting
   - Error handling

3. **test_api.py** - Integration tests voor FastAPI endpoints
   - Webhook ontvangst
   - Lead CRUD operaties
   - Message geschiedenis
   - Authenticatie flow
   - Rate limiting

4. **test_rag.py** - RAG Accuracy tests
   - Semantic search kwaliteit
   - Embedding generatie
   - Vector similarity
   - Job search relevantie

5. **test_orchestration.py** - End-to-end orchestratie tests
   - Volledige webhook → agents → database → response flow
   - Agent 1 + Agent 2 samenwerking
   - Multi-message flows
   - Concurrent conversations

---

## 🚀 Tests Draaien

### Alle Tests

```bash
python run_tests.py
```

### Specifieke Test Suites

```bash
# Agent 1 tests
python tests/test_agent_1.py

# Agent 2 tests
python tests/test_agent_2.py

# API tests (vereist draaiende server)
python -m api.main &  # Start server
python tests/test_api.py

# RAG tests
python tests/test_rag.py

# End-to-end tests
python tests/test_orchestration.py
```

### Met Pytest

```bash
# Alle tests
pytest

# Specifieke test file
pytest tests/test_agent_1.py

# Specifieke test functie
pytest tests/test_agent_1.py::test_agent1_qualified_extraction

# Verbose output
pytest -v

# Met coverage
pytest --cov=agent --cov=api
```

---

## ⚙️ Test Configuratie

### pytest.ini

Pytest configuratie in `pytest.ini`:

```ini
[pytest]
testpaths = tests
asyncio_mode = auto

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    rag: RAG accuracy tests
    slow: Slow running tests
```

### Environment Setup

Voor tests zijn de volgende environment variables nodig:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...  # Voor Agent 2
OPENAI_API_KEY=sk-...         # Voor Agent 1 + embeddings
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...
```

---

## 📊 Test Coverage

### Huidige Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| **Agent 1** | 6 tests | ✅ Complete |
| **Agent 2** | 7 tests | ✅ Complete |
| **API** | 10 tests | ✅ Complete |
| **RAG** | 10 tests | ✅ Complete |
| **Orchestration** | 5 tests | ✅ Complete |
| **TOTAAL** | **38 tests** | ✅ Complete |

### Test Categorieën

- **Unit Tests**: 13 tests (Agent 1 + Agent 2 basis)
- **Integration Tests**: 10 tests (API endpoints)
- **RAG Tests**: 10 tests (Semantic search)
- **E2E Tests**: 5 tests (Volledige flow)

---

## 🎯 Test Strategieën

### 1. Unit Tests

Testen individuele componenten in isolatie:

```python
@pytest.mark.asyncio
async def test_agent1_qualified_extraction():
    agent = Agent1PydanticAI()
    result = await agent.extract_qualification(QUALIFIED_CONVERSATION)

    assert result.overall_score >= 70
    assert result.qualification_status == "qualified"
```

### 2. Integration Tests

Testen samenwerkende componenten:

```python
@pytest.mark.asyncio
async def test_webhook_message_processing():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/webhook/whatsapp",
            json=payload
        )
        assert response.status_code == 200
```

### 3. End-to-End Tests

Testen complete gebruikersflows:

```python
@pytest.mark.asyncio
async def test_full_conversation_flow():
    # Simuleer volledige conversatie
    for message in messages:
        # Send webhook
        # Check response
        # Verify database state

    # Check qualification after 5 messages
```

---

## 🔍 Test Data

### Mock Conversaties

**Qualified Candidate (Score ≥70)**:
```python
QUALIFIED_CONVERSATION = [
    "Hoi! Ik ben Sarah",
    "Ik heb 8 jaar ervaring als kapper",
    "Ik kan knippen, kleuren, balayage en highlights",
    "Ik werk fulltime, 40 uur per week",
    "Ik ben klantgericht en teamgericht"
]
```

**Disqualified Candidate (Score <30)**:
```python
DISQUALIFIED_CONVERSATION = [
    "Hoi, ik ben Jan",
    "Ik heb geen ervaring maar wil graag leren"
]
```

**Pending Review (30 ≤ Score < 70)**:
```python
PENDING_CONVERSATION = [
    "Hoi, ik ben Lisa",
    "2 jaar ervaring in een klein salon"
]
```

---

## 🐛 Debugging

### Test Failures

Als tests falen:

1. **Check environment variables**:
   ```bash
   cat .env | grep -E "ANTHROPIC|OPENAI|SUPABASE"
   ```

2. **Check API server**:
   ```bash
   curl http://localhost:8000/
   ```

3. **Check database**:
   ```bash
   # Check Supabase connection
   python -c "from agent.tools import get_supabase_client; print(get_supabase_client())"
   ```

4. **Verbose output**:
   ```bash
   pytest -vv --tb=long tests/test_agent_1.py
   ```

### Common Issues

**Issue**: `ANTHROPIC_API_KEY not found`
- **Fix**: Voeg key toe aan `.env` file

**Issue**: `API server not available`
- **Fix**: Start server met `python -m api.main`

**Issue**: `Supabase connection failed`
- **Fix**: Check SUPABASE_URL en SUPABASE_SERVICE_KEY

**Issue**: `Test timeout`
- **Fix**: Verhoog timeout of check netwerk connectie

---

## 📈 Continuous Integration

### GitHub Actions (optioneel)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest
```

---

## ✅ Checklist voor Nieuwe Tests

Wanneer je een nieuwe test toevoegt:

- [ ] Test file in `tests/` directory
- [ ] Test naam begint met `test_`
- [ ] Async tests gebruiken `@pytest.mark.asyncio`
- [ ] Duidelijke docstring met wat wordt getest
- [ ] Assert statements met duidelijke failure messages
- [ ] Clean up na test (indien nodig)
- [ ] Voeg toe aan `run_tests.py` (indien E2E test)
- [ ] Update deze README met test beschrijving

---

## 🎓 Best Practices

1. **Keep tests isolated**: Elke test moet onafhankelijk kunnen draaien
2. **Use descriptive names**: `test_agent1_qualified_extraction` > `test_1`
3. **Test one thing**: Één test = één aspect
4. **Use fixtures**: Voor herbruikbare test data
5. **Mock external services**: Geen echte WhatsApp berichten in tests
6. **Fast tests**: Unit tests < 1s, integration tests < 5s
7. **Clear assertions**: `assert result.score >= 70, f"Expected ≥70, got {result.score}"`

---

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pydantic Testing](https://docs.pydantic.dev/latest/concepts/testing/)

---

**Laatste Update**: Fase 8 (Testing) - Complete test suite aangemaakt ✅
