# Production Deployment Guide

This guide covers deploying Mongado to production.

## Critical Configuration

### Backend Environment Variables

The backend requires the following environment variables in production:

```bash
# REQUIRED: CORS Origins
# Comma-separated list of allowed frontend domains
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# REQUIRED: Admin Authentication
ADMIN_TOKEN=your-strong-random-token-here

# OPTIONAL: 1Password Integration
OP_MONGADO_SERVICE_ACCOUNT_TOKEN=ops_xxxxx...

# OPTIONAL: Neo4j (for persistent notes)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# OPTIONAL: Ollama (for AI features)
OLLAMA_HOST=http://ollama:11434
OLLAMA_ENABLED=true
```

### Frontend Environment Variables

The frontend needs to know where the backend API is:

```bash
# Build-time variable (must be set before `npm run build`)
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

**Important**: `NEXT_PUBLIC_API_URL` must be set at **build time**, not runtime. If you change this value, you must rebuild the frontend container.

## Common Production Issues

### "Failed to fetch" or "Failed to connect to server"

**Symptoms:**
- AI Assistant returns "Error: Failed to fetch"
- Notes page doesn't load
- Login fails with "Failed to connect to server"

**Causes & Solutions:**

1. **CORS Misconfiguration** (Most Common)
   - **Problem**: Backend `CORS_ORIGINS` doesn't include your frontend domain
   - **Solution**: Update backend `.env` with your actual domain(s):
     ```bash
     CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
     ```
   - **Verify**: Check backend logs on startup. Should show:
     ```
     CORS allowed origins: ['https://yourdomain.com', 'https://www.yourdomain.com']
     ```

2. **Wrong API URL in Frontend**
   - **Problem**: Frontend is trying to connect to `localhost` instead of your API domain
   - **Solution**: Set `NEXT_PUBLIC_API_URL` before building:
     ```bash
     NEXT_PUBLIC_API_URL=https://api.yourdomain.com npm run build
     ```
   - **Verify**: Check browser DevTools Network tab. API requests should go to your production domain, not `localhost:8000`

3. **Backend Not Running**
   - **Problem**: Backend container crashed or didn't start
   - **Solution**: Check logs: `docker compose logs -f backend`
   - **Common causes**: Missing environment variables, Neo4j connection failed

4. **Network Isolation**
   - **Problem**: Frontend can't reach backend (different networks, firewall, etc.)
   - **Solution**: Verify containers are on same Docker network, firewall rules allow traffic

### Debugging Steps

1. **Check backend logs**:
   ```bash
   docker compose logs backend
   # Look for startup message showing CORS origins
   ```

2. **Check frontend is using correct API URL**:
   - Open browser DevTools → Network tab
   - Try an API action (e.g., open Notes page)
   - Check the request URL - should be your production domain, not localhost

3. **Test backend directly**:
   ```bash
   curl https://api.yourdomain.com/
   # Should return: {"message":"Mongado API","version":"0.1.0",...}
   ```

4. **Check CORS headers**:
   ```bash
   curl -H "Origin: https://yourdomain.com" \
        -H "Access-Control-Request-Method: POST" \
        -X OPTIONS \
        https://api.yourdomain.com/api/notes
   # Should include: Access-Control-Allow-Origin: https://yourdomain.com
   ```

## Deployment Checklist

### Before Deploying

- [ ] Set `CORS_ORIGINS` in backend `.env`
- [ ] Set `NEXT_PUBLIC_API_URL` before building frontend
- [ ] Generate strong `ADMIN_TOKEN` and store securely
- [ ] Configure Neo4j if using persistent notes
- [ ] Set up 1Password service account if using secrets management

### After Deploying

- [ ] Verify backend starts: check logs for CORS origins message
- [ ] Test backend health: `curl https://api.yourdomain.com/`
- [ ] Test frontend loads: visit your domain in browser
- [ ] Test API connectivity: try opening Notes or AI Assistant
- [ ] Test authentication: try logging in

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | **Yes** | `http://localhost:3000` | Comma-separated list of allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | **Yes** | `http://localhost:8000` | Backend API URL (must be set at build time) |
| `ADMIN_TOKEN` | Recommended | - | Bearer token for admin authentication |
| `NEO4J_URI` | No | `bolt://localhost:7687` | Neo4j connection string |
| `NEO4J_PASSWORD` | No | - | Neo4j password |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_ENABLED` | No | `true` | Enable/disable AI features |

## Docker Compose Production

```yaml
# docker-compose.prod.yml
services:
  backend:
    build:
      context: ./backend
      target: production
    environment:
      - CORS_ORIGINS=https://yourdomain.com
      - ADMIN_TOKEN=${ADMIN_TOKEN}
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      target: production
      args:
        - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
    ports:
      - "3000:3000"
```

## Troubleshooting Tips

1. **Always check logs first**: Most issues show clear error messages in logs
2. **Verify environment variables**: Use `docker compose config` to see resolved values
3. **Test incrementally**: Verify backend health before testing frontend
4. **Use browser DevTools**: Network tab shows exact requests and responses
5. **Check CORS headers**: Use `curl` with `Origin` header to test CORS

## Security Notes

- Never commit `.env` files with real secrets
- Use strong random tokens for `ADMIN_TOKEN` (64+ characters)
- Enable HTTPS in production (use reverse proxy like Caddy or Nginx)
- Limit `CORS_ORIGINS` to your actual domains only
- Keep 1Password tokens secure - never log or expose them
