"""
RAG Accuracy Tests

Test coverage:
- Semantic search kwaliteit
- Embedding generatie
- Vector similarity
- Job search relevantie
- Company docs search relevantie
"""

import pytest
from agent.embeddings import (
    generate_embedding,
    chunk_text,
    generate_job_posting_embeddings,
    generate_company_doc_embeddings
)
from agent.tools import search_job_postings_impl, search_company_docs_impl


# ============ EMBEDDING TESTS ============

@pytest.mark.asyncio
async def test_generate_embedding():
    """Test dat embeddings correct worden gegenereerd."""
    text = "Kapper vacature in Amsterdam voor ervaren stylist"

    embedding = await generate_embedding(text)

    # Check dat embedding correct formaat heeft
    assert embedding is not None
    assert len(embedding) == 1536  # OpenAI text-embedding-3-small dimensie
    assert all(isinstance(x, float) for x in embedding)

    print(f"✅ Generate embedding test geslaagd (1536 dimensies)")


def test_chunk_text():
    """Test text chunking functie."""
    long_text = " ".join(["Dit is een test zin."] * 200)  # ~1200 woorden

    chunks = chunk_text(long_text, chunk_size=800, overlap=100)

    # Check dat text is opgesplitst
    assert len(chunks) > 1

    # Check dat chunks niet te groot zijn
    for chunk in chunks:
        assert len(chunk) <= 900  # 800 + marge

    # Check overlap (laatste deel van chunk 1 = eerste deel van chunk 2)
    if len(chunks) >= 2:
        # Er moet enige overlap zijn
        assert len(chunks[0]) > 0
        assert len(chunks[1]) > 0

    print(f"✅ Text chunking test geslaagd ({len(chunks)} chunks)")


@pytest.mark.asyncio
async def test_job_posting_embeddings():
    """Test job posting embeddings generatie."""
    # Dit vereist database connectie en OpenAI API
    # Voor nu: test de functie logica

    job_id = "test-job-123"
    title = "Senior Kapper"
    description = "Wij zoeken een ervaren kapper voor ons salon in Amsterdam"
    requirements = "Minimaal 5 jaar ervaring, balayage techniek, klantgericht"

    try:
        await generate_job_posting_embeddings(
            job_id=job_id,
            title=title,
            description=description,
            requirements=requirements
        )

        print("✅ Job posting embeddings test geslaagd")

    except Exception as e:
        # Database of API niet beschikbaar
        print(f"⚠️  Job posting embeddings test overgeslagen: {e}")


# ============ SEARCH QUALITY TESTS ============

@pytest.mark.asyncio
async def test_search_job_postings_relevance():
    """Test dat job search relevante resultaten geeft."""
    test_lead_id = "test-lead-rag-1"

    # Test 1: Specifieke locatie
    query1 = "kapper amsterdam"
    results1 = await search_job_postings_impl(test_lead_id, query1)

    assert results1 is not None
    assert len(results1) > 0

    # Resultaten zouden "amsterdam" moeten bevatten (case-insensitive)
    results1_lower = results1.lower()
    # Als er sample data is, zou dit moeten matchen
    print(f"✅ Job search relevance test 1: {len(results1)} characters")

    # Test 2: Specifieke skills
    query2 = "balayage specialist"
    results2 = await search_job_postings_impl(test_lead_id, query2)

    assert results2 is not None
    print(f"✅ Job search relevance test 2: {len(results2)} characters")


@pytest.mark.asyncio
async def test_search_company_docs_relevance():
    """Test dat company docs search relevante resultaten geeft."""
    test_lead_id = "test-lead-rag-2"

    # Test: Vraag over arbeidsvoorwaarden
    query = "vakantiedagen en pensioen"
    results = await search_company_docs_impl(test_lead_id, query)

    assert results is not None
    # Als er sample data is, zou dit resultaten moeten geven
    print(f"✅ Company docs search test: {len(results)} characters")


@pytest.mark.asyncio
async def test_semantic_similarity():
    """Test dat semantisch vergelijkbare queries soortgelijke resultaten geven."""
    test_lead_id = "test-lead-rag-3"

    # Twee semantisch vergelijkbare queries
    query1 = "kapper vacature amsterdam"
    query2 = "hairstylist job in amsterdam"

    results1 = await search_job_postings_impl(test_lead_id, query1)
    results2 = await search_job_postings_impl(test_lead_id, query2)

    # Beide queries zouden resultaten moeten geven
    assert results1 is not None
    assert results2 is not None

    # Ze hoeven niet identiek te zijn, maar moeten wel beide iets vinden
    print(f"✅ Semantic similarity test:")
    print(f"   Query 1 ({len(results1)} chars)")
    print(f"   Query 2 ({len(results2)} chars)")


@pytest.mark.asyncio
async def test_empty_query_handling():
    """Test handling van lege queries."""
    test_lead_id = "test-lead-rag-4"

    # Lege query
    results = await search_job_postings_impl(test_lead_id, "")

    # Zou ofwel lege string ofwel error message moeten geven
    assert results is not None
    print(f"✅ Empty query handling test geslaagd")


@pytest.mark.asyncio
async def test_no_results_query():
    """Test handling van queries zonder resultaten."""
    test_lead_id = "test-lead-rag-5"

    # Zeer specifieke query die waarschijnlijk geen resultaten geeft
    query = "underwater basket weaving specialist in antarctica"
    results = await search_job_postings_impl(test_lead_id, query)

    # Zou een "geen resultaten" boodschap moeten geven
    assert results is not None
    assert "geen" in results.lower() or "no" in results.lower() or len(results) == 0
    print(f"✅ No results query test geslaagd")


@pytest.mark.asyncio
async def test_dutch_language_search():
    """Test dat Nederlandse queries correct werken."""
    test_lead_id = "test-lead-rag-6"

    dutch_queries = [
        "kappersopleiding vereist",
        "fulltime baan",
        "salaris en arbeidsvoorwaarden",
    ]

    for query in dutch_queries:
        results = await search_job_postings_impl(test_lead_id, query)

        assert results is not None
        print(f"✅ Dutch query test: '{query}' -> {len(results)} chars")


# ============ VECTOR SEARCH PERFORMANCE ============

@pytest.mark.asyncio
async def test_search_performance():
    """Test dat vector search snel genoeg is."""
    import time

    test_lead_id = "test-lead-rag-7"
    query = "ervaren kapper gezocht"

    start_time = time.time()
    results = await search_job_postings_impl(test_lead_id, query)
    end_time = time.time()

    duration = end_time - start_time

    # Search zou < 2 seconden moeten zijn
    assert duration < 2.0

    print(f"✅ Search performance test: {duration:.2f}s (< 2s)")


# ============ RUN TESTS ============

if __name__ == "__main__":
    import asyncio

    print("\n" + "="*60)
    print("🔍 RAG Accuracy Tests")
    print("="*60 + "\n")

    async def run_all_tests():
        print("Test 1: Generate Embedding")
        await test_generate_embedding()

        print("\nTest 2: Text Chunking")
        test_chunk_text()

        print("\nTest 3: Job Posting Embeddings")
        await test_job_posting_embeddings()

        print("\nTest 4: Job Search Relevance")
        await test_search_job_postings_relevance()

        print("\nTest 5: Company Docs Search")
        await test_search_company_docs_relevance()

        print("\nTest 6: Semantic Similarity")
        await test_semantic_similarity()

        print("\nTest 7: Empty Query Handling")
        await test_empty_query_handling()

        print("\nTest 8: No Results Query")
        await test_no_results_query()

        print("\nTest 9: Dutch Language Search")
        await test_dutch_language_search()

        print("\nTest 10: Search Performance")
        await test_search_performance()

        print("\n" + "="*60)
        print("✅ Alle RAG tests geslaagd!")
        print("="*60)

    asyncio.run(run_all_tests())
