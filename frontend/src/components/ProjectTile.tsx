import Link from "next/link";
import styles from "./ProjectTile.module.scss";

interface ProjectTileProps {
  title: string;
  description: string;
  href: string;
  icon?: string;
}

export default function ProjectTile({ title, description, href, icon = "📦" }: ProjectTileProps) {
  return (
    <Link href={href} className={styles.projectTile}>
      <div className={styles.content}>
        <div className={styles.icon}>{icon}</div>
        <div className={styles.textContent}>
          <h3 className={styles.title}>{title}</h3>
          <p className={styles.description}>{description}</p>
        </div>
        <svg className={styles.arrow} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}
