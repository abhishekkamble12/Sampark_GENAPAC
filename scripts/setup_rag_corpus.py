"""
scripts/setup_rag_corpus.py — One-time setup for Vertex AI RAG Engine.

Creates a RAG corpus for municipal policy documents, configures embeddings
with text-embedding-005, and optionally imports sample PDF documents.

Usage:
    python scripts/setup_rag_corpus.py                          # Create corpus
    python scripts/setup_rag_corpus.py --import-samples         # Create + import samples
    python scripts/setup_rag_corpus.py --corpus-id CORPUS_ID    # Use existing corpus

Prerequisites:
    - Google Cloud project with Vertex AI API enabled
    - Application Default Credentials configured (gcloud auth application-default login)
    - Cloud Storage bucket with policy PDFs (for --import-samples)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# ── Path setup ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("setup_rag")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "sampark-demo")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
BUCKET_NAME = os.getenv("RAG_DOCUMENTS_BUCKET", "sampark-policy-documents")
CORPUS_DISPLAY_NAME = "sampark_municipal_policies"

# Sample policy documents to seed (if --import-samples is used)
SAMPLE_POLICIES = {
    "road_repair_policy.md": """# Road Repair Policy - Municipal Corporation

## Scope
This policy covers all road repair and maintenance activities within municipal limits.

## Response Times
- Potholes > 6 inches deep: 48 hours (Critical)
- Surface cracks: 7 days (Standard)
- Major road damage (> 10 sq ft): 24 hours (Emergency)

## Procedure
1. Citizen report received → logged in system
2. Road inspector dispatched within 4 hours
3. Damage assessment completed within 24 hours
4. Repair crew assigned based on severity
5. Quality check within 7 days of completion

## Budget Allocation
- Annual road repair budget: ₹2.5 crores per ward
- Emergency fund: ₹50 lakhs per ward
""",
    "flood_management_policy.md": """# Flood Management & Drainage Policy

## Scope
Management of flood risks, drainage systems, and waterlogging in municipal areas.

## Risk Categories
- Low Risk: < 50mm rainfall forecast, no historical flooding
- Medium Risk: 50-100mm rainfall, minor historical flooding
- High Risk: > 100mm rainfall, history of severe flooding
- Critical: Cyclone warning + > 150mm rainfall

## Response Protocol
1. High Risk: Pre-deploy pumps and sandbags within 2 hours
2. Critical: Evacuation orders, emergency shelters opened
3. All wards to clear drainage channels within 24 hours of alert

## Infrastructure Requirements
- Ward 1: 3 pumps (capacity: 500 L/min each)
- Ward 2: 2 pumps (capacity: 300 L/min each)
- Ward 3: 1 pump + natural drainage channels
""",
    "water_supply_policy.md": """# Water Supply & Leakage Policy

## Scope
Management of water supply infrastructure, leak detection, and repair.

## Leak Categories
- Category 1 (Minor): Drip leaks → repaired within 7 days
- Category 2 (Medium): Visible flow → repaired within 48 hours
- Category 3 (Major): Pipe burst → emergency response within 2 hours

## Water Conservation
- All reported leaks must be logged
- Ward-level monthly water audit required
- Public awareness campaigns quarterly

## Fines & Penalties
- Unauthorized connections: ₹5,000 fine
- Wastage of drinking water: ₹2,000 fine
""",
    "sanitation_policy.md": """# Sanitation & Waste Management Policy

## Scope
Covers garbage collection, sewage management, and public sanitation.

## Collection Schedule
- Ward 1: Daily collection (7 AM - 10 AM)
- Ward 2: Alternate day collection
- Ward 3: Weekly collection (Wednesday)

## Sewage Overflow Response
- Blockage: Clear within 4 hours
- Overflow: Emergency crew dispatched within 1 hour
- Major line break: 24-hour continuous work

## Penalties
- Illegal dumping: ₹2,000 fine
- Not segregating waste: Warning (1st), ₹500 (2nd)
""",
}


def create_corpus(args: argparse.Namespace) -> str:
    """Create or retrieve a Vertex AI RAG corpus."""
    from vertexai import rag
    import vertexai

    vertexai.init(project=args.project_id, location=args.location)

    # If corpus_id is provided, use existing corpus
    if args.corpus_id:
        corpus_name = f"projects/{args.project_id}/locations/{args.location}/ragCorpora/{args.corpus_id}"
        logger.info("Using existing corpus: %s", corpus_name)
        return corpus_name

    # Create new corpus
    logger.info("Creating RAG corpus: %s", CORPUS_DISPLAY_NAME)

    embedding_model_config = rag.RagEmbeddingModelConfig(
        vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
            publisher_model="publishers/google/models/text-embedding-005"
        )
    )

    rag_corpus = rag.create_corpus(
        display_name=CORPUS_DISPLAY_NAME,
        description="Municipal policy documents for grounding Sampark AI citizen issue recommendations",
        backend_config=rag.RagVectorDbConfig(
            rag_embedding_model_config=embedding_model_config
        ),
    )

    corpus_name = rag_corpus.name
    logger.info("Created corpus: %s", corpus_name)
    return corpus_name


def import_samples(corpus_name: str, args: argparse.Namespace) -> None:
    """Import sample policy documents into the RAG corpus."""
    from google.cloud import storage
    from vertexai import rag
    import vertexai

    vertexai.init(project=args.project_id, location=args.location)
    storage_client = storage.Client(project=args.project_id)
    bucket_name = args.bucket_name

    # Ensure bucket exists
    try:
        bucket = storage_client.create_bucket(bucket_name, location=args.location)
        logger.info("Created bucket: gs://%s", bucket_name)
    except Exception:
        bucket = storage_client.bucket(bucket_name)
        logger.info("Using existing bucket: gs://%s", bucket_name)

    # Upload sample documents
    gcs_paths = []
    for doc_name, content in SAMPLE_POLICIES.items():
        blob = bucket.blob(doc_name)
        blob.upload_from_string(content, content_type="text/markdown")
        gcs_path = f"gs://{bucket_name}/{doc_name}"
        gcs_paths.append(gcs_path)
        logger.info("Uploaded: %s", gcs_path)

    # Import into RAG corpus
    logger.info("Importing %d documents into RAG corpus...", len(gcs_paths))
    rag.import_files(
        corpus_name,
        gcs_paths,
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(
                chunk_size=512,
                chunk_overlap=64,
            ),
        ),
    )
    logger.info("Import complete!")


def verify_corpus(corpus_name: str, args: argparse.Namespace) -> None:
    """Verify the corpus is working by performing a test query."""
    from vertexai import rag
    import vertexai
    from vertexai.generative_models import GenerativeModel, Tool

    vertexai.init(project=args.project_id, location=args.location)

    # Test retrieval
    rag_retrieval_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
                rag_retrieval_config=rag.RagRetrievalConfig(top_k=3),
            ),
        )
    )

    test_model = GenerativeModel(
        model_name="gemini-2.0-flash-001",
        tools=[rag_retrieval_tool],
    )

    response = test_model.generate_content(
        "What is the response time for pothole repair according to policy?"
    )

    logger.info("Test query response:")
    logger.info(response.text)
    logger.info("✅ RAG corpus is working!")


def main():
    parser = argparse.ArgumentParser(description="Set up Vertex AI RAG Engine corpus for Sampark AI")
    parser.add_argument("--project-id", default=PROJECT_ID, help="GCP project ID")
    parser.add_argument("--location", default=LOCATION, help="GCP location")
    parser.add_argument("--bucket-name", default=BUCKET_NAME, help="Cloud Storage bucket for documents")
    parser.add_argument("--corpus-id", help="Existing corpus ID to use (skip creation)")
    parser.add_argument("--import-samples", action="store_true", help="Import sample policy documents")
    parser.add_argument("--verify", action="store_true", help="Run a test query to verify the corpus")
    parser.add_argument("--output-env", action="store_true", help="Print environment variables for .env file")

    args = parser.parse_args()

    # Create corpus
    corpus_name = create_corpus(args)

    # Import samples
    if args.import_samples:
        import_samples(corpus_name, args)

    # Verify
    if args.verify:
        verify_corpus(corpus_name, args)

    # Output env vars
    if args.output_env:
        corpus_id = corpus_name.split("/")[-1]
        print(f"\nAdd these to your .env file:")
        print(f"RAG_CORPUS_ID={corpus_id}")
        print(f"RAG_CORPUS_NAME={corpus_name}")

    logger.info("Setup complete!")
    return corpus_name


if __name__ == "__main__":
    main()
