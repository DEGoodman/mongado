# 1Password Service Account Setup

This guide will help you set up the `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` environment variable for both local development and production deployments.

## Local Development Setup

### Step 1: Add Token to ~/.zshrc

Open your `~/.zshrc` file in an editor:

```bash
open ~/.zshrc
# or
nano ~/.zshrc
# or
vim ~/.zshrc
```

Add the following line at the end of the file:

```bash
# 1Password Service Account for mongado project
export OP_MONGADO_SERVICE_ACCOUNT_TOKEN="ops_your_actual_token_here"
```

Replace `ops_your_actual_token_here` with your actual 1Password service account token.

### Step 2: Reload Your Shell

```bash
source ~/.zshrc
```

### Step 3: Verify It's Set

```bash
echo $OP_MONGADO_SERVICE_ACCOUNT_TOKEN
```

You should see your token printed (starting with `ops_`).

### Step 4: Test with the Application

**Without Docker:**
```bash
cd backend
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

You should see: `✓ 1Password SDK initialized successfully`

**With Docker:**
```bash
docker compose up
```

The token will be automatically passed from your environment to the container.

## Production Deployment

### For Cloud Providers (AWS, GCP, Azure, etc.)

Set the environment variable in your cloud provider's console or CLI:

**AWS (ECS/Fargate):**
```bash
# In task definition environment variables
OP_MONGADO_SERVICE_ACCOUNT_TOKEN=ops_your_token_here
```

**Google Cloud Run:**
```bash
gcloud run deploy mongado-backend \
  --set-env-vars OP_MONGADO_SERVICE_ACCOUNT_TOKEN=ops_your_token_here
```

**Azure Container Apps:**
```bash
az containerapp update \
  --name mongado-backend \
  --set-env-vars OP_MONGADO_SERVICE_ACCOUNT_TOKEN=ops_your_token_here
```

### For Docker Deployments

**Option 1: Pass via command line**
```bash
docker compose -f docker-compose.prod.yml up -d
# Token is automatically read from your environment
```

**Option 2: Set in deployment script**
```bash
export OP_MONGADO_SERVICE_ACCOUNT_TOKEN="ops_your_token_here"
docker compose -f docker-compose.prod.yml up -d
```

**Option 3: Use .env file on server (not recommended for production)**
```bash
# On your production server, create backend/.env
echo "OP_MONGADO_SERVICE_ACCOUNT_TOKEN=ops_your_token_here" > backend/.env
docker compose -f docker-compose.prod.yml up -d
```

### For CI/CD Pipelines

**GitHub Actions:**
1. Go to repository Settings → Secrets and variables → Actions
2. Add new repository secret: `OP_MONGADO_SERVICE_ACCOUNT_TOKEN`
3. In your workflow:

```yaml
env:
  OP_MONGADO_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_MONGADO_SERVICE_ACCOUNT_TOKEN }}
```

**GitLab CI:**
1. Go to Settings → CI/CD → Variables
2. Add variable: `OP_MONGADO_SERVICE_ACCOUNT_TOKEN`
3. In your `.gitlab-ci.yml`:

```yaml
variables:
  OP_MONGADO_SERVICE_ACCOUNT_TOKEN: $OP_MONGADO_SERVICE_ACCOUNT_TOKEN
```

## Security Best Practices

1. **Never commit the token to git** - The `.gitignore` already excludes `.env` files
2. **Use different tokens for dev/staging/prod** - Create separate service accounts
3. **Rotate tokens regularly** - Update in all environments when you do
4. **Limit service account permissions** - Only grant access to vaults that are needed
5. **Monitor usage** - Check 1Password activity logs for unexpected access

## Troubleshooting

### Token not found
```
⚠ 1Password not configured - install 'op' CLI and sign in, or set OP_MONGADO_SERVICE_ACCOUNT_TOKEN
```

**Solution:** Make sure you've added the token to `~/.zshrc` and run `source ~/.zshrc`

### Token invalid
```
⚠ Failed to initialize 1Password SDK: [error details]
```

**Solution:**
- Verify the token starts with `ops_`
- Check the token hasn't been revoked in 1Password
- Ensure the service account has access to the required vaults

### Docker can't access token
```
⚠ 1Password not configured
```

**Solution:** Make sure the token is exported in your current shell before running `docker compose up`

```bash
echo $OP_MONGADO_SERVICE_ACCOUNT_TOKEN  # Should print your token
source ~/.zshrc  # If empty, reload shell config
docker compose up
```

## Next Steps

Once your token is configured, you can:

1. Create secrets in 1Password (API keys, database credentials, etc.)
2. Reference them in your code using the format: `op://vault-name/item-name/field-name`
3. Use the `SecretManager` to retrieve them:

```python
from config import get_secret_manager

secret_manager = get_secret_manager()
api_key = secret_manager.get_secret("op://Private/OpenAI/credential")
```

See the main [README.md](../README.md) for more information on using secrets in your application.
