"use client";

import { useState, useRef, useEffect } from "react";
import { TemplateMetadata } from "@/lib/api/templates";
import styles from "./TemplateSelector.module.scss";

interface TemplateSelectorProps {
  templates: TemplateMetadata[];
  onSelectTemplate: (templateId: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export default function TemplateSelector({
  templates,
  onSelectTemplate,
  disabled = false,
  loading = false,
}: TemplateSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen]);

  const handleSelectTemplate = (templateId: string) => {
    onSelectTemplate(templateId);
    setIsOpen(false);
  };

  if (templates.length === 0) {
    return null;
  }

  return (
    <div className={styles.container} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={styles.triggerButton}
        disabled={disabled || loading}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className={styles.icon}>📄</span>
        <span className={styles.label}>{loading ? "Loading..." : "Template"}</span>
        <svg
          className={`${styles.chevron} ${isOpen ? styles.open : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className={styles.dropdown} role="listbox">
          <div className={styles.dropdownHeader}>
            <span className={styles.headerTitle}>Start from template</span>
          </div>
          <div className={styles.templateList}>
            {templates.map((template) => (
              <button
                key={template.id}
                type="button"
                onClick={() => handleSelectTemplate(template.id)}
                className={styles.templateItem}
                role="option"
                aria-selected={false}
              >
                <span className={styles.templateIcon}>{template.icon}</span>
                <div className={styles.templateInfo}>
                  <span className={styles.templateTitle}>{template.title}</span>
                  <span className={styles.templateDescription}>{template.description}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
