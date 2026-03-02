# 🚀 Rizz API Server

A scalable REST API built with Flask, featuring JWT authentication and SQLite database.

## Features

- 🔐 JWT Authentication
- 👤 User registration and login
- 📝 CRUD operations for posts
- 💬 Comments system
- 🔒 Protected endpoints
- 📊 Health check endpoint
- 📚 Auto-generated API docs

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login user | No |
| GET | `/api/auth/me` | Get current user | Yes |

### Posts

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/posts` | Get all posts | No |
| GET | `/api/posts/<id>` | Get single post | No |
| POST | `/api/posts` | Create post | Yes |
| PUT | `/api/posts/<id>` | Update post | Yes |
| DELETE | `/api/posts/<id>` | Delete post | Yes |

### Comments

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/posts/<id>/comments` | Add comment | Yes |
| DELETE | `/api/comments/<id>` | Delete comment | Yes |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api` | API information |
| GET | `/api/health` | Health check |

## Usage Examples

### Register a User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "password123"}'
```

### Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@rizz.dev"
  }
}
```

### Create a Post (with auth)

```bash
curl -X POST http://localhost:5000/api/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"title": "My First Post", "content": "Hello World!", "published": true}'
```

### Get All Posts

```bash
curl http://localhost:5000/api/posts
```

### Get Posts (published only)

```bash
curl "http://localhost:5000/api/posts?published=true"
```

### Add a Comment

```bash
curl -X POST http://localhost:5000/api/posts/1/comments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"content": "Great post!"}'
```

## Default Credentials

A default admin user is created on first run:

- **Username:** `admin`
- **Password:** `admin123`

⚠️ **Change this in production!**

## Database

Data is stored in `~/.rizz_api.db` (SQLite).

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key | Auto-generated |

```bash
# Set custom secret key
export SECRET_KEY="your-super-secret-key"
python app.py
```

## Project Structure

```
api-server/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## License

MIT License - username9999
