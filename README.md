# 🎬 CineMate MCP Server

**CineMate** is your **Ultimate Personal Movie Tracker & Assistant**, built on the Model Context Protocol (MCP). 

It doesn't just find movies—it **remembers** them. CineMate helps you build a personal library of your viewing history, manages your watchlist, and seamlessly integrates with your life via **Google Calendar** and **TMDB (The Movie Database)**.

With CineMate, your AI assistant becomes a dedicated cinema companion that knows what you've seen, what you loved, and what you want to watch next.

With CineMate, you can ask your AI to:
- 🔍 **Find movies & TV shows** with detailed metadata.
- 📺 **Check where to watch** titles in your country (streaming/rent/buy).
- 📅 **Schedule movies** specifically on your Google Calendar (e.g., "Schedule Inception for Friday at 8pm").
- 🍿 **Plan Binge Sessions**: Automatically calculate how long a TV show takes to watch and block out time on your calendar (e.g., "Plan a binge of Breaking Bad, 3 episodes a night").
- 📝 **Track Watched Content**: Log movies, rate them, and keep a watchlist.
- 📊 **Analyze Stats**: Get insights into your viewing habits and favorite genres.

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** (Recommended for fast dependency management) or standard `pip`.
- A **Google Cloud Project** with Calendar API enabled (for scheduling).
- A **TMDB API Key** (for movie data).

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/CineMate.git
cd CineMate

# Install dependencies using uv (creates .venv automatically)
uv sync
```

### 2. Configure Environment variables
Create a `.env` file in the root directory:
```bash
# Get your key from https://www.themoviedb.org/settings/api
TMDB_API_KEY=your_tmdb_api_key_here
```

### 3. Google Calendar Credentials
To allow CineMate to manage your calendar, you need OAuth credentials:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the **Google Calendar API**.
4. Go to **Credentials** > **Create Credentials** > **OAuth client ID**.
5. Select **Desktop app**.
6. Download the JSON file, **rename it to `credentials.json`**, and place it in the root folder of this project.

> _Note: `credentials.example.json` is provided in the repo to show the expected format._

---

## 🚀 Usage

### Running the Server
Start the MCP server using `uv`:

```bash
uv run fastmcp dev src/main.py
```

_On the first run, a browser window will open asking you to log in to your Google account. This authorizes the application and creates a local `token.json` file for future non-interactive runs._

### Connecting to Claude Desktop
To use CineMate with Claude Desktop, add the following configuration to your `claude_desktop_config.json`:

**Windows Configuration:**
`C:\Users\YourUser\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "CineMate": {
      "command": "uv",
      "args": [
        "run",
        "fastmcp",
        "run",
        "src/main.py"
      ],
      "cwd": "C:\\path\\to\\your\\CineMate",
      "env": {
        "TMDB_API_KEY": "your_key_here_if_not_using_dotenv_file"
      }
    }
  }
}
```
_(Make sure to update `C:\\path\\to\\your\\CineMate` to the actual path on your machine)._

---

## 📂 Project Structure

The project follows a modern Python `src` layout:

```
CineMate/
├── src/
│   ├── main.py              # Entry point & Tool definitions
│   ├── core/
│   │   └── database.py      # SQLite database handler
│   └── services/            # Business logic modules
│       ├── cine_service.py
│       ├── movie_service.py
│       ├── calendar_service.py
│       └── binge_service.py
├── cinemate.db              # Local database (auto-created)
├── credentials.json         # Google OAuth Secret (User provided)
├── token.json               # OAuth Token (Auto-generated on first login)
├── pyproject.toml           # Dependencies
└── README.md
```

## 🛡️ Privacy & Data
- **Local Database**: Your watch history and watchlist are stored locally in `cinemate.db` (SQLite).
- **Google Data**: This app only requests access to manage Calendar events it creates. It stores the access token locally in `token.json`.
- **No Cloud Tracking**: CineMate does not send your usage data to any third-party server other than TMDB (for search) and Google (for calendar).
