# API Client Migration Guide

This guide explains how to migrate from the old manual `api.ts` functions to the new type-safe `api-client.ts` powered by OpenAPI code generation.

## Benefits of Migration

- ✅ **Full type safety**: All request parameters and responses are typed from the OpenAPI schema
- ✅ **Autocomplete**: IDE provides intelligent suggestions for all API calls
- ✅ **Compile-time validation**: Catch API contract violations before runtime
- ✅ **Auto-sync with backend**: Types regenerate from OpenAPI schema
- ✅ **Less code**: No manual type definitions needed

## Quick Start

### Before (Old API)
```ts
import { getFighters } from '@/lib/api';
import type { PaginatedFightersResponse } from '@/lib/types';

const response: PaginatedFightersResponse = await getFighters(20, 0);
console.log(response.fighters);
```

### After (Type-Safe Client)
```ts
import client from '@/lib/api-client';

const { data, error } = await client.GET('/fighters/', {
  params: {
    query: { limit: 20, offset: 0 }
  }
});

if (error) {
  // Handle error (typed!)
  console.error(error);
  return;
}

// data is fully typed from OpenAPI schema
console.log(data.fighters);
```

## Migration Examples

### Example 1: List Fighters
**Old:**
```ts
import { getFighters } from '@/lib/api';

async function loadFighters() {
  try {
    const data = await getFighters(20, 0);
    return data;
  } catch (error) {
    console.error('Failed to load fighters', error);
    throw error;
  }
}
```

**New:**
```ts
import client from '@/lib/api-client';

async function loadFighters() {
  const { data, error } = await client.GET('/fighters/', {
    params: {
      query: { limit: 20, offset: 0 }
    }
  });

  if (error) {
    console.error('Failed to load fighters', error);
    throw error;
  }

  return data;
}
```

### Example 2: Search Fighters
**Old:**
```ts
import { searchFighters } from '@/lib/api';

async function searchByName(query: string) {
  const data = await searchFighters(query, null, null, 20, 0);
  return data;
}
```

**New:**
```ts
import client from '@/lib/api-client';

async function searchByName(query: string) {
  const { data, error } = await client.GET('/search/', {
    params: {
      query: {
        q: query,
        limit: 20,
        offset: 0
      }
    }
  });

  if (error) throw error;
  return data;
}
```

### Example 3: Get Fighter Details
**Old:**
```ts
// Would need to add this function to api.ts manually
async function getFighterById(id: string) {
  const response = await fetch(`${API_URL}/fighters/${id}`);
  return response.json();
}
```

**New:**
```ts
import client from '@/lib/api-client';

async function getFighterById(id: string) {
  const { data, error } = await client.GET('/fighters/{fighter_id}', {
    params: {
      path: { fighter_id: id }
    }
  });

  if (error) throw error;
  return data;
}
```

### Example 4: Compare Fighters
**Old:**
```ts
import { compareFighters } from '@/lib/api';

async function compare(ids: string[]) {
  return await compareFighters(ids);
}
```

**New:**
```ts
import client from '@/lib/api-client';

async function compare(ids: string[]) {
  const { data, error } = await client.GET('/fighters/compare', {
    params: {
      query: { fighter_ids: ids }
    }
  });

  if (error) throw error;
  return data;
}
```

### Example 5: Get Fight Graph
**Old:**
```ts
import { getFightGraph } from '@/lib/api';

async function loadGraph() {
  return await getFightGraph({
    division: 'Lightweight',
    startYear: 2020,
    limit: 100
  });
}
```

**New:**
```ts
import client from '@/lib/api-client';

async function loadGraph() {
  const { data, error } = await client.GET('/fightweb/graph', {
    params: {
      query: {
        division: 'Lightweight',
        start_year: 2020,
        limit: 100
      }
    }
  });

  if (error) throw error;
  return data;
}
```

## Parameter Types

The new client automatically infers parameter types from the OpenAPI schema:

- **Path parameters**: `params.path.{param_name}`
- **Query parameters**: `params.query.{param_name}`
- **Request body**: `body: { ... }`
- **Headers**: `params.header.{header_name}`

## Error Handling

The client returns a tuple `{ data, error }`:

```ts
const { data, error } = await client.GET('/fighters/');

if (error) {
  // error is typed based on OpenAPI error schemas
  console.error(error.message);
  console.error(error.status); // HTTP status code
  return;
}

// data is typed based on OpenAPI success response
console.log(data.fighters);
```

## Type Inference

All types are automatically inferred - no imports needed!

```ts
const { data } = await client.GET('/fighters/');

// data.fighters is typed as FighterListItem[]
// TypeScript knows all fields and their types
const firstFighter = data.fighters[0];
console.log(firstFighter.name); // ✅ Typed!
console.log(firstFighter.invalidField); // ❌ Compile error!
```

## Regenerating Types

When the backend OpenAPI schema changes:

```bash
# Start backend first
make api-dev

# In another terminal, regenerate types
make types-generate

# Or manually
cd frontend && pnpm generate:types
```

Types are automatically regenerated on `make dev` and `make dev-local`.

## Incremental Migration Strategy

You don't need to migrate everything at once:

1. **Phase 1**: New features use the new client
2. **Phase 2**: Migrate hooks (`useFighters`, `useFighter`, etc.)
3. **Phase 3**: Migrate remaining components
4. **Phase 4**: Remove old `api.ts` and `types.ts`

Both clients can coexist during migration.

## Common Patterns

### With React Query / SWR
```ts
import useSWR from 'swr';
import client from '@/lib/api-client';

function useFighters(limit = 20, offset = 0) {
  return useSWR(
    `/fighters?limit=${limit}&offset=${offset}`,
    async () => {
      const { data, error } = await client.GET('/fighters/', {
        params: { query: { limit, offset } }
      });
      if (error) throw error;
      return data;
    }
  );
}
```

### In Server Components (Next.js)
```ts
import client from '@/lib/api-client';

export default async function FightersPage() {
  const { data, error } = await client.GET('/fighters/', {
    params: { query: { limit: 20, offset: 0 } }
  });

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <div>
      {data.fighters.map(fighter => (
        <div key={fighter.fighter_id}>{fighter.name}</div>
      ))}
    </div>
  );
}
```

## Troubleshooting

**Q: Types are stale after backend changes**
```bash
make types-generate
```

**Q: Backend is not running**
```bash
make api-dev  # Start backend first
```

**Q: TypeScript errors after regeneration**
The OpenAPI schema changed. Update your code to match the new contract.

**Q: Want to see all available endpoints**
Check `frontend/src/lib/generated/api-schema.ts` or the Swagger UI at `http://localhost:8000/docs`.

## Resources

- [openapi-typescript docs](https://openapi-ts.dev/)
- [openapi-fetch docs](https://openapi-ts.dev/openapi-fetch/)
- Backend API docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
