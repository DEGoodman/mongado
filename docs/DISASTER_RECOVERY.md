# Disaster Recovery Guide

This guide covers how to rebuild your production environment from scratch if the droplet is destroyed or compromised.

## Prerequisites

All secrets are stored in 1Password vault "mongado":
- `mongado-prod-passkey` - Admin authentication passkey
- `mongado-service-account` - 1Password service account token
- `github-deploy-key` - GitHub Actions SSH keypair
- `digitalocean-droplet` - Droplet info and notes

GitHub Secrets are already configured at: `github.com/degoodman/mongado/settings/secrets/actions`

## Recovery Steps

### 1. Create New Droplet

```bash
# DigitalOcean Dashboard → Create Droplet
# - Ubuntu 22.04 LTS
# - $12/month (2GB) or $24/month (4GB)
# - Add your SSH key
# - Note the new IP address
```

### 2. Update DNS Records

In Fastmail DNS settings, update A records to new droplet IP:
```
Type: A    Name: @      Value: <NEW_DROPLET_IP>
Type: A    Name: www    Value: <NEW_DROPLET_IP>
Type: A    Name: api    Value: <NEW_DROPLET_IP>
```

Wait 5-30 minutes for DNS propagation.

### 3. Update GitHub Secrets

Go to `github.com/degoodman/mongado/settings/secrets/actions`

Update:
- `DO_HOST` → New droplet IP address

Verify these are still correct:
- `DO_SSH_PRIVATE_KEY` (from 1Password)
- `DO_USER` (should be `root`)
- `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` (from 1Password)
- `ADMIN_PASSKEY` (from 1Password)
- `NEXT_PUBLIC_API_URL` (should be `https://api.mongado.com`)

### 4. SSH into New Droplet

```bash
ssh root@<NEW_DROPLET_IP>
```

### 5. Run Initial Setup

```bash
# Update system
apt update && apt upgrade -y
reboot

# SSH back in after reboot
ssh root@<NEW_DROPLET_IP>

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose-plugin -y

# Install other tools
apt install -y git curl wget nginx certbot python3-certbot-nginx

# Verify installations
docker --version
docker compose version
nginx -v
certbot --version
```

### 6. Configure Git and Clone Repo

```bash
# Create project directory
mkdir -p /opt/mongado
cd /opt/mongado

# Clone repository
git clone https://github.com/degoodman/mongado.git .

# Configure Git
git config --global credential.helper store
```

### 7. Add Deploy Key to Authorized Keys

```bash
# Get public key from 1Password (github-deploy-key → public_key)
echo "ssh-ed25519 AAAAC3... github-actions-mongado" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 8. Configure Nginx

```bash
# Create temporary HTTP-only config
cat > /etc/nginx/sites-available/mongado << 'EOF'
# Frontend - mongado.com and www.mongado.com
server {
    listen 80;
    listen [::]:80;
    server_name mongado.com www.mongado.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

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
    listen 80;
    listen [::]:80;
    server_name api.mongado.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

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

# Enable site
ln -s /etc/nginx/sites-available/mongado /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test and restart
nginx -t
systemctl restart nginx
```

### 9. Set Up Environment Variables

```bash
cd /opt/mongado

# Get secrets from 1Password
# - ADMIN_PASSKEY: op://mongado/mongado-prod-passkey/password
# - OP_TOKEN: op://mongado/mongado-service-account/token

# Create backend/.env
cat > backend/.env << 'EOF'
DEBUG=false
OP_MONGADO_SERVICE_ACCOUNT_TOKEN=<paste-token-here>
ADMIN_PASSKEY=<paste-passkey-here>
EOF

chmod 600 backend/.env
```

### 10. Configure Firewall

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

### 11. Wait for DNS Propagation

```bash
# Check DNS is resolving to new IP
dig mongado.com +short
dig www.mongado.com +short
dig api.mongado.com +short

# All should return: <NEW_DROPLET_IP>
```

### 12. Set Up SSL Certificates

```bash
# After DNS propagates
certbot --nginx -d mongado.com -d www.mongado.com -d api.mongado.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# Verify auto-renewal
certbot renew --dry-run
```

### 13. First Manual Deployment

```bash
cd /opt/mongado

# Set environment variables
export NEXT_PUBLIC_API_URL="https://api.mongado.com"
export OP_MONGADO_SERVICE_ACCOUNT_TOKEN="<from-1password>"

# Build and start
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### 14. Verify Deployment

```bash
# Check containers
docker ps

# Check backend
curl http://localhost:8000/
curl https://api.mongado.com/

# Check frontend
curl http://localhost:3000/
curl https://mongado.com/

# Check SSL
curl -I https://mongado.com/ | grep -i "HTTP/2 200"
```

### 15. Trigger GitHub Actions

```bash
# From your local machine
git commit --allow-empty -m "Test deployment after disaster recovery"
git push origin main

# Watch deployment at: github.com/degoodman/mongado/actions
```

## Post-Recovery Checklist

- [ ] All three domains resolve to new droplet IP
- [ ] SSL certificates are valid (check in browser)
- [ ] Backend API responds at https://api.mongado.com/
- [ ] Frontend loads at https://mongado.com/
- [ ] Email still works (MX records unchanged)
- [ ] GitHub Actions deployment succeeds
- [ ] Docker containers restart automatically (`docker ps` shows restart policy)
- [ ] Firewall is configured (`ufw status`)
- [ ] SSL auto-renewal works (`certbot renew --dry-run`)

## Database Backup & Restore (Neo4j)

**Note**: Currently not implemented. When you add Neo4j:

### Backup

```bash
# Create backup
docker exec mongado-neo4j neo4j-admin database dump neo4j \
  --to-path=/backups/neo4j_backup_$(date +%Y%m%d).dump

# Copy to local machine
scp root@<DROPLET_IP>:/opt/mongado/backups/*.dump ~/mongado-backups/
```

### Restore

```bash
# Copy backup to new droplet
scp ~/mongado-backups/neo4j_backup_YYYYMMDD.dump root@<NEW_DROPLET_IP>:/opt/mongado/backups/

# Restore
docker exec mongado-neo4j neo4j-admin database load neo4j \
  --from-path=/backups/neo4j_backup_YYYYMMDD.dump \
  --overwrite-destination=true

# Restart Neo4j
docker restart mongado-neo4j
```

## Time Estimate

Total recovery time: **1-2 hours**

- Droplet creation: 2 minutes
- DNS propagation: 5-30 minutes
- Setup commands: 15-30 minutes
- SSL certificate: 5 minutes
- First deployment: 10-15 minutes
- Verification: 5-10 minutes

## Prevention

To minimize recovery needs:

1. **Automated Backups**
   - Set up daily Neo4j backups (when added)
   - Store in DigitalOcean Spaces or S3
   - Keep 7 days of backups

2. **Infrastructure as Code**
   - All configuration is in git (Nginx, Docker Compose)
   - Secrets in 1Password and GitHub Secrets
   - Easy to recreate

3. **Monitoring**
   - Set up uptime monitoring (UptimeRobot, Pingdom)
   - Alert on downtime
   - Monitor SSL expiration

4. **Documentation**
   - Keep this runbook updated
   - Document any manual changes
   - Test recovery process annually

## Related Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Initial deployment guide
- **[DNS_SETUP.md](DNS_SETUP.md)** - DNS configuration
- **[PRODUCTION_ENV.md](PRODUCTION_ENV.md)** - Environment variables
- **[ROADMAP.md](ROADMAP.md)** - Future enhancements

---

Last updated: 2025-10-12
