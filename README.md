# Mongado Blog

A modern blog application built with Django REST Framework and Vue.js.

## Features

- Blog posts with categories and tags
- Search functionality
- Dark mode support
- Responsive design
- RESTful API backend
- Modern Vue.js frontend
- Secure secrets management with 1Password

## Tech Stack

### Backend
- Django
- Django REST Framework
- SQLite (development)

### Frontend
- Vue.js 3
- Vue Router
- Axios
- Tailwind CSS

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn
- 1Password CLI (optional, for secrets management)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mongado.git
cd mongado
```

2. Set up the backend:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables 
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

3. Set up the frontend:
```bash
cd frontend
npm install
npm run dev
```

The application will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173

## Secrets Management with 1Password (Optional)

### Local Development

For local development, you can:
1. Create a `.env` file from the example: `cp .env.example .env`
2. Manually populate the `.env` file with your local settings

### Production Deployment

For production environments, you can use the 1Password CLI to inject secrets:

1. Install 1Password CLI from https://1password.com/downloads/command-line/
2. Sign in to 1Password CLI: `op signin`
3. Create a deployment script (add to `.gitignore`):

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

### CI/CD Integration

See the `dev_notes/1password_setup.md` file for detailed information on integrating 1Password with CI/CD systems.

## Project Structure

```
mongado/
├── blog/             # Blog app
├── frontend/         # Vue.js project
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── App.vue
│   └── package.json
├── mongado/          # Project settings
└── README.md
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.