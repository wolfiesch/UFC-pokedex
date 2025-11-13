/**
 * Error logging utility for the UFC Pokedex application.
 * Provides structured logging in development and can be extended for production monitoring.
 */

import { ApiError } from "./errors";

export enum LogLevel {
  DEBUG = "debug",
  INFO = "info",
  WARN = "warn",
  ERROR = "error",
}

interface LogContext {
  [key: string]: unknown;
}

class Logger {
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === "development";
  }

  /**
   * Format timestamp for logs
   */
  private getTimestamp(): string {
    return new Date().toISOString();
  }

  /**
   * Format log message with context
   */
  private formatMessage(
    level: LogLevel,
    message: string,
    context?: LogContext,
  ): string {
    const timestamp = this.getTimestamp();
    const contextStr = context ? ` ${JSON.stringify(context)}` : "";
    return `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`;
  }

  /**
   * Log debug message (development only)
   */
  debug(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.debug(this.formatMessage(LogLevel.DEBUG, message, context));
    }
  }

  /**
   * Log info message
   */
  info(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.info(this.formatMessage(LogLevel.INFO, message, context));
    }
  }

  /**
   * Log warning message
   */
  warn(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.warn(this.formatMessage(LogLevel.WARN, message, context));
    }
  }

  /**
   * Log error message
   */
  error(message: string, error?: Error | ApiError, context?: LogContext): void {
    const errorContext: LogContext = {
      ...context,
    };

    if (error) {
      if (error instanceof ApiError) {
        errorContext.errorType = error.errorType;
        errorContext.statusCode = error.statusCode;
        errorContext.requestId = error.requestId;
        errorContext.path = error.path;
        errorContext.retryCount = error.retryCount;
        errorContext.isRetryable = error.isRetryable;
        errorContext.detail = error.detail;
        errorContext.timestamp = error.timestamp.toISOString();

        if (error.validationErrors) {
          errorContext.validationErrors = error.validationErrors;
        }
      } else {
        errorContext.errorName = error.name;
        errorContext.errorMessage = error.message;
      }

      errorContext.stack = error.stack;
    }

    if (this.isDevelopment) {
      console.error(this.formatMessage(LogLevel.ERROR, message, errorContext));
    }

    // In production, you would send this to a monitoring service
    // Example: Sentry, LogRocket, Datadog, etc.
    // this.sendToMonitoring(message, errorContext);
  }

  /**
   * Log API request
   */
  logRequest(method: string, url: string, context?: LogContext): void {
    this.debug(`API Request: ${method} ${url}`, context);
  }

  /**
   * Log API response
   */
  logResponse(
    method: string,
    url: string,
    statusCode: number,
    duration?: number,
    context?: LogContext,
  ): void {
    const durationStr = duration !== undefined ? ` (${duration}ms)` : "";
    this.debug(
      `API Response: ${method} ${url} ${statusCode}${durationStr}`,
      context,
    );
  }

  /**
   * Log API error
   */
  logApiError(
    method: string,
    url: string,
    error: ApiError,
    context?: LogContext,
  ): void {
    this.error(
      `API Error: ${method} ${url} - ${error.getTechnicalSummary()}`,
      error,
      context,
    );
  }

  /**
   * Log retry attempt
   */
  logRetry(
    method: string,
    url: string,
    retryCount: number,
    maxRetries: number,
    context?: LogContext,
  ): void {
    this.warn(
      `Retrying ${method} ${url} (attempt ${retryCount}/${maxRetries})`,
      context,
    );
  }

  /**
   * Log component error (for Error Boundary)
   */
  logComponentError(
    componentName: string,
    error: Error,
    errorInfo?: React.ErrorInfo,
  ): void {
    this.error(`Component Error in ${componentName}: ${error.message}`, error, {
      componentStack: errorInfo?.componentStack,
    });
  }

  /**
   * Placeholder for production monitoring integration
   * Uncomment and configure when adding monitoring service
   */
  // private sendToMonitoring(message: string, context: LogContext): void {
  //   if (!this.isDevelopment) {
  //     // Example Sentry integration:
  //     // Sentry.captureMessage(message, {
  //     //   level: 'error',
  //     //   extra: context,
  //     // });
  //
  //     // Example LogRocket integration:
  //     // LogRocket.captureMessage(message, {
  //     //   tags: { type: context.errorType as string },
  //     //   extra: context,
  //     // });
  //   }
  // }
}

// Export singleton instance
export const logger = new Logger();
