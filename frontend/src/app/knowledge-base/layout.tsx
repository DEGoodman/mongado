/**
 * Knowledge Base Layout
 * Wraps all KB pages with persistent top navigation
 */

import TopNavigation from "@/components/TopNavigation";

export default function KnowledgeBaseLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopNavigation />
      {children}
    </>
  );
}
