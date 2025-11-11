"""Custom retry middleware with exponential backoff for UFC.com scraping.

This middleware extends Scrapy's RetryMiddleware to implement exponential backoff
for rate limiting (429) and server errors (503), respecting Retry-After headers.
"""

from __future__ import annotations

import time

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Request, Response
from scrapy.spiders import Spider
from scrapy.utils.response import response_status_message


class UFCComRetryMiddleware(RetryMiddleware):
    """Custom retry logic with exponential backoff for UFC.com.

    Features:
    - Respects Retry-After header when present
    - Exponential backoff for rate limiting (429) and server errors (503)
    - Max backoff of 5 minutes
    - Logs wait times for monitoring
    """

    def process_response(
        self, request: Request, response: Response, spider: Spider
    ) -> Response | Request:
        """Process response and retry with backoff on rate limits or errors.

        Args:
            request: The request that generated this response
            response: The response to process
            spider: The spider instance

        Returns:
            Either the original response or a retry request
        """
        # Check if this is a retryable status code
        if response.status in [429, 503]:
            return self._retry_with_backoff(request, response, spider)

        # Let parent class handle other retry logic
        return super().process_response(request, response, spider)

    def _retry_with_backoff(
        self, request: Request, response: Response, spider: Spider
    ) -> Response | Request:
        """Retry request with exponential backoff.

        Args:
            request: The request to retry
            response: The response that triggered the retry
            spider: The spider instance

        Returns:
            Either a retry request or the original response if max retries exceeded
        """
        retry_times = request.meta.get("retry_times", 0) + 1
        max_retry_times = self.max_retry_times

        if retry_times <= max_retry_times:
            # Check for Retry-After header
            retry_after = response.headers.get(b"Retry-After")

            if retry_after:
                try:
                    delay = int(retry_after.decode())
                    spider.logger.warning(
                        f"Rate limited! Retry-After header: {delay}s "
                        f"(attempt {retry_times}/{max_retry_times})"
                    )
                except (ValueError, UnicodeDecodeError):
                    # If Retry-After is not an integer, use exponential backoff
                    delay = self._calculate_backoff_delay(retry_times)
                    spider.logger.warning(
                        f"Rate limited! Using exponential backoff: {delay}s "
                        f"(attempt {retry_times}/{max_retry_times})"
                    )
            else:
                # No Retry-After header, use exponential backoff
                delay = self._calculate_backoff_delay(retry_times)
                spider.logger.warning(
                    f"Server error {response.status}! Exponential backoff: {delay}s "
                    f"(attempt {retry_times}/{max_retry_times})"
                )

            # Sleep before retrying
            time.sleep(delay)

            # Create retry request
            reason = response_status_message(response.status)
            retry_request = self._retry(request, reason, spider) or response

            # Update retry metadata
            if isinstance(retry_request, Request):
                retry_request.meta["retry_times"] = retry_times

            return retry_request

        else:
            spider.logger.error(
                f"Gave up retrying {request.url} after {max_retry_times} attempts "
                f"(status: {response.status})"
            )
            return response

    def _calculate_backoff_delay(self, retry_count: int) -> int:
        """Calculate exponential backoff delay.

        Formula: min(2^retry_count, 300)
        - retry_count=1: 2s
        - retry_count=2: 4s
        - retry_count=3: 8s
        - retry_count=4: 16s
        - retry_count=5: 32s
        - retry_count=6+: 64s...300s (max 5 minutes)

        Args:
            retry_count: Number of retry attempts

        Returns:
            Delay in seconds
        """
        return min(2**retry_count, 300)
