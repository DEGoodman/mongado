# 1Password Setup Guide for Mongado Project

## Local Development

1. Install 1Password CLI:
   - macOS: `brew install 1password-cli`
   - Windows: Download from https://1password.com/downloads/command-line/
   - Linux: Follow instructions at https://1password.com/downloads/command-line/

2. Sign in to 1Password CLI:
   ```bash
   op signin
   ```

3. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

4. For local development, you can manually populate the `.env` file with your local settings

## Production Setup

1. Create a 1Password vault for the project if one doesn't exist

2. Add the following secrets to the vault:
   - Django `SECRET_KEY`
   - `DATABASE_URL` (if using a remote database)
   - Any other environment-specific secrets

3. Create a deployment script that looks like this (don't commit this file!):

   ```bash
   #!/bin/bash
   # deploy.sh - Do not commit this file!

   # Sign in to 1Password
   eval $(op signin)

   # Export secrets from 1Password
   export SECRET_KEY="$(op read op://vault-name/item-name/field-name)"
   export DATABASE_URL="$(op read op://vault-name/item-name/field-name)"
   export DEBUG="False"
   export ALLOWED_HOSTS="your-domain.com"
   # Add other required environment variables

   # Run your production server
   # Example: gunicorn mongado.wsgi:application
   ```

4. Make the script executable:
   ```bash
   chmod +x deploy.sh
   ```

## CI/CD Integration

### GitHub Actions

1. Create service account in 1Password for your CI/CD system

2. Install the 1Password GitHub Action in your workflow:

```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install 1Password CLI
        uses: 1password/install-cli-action@v1
      
      - name: Load secrets
        uses: 1password/load-secrets-action@v1
        with:
          # Connect to 1Password using details from GitHub secrets
          service-account-token: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
        env:
          DJANGO_SECRET_KEY: op://vault-name/django-secret/secret-key
          DATABASE_URL: op://vault-name/database/url
          
      - name: Deploy
        run: |
          # Your deployment commands here, using the loaded environment variables
          echo "Deploying with secrets from 1Password"
```

## Security Notes

- Never commit `.env` files or any files containing secrets
- Make sure `deploy.sh` and any other files with 1Password commands are in `.gitignore`
- Rotate secrets periodically following security best practices
- Set up appropriate access controls in your 1Password vault