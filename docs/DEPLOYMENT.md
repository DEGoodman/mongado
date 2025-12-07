# Deployment Guide

This guide covers deploying Mongado to DigitalOcean using GitHub Actions for continuous deployment.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         mongado.com                         │
│                     (Hover.com DNS)                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
 A: Frontend            A: Backend API
 mongado.com            api.mongado.com
      │                       │
      │                       │
      ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│              DigitalOcean Droplet                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Nginx (Frontend)│  │ FastAPI (Backend)│                │
│  │  Port: 80/443    │  │ Port: 8000       │                │
│  │  Docker          │  │ Docker           │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Neo4j Database  │  │  Static Files    │                │
│  │  Port: 7687      │  │  /opt/mongado    │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. DigitalOcean Account Setup

You've already authenticated GitHub with DigitalOcean, which is great! Now you need:

1. **Create a Droplet** (if you haven't already):
   - Go to DigitalOcean dashboard → Create → Droplets
   - Choose: Ubuntu 22.04 LTS
   - Plan: Basic ($12/month recommended for start)
     - 2 GB RAM / 1 CPU
     - 50 GB SSD
     - 2 TB transfer
   - Add SSH key (generate if needed)
   - Choose datacenter region (closest to your users)
   - Hostname: `mongado-prod`

2. **Note your Droplet IP address** (you'll need this for DNS)

### 2. Domain Configuration (Hover.com)

Since you already use Fastmail for email at mongado.com, you need to carefully add DNS records without breaking email.

**Important**: Do NOT remove existing MX records for Fastmail!

#### Current DNS Records (Keep These)

Your existing Fastmail MX records should look like:
```
Type: MX   Name: @   Value: in1-smtp.messagingengine.com   Priority: 10
Type: MX   Name: @   Value: in2-smtp.messagingengine.com   Priority: 20
Type: TXT  Name: @   Value: v=spf1 include:spf.messagingengine.com ?all
```

#### New DNS Records to Add

Add these A records for your website:

```
Type: A    Name: @              Value: <YOUR_DROPLET_IP>   TTL: 3600
Type: A    Name: www            Value: <YOUR_DROPLET_IP>   TTL: 3600
Type: A    Name: api            Value: <YOUR_DROPLET_IP>   TTL: 3600
```

**Result**:
- `mongado.com` → your droplet (website)
- `www.mongado.com` → your droplet (website)
- `api.mongado.com` → your droplet (API)
- `mail.mongado.com` → Fastmail (email unchanged)
- MX records → Fastmail (email unchanged)

**Note**: DNS propagation takes 1-48 hours, but usually completes within 30 minutes.

### 3. GitHub Secrets Setup

Go to your GitHub repo: `github.com/degoodman/mongado` → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Description | Example Value | How to Generate |
|------------|-------------|---------------|-----------------|
| `DO_SSH_PRIVATE_KEY` | SSH private key for droplet access | `-----BEGIN OPENSSH PRIVATE KEY-----...` | `cat ~/.ssh/id_rsa` or generate new keypair |
| `DO_HOST` | Droplet IP address | `164.90.xxx.xxx` | DigitalOcean dashboard |
| `DO_USER` | SSH user (usually `root`) | `root` | Default: `root` |
| `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` | 1Password service account token | `ops_xxx...` | 1Password → Developer → Service Accounts |
| `ADMIN_PASSKEY` | Admin authentication passkey | `your-secret-passkey-here` | `openssl rand -base64 32` |
| `NEXT_PUBLIC_API_URL` | Production API URL | `https://api.mongado.com` | Your API domain |

### Environment Variables Reference

#### Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | **Yes** | `http://localhost:3000` | Comma-separated list of allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | **Yes** | `http://localhost:8000` | Backend API URL (must be set at build time) |
| `ADMIN_TOKEN` | **Yes** | - | Bearer token for admin authentication |
| `NEO4J_PASSWORD` | **Yes** | - | Neo4j database password (auto-constructs NEO4J_AUTH) |

#### Optional Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` | No | - | 1Password service account token |
| `NEO4J_URI` | No | `bolt://localhost:7687` | Neo4j connection string |
| `NEO4J_USER` | No | `neo4j` | Neo4j username |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_ENABLED` | No | `true` | Enable/disable AI features |
| `DEBUG` | No | `false` | Enable debug mode (set to `false` in production) |

**Important Notes**:
- `NEXT_PUBLIC_API_URL` must be set at **build time**, not runtime. If you change this value, you must rebuild the frontend container.
- `CORS_ORIGINS` must include all domains that will access your API (both `mongado.com` and `www.mongado.com`)
- Use strong random tokens for `ADMIN_TOKEN` (64+ characters): `openssl rand -base64 64`

**To get your SSH private key**:
```bash
# On your local machine
cat ~/.ssh/id_rsa

# Or generate a new one specifically for deployment
ssh-keygen -t ed25519 -C "github-actions-mongado" -f ~/.ssh/mongado_deploy
cat ~/.ssh/mongado_deploy  # This is your private key for GitHub secrets
```

## DigitalOcean Droplet Setup

SSH into your droplet and run these commands:

### 1. Initial Server Setup

```bash
# SSH into your droplet
ssh root@<YOUR_DROPLET_IP>

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installations
docker --version
docker compose version

# Install other utilities
apt install -y git curl wget nginx certbot python3-certbot-nginx

# Create project directory
mkdir -p /opt/mongado
cd /opt/mongado

# Clone your repository (you'll be prompted for credentials)
git clone https://github.com/degoodman/mongado.git .

# Set up Git to remember credentials for future pulls
git config --global credential.helper store
```

### 2. Set Up Nginx as Reverse Proxy

Create Nginx configuration:

```bash
# Create Nginx config for Mongado
cat > /etc/nginx/sites-available/mongado << 'EOF'
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name mongado.com www.mongado.com api.mongado.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# Frontend - mongado.com and www.mongado.com
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mongado.com www.mongado.com;

    # SSL certificates (will be set up by certbot)
    ssl_certificate /etc/letsencrypt/live/mongado.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mongado.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to frontend container
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Backend API - api.mongado.com
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.mongado.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/mongado.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mongado.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to backend container
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable the site
ln -s /etc/nginx/sites-available/mongado /etc/nginx/sites-enabled/

# Remove default site
rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Restart Nginx
systemctl restart nginx
```

### 3. Set Up SSL Certificates (Let's Encrypt)

**Important**: Wait until DNS has propagated (your A records point to the droplet) before running this!

```bash
# Verify DNS is working first
dig mongado.com +short  # Should return your droplet IP
dig api.mongado.com +short  # Should return your droplet IP

# Request SSL certificates for all domains
certbot --nginx -d mongado.com -d www.mongado.com -d api.mongado.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# Verify auto-renewal works
certbot renew --dry-run

# Certificates will auto-renew via cron
```

### 4. Set Up Firewall

```bash
# Configure UFW firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable

# Verify
ufw status
```

### 5. Set Up Environment Variables

```bash
cd /opt/mongado

# Create backend .env file (will be overwritten by GitHub Actions, but useful for manual testing)
cat > backend/.env << 'EOF'
DEBUG=false
OP_MONGADO_SERVICE_ACCOUNT_TOKEN=your-token-here
ADMIN_PASSKEY=your-passkey-here
EOF

# Set permissions
chmod 600 backend/.env
```

### 6. First Manual Deployment

```bash
cd /opt/mongado

# Export environment variables
export NEXT_PUBLIC_API_URL="https://api.mongado.com"
export OP_MONGADO_SERVICE_ACCOUNT_TOKEN="your-token-here"

# Build and start containers
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Verify containers are running
docker ps
```

### 7. Add GitHub Actions SSH Key

```bash
# Add the public key from your GitHub Actions SSH keypair to authorized_keys
echo "ssh-ed25519 AAAAC3... github-actions-mongado" >> ~/.ssh/authorized_keys

# Set proper permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## GitHub Actions Workflow

The deployment workflow (`.github/workflows/deploy.yml`) will:

1. ✅ Run CI checks (tests, linting, type checking)
2. 🔐 SSH into your DigitalOcean droplet
3. 📦 Pull latest code from `main` branch
4. 🐳 Build Docker images
5. 🚀 Deploy new containers
6. 🏥 Run health checks
7. ✅ Verify deployment or rollback on failure

**Deployment triggers:**
- Push to `main` branch (automatic)
- Manual trigger via GitHub Actions UI

## Deployment Process

### Automatic Deployment

1. Push code to `main` branch:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. GitHub Actions will automatically:
   - Run CI pipeline
   - Deploy to DigitalOcean (if CI passes)
   - Verify the deployment

3. Monitor deployment:
   - Go to GitHub repo → Actions tab
   - Watch the "Deploy to DigitalOcean" workflow

### Manual Deployment

1. Go to GitHub repo → Actions → "Deploy to DigitalOcean"
2. Click "Run workflow" → Select `main` branch → Run
3. Monitor progress in the Actions tab

### Rollback

If deployment fails, the workflow automatically rolls back to the previous version.

**Manual rollback** (if needed):
```bash
# SSH into droplet
ssh root@<YOUR_DROPLET_IP>

cd /opt/mongado

# View commit history
git log --oneline -n 10

# Rollback to a specific commit
git reset --hard <commit-hash>

# Restart containers
docker compose -f docker-compose.prod.yml up -d
```

## Monitoring & Maintenance

### View Logs

```bash
# SSH into droplet
ssh root@<YOUR_DROPLET_IP>

cd /opt/mongado

# All containers
docker compose -f docker-compose.prod.yml logs -f

# Specific container
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Health Checks

```bash
# Check backend API
curl https://api.mongado.com/

# Check frontend
curl https://mongado.com/

# Check container status
docker ps

# Check container health
docker inspect --format='{{.State.Health.Status}}' mongado-backend-prod
docker inspect --format='{{.State.Health.Status}}' mongado-frontend-prod
```

### Update System

```bash
# SSH into droplet
ssh root@<YOUR_DROPLET_IP>

# Update packages
apt update && apt upgrade -y

# Update Docker images (from within /opt/mongado)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Clean up old images
docker image prune -a -f
```

### Database Backups

**For Neo4j** (when you add it):
```bash
# Create backup script
cat > /opt/mongado/scripts/backup-neo4j.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/mongado/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

docker exec mongado-neo4j neo4j-admin database dump neo4j \
  --to-path=/backups/neo4j_backup_$DATE.dump

# Keep last 7 days of backups
find $BACKUP_DIR -name "neo4j_backup_*.dump" -mtime +7 -delete
EOF

chmod +x /opt/mongado/scripts/backup-neo4j.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/mongado/scripts/backup-neo4j.sh") | crontab -
```

## Common Production Issues & Troubleshooting

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
     CORS_ORIGINS=https://mongado.com,https://www.mongado.com
     ```
   - **Verify**: Check backend logs on startup. Should show:
     ```
     CORS allowed origins: ['https://mongado.com', 'https://www.mongado.com']
     ```

2. **Wrong API URL in Frontend**
   - **Problem**: Frontend is trying to connect to `localhost` instead of your API domain
   - **Solution**: Set `NEXT_PUBLIC_API_URL` before building:
     ```bash
     NEXT_PUBLIC_API_URL=https://api.mongado.com npm run build
     ```
   - **Verify**: Check browser DevTools Network tab. API requests should go to your production domain, not `localhost:8000`

3. **Backend Not Running**
   - **Problem**: Backend container crashed or didn't start
   - **Solution**: Check logs: `docker compose -f docker-compose.prod.yml logs -f backend`
   - **Common causes**: Missing environment variables, Neo4j connection failed

4. **Network Isolation**
   - **Problem**: Frontend can't reach backend (different networks, firewall, etc.)
   - **Solution**: Verify containers are on same Docker network, firewall rules allow traffic

### Debugging Steps

1. **Check backend logs**:
   ```bash
   ssh root@<YOUR_DROPLET_IP>
   cd /opt/mongado
   docker compose -f docker-compose.prod.yml logs backend
   # Look for startup message showing CORS origins
   ```

2. **Check frontend is using correct API URL**:
   - Open browser DevTools → Network tab
   - Try an API action (e.g., open Notes page)
   - Check the request URL - should be your production domain, not localhost

3. **Test backend directly**:
   ```bash
   curl https://api.mongado.com/
   # Should return: {"message":"Mongado API","version":"0.1.0",...}
   ```

4. **Check CORS headers**:
   ```bash
   curl -H "Origin: https://mongado.com" \
        -H "Access-Control-Request-Method: POST" \
        -X OPTIONS \
        https://api.mongado.com/api/notes
   # Should include: Access-Control-Allow-Origin: https://mongado.com
   ```

### Deployment Fails

1. **Check GitHub Actions logs**:
   - Go to repo → Actions → Click failed workflow
   - Expand steps to see detailed error messages

2. **Check droplet logs**:
   ```bash
   ssh root@<YOUR_DROPLET_IP>
   cd /opt/mongado
   docker compose -f docker-compose.prod.yml logs --tail=100
   ```

3. **Common issues**:
   - SSH key not added to droplet
   - Insufficient disk space: `df -h`
   - Docker not running: `systemctl status docker`
   - Port conflicts: `netstat -tulpn`
   - CORS misconfiguration (see above)

### DNS Not Working

1. **Verify DNS propagation**:
   ```bash
   # From your local machine
   dig mongado.com +short
   dig api.mongado.com +short
   ```

2. **Check Hover.com DNS settings**:
   - Ensure A records point to correct droplet IP
   - TTL should be 3600 seconds (1 hour)

3. **Fastmail email still working?**:
   - Verify MX records are untouched
   - Test sending/receiving email

### SSL Certificate Issues

1. **Certificate not issued**:
   ```bash
   # Check if DNS is resolving first
   dig mongado.com +short

   # Try again
   certbot --nginx -d mongado.com -d www.mongado.com -d api.mongado.com
   ```

2. **Certificate expired** (shouldn't happen with auto-renewal):
   ```bash
   certbot renew --force-renewal
   systemctl reload nginx
   ```

### Site Not Loading

1. **Check Nginx**:
   ```bash
   nginx -t  # Test config
   systemctl status nginx
   systemctl restart nginx
   ```

2. **Check containers**:
   ```bash
   docker ps  # Should see backend and frontend running
   docker compose -f docker-compose.prod.yml restart
   ```

3. **Check firewall**:
   ```bash
   ufw status
   # Should show: 22/tcp (OpenSSH), 80/tcp, 443/tcp (Nginx Full)
   ```

## Cost Estimate

### DigitalOcean Droplet
- **Basic Plan**: $12/month (2GB RAM, 1 CPU, 50GB SSD)
- **Recommended Plan**: $24/month (4GB RAM, 2 CPUs, 80GB SSD)

### Domain (Hover.com)
- Already owned: mongado.com

### SSL Certificate (Let's Encrypt)
- **Free** (auto-renews every 90 days)

### Total Monthly Cost
- **Minimum**: $12/month (droplet only)
- **Recommended**: $24/month (for better performance)

## Security Best Practices

1. **Keep system updated**:
   ```bash
   apt update && apt upgrade -y
   ```

2. **Monitor failed login attempts**:
   ```bash
   grep "Failed password" /var/log/auth.log | tail -20
   ```

3. **Disable root SSH login** (optional, but recommended):
   ```bash
   # Create a non-root user first
   adduser deploy
   usermod -aG sudo deploy
   usermod -aG docker deploy

   # Then disable root login
   sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
   systemctl restart ssh
   ```

4. **Set up automatic security updates**:
   ```bash
   apt install unattended-upgrades -y
   dpkg-reconfigure -plow unattended-upgrades
   ```

## Next Steps

After deployment is working:

1. ✅ Set up monitoring (Datadog, Sentry, or self-hosted)
2. ✅ Add database backups to cloud storage (DigitalOcean Spaces)
3. ✅ Set up log aggregation
4. ✅ Add CDN (Cloudflare) for static assets
5. ✅ Configure error alerting

See `docs/ROADMAP.md` for full list of planned improvements.

## Related Documentation

- **[SETUP.md](SETUP.md)** - Local development setup
- **[TESTING.md](TESTING.md)** - Testing guide
- **[ROADMAP.md](ROADMAP.md)** - Future enhancements
- **[knowledge-base/README.md](knowledge-base/README.md)** - Knowledge Base architecture

---

**Questions or issues?** Check the Troubleshooting section above or review the GitHub Actions logs for deployment errors.
