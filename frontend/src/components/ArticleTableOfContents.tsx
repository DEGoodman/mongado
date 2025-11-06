"use client";

import { useEffect, useState } from "react";
import styles from "./ArticleTableOfContents.module.scss";

interface TocItem {
  id: string;
  text: string;
  level: number;
}

interface ArticleTableOfContentsProps {
  content: string;
}

export default function ArticleTableOfContents({ content }: ArticleTableOfContentsProps) {
  const [tocItems, setTocItems] = useState<TocItem[]>([]);
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    // Extract headings from markdown content
    const headingRegex = /^(#{2,4})\s+(.+)$/gm;
    const items: TocItem[] = [];
    const idCounts = new Map<string, number>(); // Track duplicate IDs
    let match;

    while ((match = headingRegex.exec(content)) !== null) {
      const level = match[1].length; // Count # symbols
      const text = match[2].trim();
      // Create URL-friendly ID from heading text
      let baseId = text
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, "")
        .replace(/\s+/g, "-");

      // Handle duplicate IDs by appending a counter
      const count = idCounts.get(baseId) || 0;
      const id = count === 0 ? baseId : `${baseId}-${count}`;
      idCounts.set(baseId, count + 1);

      items.push({ id, text, level });
    }

    setTocItems(items);
  }, [content]);

  useEffect(() => {
    // Track active section based on scroll position
    const handleScroll = () => {
      const headings = tocItems.map((item) => document.getElementById(item.id)).filter(Boolean);

      // Find the heading that's currently in view
      for (let i = headings.length - 1; i >= 0; i--) {
        const heading = headings[i];
        if (heading && heading.getBoundingClientRect().top <= 100) {
          setActiveId(tocItems[i].id);
          break;
        }
      }
    };

    window.addEventListener("scroll", handleScroll);
    handleScroll(); // Initial call

    return () => window.removeEventListener("scroll", handleScroll);
  }, [tocItems]);

  if (tocItems.length === 0) {
    return null;
  }

  return (
    <nav className={styles.toc}>
      <h3 className={styles.title}>Table of Contents</h3>
      <ul className={styles.list}>
        {tocItems.map((item) => (
          <li
            key={item.id}
            style={{ paddingLeft: `${(item.level - 2) * 0.75}rem` }}
            className={styles.listItem}
          >
            <a
              href={`#${item.id}`}
              className={`${styles.link} ${activeId === item.id ? styles.active : ""}`}
              onClick={(e) => {
                e.preventDefault();
                const element = document.getElementById(item.id);
                if (element) {
                  const offset = 80; // Account for sticky header
                  const elementPosition = element.getBoundingClientRect().top;
                  const offsetPosition = elementPosition + window.pageYOffset - offset;

                  window.scrollTo({
                    top: offsetPosition,
                    behavior: "smooth",
                  });
                }
              }}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
