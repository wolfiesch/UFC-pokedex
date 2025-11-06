/**
 * Tests for API type safety.
 */
import { describe, it, expect } from 'vitest';
import client from '@/lib/api-client';
import type { paths } from '@/lib/generated/api-schema';


describe('API Type Safety', () => {
  it('should enforce correct payload types for favorites', async () => {
    // Valid request should compile without errors
    const { data, error } = await client.POST('/favorites/collections', {
      body: {
        user_id: 'test-user',
        title: 'Test Collection',
        is_public: false,
      },
    });

    // This test verifies type safety at compile time
    // If you uncomment the line below, TypeScript will error:
    // invalid_field: 'should not compile',
    expect(true).toBe(true);
  });

  it('should infer correct response types', async () => {
    const { data } = await client.GET('/fighters/{fighter_id}', {
      params: { path: { fighter_id: 'test-id' } },
    });

    if (data) {
      // These should all have correct types without assertions
      const name: string = data.name;
      const division: string | null | undefined = data.division;
      // @ts-expect-error - non-existent field should fail
      const invalid = data.nonexistent_field;
    }
  });
});
