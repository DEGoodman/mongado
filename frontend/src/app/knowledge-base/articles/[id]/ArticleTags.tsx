"use client";

import { useRouter } from "next/navigation";
import { TagPillList } from "@/components/TagPill";

/**
 * Clickable tag list island - navigates to the articles list filtered by tag.
 */
export default function ArticleTags({ tags }: { tags: string[] }) {
  const router = useRouter();

  const handleTagClick = (tag: string) => {
    router.push(`/knowledge-base/articles?tags=${encodeURIComponent(tag)}`);
  };

  return <TagPillList tags={tags} showHash onClick={handleTagClick} variant="article" />;
}
