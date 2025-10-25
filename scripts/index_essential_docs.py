"""
FAST Essential Documentation Indexing - Only Critical Docs.

Indexes only the most important docs for WhatsApp platform:
- Chatwoot API (contact/conversation management)
- WAHA API (WhatsApp message sending)

This is ~10x faster than indexing all docs.

Usage:
    python scripts/index_essential_docs.py
"""
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import hashlib
import re
import math
from supabase import create_client
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DOCS_DIR = Path(__file__).parent.parent / "documents"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_DIMENSIONS = 1536

# ALL DOCUMENTATION FILES
ESSENTIAL_DOCS = [
    "chatwoot/api-reference.md",
    "waha/api-reference.md",
    "README.md",
    "langgraph/state-management.md",
    "docker/docker-compose-networking.md",
    "chatwoot/docker-deployment.md",
    "rag/agentic-rag-patterns.md",
    "supabase/pgvector-guide.md",
    "waha/docker-setup.md",
]


def create_simple_embedding(text: str) -> List[float]:
    """Create simple deterministic embedding."""
    text = text.lower()
    words = re.findall(r'\w+', text)
    embedding = [0.0] * EMBEDDING_DIMENSIONS

    # Word frequency
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    for word, freq in word_freq.items():
        word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = word_hash % 768
        embedding[idx] += math.log(1 + freq)

    # Position component
    for i, word in enumerate(words[:384]):
        word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = 768 + (word_hash % 384)
        position_weight = 1.0 / (1 + i * 0.01)
        embedding[idx] += position_weight

    # Character n-grams
    char_ngrams = [text[i:i+3] for i in range(len(text)-2)]
    ngram_freq = {}
    for ngram in char_ngrams:
        ngram_freq[ngram] = ngram_freq.get(ngram, 0) + 1

    for ngram, freq in list(ngram_freq.items())[:384]:
        ngram_hash = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
        idx = 1152 + (ngram_hash % 384)
        embedding[idx] += math.log(1 + freq)

    # Normalize
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


def chunk_markdown(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """Chunk markdown document semantically."""
    chunks = []
    lines = content.split('\n')
    current_section = []
    current_header = "Introduction"

    for line in lines:
        if line.startswith('## '):
            if current_section:
                section_text = '\n'.join(current_section)
                chunks.extend(_split_long_section(section_text, current_header))

            current_header = line.replace('## ', '').strip()
            current_section = [line]
        else:
            current_section.append(line)

    if current_section:
        section_text = '\n'.join(current_section)
        chunks.extend(_split_long_section(section_text, current_header))

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
    """Split long sections with overlap."""
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        if end < len(text):
            break_point = text.rfind('\n\n', start, end)
            if break_point > start:
                end = break_point

        chunk = text[start:end].strip()

        if not chunk.startswith('#'):
            chunk = f"## {header}\n\n{chunk}"

        chunks.append(chunk)
        start = end - CHUNK_OVERLAP

    return chunks


async def store_in_supabase(chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
    """Store chunks in Supabase."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

    supabase = create_client(supabase_url, supabase_key)

    logger.info(f"Storing {len(chunks)} chunks in Supabase...")

    records = []
    for chunk, embedding in zip(chunks, embeddings):
        records.append({
            "content": chunk["content"],
            "embedding": embedding,
            "metadata": chunk["metadata"]
        })

    # Insert in smaller batches for speed
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        try:
            response = supabase.table("documents").insert(batch).execute()
            logger.info(f"✅ Batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1} inserted")

        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            raise

    logger.info(f"✅ Stored {len(records)} chunks")


async def index_essential_docs():
    """Index only essential documentation."""
    logger.info("🚀 Fast indexing - ESSENTIAL DOCS ONLY")
    logger.info(f"📋 Indexing: {', '.join(ESSENTIAL_DOCS)}")

    all_chunks = []

    for doc_path in ESSENTIAL_DOCS:
        file_path = DOCS_DIR.parent / "documents" / doc_path

        if not file_path.exists():
            logger.warning(f"⚠️ File not found: {doc_path}")
            continue

        logger.info(f"📖 Processing: {doc_path}")

        try:
            content = file_path.read_text(encoding='utf-8')
            chunks = chunk_markdown(content, file_path)
            all_chunks.extend(chunks)

            logger.info(f"  ✅ Created {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")
            continue

    logger.info(f"📦 Total chunks: {len(all_chunks)}")

    # Create embeddings (show progress every 5 chunks)
    logger.info("🔢 Creating embeddings...")
    embeddings = []

    for i, chunk in enumerate(all_chunks):
        if i % 5 == 0:
            logger.info(f"  Progress: {i}/{len(all_chunks)}")

        embedding = create_simple_embedding(chunk["content"])
        embeddings.append(embedding)

    logger.info(f"✅ Created {len(embeddings)} embeddings")

    # Store in Supabase
    await store_in_supabase(all_chunks, embeddings)

    logger.info("🎉 Essential docs indexed!")
    logger.info("💡 You can now test RAG with Chatwoot & WAHA documentation")


if __name__ == "__main__":
    asyncio.run(index_essential_docs())
