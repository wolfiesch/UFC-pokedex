"use client";

import React from "react";
import { logger } from "@/lib/logger";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary component to catch React component errors.
 * Provides a fallback UI and error logging functionality.
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    logger.logComponentError(
      this.constructor.name,
      error,
      errorInfo
    );
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      // Default fallback UI
      return (
        <div className="flex min-h-screen flex-col items-center justify-center p-6">
          <div className="w-full max-w-2xl rounded-3xl border border-destructive/30 bg-destructive/10 p-8 text-destructive-foreground">
            <div className="mb-4 flex items-start gap-4">
              <div className="flex-shrink-0">
                <svg
                  className="h-8 w-8 text-destructive"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h2 className="mb-2 text-xl font-bold">
                  Something went wrong
                </h2>
                <p className="mb-4 text-sm">
                  The application encountered an unexpected error. This has been logged
                  for investigation.
                </p>

                <div className="mb-4 rounded-lg border border-destructive/20 bg-background/50 p-4 font-mono text-xs">
                  <p className="mb-1 font-bold">Error Details:</p>
                  <p className="mb-2 text-destructive">
                    {this.state.error.name}: {this.state.error.message}
                  </p>
                  {this.state.error.stack && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                        Stack Trace
                      </summary>
                      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-muted-foreground">
                        {this.state.error.stack}
                      </pre>
                    </details>
                  )}
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={this.handleReset}
                    className="rounded-full bg-primary px-6 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={() => window.location.reload()}
                    className="rounded-full border border-input bg-background px-6 py-2 text-sm font-semibold transition-colors hover:bg-accent hover:text-accent-foreground"
                  >
                    Reload Page
                  </button>
                  <a
                    href="/"
                    className="rounded-full border border-input bg-background px-6 py-2 text-sm font-semibold transition-colors hover:bg-accent hover:text-accent-foreground"
                  >
                    Go Home
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
