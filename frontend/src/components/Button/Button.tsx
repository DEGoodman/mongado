/**
 * Button Component
 * Reusable button with variants: primary, secondary, tertiary, ghost
 * Part of the retro-modern design system
 */

import styles from "./Button.module.scss";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Button variant
   * - primary: Solid blue background (main CTAs)
   * - secondary: Outlined blue border (secondary actions)
   * - tertiary: Grey background (tertiary actions)
   * - ghost: Transparent (subtle actions)
   */
  variant?: "primary" | "secondary" | "tertiary" | "ghost";

  /**
   * Button size
   */
  size?: "sm" | "md" | "lg";

  /**
   * Full width button
   */
  fullWidth?: boolean;

  /**
   * Button content
   */
  children: React.ReactNode;

  /**
   * Additional CSS class
   */
  className?: string;
}

export default function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const classNames = [
    styles.button,
    styles[variant],
    styles[size],
    fullWidth ? styles.fullWidth : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classNames} {...props}>
      {children}
    </button>
  );
}
