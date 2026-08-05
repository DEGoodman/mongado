import Link from "next/link";
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
        {/* Hero: name spans the page, the columns below share the space */}
        <header className={styles.hero}>
          <p className={styles.eyebrow}>
            {siteConfig.author.title} — {siteConfig.author.location}
          </p>
          <h1 className={styles.title}>{siteConfig.author.fullTitle}</h1>
          <div className={styles.rule} aria-hidden="true" />

          <div className={styles.heroGrid}>
            <div className={styles.heroIntro}>
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
            </div>

            <Link href="/knowledge-base" className={styles.kbCard}>
              <span className={styles.kbCardTitle}>
                Knowledge base
                <span className={styles.kbCardArrow} aria-hidden="true">
                  →
                </span>
              </span>
              <span className={styles.kbCardDescription}>
                A curated digital garden of engineering and leadership insights.
              </span>
            </Link>
          </div>
        </header>

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
