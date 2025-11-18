"""Article CRUD and AI features API routes."""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from models import (
    ArticleMetadata,
    ArticleMetadataListResponse,
    BatchConceptExtractionResponse,
    BatchConceptSuggestion,
    ConceptExtractionResponse,
    ConceptSuggestion,
    ResourceResponse,
    SummaryResponse,
)
from models.resource import Resource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


def create_articles_router(
    get_static_articles: Any,  # Callable that returns current articles list
    ollama_client: Any,
) -> APIRouter:
    """Create articles router with dependencies injected.

    Provides full CRUD operations for articles plus AI-powered features
    like summarization and concept extraction.
    """

    @router.get("", response_model=ArticleMetadataListResponse)
    def list_articles() -> ArticleMetadataListResponse:
        """Get all static articles metadata (without content), ordered by publication date descending.

        Returns lightweight metadata for article list views. Use GET /api/articles/{id}
        to retrieve full article content.
        """
        from dateutil import parser

        articles = get_static_articles()

        # Sort by published_date (newer first), fallback to created_at
        def get_sort_key(resource: dict[str, Any]) -> Any:
            date_str = resource.get("published_date") or resource.get("created_at")
            if date_str:
                try:
                    return parser.parse(str(date_str))
                except Exception:
                    return parser.parse("1970-01-01")
            return parser.parse("1970-01-01")

        sorted_articles = sorted(articles, key=get_sort_key, reverse=True)

        # Convert to ArticleMetadata (excludes content and html_content)
        metadata_list = [ArticleMetadata(**article) for article in sorted_articles]

        return ArticleMetadataListResponse(resources=metadata_list)

    @router.get("/{article_id}", response_model=ResourceResponse)
    def get_article(article_id: int) -> ResourceResponse:
        """Get a specific article by ID."""
        articles = get_static_articles()
        for article in articles:
            if article["id"] == article_id:
                return ResourceResponse(resource=Resource(**article))
        raise HTTPException(status_code=404, detail="Article not found")

    @router.get("/{article_id}/summary", response_model=SummaryResponse)
    def get_article_summary(article_id: int) -> SummaryResponse:
        """Generate an AI summary of a specific article using Ollama."""
        if not ollama_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="AI summary feature is not available. Ollama is not running or not configured.",
            )

        # Find the article
        articles = get_static_articles()
        article = None
        for a in articles:
            if a["id"] == article_id:
                article = a
                break

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Generate summary
        summary = ollama_client.summarize_article(article["content"])

        if not summary:
            raise HTTPException(
                status_code=500, detail="Failed to generate summary. Please try again."
            )

        return SummaryResponse(summary=summary)

    @router.post("/{article_id}/extract-concepts", response_model=ConceptExtractionResponse)
    def extract_article_concepts(article_id: int) -> ConceptExtractionResponse:
        """Extract key concepts from an article that could become Zettelkasten notes.

        Analyzes article content using AI to identify frameworks, methodologies,
        principles, and mental models worth capturing as atomic notes.

        Returns empty list if Ollama unavailable or article not found.
        """
        # If Ollama unavailable, return empty concepts
        if not ollama_client.is_available():
            logger.warning("Ollama not available for concept extraction")
            return ConceptExtractionResponse(concepts=[], count=0)

        # Find the article
        articles = get_static_articles()
        article = None
        for a in articles:
            if a["id"] == article_id:
                article = a
                break

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Get article content
        article_title = article.get("title", "Untitled")
        article_content = article.get("content", "")

        if not article_content:
            logger.warning("Article %s has no content", article_id)
            return ConceptExtractionResponse(concepts=[], count=0)

        # Build prompt for LLM
        # Limit content to avoid token limits (first ~3000 chars should capture key concepts)
        content_preview = article_content[:3000]
        if len(article_content) > 3000:
            content_preview += "\n\n[Article continues...]"

        prompt = f"""Analyze this article and identify 5-10 key concepts that would make good atomic notes in a Zettelkasten.

Article Title: {article_title}

Article Content:
{content_preview}

Focus on:
- Frameworks and methodologies (e.g., "DORA metrics", "Rocks & Barnacles")
- Important principles or practices (e.g., "Psychological safety", "Continuous delivery")
- Specific techniques (e.g., "Wardley mapping", "Incident retrospectives")
- Mental models (e.g., "Queue theory", "Lead time vs cycle time")

For each concept, provide:
- concept: Short name suitable as a note title (2-5 words)
- excerpt: Brief quote or paraphrase showing where it appears (1-2 sentences)
- confidence: Float 0-1 indicating how well-defined the concept is
- reason: Why this concept is worth capturing as a separate note

Return ONLY a JSON array of concept suggestions.
Example: [{{"concept": "DORA metrics", "excerpt": "Four key metrics...", "confidence": 0.9, "reason": "Core framework for measuring software delivery"}}]

JSON:"""

        try:
            # Use qwen2.5:1.5b for structured output
            response_data = ollama_client.client.generate(
                model="qwen2.5:1.5b",
                prompt=prompt,
                options={"num_ctx": 8192}
            )

            response = response_data.get("response", "")
            if not response:
                logger.error("Empty response from Ollama for concept extraction")
                return ConceptExtractionResponse(concepts=[], count=0)

            # Defensive JSON parsing (same pattern as other endpoints)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Try to parse as array
            try:
                concepts_data = json.loads(response)
                if isinstance(concepts_data, dict):
                    concepts_data = [concepts_data]
                elif not isinstance(concepts_data, list):
                    logger.error("Unexpected response format: %s", type(concepts_data))
                    return ConceptExtractionResponse(concepts=[], count=0)
            except json.JSONDecodeError:
                # Try line-by-line parsing
                concepts_data = []
                for line in response.split('\n'):
                    line = line.strip()
                    if line and line.startswith('{'):
                        try:
                            obj = json.loads(line)
                            concepts_data.append(obj)
                        except json.JSONDecodeError:
                            continue

                if not concepts_data:
                    logger.error("Could not parse any JSON from response")
                    logger.error("Full response was: %s", response[:500])
                    return ConceptExtractionResponse(concepts=[], count=0)

            # Convert to ConceptSuggestion models
            concepts = []
            for c in concepts_data:
                try:
                    concepts.append(
                        ConceptSuggestion(
                            concept=c.get("concept", ""),
                            excerpt=c.get("excerpt", ""),
                            confidence=c.get("confidence", 0.5),
                            reason=c.get("reason", "")
                        )
                    )
                except Exception as e:
                    logger.warning("Failed to parse concept: %s - %s", c, e)
                    continue

            # Limit to top 10 concepts
            concepts = concepts[:10]

            logger.info("Extracted %d concepts from article %s", len(concepts), article_id)
            return ConceptExtractionResponse(concepts=concepts, count=len(concepts))

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from Ollama: %s", e)
            logger.error("Full response was: %s", response[:500])
            return ConceptExtractionResponse(concepts=[], count=0)
        except Exception as e:
            logger.error("Error extracting concepts: %s", e)
            return ConceptExtractionResponse(concepts=[], count=0)

    @router.post("/extract-all-concepts", response_model=BatchConceptExtractionResponse)
    def extract_all_article_concepts() -> BatchConceptExtractionResponse:
        """Extract and deduplicate concepts from all articles.

        Batch processes all articles and aggregates concepts, showing which articles
        mention each concept. Deduplicates similar concepts across articles.

        Returns empty list if Ollama unavailable.
        """
        # If Ollama unavailable, return empty
        if not ollama_client.is_available():
            logger.warning("Ollama not available for batch concept extraction")
            return BatchConceptExtractionResponse(concepts=[], count=0, articles_processed=0)

        # Get all static articles (not user resources, just the curated articles) - get current state dynamically
        articles = [r for r in get_static_articles() if r.get("type") == "article"]

        if not articles:
            logger.warning("No articles found for batch concept extraction")
            return BatchConceptExtractionResponse(concepts=[], count=0, articles_processed=0)

        # Extract concepts from each article
        concept_map: dict[str, dict] = {}  # concept_name -> {excerpts, confidence, reasons, article_ids, article_titles}

        for article in articles:
            article_id = article["id"]
            article_title = article.get("title", "Untitled")

            # Extract concepts for this article
            result = extract_article_concepts(article_id)

            # Aggregate concepts
            for concept_obj in result.concepts:
                concept_name = concept_obj.concept.lower().strip()

                if concept_name not in concept_map:
                    concept_map[concept_name] = {
                        "concept": concept_obj.concept,  # Use original casing from first occurrence
                        "excerpts": [],
                        "confidences": [],
                        "reasons": [],
                        "article_ids": [],
                        "article_titles": [],
                    }

                concept_map[concept_name]["excerpts"].append(concept_obj.excerpt)
                concept_map[concept_name]["confidences"].append(concept_obj.confidence)
                concept_map[concept_name]["reasons"].append(concept_obj.reason)
                concept_map[concept_name]["article_ids"].append(article_id)
                concept_map[concept_name]["article_titles"].append(article_title)

        # Convert to BatchConceptSuggestion models
        batch_concepts = []
        for data in concept_map.values():
            # Use the highest confidence score
            max_confidence = max(data["confidences"])
            # Use the first excerpt (could enhance to pick best one)
            excerpt = data["excerpts"][0]
            # Combine reasons or use the first one
            reason = data["reasons"][0]
            if len(data["article_ids"]) > 1:
                reason = f"Mentioned in {len(data['article_ids'])} articles. {reason}"

            batch_concepts.append(
                BatchConceptSuggestion(
                    concept=data["concept"],
                    excerpt=excerpt,
                    confidence=max_confidence,
                    reason=reason,
                    article_ids=data["article_ids"],
                    article_titles=data["article_titles"],
                )
            )

        # Sort by confidence (highest first)
        batch_concepts.sort(key=lambda x: x.confidence, reverse=True)

        logger.info(
            "Extracted %d unique concepts from %d articles",
            len(batch_concepts),
            len(articles)
        )

        return BatchConceptExtractionResponse(
            concepts=batch_concepts,
            count=len(batch_concepts),
            articles_processed=len(articles),
        )

    return router
