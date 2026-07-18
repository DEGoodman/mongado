/**
 * Knowledge Base Layout
 * Wraps all KB pages with persistent top navigation
 */

import TopNavigation from "@/components/TopNavigation";
import DelightEffects from "@/components/Delight";

export default function KnowledgeBaseLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopNavigation />
      <DelightEffects>{children}</DelightEffects>
    </>
  );
}
