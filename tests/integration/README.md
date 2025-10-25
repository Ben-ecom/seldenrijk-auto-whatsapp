# Integration Tests

## Requirements

Integration tests require a **local Supabase instance** running on `localhost:54321`.

### Setup Local Supabase

1. Install Supabase CLI:
   ```bash
   npm install -g supabase
   ```

2. Start local Supabase (with pgvector extension):
   ```bash
   supabase start
   ```

3. Run integration tests:
   ```bash
   pytest tests/integration -m integration
   ```

## Skip Integration Tests

To run only unit tests (for CI/CD or quick testing):

```bash
pytest tests/unit -m "not integration"
```

Or explicitly skip integration tests:

```bash
pytest -m "not integration"
```

## Production Supabase

Production Supabase instance is configured via environment variables:
- `SUPABASE_URL`: https://wnzozivtrrlsphsmkavl.supabase.co
- `SUPABASE_KEY`: Service role key

Integration tests use the **VectorStore** service which currently connects to localhost:54321 by default for testing purposes.
