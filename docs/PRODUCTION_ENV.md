# Production Environment Variables

This guide explains how to configure environment variables for production deployment.

## Required Environment Variables

### Application Settings

```bash
DEBUG=false  # Always false in production
```

### 1Password Service Account Token

```bash
OP_MONGADO_SERVICE_ACCOUNT_TOKEN=ops_xxxxxxxxxxxxx
```

**How to get this:**
1. Log into 1Password
2. Go to Settings → Developer → Service Accounts
3. Create a service account named "mongado-production"
4. Grant read access to the "mongado" vault
5. Copy the token (starts with `ops_`)
6. Store in GitHub Secrets as `OP_MONGADO_SERVICE_ACCOUNT_TOKEN`

### Admin Authentication Passkey

```bash
ADMIN_PASSKEY=your-strong-random-passkey
```

**How to generate:**
```bash
# Generate a strong 32-character passkey
openssl rand -base64 32

# Or use 1Password password generator:
# - Length: 32 characters
# - Include: Letters, numbers, symbols
# - Save to vault: op://mongado/mongado-prod-passkey/password
```

**Store in:**
- GitHub Secrets: `ADMIN_PASSKEY`
- 1Password vault for backup

### API Configuration

```bash
NEXT_PUBLIC_API_URL=https://api.mongado.com
```

**Important:** This must be set in GitHub Secrets as `NEXT_PUBLIC_API_URL` for the deployment workflow.

## GitHub Secrets Setup

Go to your GitHub repository: `github.com/degoodman/mongado` → Settings → Secrets and variables → Actions

### Required Secrets

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `DO_SSH_PRIVATE_KEY` | SSH private key for droplet | See DNS_SETUP.md |
| `DO_HOST` | Droplet IP address | DigitalOcean dashboard |
| `DO_USER` | SSH user (usually `root`) | Default: `root` |
| `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` | 1Password service account | 1Password → Developer → Service Accounts |
| `ADMIN_PASSKEY` | Admin authentication passkey | Generate with `openssl rand -base64 32` |
| `NEXT_PUBLIC_API_URL` | Production API URL | `https://api.mongado.com` |

### Adding a Secret to GitHub

1. Navigate to: `github.com/degoodman/mongado/settings/secrets/actions`
2. Click "New repository secret"
3. Enter the secret name (exactly as shown above)
4. Paste the secret value
5. Click "Add secret"

## Environment Files on Server

### Backend .env File

The GitHub Actions workflow automatically creates `backend/.env` on the server with:

```bash
DEBUG=false
OP_MONGADO_SERVICE_ACCOUNT_TOKEN=<from GitHub secret>
ADMIN_PASSKEY=<from GitHub secret>
```

**Manual setup** (if needed):
```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

cd /opt/mongado/backend

# Copy the example file
cp .env.production.example .env

# Edit with your values
nano .env
```

### Docker Compose Environment

The `docker-compose.prod.yml` file uses these environment variables:

```yaml
environment:
  - DEBUG=false
  - OP_MONGADO_SERVICE_ACCOUNT_TOKEN=${OP_MONGADO_SERVICE_ACCOUNT_TOKEN}
```

These are automatically set by the GitHub Actions deployment workflow.

## Optional Environment Variables

### Database (Neo4j)

When you add Neo4j:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

### AI/Ollama

If using Ollama for AI features:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

### Monitoring

For error tracking with Sentry:

```bash
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

### Logging

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json  # For log aggregation tools
```

## Verifying Environment Variables

### On Server

SSH into your droplet and verify:

```bash
cd /opt/mongado

# Check backend .env file exists
ls -la backend/.env

# View contents (be careful not to commit!)
cat backend/.env

# Check Docker environment
docker exec mongado-backend-prod env | grep OP_
docker exec mongado-backend-prod env | grep DEBUG
```

### In GitHub Actions

Check the workflow run logs:
1. Go to GitHub → Actions
2. Click on the latest deployment workflow
3. Expand "Deploy to DigitalOcean" step
4. Look for environment variable setup messages

## Security Best Practices

### 1. Never Commit Secrets

Ensure `.env` files are in `.gitignore`:

```bash
# Check if .env is ignored
git check-ignore backend/.env

# If not, add to .gitignore
echo "backend/.env" >> .gitignore
```

### 2. Rotate Secrets Regularly

**Every 90 days:**
1. Generate new `ADMIN_PASSKEY`
2. Update in GitHub Secrets
3. Update in 1Password vault
4. Redeploy application

**1Password Service Account Token:**
- Rotate annually or after any security incident
- Update in GitHub Secrets immediately after rotation

### 3. Use 1Password for Backup

Store all production secrets in 1Password:

```
Vault: mongado
├── mongado-prod-passkey
│   └── password: <ADMIN_PASSKEY>
├── mongado-service-account
│   └── token: <OP_MONGADO_SERVICE_ACCOUNT_TOKEN>
└── digitalocean-ssh-key
    └── private_key: <DO_SSH_PRIVATE_KEY>
```

### 4. Limit Access

- **GitHub Secrets**: Only repository admins can view/edit
- **1Password Vault**: Restrict access to yourself only
- **DigitalOcean**: Enable two-factor authentication

## Troubleshooting

### Deployment Fails with "Authentication Error"

**Problem**: GitHub Actions can't SSH into droplet

**Solution**:
1. Verify `DO_SSH_PRIVATE_KEY` in GitHub Secrets
2. Check public key is in droplet's `~/.ssh/authorized_keys`
3. Test SSH manually: `ssh -i ~/.ssh/mongado_deploy root@YOUR_DROPLET_IP`

### Admin Login Fails

**Problem**: Can't log in with admin passkey

**Solution**:
1. Verify `ADMIN_PASSKEY` in GitHub Secrets matches what you're using
2. Check backend logs: `docker compose -f docker-compose.prod.yml logs backend`
3. Verify backend `.env` file has correct passkey
4. Redeploy to refresh environment variables

### 1Password Integration Not Working

**Problem**: Can't fetch secrets from 1Password

**Solution**:
1. Verify `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` is correct
2. Check service account has access to "mongado" vault
3. Test token manually:
   ```bash
   export OP_SERVICE_ACCOUNT_TOKEN="<your-token>"
   op vault list
   ```
4. Check backend logs for 1Password connection errors

### Environment Variables Not Updating

**Problem**: Changed secret in GitHub but app still uses old value

**Solution**:
1. Trigger a new deployment (push to `main` or manual workflow)
2. SSH into droplet and verify `/opt/mongado/backend/.env` was updated
3. Restart containers:
   ```bash
   cd /opt/mongado
   docker compose -f docker-compose.prod.yml restart
   ```

## Checklist: Pre-Deployment

Before deploying to production, ensure:

- [ ] All required GitHub Secrets are set
- [ ] `ADMIN_PASSKEY` is strong (32+ characters)
- [ ] `NEXT_PUBLIC_API_URL` points to `https://api.mongado.com`
- [ ] `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` is valid
- [ ] SSH key (`DO_SSH_PRIVATE_KEY`) can access droplet
- [ ] All secrets are backed up in 1Password
- [ ] `.env` files are in `.gitignore`
- [ ] DNS records are configured (see DNS_SETUP.md)
- [ ] Droplet is set up (see DEPLOYMENT.md)

## Related Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full deployment guide
- **[DNS_SETUP.md](DNS_SETUP.md)** - DNS configuration for mongado.com
- **[SETUP.md](SETUP.md)** - Local development setup
- **[ROADMAP.md](ROADMAP.md)** - Future enhancements

---

**Questions?** Check the Troubleshooting section above or review GitHub Actions logs for detailed error messages.
