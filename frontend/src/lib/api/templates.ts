/**
 * Templates API client for note templates
 */

import { apiGet } from "./client";

export interface TemplateMetadata {
  id: string;
  title: string;
  description: string;
  icon: string;
}

export interface Template extends TemplateMetadata {
  content: string;
}

export interface TemplateListResponse {
  templates: TemplateMetadata[];
  count: number;
}

/**
 * List all available note templates
 */
export async function listTemplates(): Promise<TemplateListResponse> {
  return apiGet<TemplateListResponse>("/api/templates");
}

/**
 * Get a specific template by ID
 */
export async function getTemplate(templateId: string): Promise<Template> {
  return apiGet<Template>(`/api/templates/${templateId}`);
}
