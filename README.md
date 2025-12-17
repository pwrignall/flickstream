# FlickStream - TMDb Watchlist Viewer

A simple Python web application to view and filter your TMDb watchlist with streaming service availability.

## Features

- 📺 View your entire TMDb watchlist
- 🎬 Filter by streaming services you're subscribed to
- 🎭 Filter by genre and release year
- 🔍 Search movies by title
- ⭐ Sort by title, release date, or rating
- 🎨 Clean, dark-themed interface
- 🐳 Easy Docker deployment

## Quick Start (Local Development)

Want to try it out without setting up TMDb credentials? Use the included test database:

```bash
# Option 1: Use the helper script
./dev-server.sh

# Option 2: Manual setup
uv sync
export DB_PATH=./dev.db
export TMDB_ACCOUNT_ID=dev_account
uv run python app.py
```

Visit `http://localhost:5000` and you'll see 5 classic movies with pre-cached streaming data!

## Prerequisites

1. A TMDb account with movies in your watchlist
2. TMDb API key (get one at https://www.themoviedb.org/settings/api)
3. Docker and Docker Compose installed on your system

## Setup

### 1. Get Your TMDb Credentials

1. Go to https://www.themoviedb.org/settings/api and create an API key
2. Note your Account ID from https://www.themoviedb.org/settings/account

### 2. Configure Environment Variables

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```
TMDB_API_KEY=your_actual_api_key_here
TMDB_ACCOUNT_ID=your_actual_account_id_here

# Optional: Configure your streaming services (comma-separated)
MY_STREAMING_SERVICES=Netflix,Amazon Prime Video,Disney Plus

# Optional: Your region for streaming providers (default: US)
USER_REGION=GB

# Optional: Cache expiration times in hours
WATCHLIST_CACHE_HOURS=6
PROVIDERS_CACHE_HOURS=24
```

### 3. Run with Docker Compose

```bash
docker-compose up -d
```

The application will be available at `http://localhost:5000`

### 4. Configure Your Streaming Services

When you first open the app, click on the streaming services you're subscribed to. Your selections will be saved in your browser.

## Development Mode

To run without Docker for development:

```bash
# Install uv (if not already installed)
# On macOS and Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# On Windows, see: https://docs.astral.sh/uv/getting-started/installation/

# Install dependencies
uv sync

# Set environment variables
export TMDB_API_KEY=your_key
export TMDB_ACCOUNT_ID=your_id

# Run the app
uv run python app.py
```

### Using the Test Database

For local development without TMDb API calls, a pre-populated SQLite database (`dev.db`) is included with test data containing 5 classic movies:

```bash
# Set environment to use the local dev database
export DB_PATH=./dev.db
export TMDB_ACCOUNT_ID=dev_account

# Run the app (no TMDb API key needed for cached data)
uv run python app.py
```

The test database includes:
- **5 classic movies**:
  - The Shawshank Redemption (1994)
  - The Godfather (1972)
  - The Godfather Part II (1974)
  - Schindler's List (1993)
  - 12 Angry Men (1957)
- Pre-cached provider information for Netflix, Amazon Prime Video, and Paramount Plus
- Pre-cached runtime data for all movies

To reinitialize or reset the test database at any time:
```bash
python3 init_dev_db.py
```

**Note**: To fetch fresh data or add more movies, you'll need to set your real TMDb credentials.

## Database Configuration

FlickStream uses SQLite to cache TMDb API responses. By default:
- **Docker/Production**: Uses `/app/flickstream_cache.db` inside the container
- **Local Development**: Set `DB_PATH` environment variable to use a different database

The included `dev.db` is a pre-populated development database that doesn't require API calls.

## Configuration

### Change Your Region

The app defaults to US streaming providers. To change this, set the `USER_REGION` variable in your `.env` file:

```
USER_REGION=GB  # Change to 'CA', 'AU', 'DE', 'FR', etc.
```

### Pre-configure Your Streaming Services

You can optionally pre-configure your streaming services in the `.env` file instead of selecting them in the UI:

```
MY_STREAMING_SERVICES=Netflix,Amazon Prime Video,Disney Plus,Hulu
```

If not set, you can still select your services through the web interface.

## Troubleshooting

### No movies showing up
- Verify your TMDb API key and Account ID are correct
- Make sure you have movies in your TMDb watchlist
- Check the container logs: `docker-compose logs -f`

### Providers not showing
- Ensure the `USER_REGION` environment variable in your `.env` file matches your location
- Not all movies have streaming provider data for all regions

### Port already in use
- Change the port in `docker-compose.yml` from `5000:5000` to `8080:5000` (or another port)

## Tech Stack

- **Backend**: Flask (Python web framework)
- **Frontend**: Vanilla JavaScript with modern CSS
- **API**: TMDb API v3
- **Dependency Management**: uv (fast Python package installer)
- **Deployment**: Docker + Gunicorn

## License

MIT License - feel free to modify and use as needed!
