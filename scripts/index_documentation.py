"""
Documentation Indexing Script for RAG.

This script:
1. Reads all markdown files from documents/ directory
2. Chunks documents semantically (1000 chars, 200 overlap)
3. Embeds chunks using OpenAI text-embedding-3-small
4. Stores in Supabase pgvector with metadata

Usage:
    python scripts/index_documentation.py

Environment Variables Required:
    - OPENAI_API_KEY
    - SUPABASE_URL
    - SUPABASE_KEY
"""
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import openai
from supabase import create_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DOCS_DIR = Path(__file__).parent.parent / "documents"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def chunk_markdown(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """
    Chunk markdown document semantically.

    Strategy:
    - Split by headers (##, ###) for semantic boundaries
    - Group small sections together (target ~1000 chars)
    - Add overlap between chunks

    Args:
        content: Markdown content
        file_path: Path to source file

    Returns:
        List of chunk dicts with content and metadata
    """
    chunks = []

    # Split by headers
    lines = content.split('\n')
    current_section = []
    current_header = "Introduction"

    for line in lines:
        # Detect headers
        if line.startswith('## '):
            # Save previous section
            if current_section:
                section_text = '\n'.join(current_section)
                chunks.extend(_split_long_section(section_text, current_header))

            # Start new section
            current_header = line.replace('## ', '').strip()
            current_section = [line]
        else:
            current_section.append(line)

    # Save last section
    if current_section:
        section_text = '\n'.join(current_section)
        chunks.extend(_split_long_section(section_text, current_header))

    # Add metadata
    category = file_path.parent.name
    source_file = str(file_path.relative_to(DOCS_DIR.parent))

    chunk_dicts = []
    for i, chunk_text in enumerate(chunks):
        chunk_dicts.append({
            "content": chunk_text,
            "metadata": {
                "source": source_file,
                "category": category,
                "section": current_header if i == 0 else f"{current_header} (cont.)",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "language": "en"
            }
        })

    return chunk_dicts


def _split_long_section(text: str, header: str) -> List[str]:
    """
    Split long sections into chunks with overlap.

    Args:
        text: Section text
        header: Section header

    Returns:
        List of chunk strings
    """
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        # Try to break at paragraph boundary
        if end < len(text):
            # Look for double newline (paragraph break)
            break_point = text.rfind('\n\n', start, end)
            if break_point > start:
                end = break_point

        chunk = text[start:end].strip()

        # Add header to each chunk for context
        if not chunk.startswith('#'):
            chunk = f"## {header}\n\n{chunk}"

        chunks.append(chunk)

        # Move start with overlap
        start = end - CHUNK_OVERLAP

    return chunks


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple texts using OpenAI API.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    logger.info(f"Embedding {len(texts)} texts...")

    try:
        response = await openai.embeddings.acreate(
            model=EMBEDDING_MODEL,
            input=texts
        )

        embeddings = [item.embedding for item in response.data]
        logger.info(f"✅ Embedded {len(embeddings)} texts")

        return embeddings

    except Exception as e:
        logger.error(f"❌ Embedding failed: {e}")
        raise


async def store_in_supabase(chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
    """
    Store chunks and embeddings in Supabase pgvector.

    Args:
        chunks: List of chunk dicts with content and metadata
        embeddings: List of embedding vectors
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

    supabase = create_client(supabase_url, supabase_key)

    logger.info(f"Storing {len(chunks)} chunks in Supabase...")

    # Prepare records
    records = []
    for chunk, embedding in zip(chunks, embeddings):
        records.append({
            "content": chunk["content"],
            "embedding": embedding,
            "metadata": chunk["metadata"]
        })

    # Batch insert (100 at a time)
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        try:
            response = supabase.table("documents").insert(batch).execute()
            logger.info(f"✅ Inserted batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1}")

        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            raise

    logger.info(f"✅ Stored {len(records)} chunks in Supabase")


async def index_documentation():
    """
    Main function: Index all documentation.
    """
    logger.info("🚀 Starting documentation indexing...")

    # 1. Validate environment
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be set")

    openai.api_key = os.getenv("OPENAI_API_KEY")

    # 2. Find all markdown files
    markdown_files = list(DOCS_DIR.rglob("*.md"))
    logger.info(f"📄 Found {len(markdown_files)} markdown files")

    if not markdown_files:
        logger.warning("⚠️ No markdown files found in documents/")
        return

    # 3. Process each file
    all_chunks = []

    for file_path in markdown_files:
        logger.info(f"📖 Processing: {file_path.relative_to(DOCS_DIR.parent)}")

        try:
            content = file_path.read_text(encoding='utf-8')
            chunks = chunk_markdown(content, file_path)
            all_chunks.extend(chunks)

            logger.info(f"  ✅ Created {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"  ❌ Failed to process {file_path}: {e}")
            continue

    logger.info(f"📦 Total chunks created: {len(all_chunks)}")

    # 4. Embed all chunks
    texts = [chunk["content"] for chunk in all_chunks]
    embeddings = await embed_texts(texts)

    # 5. Store in Supabase
    await store_in_supabase(all_chunks, embeddings)

    logger.info("🎉 Documentation indexing complete!")


if __name__ == "__main__":
    asyncio.run(index_documentation())
