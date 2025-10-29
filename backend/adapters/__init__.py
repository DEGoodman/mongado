"""Database and storage adapters for external services."""

from adapters.article_loader import load_static_articles
from adapters.neo4j import Neo4jAdapter, get_neo4j_adapter

__all__ = [
    # Article loader
    "load_static_articles",
    # Neo4j adapter
    "Neo4jAdapter",
    "get_neo4j_adapter",
]
