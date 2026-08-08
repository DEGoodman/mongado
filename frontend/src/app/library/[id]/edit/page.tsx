"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Breadcrumb from "@/components/Breadcrumb";
import PageHeader from "@/components/PageHeader";
import { LoadingState, ErrorState } from "@/components/PageState";
import LibraryEntryForm, { LibraryFormValues, parseTags } from "@/components/LibraryEntryForm";
import { getLibraryEntry, updateLibraryEntry } from "@/lib/api/library";
import { logger } from "@/lib/logger";
import styles from "../../page.module.scss";

export default function EditLibraryEntryPage() {
  const router = useRouter();
  const params = useParams();
  const entryId = params.id as string;

  const [initialValues, setInitialValues] = useState<LibraryFormValues | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const entry = await getLibraryEntry(entryId);
        setInitialValues({
          title: entry.title,
          source_url: entry.source_url,
          author: entry.author,
          type: entry.type,
          summary: entry.summary,
          tags: entry.tags.join(", "),
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load entry");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [entryId]);

  const handleSubmit = async (values: LibraryFormValues) => {
    await updateLibraryEntry(entryId, {
      title: values.title.trim(),
      source_url: values.source_url.trim(),
      author: values.author.trim(),
      type: values.type,
      summary: values.summary,
      tags: parseTags(values.tags),
    });
    logger.info("Updated library entry", { id: entryId });
    router.push(`/library/${entryId}`);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingState label="Loading entry" />
      </div>
    );
  }

  if (error || !initialValues) {
    return (
      <div className={styles.container}>
        <ErrorState
          message={error || "Entry not found"}
          backHref="/library"
          backLabel="Back to Library"
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <PageHeader title="Edit Library Entry" breadcrumb={<Breadcrumb section="library" />} />
      <main className={styles.main}>
        <LibraryEntryForm
          initialValues={initialValues}
          submitLabel="Save changes"
          onSubmit={handleSubmit}
          onCancelHref={`/library/${entryId}`}
        />
      </main>
    </div>
  );
}
