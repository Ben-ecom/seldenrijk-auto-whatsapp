"""
RAG Embeddings: Generate and store vector embeddings for semantic search

This module handles:
- Generating embeddings for job postings and company docs
- Chunking content for optimal RAG performance
- Storing embeddings in PGVector
- Batch processing for efficiency
"""

import os
from typing import Any
from openai import OpenAI, AsyncOpenAI
from supabase import create_client, Client


# ============ CONSTANTS ============
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE = 800  # Characters per chunk
CHUNK_OVERLAP = 100  # Overlap for context continuity


# ============ CLIENTS ============

def get_openai_client() -> OpenAI:
    """Get synchronous OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def get_async_openai_client() -> AsyncOpenAI:
    """Get asynchronous OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return AsyncOpenAI(api_key=api_key)


def get_supabase_client() -> Client:
    """Get Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

    return create_client(url, key)


# ============ TEXT CHUNKING ============

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for better semantic search.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks for context continuity

    Returns:
        List of text chunks

    Example:
        >>> text = "This is a long job description..." * 100
        >>> chunks = chunk_text(text, chunk_size=500, overlap=50)
        >>> len(chunks)
        15
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            for i in range(min(100, chunk_size // 4)):
                if end - i > start and text[end - i:end - i + 1] in '.!?\n':
                    end = end - i + 1
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks


# ============ JOB POSTINGS EMBEDDINGS ============

async def generate_job_posting_embeddings(
    job_id: str,
    title: str,
    description: str,
    requirements: str,
    benefits: str | None = None
) -> list[dict[str, Any]]:
    """
    Generate embeddings for a job posting.

    Creates separate chunks for title, description, requirements, and benefits
    to enable fine-grained semantic search.

    Args:
        job_id: UUID of job posting
        title: Job title
        description: Job description
        requirements: Job requirements
        benefits: Job benefits (optional)

    Returns:
        List of embedding records ready for database insertion

    Example:
        >>> embeddings = await generate_job_posting_embeddings(
        ...     job_id="123",
        ...     title="Senior Hairstylist",
        ...     description="We are looking for...",
        ...     requirements="5 years experience..."
        ... )
        >>> len(embeddings)
        4
    """
    client = get_async_openai_client()
    supabase = get_supabase_client()

    # Prepare chunks with metadata
    chunks_to_embed = [
        {"type": "title", "text": title, "index": 0},
    ]

    # Chunk description
    desc_chunks = chunk_text(description)
    for idx, chunk in enumerate(desc_chunks):
        chunks_to_embed.append({"type": "description", "text": chunk, "index": idx})

    # Chunk requirements
    req_chunks = chunk_text(requirements)
    for idx, chunk in enumerate(req_chunks):
        chunks_to_embed.append({"type": "requirements", "text": chunk, "index": idx})

    # Chunk benefits if provided
    if benefits:
        ben_chunks = chunk_text(benefits)
        for idx, chunk in enumerate(ben_chunks):
            chunks_to_embed.append({"type": "benefits", "text": chunk, "index": idx})

    # Generate embeddings in batch
    texts = [chunk["text"] for chunk in chunks_to_embed]
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )

    # Prepare database records
    embedding_records = []
    for chunk, embedding_data in zip(chunks_to_embed, response.data):
        embedding_records.append({
            "job_posting_id": job_id,
            "chunk_text": chunk["text"],
            "chunk_type": chunk["type"],
            "chunk_index": chunk["index"],
            "embedding": embedding_data.embedding
        })

    # Insert into database
    supabase.table("job_embeddings").insert(embedding_records).execute()

    print(f"✅ Generated {len(embedding_records)} embeddings for job {job_id}")
    return embedding_records


# ============ COMPANY DOCS EMBEDDINGS ============

async def generate_company_doc_embeddings(
    doc_id: str,
    title: str,
    content: str
) -> list[dict[str, Any]]:
    """
    Generate embeddings for a company document.

    Args:
        doc_id: UUID of company doc
        title: Document title
        content: Document content

    Returns:
        List of embedding records

    Example:
        >>> embeddings = await generate_company_doc_embeddings(
        ...     doc_id="456",
        ...     title="Sollicitatieprocedure",
        ...     content="Onze procedure bestaat uit..."
        ... )
    """
    client = get_async_openai_client()
    supabase = get_supabase_client()

    # Include title in first chunk for context
    full_text = f"{title}\n\n{content}"
    chunks = chunk_text(full_text)

    # Generate embeddings
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=chunks
    )

    # Prepare records
    embedding_records = []
    for idx, (chunk, embedding_data) in enumerate(zip(chunks, response.data)):
        embedding_records.append({
            "doc_id": doc_id,
            "chunk_text": chunk,
            "chunk_index": idx,
            "embedding": embedding_data.embedding
        })

    # Insert into database
    supabase.table("company_doc_embeddings").insert(embedding_records).execute()

    print(f"✅ Generated {len(embedding_records)} embeddings for doc {doc_id}")
    return embedding_records


# ============ BATCH PROCESSING ============

async def process_all_jobs() -> int:
    """
    Process all job postings and generate embeddings.

    Returns:
        Number of jobs processed
    """
    supabase = get_supabase_client()

    # Fetch all active jobs without embeddings
    jobs = supabase.table("job_postings").select("*").eq("is_active", True).execute()

    total_processed = 0

    for job in jobs.data:
        # Check if embeddings already exist
        existing = supabase.table("job_embeddings").select("id").eq("job_posting_id", job["id"]).execute()

        if existing.data:
            print(f"⏭️  Skipping job {job['id']} (embeddings exist)")
            continue

        # Generate embeddings
        await generate_job_posting_embeddings(
            job_id=job["id"],
            title=job["title"],
            description=job["description"],
            requirements=job["requirements"],
            benefits=job.get("benefits")
        )
        total_processed += 1

    print(f"\n✅ Processed {total_processed} jobs")
    return total_processed


async def process_all_docs() -> int:
    """
    Process all company docs and generate embeddings.

    Returns:
        Number of docs processed
    """
    supabase = get_supabase_client()

    # Fetch all active docs without embeddings
    docs = supabase.table("company_docs").select("*").eq("is_active", True).execute()

    total_processed = 0

    for doc in docs.data:
        # Check if embeddings already exist
        existing = supabase.table("company_doc_embeddings").select("id").eq("doc_id", doc["id"]).execute()

        if existing.data:
            print(f"⏭️  Skipping doc {doc['id']} (embeddings exist)")
            continue

        # Generate embeddings
        await generate_company_doc_embeddings(
            doc_id=doc["id"],
            title=doc["title"],
            content=doc["content"]
        )
        total_processed += 1

    print(f"\n✅ Processed {total_processed} docs")
    return total_processed


# ============ UTILITY: SEED SAMPLE DATA ============

async def seed_sample_data():
    """
    Seed database with sample job postings and company docs for testing.
    """
    supabase = get_supabase_client()

    # Sample job postings
    sample_jobs = [
        {
            "title": "Senior Hairstylist - Amsterdam Centrum",
            "location": "Amsterdam",
            "job_type": "fulltime",
            "salary_range": "€2500-€3500/maand",
            "description": """
We zoeken een ervaren kapper met passie voor klantcontact en moderne technieken.
Je werkt in ons salon in Amsterdam centrum, waar je dagelijks klanten helpt met
knippen, kleuren en stylen. We hebben een jong, dynamisch team en werken met
premium producten zoals Redken en L'Oréal Professionnel.

Als Senior Hairstylist ben je verantwoordelijk voor:
- Knippen en stylen volgens de laatste trends
- Kleuren, highlights en balayage
- Adviseren van klanten over haar en producten
- Begeleiden van junior stylisten
- Bijdragen aan een positieve werksfeer
            """,
            "requirements": """
Wat we zoeken:
- Minimaal 5 jaar ervaring als kapper
- Diploma kappersopleiding (MBO niveau 3 of hoger)
- Uitstekende klantvaardigheden
- Kennis van moderne kleurtechnieken (balayage, ombre, etc.)
- Creatief en trendbewust
- Teamplayer met een positieve instelling
- Flexibel in werktijden (inclusief zaterdagen)
            """,
            "benefits": """
Wat we bieden:
- Goed salaris (€2500-€3500 afhankelijk van ervaring)
- 25 vakantiedagen per jaar
- Doorgroeimogelijkheden naar Salon Manager
- Opleidingsbudget voor vakinhoudelijke cursussen
- Pensioenregeling
- Werkkleding en eigen schaar/tools
- Gezellig team met regelmatige teamuitjes
            """
        },
        {
            "title": "Junior Kapper - Rotterdam",
            "location": "Rotterdam",
            "job_type": "fulltime",
            "salary_range": "€1800-€2200/maand",
            "description": """
Ben je net afgestudeerd of heb je 1-2 jaar ervaring? Dan is deze functie perfect!
We bieden je de kans om je verder te ontwikkelen in een professioneel salon.
Je werkt onder begeleiding van onze senior stylisten en krijgt veel ruimte om
te leren en te groeien.
            """,
            "requirements": """
- MBO diploma kappersopleiding
- 0-2 jaar werkervaring
- Leergierig en enthousiast
- Goede basisvaardigheden (knippen, wassen, föhnen)
- Klantgericht en communicatief vaardig
            """,
            "benefits": """
- Startsalaris €1800-€2200
- Veel leermogelijkheden en begeleiding
- Doorgroeiperspectief naar Stylist functie
- 8% vakantiegeld
- Reiskostenvergoeding
            """
        },
        {
            "title": "Parttime Kapper - Utrecht (24 uur)",
            "location": "Utrecht",
            "job_type": "parttime",
            "salary_range": "€15-€18/uur",
            "description": """
Zoek je een leuke parttime baan als kapper? Wij zoeken iemand voor 3 dagen per week
(24 uur) in ons salon in Utrecht. Ideaal als je flexibiliteit zoekt of andere
bezigheden hebt.
            """,
            "requirements": """
- 3+ jaar ervaring
- Beschikbaar voor 3 dagen per week (flexibel in te plannen)
- Zelfstandig kunnen werken
- Ervaring met kleuren en knippen
            """,
            "benefits": """
- €15-€18 per uur
- Flexibele planning in overleg
- Gezellig team
- Kortingen op producten
            """
        }
    ]

    # Insert jobs and generate embeddings
    for job_data in sample_jobs:
        # Insert job
        result = supabase.table("job_postings").insert(job_data).execute()
        job_id = result.data[0]["id"]

        # Generate embeddings
        await generate_job_posting_embeddings(
            job_id=job_id,
            title=job_data["title"],
            description=job_data["description"],
            requirements=job_data["requirements"],
            benefits=job_data.get("benefits")
        )

    # Sample company docs
    sample_docs = [
        {
            "title": "Sollicitatieprocedure",
            "doc_type": "process",
            "content": """
Onze sollicitatieprocedure bestaat uit 3 stappen:

1. WhatsApp screening (5-10 minuten)
   - Je krijgt eerst een WhatsApp bericht van onze recruitment assistent
   - We stellen enkele vragen over je ervaring en beschikbaarheid
   - Dit duurt ongeveer 5-10 minuten

2. Video kennismaking (30 minuten)
   - Als de screening positief is, plannen we een video gesprek
   - Je spreekt met de salon manager
   - We bespreken je ervaring, motivatie en verwachtingen
   - Je kunt vragen stellen over het werk en het team

3. Proefdag in het salon (4 uur)
   - Als het video gesprek goed verloopt, nodigenwij je uit voor een proefdag
   - Je werkt een halve dag mee in het salon
   - Je ontmoet het team en krijgt een gevoel voor de werksfeer
   - We kijken samen of er een goede match is

De hele procedure duurt ongeveer 1-2 weken. We streven ernaar om binnen
3 werkdagen na elke stap contact met je op te nemen.
            """
        },
        {
            "title": "Salaris en Arbeidsvoorwaarden",
            "doc_type": "benefits",
            "content": """
Salaris:
- Junior Kapper: €1800-€2200 bruto per maand (fulltime)
- Stylist: €2200-€2800 bruto per maand
- Senior Stylist: €2500-€3500 bruto per maand
- Salon Manager: €3200-€4000 bruto per maand

Alle salarissen zijn afhankelijk van ervaring en worden jaarlijks geëvalueerd.

Arbeidsvoorwaarden:
- 25 vakantiedagen per jaar (bij fulltime)
- 8% vakantiegeld
- Pensioenregeling via bedrijfspensioenfonds
- Reiskostenvergoeding (€0.23 per km)
- Korting op haarproducten (40%)
- Gratis knip- en kleurbeurt bij collega's
- Opleidingsbudget (€500 per jaar)
- Werkkleding en tools verstrekt door bedrijf
- Teamuitjes (2x per jaar)
- Kerstpakket

Werktijden:
- Fulltime = 40 uur per week
- Parttime = 24-32 uur per week (in overleg)
- Rooster 4 weken van tevoren bekend
- Flexibiliteit wordt gewaardeerd, maar niet vereist voor alle posities
- Zaterdag werken is onderdeel van het rooster (roulatie)
            """
        },
        {
            "title": "Bedrijfscultuur en Werksfeer",
            "doc_type": "culture",
            "content": """
Onze bedrijfscultuur:

Wij geloven in:
- Klantgerichtheid: De klant staat altijd centraal
- Professionaliteit: We werken volgens de laatste standaarden
- Teamwork: We helpen elkaar en delen kennis
- Ontwikkeling: Iedereen krijgt ruimte om te groeien
- Plezier: Werk moet leuk zijn!

Ons team:
- Mix van junior en senior stylisten
- Leeftijd varieert van 21 tot 45 jaar
- Informele, gezellige sfeer
- Open communicatie
- Wekelijkse teamoverleg
- Maandelijkse borrels

Ontwikkeling:
- Minimaal 2 vakinhoudelijke trainingen per jaar
- Interne workshops door senior stylisten
- Budget voor externe cursussen
- Mogelijkheid tot specialisatie (kleuren, extensions, bruidskapsel)
- Doorgroeien naar salon manager mogelijk

Wat we van je verwachten:
- Passie voor het vak
- Klantgericht en communicatief
- Teamplayer
- Flexibel in denken en werken
- Bereidheid om te leren en je te ontwikkelen
            """
        }
    ]

    # Insert docs and generate embeddings
    for doc_data in sample_docs:
        # Insert doc
        result = supabase.table("company_docs").insert(doc_data).execute()
        doc_id = result.data[0]["id"]

        # Generate embeddings
        await generate_company_doc_embeddings(
            doc_id=doc_id,
            title=doc_data["title"],
            content=doc_data["content"]
        )

    print("\n✅ Sample data seeded successfully!")


# ============ CLI ============

if __name__ == "__main__":
    """
    CLI for embedding generation.

    Usage:
        python -m agent.embeddings seed        # Seed sample data
        python -m agent.embeddings jobs        # Process all jobs
        python -m agent.embeddings docs        # Process all docs
        python -m agent.embeddings all         # Process everything
    """
    import sys
    import asyncio

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python -m agent.embeddings [seed|jobs|docs|all]")
            return

        command = sys.argv[1]

        if command == "seed":
            await seed_sample_data()
        elif command == "jobs":
            await process_all_jobs()
        elif command == "docs":
            await process_all_docs()
        elif command == "all":
            await process_all_jobs()
            await process_all_docs()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python -m agent.embeddings [seed|jobs|docs|all]")

    asyncio.run(main())
