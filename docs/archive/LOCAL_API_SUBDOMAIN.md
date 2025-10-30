# Local API Subdomain Setup (Optional)

This guide shows how to set up `api.localhost` for local development to mirror the production subdomain structure.

## Why?

In production, the API is accessible at `https://api.mongado.com`. To test the same subdomain structure locally, you can set up `http://api.localhost:8000`.

**Note:** This is completely optional. You can continue using `http://localhost:8000` if you prefer.

## Option 1: Use /etc/hosts (Recommended)

Add a local DNS entry to route `api.localhost` to `127.0.0.1`:

```bash
# Add to /etc/hosts
echo "127.0.0.1 api.localhost" | sudo tee -a /etc/hosts
```

Now you can access:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000` or `http://api.localhost:8000`
- API Docs: `http://localhost:8000/docs` or `http://api.localhost:8000/docs`

## Option 2: Use a Local Nginx Proxy

Set up nginx locally to proxy requests:

```bash
# Install nginx (if not already installed)
brew install nginx  # macOS
# or
sudo apt install nginx  # Linux

# Create local config
cat > /usr/local/etc/nginx/servers/mongado.conf << 'EOF'
# Frontend
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Backend API
server {
    listen 80;
    server_name api.localhost;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Start nginx
sudo nginx
# or
brew services start nginx
```

Then add to `/etc/hosts`:
```bash
echo "127.0.0.1 api.localhost" | sudo tee -a /etc/hosts
```

Now you can access:
- Frontend: `http://localhost` (port 80)
- Backend: `http://api.localhost` (port 80)
- API Docs: `http://api.localhost/docs`

## Verification

Test the setup:

```bash
# Test backend API
curl http://api.localhost:8000/
# or with nginx proxy
curl http://api.localhost/

# Should return: {"message":"Mongado API","version":"0.1.0",...}

# Test API docs
curl http://api.localhost:8000/docs | head -10
```

## Cleanup

To remove the local subdomain setup:

```bash
# Remove from /etc/hosts
sudo sed -i.bak '/api.localhost/d' /etc/hosts

# Stop nginx (if using Option 2)
brew services stop nginx  # macOS
# or
sudo systemctl stop nginx  # Linux
```

## Frontend Configuration

If you want the frontend to use the subdomain in local development, update `frontend/.env.local`:

```bash
# Use subdomain locally
NEXT_PUBLIC_API_URL=http://api.localhost:8000

# Or continue using localhost
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart the frontend after changing this value.
