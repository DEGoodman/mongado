# API Documentation

## Interactive API Documentation

Mongado API comes with built-in interactive documentation powered by FastAPI:

**Local Development:**
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

**Production:**
- **Swagger UI**: [https://api.mongado.com/docs](https://api.mongado.com/docs)
- **ReDoc**: [https://api.mongado.com/redoc](https://api.mongado.com/redoc)
- **OpenAPI Schema**: [https://api.mongado.com/openapi.json](https://api.mongado.com/openapi.json)

## Using the Swagger UI

### Basic Usage

1. Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser
2. Browse available endpoints organized by tags (notes, resources, AI features)
3. Click on any endpoint to see details, parameters, and examples
4. Click "Try it out" to test endpoints directly from the browser

### Authentication

For admin-only endpoints (creating persistent notes, etc.):

1. Click the **Authorize** button (🔓) at the top right
2. Enter your admin token in the "Value" field (without "Bearer " prefix)
3. Click **Authorize** then **Close**
4. All subsequent requests will include your Bearer token

To get your admin token:
```bash
# From 1Password (if configured)
op read "op://Dev/Mongado Admin Token/password"

# Or check your .env file
cat backend/.env | grep ADMIN_TOKEN
```

### Session Management (Anonymous Users)

For testing ephemeral notes without authentication:

1. Generate a session ID: `curl http://localhost:8000/api/notes/generate-id`
2. Add `X-Session-ID` header with your session ID when testing endpoints
3. Ephemeral notes are only visible within the same session

## Common API Operations

### Create a Persistent Note (Admin)

```bash
curl -X POST http://localhost:8000/api/notes \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Note",
    "content": "This is a note with a [[wikilink]] to another note.",
    "tags": ["pkm", "learning"]
  }'
```

### Create an Ephemeral Note (Visitor)

```bash
curl -X POST http://localhost:8000/api/notes \
  -H "X-Session-ID: curious-elephant" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Temporary note for testing",
    "tags": ["test"]
  }'
```

### List All Notes

```bash
# As admin (sees all persistent notes)
curl -H "Authorization: Bearer your-admin-token" \
  http://localhost:8000/api/notes

# As visitor (sees only your ephemeral notes)
curl -H "X-Session-ID: curious-elephant" \
  http://localhost:8000/api/notes
```

### Get a Specific Note

```bash
curl http://localhost:8000/api/notes/semantic-web
```

### Update a Note

```bash
curl -X PUT http://localhost:8000/api/notes/semantic-web \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated content with new [[wikilinks]]",
    "title": "Semantic Web",
    "tags": ["web", "data", "standards"]
  }'
```

### Delete a Note

```bash
curl -X DELETE http://localhost:8000/api/notes/semantic-web \
  -H "Authorization: Bearer your-admin-token"
```

### Semantic Search

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "knowledge management systems",
    "top_k": 5
  }'
```

### Ask a Question (AI Q&A)

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the Zettelkasten method?"
  }'
```

### Get Graph Data

```bash
# Get full graph
curl http://localhost:8000/api/notes/graph/data

# Get local subgraph for a specific note
curl http://localhost:8000/api/notes/semantic-web/graph
```

### Get Backlinks

```bash
curl http://localhost:8000/api/notes/semantic-web/backlinks
```

### Get Outbound Links

```bash
curl http://localhost:8000/api/notes/semantic-web/links
```

## Bulk Operations

### Backup All Notes

Export all your notes to a JSON file:

```bash
curl -H "Authorization: Bearer your-admin-token" \
  http://localhost:8000/api/notes | \
  python3 -m json.tool > notes_backup_$(date +%Y%m%d).json
```

### Bulk Import Notes

Create a script to import multiple notes:

```bash
#!/bin/bash
TOKEN="your-admin-token"

# Read notes from a JSON file and import them
cat notes_to_import.json | jq -c '.[]' | while read note; do
  curl -X POST http://localhost:8000/api/notes \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$note"

  # Add small delay to respect rate limits
  sleep 0.5
done
```

## Rate Limits

- **Note Creation**: 10 notes per minute per IP address
- Other endpoints: No rate limits currently

## Response Codes

- `200` - Success
- `201` - Created (for POST requests)
- `400` - Bad request (missing required fields)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (trying to modify read-only resources)
- `404` - Not found
- `429` - Too many requests (rate limit exceeded)
- `500` - Internal server error
- `503` - Service unavailable (e.g., Ollama not running)

## Wikilinks

Notes support wikilinks using double bracket syntax: `[[note-id]]`

Wikilinks are automatically:
- Parsed from note content
- Stored as graph relationships in Neo4j
- Used to generate backlinks
- Rendered as clickable links in the frontend

Example:
```markdown
This note discusses [[zettelkasten-method]] which is related to [[knowledge-graphs]].

See also: [[note-taking]], [[second-brain]]
```

## Production Use

For production deployments:

1. **Always use HTTPS** to protect your Bearer token
2. **Rotate tokens regularly** for security
3. **Set up proper CORS** origins in production
4. **Use environment-specific tokens** (dev vs prod)
5. **Monitor rate limits** if exposing publicly

## See Also

- [Testing Guide](TESTING.md) - How to test the API
- [Setup Guide](SETUP.md) - Initial configuration
- [Knowledge Base Docs](knowledge-base/README.md) - Notes and articles system
