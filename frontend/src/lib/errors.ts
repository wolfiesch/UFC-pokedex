/**
 * Custom error types for the UFC Pokedex application.
 * Provides detailed error information for better user experience.
 */

export enum ErrorType {
  VALIDATION_ERROR = "validation_error",
  NOT_FOUND = "not_found",
  DATABASE_ERROR = "database_error",
  NETWORK_ERROR = "network_error",
  INTERNAL_ERROR = "internal_error",
  TIMEOUT_ERROR = "timeout_error",
  AUTHENTICATION_ERROR = "authentication_error",
  AUTHORIZATION_ERROR = "authorization_error",
  PARSE_ERROR = "parse_error",
  UNKNOWN_ERROR = "unknown_error",
}

export interface ValidationErrorDetail {
  field: string;
  message: string;
  value?: unknown;
}

export interface ErrorResponseData {
  error_type?: string;
  message: string;
  detail?: string;
  status_code?: number;
  timestamp?: string;
  request_id?: string;
  path?: string;
  retry_after?: number;
  errors?: ValidationErrorDetail[];
}

/**
 * Base API error class with detailed information
 */
export class ApiError extends Error {
  public readonly errorType: ErrorType;
  public readonly statusCode: number;
  public readonly detail?: string;
  public readonly timestamp: Date;
  public readonly requestId?: string;
  public readonly path?: string;
  public readonly retryAfter?: number;
  public readonly validationErrors?: ValidationErrorDetail[];
  public readonly retryCount: number;
  public readonly isRetryable: boolean;

  constructor(
    message: string,
    options: {
      errorType?: ErrorType;
      statusCode?: number;
      detail?: string;
      timestamp?: Date | string;
      requestId?: string;
      path?: string;
      retryAfter?: number;
      validationErrors?: ValidationErrorDetail[];
      retryCount?: number;
      cause?: Error;
    } = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.errorType = options.errorType || ErrorType.UNKNOWN_ERROR;
    this.statusCode = options.statusCode || 500;
    this.detail = options.detail;
    this.timestamp =
      options.timestamp instanceof Date
        ? options.timestamp
        : options.timestamp
          ? new Date(options.timestamp)
          : new Date();
    this.requestId = options.requestId;
    this.path = options.path;
    this.retryAfter = options.retryAfter;
    this.validationErrors = options.validationErrors;
    this.retryCount = options.retryCount || 0;

    // Determine if error is retryable based on status code and error type
    this.isRetryable = this.determineRetryability();

    if (options.cause) {
      this.cause = options.cause;
    }
  }

  private determineRetryability(): boolean {
    // Network errors are always retryable
    if (this.errorType === ErrorType.NETWORK_ERROR) {
      return true;
    }

    // Timeout errors are retryable
    if (this.errorType === ErrorType.TIMEOUT_ERROR) {
      return true;
    }

    // 5xx server errors are retryable
    if (this.statusCode >= 500 && this.statusCode < 600) {
      return true;
    }

    // 429 Too Many Requests is retryable
    if (this.statusCode === 429) {
      return true;
    }

    // 408 Request Timeout is retryable
    if (this.statusCode === 408) {
      return true;
    }

    // 4xx client errors (except above) are NOT retryable
    if (this.statusCode >= 400 && this.statusCode < 500) {
      return false;
    }

    return false;
  }

  /**
   * Get a user-friendly error message
   */
  getUserMessage(): string {
    if (this.validationErrors && this.validationErrors.length > 0) {
      const errorList = this.validationErrors
        .map((e) => `${e.field}: ${e.message}`)
        .join(", ");
      return `${this.message}: ${errorList}`;
    }

    if (this.detail) {
      return `${this.message}: ${this.detail}`;
    }

    return this.message;
  }

  /**
   * Get a technical error summary for debugging
   */
  getTechnicalSummary(): string {
    const parts: string[] = [
      `[${this.errorType}]`,
      `HTTP ${this.statusCode}`,
      this.message,
    ];

    if (this.detail) {
      parts.push(`- ${this.detail}`);
    }

    if (this.requestId) {
      parts.push(`(Request ID: ${this.requestId})`);
    }

    if (this.retryCount > 0) {
      parts.push(`(Retry attempt ${this.retryCount})`);
    }

    return parts.join(" ");
  }

  /**
   * Create ApiError from backend error response
   */
  static fromResponse(data: ErrorResponseData, statusCode: number): ApiError {
    const errorType = data.error_type
      ? (data.error_type as ErrorType)
      : ErrorType.UNKNOWN_ERROR;

    return new ApiError(data.message, {
      errorType,
      statusCode,
      detail: data.detail,
      timestamp: data.timestamp,
      requestId: data.request_id,
      path: data.path,
      retryAfter: data.retry_after,
      validationErrors: data.errors,
    });
  }

  /**
   * Create ApiError from fetch network error
   */
  static fromNetworkError(error: Error, retryCount = 0): ApiError {
    return new ApiError("Network request failed", {
      errorType: ErrorType.NETWORK_ERROR,
      statusCode: 0,
      detail: error.message,
      retryCount,
      cause: error,
    });
  }

  /**
   * Create ApiError from timeout
   */
  static fromTimeout(timeoutMs: number): ApiError {
    return new ApiError("Request timeout", {
      errorType: ErrorType.TIMEOUT_ERROR,
      statusCode: 408,
      detail: `Request took longer than ${timeoutMs}ms`,
    });
  }

  /**
   * Create ApiError from JSON parse error
   */
  static fromParseError(error: Error): ApiError {
    return new ApiError("Failed to parse server response", {
      errorType: ErrorType.PARSE_ERROR,
      statusCode: 500,
      detail: error.message,
      cause: error,
    });
  }
}

/**
 * Network-specific error (connection issues, DNS failures, etc.)
 */
export class NetworkError extends ApiError {
  constructor(message: string, detail?: string, retryCount = 0) {
    super(message, {
      errorType: ErrorType.NETWORK_ERROR,
      statusCode: 0,
      detail,
      retryCount,
    });
    this.name = "NetworkError";
  }
}

/**
 * Resource not found error (404)
 */
export class NotFoundError extends ApiError {
  constructor(resource: string, detail?: string) {
    super(`${resource} not found`, {
      errorType: ErrorType.NOT_FOUND,
      statusCode: 404,
      detail,
    });
    this.name = "NotFoundError";
  }
}

/**
 * Validation error (422)
 */
export class ValidationError extends ApiError {
  constructor(
    message: string,
    validationErrors: ValidationErrorDetail[],
    detail?: string
  ) {
    super(message, {
      errorType: ErrorType.VALIDATION_ERROR,
      statusCode: 422,
      detail,
      validationErrors,
    });
    this.name = "ValidationError";
  }
}

/**
 * Server error (5xx)
 */
export class ServerError extends ApiError {
  constructor(message: string, statusCode: number, detail?: string) {
    super(message, {
      errorType: ErrorType.INTERNAL_ERROR,
      statusCode,
      detail,
    });
    this.name = "ServerError";
  }
}

/**
 * Timeout error
 */
export class TimeoutError extends ApiError {
  constructor(message: string, timeoutMs: number) {
    super(message, {
      errorType: ErrorType.TIMEOUT_ERROR,
      statusCode: 408,
      detail: `Request took longer than ${timeoutMs}ms`,
    });
    this.name = "TimeoutError";
  }
}
