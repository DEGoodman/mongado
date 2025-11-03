/**
 * Card Component
 * Reusable card container with variants: default, elevated, interactive
 * Part of the retro-modern design system
 */

import styles from "./Card.module.scss";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Card variant
   * - default: Standard card with grey background
   * - elevated: Canvas background with shadow
   * - interactive: Hover and click effects (for clickable cards)
   */
  variant?: "default" | "elevated" | "interactive";

  /**
   * Card padding size
   */
  size?: "sm" | "md" | "lg";

  /**
   * Remove padding (useful for custom internal layout)
   */
  noPadding?: boolean;

  /**
   * Full width card
   */
  fullWidth?: boolean;

  /**
   * Card content
   */
  children: React.ReactNode;

  /**
   * Additional CSS class
   */
  className?: string;

  /**
   * HTML element type (div or article)
   */
  as?: "div" | "article" | "section";
}

export default function Card({
  variant = "default",
  size = "md",
  noPadding = false,
  fullWidth = false,
  children,
  className = "",
  as: Component = "div",
  ...props
}: CardProps) {
  const classNames = [
    styles.card,
    variant !== "default" ? styles[variant] : "",
    styles[size],
    noPadding ? styles.noPadding : "",
    fullWidth ? styles.fullWidth : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Component className={classNames} {...props}>
      {children}
    </Component>
  );
}
