"""API routes for note templates."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from adapters.template_loader import get_template, list_templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateMetadata(BaseModel):
    """Template metadata without content."""

    id: str
    title: str
    description: str
    icon: str


class TemplateListResponse(BaseModel):
    """Response for listing templates."""

    templates: list[TemplateMetadata]
    count: int


class TemplateResponse(BaseModel):
    """Full template with content."""

    id: str
    title: str
    description: str
    icon: str
    content: str


@router.get("", response_model=TemplateListResponse)
async def get_templates() -> TemplateListResponse:
    """List all available note templates.

    Returns template metadata without the full content.
    Use GET /api/templates/{template_id} to get full content.

    Returns:
        List of available templates with metadata
    """
    template_dicts = list_templates()
    templates = [TemplateMetadata(**t) for t in template_dicts]
    return TemplateListResponse(templates=templates, count=len(templates))


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template_by_id(template_id: str) -> TemplateResponse:
    """Get a specific template by ID.

    Args:
        template_id: Template identifier (e.g., "person", "book", "concept", "project")

    Returns:
        Full template with content

    Raises:
        HTTPException: 404 if template not found
    """
    template = get_template(template_id)

    if template is None:
        logger.warning("Template not found: %s", template_id)
        raise HTTPException(
            status_code=404,
            detail=f"Template not found: {template_id}",
        )

    return TemplateResponse(**template)
