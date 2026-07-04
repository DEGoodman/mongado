import { siteConfig } from "@/lib/site-config";
import ThemeToggle from "@/components/ThemeToggle";
import styles from "./page.module.scss";

export default function Home() {
  return (
    <div className={styles.container}>
      <div className={styles.themeCorner}>
        <ThemeToggle />
      </div>
      <main className={styles.main}>
        {/* Hero Section */}
        <header className={styles.hero}>
          <p className={styles.eyebrow}>
            {siteConfig.author.title} — {siteConfig.author.location}
          </p>
          <h1 className={styles.title}>{siteConfig.author.fullTitle}</h1>
          <div className={styles.rule} aria-hidden="true" />
          <p className={styles.bio}>{siteConfig.author.bio}</p>

          <nav className={styles.socialLinks} aria-label="Social links">
            <a href={siteConfig.links.github} target="_blank" rel="noopener noreferrer">
              github ↗
            </a>
            <a href={siteConfig.links.linkedin} target="_blank" rel="noopener noreferrer">
              linkedin ↗
            </a>
            <a href={siteConfig.links.email}>email ↗</a>
          </nav>
        </header>

        {/* Knowledge Base Section */}
        <section className={styles.kbSection}>
          <p className={styles.kbEyebrow}>Knowledge base</p>
          <h2 className={styles.kbTitle}>Part published blog, part digital garden</h2>
          <p className={styles.kbDescription}>
            A curated collection of engineering and leadership insights. Long-form articles on
            topics I&apos;m passionate about, alongside quick-reference notes and interconnected
            thoughts following a Zettelkasten approach — from technical deep-dives to frameworks
            like &quot;The 5 Dysfunctions of a Team&quot; and Daniel Pink&apos;s motivation triad.
          </p>
          <a href="/knowledge-base" className={styles.kbButton}>
            Explore the knowledge base
            <svg
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              width="18"
              height="18"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </a>
        </section>

        {/* Other Projects Link */}
        <div className={styles.projectsLink}>
          <a href={siteConfig.links.github} target="_blank" rel="noopener noreferrer">
            View more projects on GitHub →
          </a>
        </div>

        {/* Footer note */}
        <footer className={styles.footer}>
          <p>Built with Next.js, FastAPI, and Python</p>
          <p className={styles.copyright}>
            © 2025 {siteConfig.author.name} • {siteConfig.author.location}
          </p>
        </footer>
      </main>
    </div>
  );
}
