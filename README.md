# Mongado Blog

A modern blog application built with Django REST Framework and Vue.js.

## Features

- Blog posts with categories and tags
- Search functionality
- Dark mode support
- Responsive design
- RESTful API backend
- Modern Vue.js frontend

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

## Project Structure

```
mongado/
├── backend/           # Django project
│   ├── blog/         # Blog app
│   └── mongado/      # Project settings
├── frontend/         # Vue.js project
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── App.vue
│   └── package.json
└── README.md
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 