"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function KnowledgeBaseRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to /notes
    router.replace("/notes");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <p className="text-gray-600">Redirecting to Notes...</p>
      </div>
    </div>
  );
}
