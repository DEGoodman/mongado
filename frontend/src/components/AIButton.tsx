"use client";

import styles from "./AIButton.module.scss";

interface AIButtonProps {
  onClick: () => void;
}

export default function AIButton({ onClick }: AIButtonProps) {
  return (
    <button onClick={onClick} className={styles.aiButton} aria-label="Open AI Assistant">
      <svg className={styles.icon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
        />
      </svg>
    </button>
  );
}
