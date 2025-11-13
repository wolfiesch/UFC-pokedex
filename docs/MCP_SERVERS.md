# MCP Servers Documentation

This document describes the MCP (Model Context Protocol) servers configured for the UFC Pokedex project and how to use them with Claude Code.

## Overview

MCP servers extend Claude Code's capabilities by providing specialized tools for database interaction, API testing, and more. This project uses two custom MCP servers:

1. **postgres-mcp** - PostgreSQL database management and optimization
2. **rest-api** - REST API testing and debugging

## Installation Status

Both servers are installed and configured in `~/Library/Application Support/Claude/claude_desktop_config.json`.

**Note**: You must restart Claude Desktop/Claude Code after configuration changes for the servers to become available.

---

## Quick Start Guide

### Step 1: Verify Installation

Before using the MCP servers, make sure they're installed:

```bash
# Check postgres-mcp
which postgres-mcp
# Should output: /Users/<username>/.local/bin/postgres-mcp

# Check rest-api MCP
which dkmaker-mcp-rest-api
# Should output: /opt/homebrew/bin/dkmaker-mcp-rest-api (or similar)
```

### Step 2: Start Required Services

Make sure the UFC Pokedex services are running:

```bash
# Start the database (if using Docker)
make ensure-docker

# Start the API server
make run

# Verify services are running
pg_isready -h localhost -p 5432  # Database should respond
curl http://localhost:8000/health  # API should return {"status": "healthy"}
```

### Step 3: Restart Claude Code

After configuration changes, **completely quit and restart Claude Desktop/Claude Code** for the MCP servers to load.

### Step 4: Test Database MCP

Try these simple commands in Claude Code:

**Example 1: Explore the database**
```
Show me all tables in the UFC Pokedex database
```

**Example 2: Query fighter data**
```
Show me the top 5 fighters by number of wins
```

**Example 3: Check database health**
```
Run a health check on the database
```

**Expected Tools Used:**
- `mcp__postgres__list_objects`
- `mcp__postgres__execute_sql`
- `mcp__postgres__analyze_db_health`

### Step 5: Test API MCP

Try these API testing commands:

**Example 1: List all fighters**
```
Test the GET /api/fighters endpoint
```

**Example 2: Get a specific fighter**
```
Test getting fighter with ID bd58d34e39b7b12a
```

**Example 3: Test with filters**
```
Test the fighters API with query parameter weightclass=Lightweight
```

**Expected Tools Used:**
- `mcp__rest_api__test_request`

### Step 6: Common First Tasks

#### Database Exploration
```
1. "What tables exist in the database?"
2. "Show me the structure of the fighters table"
3. "How many fighters are in the database?"
4. "Show me fighters from the Lightweight division"
```

#### API Testing
```
1. "Test the /health endpoint"
2. "Test getting all events"
3. "Test the fighters search with query parameters"
4. "What's the response structure for the fighters endpoint?"
```

#### Performance Analysis
```
1. "Check the database health"
2. "What are the slowest queries?"
3. "Analyze the query that searches fighters by name"
4. "What indexes would help improve fighter lookups?"
```

### Troubleshooting Quick Start

**MCP tools not showing up?**
1. Verify you've completely restarted Claude Desktop/Claude Code
2. Check `~/Library/Application Support/Claude/claude_desktop_config.json` is valid JSON
3. Run `which postgres-mcp` and `which dkmaker-mcp-rest-api` to verify installation

**Database connection errors?**
1. Ensure PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Test connection manually: `psql postgresql://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex -c "SELECT 1;"`
3. Check Docker is running if using Docker mode

**API connection errors?**
1. Verify API is running: `curl http://localhost:8000/health`
2. Check no port conflicts: `lsof -i :8000`
3. Review backend logs for startup errors

**Still having issues?**
- See the full [Troubleshooting](#troubleshooting) section below
- Check MCP server logs in Claude Code
- Verify environment variables in config are correct

---

## 1. PostgreSQL MCP Server (`postgres-mcp`)

### Configuration

```json
{
  "postgres": {
    "command": "postgres-mcp",
    "args": [],
    "env": {
      "POSTGRES_CONNECTION_URI": "postgresql://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex",
      "ACCESS_MODE": "restricted"
    }
  }
}
```

### Access Modes

- **restricted** (default): Read-only queries, safe for exploration
- **unrestricted**: Full read/write access (use with caution)

### Available Tools

#### `list_schemas`
Lists all database schemas in the PostgreSQL instance.

**Example Usage:**
```
List all schemas in the UFC Pokedex database
```

**Use Cases:**
- Explore database structure
- Verify migrations have been applied
- Find specific schemas

---

#### `list_objects`
Lists database objects (tables, views, indexes, etc.) within a specified schema.

**Parameters:**
- `schema` - Schema name (e.g., "public")

**Example Usage:**
```
Show me all tables in the public schema
```

**Use Cases:**
- Discover available tables
- Find indexes on tables
- Locate views and materialized views

---

#### `get_object_details`
Provides detailed information about specific database objects including columns, data types, and constraints.

**Parameters:**
- `schema` - Schema name
- `object_name` - Table/view name

**Example Usage:**
```
Get the structure of the fighters table
```

**Use Cases:**
- Understand table schema before writing queries
- Verify column types and constraints
- Check foreign key relationships

---

#### `execute_sql`
Runs SQL statements. In restricted mode, only SELECT queries are allowed.

**Parameters:**
- `query` - SQL statement to execute

**Example Usage:**
```
Show me the top 10 fighters by number of wins
```

**SQL Example:**
```sql
SELECT name, record, wins
FROM fighters
ORDER BY wins DESC
LIMIT 10;
```

**Use Cases:**
- Explore data without writing Python scripts
- Quick data analysis
- Verify data integrity
- Generate reports

**Safety:**
- Restricted mode prevents UPDATE, DELETE, DROP
- Always use parameterized queries for user input
- Test queries on development database first

---

#### `explain_query`
Generates execution plans for SQL queries, showing how PostgreSQL will process them.

**Parameters:**
- `query` - SQL query to analyze
- `hypothetical_indexes` (optional) - Test index performance without creating them

**Example Usage:**
```
Explain the query plan for finding fighters by name
```

**SQL Example:**
```sql
EXPLAIN ANALYZE
SELECT * FROM fighters
WHERE name ILIKE '%conor%';
```

**Use Cases:**
- Debug slow queries
- Identify missing indexes
- Test index effectiveness before creating
- Optimize query performance

**Reading Results:**
- Look for "Seq Scan" (table scan) vs "Index Scan"
- Check "Execution Time" for actual performance
- "Rows" shows estimated vs actual row counts

---

#### `get_top_queries`
Reports the slowest SQL queries using `pg_stat_statements` data.

**Requirements:**
- `pg_stat_statements` extension must be enabled

**Example Usage:**
```
Show me the slowest queries in the database
```

**Use Cases:**
- Identify performance bottlenecks
- Find queries that need optimization
- Monitor database workload

---

#### `analyze_workload_indexes`
Identifies resource-intensive queries and recommends optimal indexes.

**Example Usage:**
```
Analyze the database workload and recommend indexes
```

**Use Cases:**
- Optimize database performance
- Reduce query execution time
- Improve application responsiveness

**What It Does:**
- Analyzes query patterns
- Identifies missing indexes
- Suggests index definitions
- Estimates performance improvement

---

#### `analyze_query_indexes`
Recommends indexes for a specific SQL query.

**Parameters:**
- `query` - SQL query to analyze

**Example Usage:**
```
What indexes would improve this query?
SELECT * FROM fights WHERE event_id = 'xyz' AND fighter_id = 'abc';
```

**Use Cases:**
- Optimize a specific slow query
- Design indexes for new features
- Understand query access patterns

---

#### `analyze_db_health`
Performs comprehensive health checks on the database.

**Example Usage:**
```
Check the health of the UFC Pokedex database
```

**Health Checks:**
- **Buffer cache hit rate** - How often data is found in memory
- **Connection health** - Active and idle connections
- **Constraint validation** - Integrity constraint status
- **Index health** - Bloat and effectiveness
- **Sequence limits** - Approaching max values
- **Vacuum health** - Table maintenance status

**Use Cases:**
- Regular database maintenance
- Troubleshoot performance issues
- Identify configuration problems
- Monitor database growth

---

## 2. REST API Testing MCP Server (`rest-api`)

### Configuration

```json
{
  "rest-api": {
    "command": "dkmaker-mcp-rest-api",
    "args": [],
    "env": {
      "BASE_URL": "http://localhost:8000",
      "TIMEOUT": "30000"
    }
  }
}
```

### Environment Variables

- **BASE_URL** - Base URL for API requests (default: http://localhost:8000)
- **TIMEOUT** - Request timeout in milliseconds (default: 30000)
- **AUTH_TYPE** - Authentication type (Bearer, Basic, ApiKey)
- **AUTH_TOKEN** - Token for Bearer authentication
- **API_KEY_HEADER** - Header name for API key auth
- **API_KEY_VALUE** - API key value

### Available Tool: `test_request`

The main tool for testing REST API endpoints.

**Parameters:**
- `method` - HTTP method (GET, POST, PUT, DELETE, PATCH)
- `endpoint` - API endpoint path (e.g., "/api/fighters")
- `body` (optional) - Request body as JSON string
- `headers` (optional) - Additional headers as object

---

### Example Usage

#### GET Request - List Fighters
```
Test the API endpoint GET /api/fighters
```

**Direct tool call:**
```typescript
test_request({
  "method": "GET",
  "endpoint": "/api/fighters"
})
```

---

#### GET Request - Single Fighter
```
Test getting fighter with ID bd58d34e39b7b12a
```

**Direct tool call:**
```typescript
test_request({
  "method": "GET",
  "endpoint": "/api/fighters/bd58d34e39b7b12a"
})
```

---

#### GET Request with Query Parameters
```
Test the fighters API with search filters
```

**Direct tool call:**
```typescript
test_request({
  "method": "GET",
  "endpoint": "/api/fighters?weightclass=Lightweight&limit=10"
})
```

---

#### POST Request - Create Resource
```
Test creating a new fighter via the API
```

**Direct tool call:**
```typescript
test_request({
  "method": "POST",
  "endpoint": "/api/fighters",
  "body": JSON.stringify({
    "name": "Test Fighter",
    "weightclass": "Welterweight"
  }),
  "headers": {
    "Content-Type": "application/json"
  }
})
```

---

#### PUT Request - Update Resource
```
Test updating fighter bd58d34e39b7b12a
```

**Direct tool call:**
```typescript
test_request({
  "method": "PUT",
  "endpoint": "/api/fighters/bd58d34e39b7b12a",
  "body": JSON.stringify({
    "record": "20-5-0"
  }),
  "headers": {
    "Content-Type": "application/json"
  }
})
```

---

#### DELETE Request
```
Test deleting a resource
```

**Direct tool call:**
```typescript
test_request({
  "method": "DELETE",
  "endpoint": "/api/fighters/test-id"
})
```

---

### Authentication

#### Bearer Token
Update configuration with:
```json
{
  "env": {
    "BASE_URL": "http://localhost:8000",
    "AUTH_TYPE": "Bearer",
    "AUTH_TOKEN": "your-jwt-token-here"
  }
}
```

#### API Key
Update configuration with:
```json
{
  "env": {
    "BASE_URL": "http://localhost:8000",
    "AUTH_TYPE": "ApiKey",
    "API_KEY_HEADER": "X-API-Key",
    "API_KEY_VALUE": "your-api-key-here"
  }
}
```

#### Basic Auth
Update configuration with:
```json
{
  "env": {
    "BASE_URL": "http://localhost:8000",
    "AUTH_TYPE": "Basic",
    "AUTH_USER": "username",
    "AUTH_PASS": "password"
  }
}
```

---

## Common Workflows

### 1. Explore Database Structure
```
1. List all schemas
2. Show tables in public schema
3. Get details of the fighters table
4. Execute a sample query to see data
```

### 2. Optimize a Slow Query
```
1. Get top queries to identify slow ones
2. Explain query to see execution plan
3. Analyze query indexes for recommendations
4. Test hypothetical indexes with explain_query
```

### 3. Database Health Check
```
1. Run analyze_db_health
2. Review buffer cache hit rate (should be >95%)
3. Check for index bloat
4. Verify vacuum is running properly
```

### 4. Test API Endpoint Flow
```
1. GET /api/fighters to list all fighters
2. POST /api/fighters to create a new one
3. GET /api/fighters/{id} to retrieve it
4. PUT /api/fighters/{id} to update it
5. DELETE /api/fighters/{id} to remove it
```

### 5. Verify API Changes
```
1. Test endpoint before code changes
2. Make code changes
3. Test endpoint after changes
4. Compare response structure and data
```

---

## Tips and Best Practices

### PostgreSQL MCP

✅ **Do:**
- Start in restricted mode for safety
- Use EXPLAIN ANALYZE to understand query performance
- Regularly check database health
- Test hypothetical indexes before creating them
- Use parameterized queries for dynamic values

❌ **Don't:**
- Run unrestricted mode on production databases
- Execute queries without understanding their impact
- Ignore index recommendations without investigation
- Create indexes without testing first

### REST API MCP

✅ **Do:**
- Test against local development server first
- Verify response status codes and structure
- Use proper Content-Type headers
- Test error cases (404, 400, 500)
- Document expected responses

❌ **Don't:**
- Test destructive operations on production
- Hardcode sensitive tokens in configuration
- Ignore timeout settings for slow endpoints
- Skip authentication testing

---

## Troubleshooting

### MCP Servers Not Available

**Problem:** Tools don't show up after configuration.

**Solutions:**
1. Restart Claude Desktop/Claude Code completely
2. Check configuration file syntax (valid JSON)
3. Verify installation: `which postgres-mcp` and `which dkmaker-mcp-rest-api`
4. Check Claude Code logs for errors

### PostgreSQL Connection Failed

**Problem:** Database connection errors.

**Solutions:**
1. Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Check credentials in connection URI
3. Ensure database exists: `psql -l`
4. Verify network access (localhost vs remote)

### API Requests Timeout

**Problem:** Requests take too long and fail.

**Solutions:**
1. Increase TIMEOUT in configuration (e.g., 60000 for 60 seconds)
2. Check if API server is running
3. Test endpoint directly with curl
4. Review server logs for errors

### Query Performance Issues

**Problem:** Queries are slow.

**Solutions:**
1. Use `explain_query` to see execution plan
2. Run `analyze_workload_indexes` for recommendations
3. Check `analyze_db_health` for general issues
4. Review `get_top_queries` for patterns

---

## Configuration File Location

**macOS/Linux:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

## Related Documentation

- [PostgreSQL MCP GitHub](https://github.com/crystaldba/postgres-mcp)
- [REST API MCP GitHub](https://github.com/dkmaker/mcp-rest-api)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [UFC Pokedex API Documentation](../backend/README.md)

---

**Last Updated:** 01/12/2025 11:45 PM
