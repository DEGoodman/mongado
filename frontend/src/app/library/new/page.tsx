"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Breadcrumb from "@/components/Breadcrumb";
import PageHeader from "@/components/PageHeader";
import LibraryEntryForm, { LibraryFormValues, parseTags } from "@/components/LibraryEntryForm";
import { createLibraryEntry } from "@/lib/api/library";
import { isAuthenticated } from "@/lib/api/client";
import { logger } from "@/lib/logger";
import styles from "../page.module.scss";

export default function NewLibraryEntryPage() {
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  // isAuthenticated reads localStorage — only valid after hydration
  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  const handleSubmit = async (values: LibraryFormValues) => {
    const entry = await createLibraryEntry({
      title: values.title.trim(),
      source_url: values.source_url.trim(),
      author: values.author.trim(),
      type: values.type,
      summary: values.summary,
      tags: parseTags(values.tags),
    });
    logger.info("Created library entry", { id: entry.id });
    router.push(`/library/${entry.id}`);
  };

  return (
    <div className={styles.container}>
      <PageHeader
        title="New Library Entry"
        subtitle="Add a resource worth reaching back to"
        breadcrumb={<Breadcrumb section="library" />}
      />
      <main className={styles.main}>
        {authed === false ? (
          <div className={styles.noResults}>
            <p>You need to sign in as admin to add library entries.</p>
            <Link href="/library" className={styles.clearButton}>
              Back to Library
            </Link>
          </div>
        ) : (
          <LibraryEntryForm
            submitLabel="Create entry"
            onSubmit={handleSubmit}
            onCancelHref="/library"
          />
        )}
      </main>
    </div>
  );
}
