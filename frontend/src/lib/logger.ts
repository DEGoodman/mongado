/**
 * Logging utility for the frontend.
 *
 * Uses console methods in development and can be extended
 * for production logging services (e.g., Sentry, LogRocket).
 */

type LogLevel = "debug" | "info" | "warn" | "error";

class Logger {
  private isDevelopment = process.env.NODE_ENV === "development";

  /**
   * Log debug information (only in development)
   */
  debug(message: string, ...args: unknown[]): void {
    if (this.isDevelopment) {
      console.debug(`[DEBUG] ${message}`, ...args);
    }
  }

  /**
   * Log informational messages
   */
  info(message: string, ...args: unknown[]): void {
    console.info(`[INFO] ${message}`, ...args);
  }

  /**
   * Log warnings
   */
  warn(message: string, ...args: unknown[]): void {
    console.warn(`[WARN] ${message}`, ...args);
  }

  /**
   * Log errors
   */
  error(message: string, error?: unknown, ...args: unknown[]): void {
    console.error(`[ERROR] ${message}`, error, ...args);

    // In production, you could send errors to a service like Sentry:
    // if (!this.isDevelopment && typeof window !== 'undefined') {
    //   Sentry.captureException(error);
    // }
  }

  /**
   * Create a logger with a specific context/module name
   */
  withContext(context: string): ContextLogger {
    return new ContextLogger(context, this);
  }
}

class ContextLogger {
  constructor(
    private context: string,
    private logger: Logger
  ) {}

  debug(message: string, ...args: unknown[]): void {
    this.logger.debug(`[${this.context}] ${message}`, ...args);
  }

  info(message: string, ...args: unknown[]): void {
    this.logger.info(`[${this.context}] ${message}`, ...args);
  }

  warn(message: string, ...args: unknown[]): void {
    this.logger.warn(`[${this.context}] ${message}`, ...args);
  }

  error(message: string, error?: unknown, ...args: unknown[]): void {
    this.logger.error(`[${this.context}] ${message}`, error, ...args);
  }
}

// Export singleton instance
export const logger = new Logger();

// Export for testing
export { Logger, ContextLogger };
