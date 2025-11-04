/**
 * API Proxy Route
 *
 * Proxies all /api/* requests to the backend API server.
 * This works around Cloudflare tunnel SSL issues with the api subdomain
 * by routing all API traffic through the working frontend tunnel.
 *
 * Example:
 * Browser: https://ufc.wolfgangschoenberger.com/api/fighters/
 * → Next.js: http://localhost:8000/fighters/
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_SSR_API_BASE_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const path = params.path.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${API_BASE_URL}/${path}${searchParams ? `?${searchParams}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Don't cache to ensure fresh data
      cache: 'no-store',
    });

    // Get response body
    const data = await response.arrayBuffer();

    // Forward the response with original headers
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
        'Cache-Control': response.headers.get('Cache-Control') || 'no-cache',
        'Last-Modified': response.headers.get('Last-Modified') || '',
        'ETag': response.headers.get('ETag') || '',
      },
    });
  } catch (error) {
    console.error('API Proxy Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from API' },
      { status: 500 }
    );
  }
}
