# 🎯 JiraHub

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.41.0+-red.svg)](https://streamlit.io)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **comprehensive Jira team management dashboard** built with Streamlit. JiraHub provides real-time visibility into team workload, ticket status, and project progress across multiple Jira projects and boards with advanced filtering, caching, and automated team member syncing.

## ✨ Key Features

- 🔌 **Jira Cloud Integration** - Connect to your Jira Cloud instance via REST API v3 + Agile v1.0
- 📊 **Multi-Project Dashboard** - View and manage tickets across multiple projects simultaneously
- 🎯 **Board Filtering** - Filter boards per project to focus on specific team areas
- 🔍 **Advanced Filtering** - Filter by:
  - Assignee & Team Labels
  - Status (include/exclude)
  - Created & Due Date ranges
  - Jira Issue Labels
  - Story Points
- 👥 **Team Member Management** - Auto-sync team members from Jira assignees, assign labels for organization
- 📈 **Workload Analysis** - View workload distribution, status breakdown, and overdue tickets
- 💾 **Smart Caching** - Redis-powered caching for fast data retrieval
- 🔐 **Session Persistence** - Cookie-based session management survives browser refresh
- 🗄️ **Multi-Tenant Ready** - Role-based access control (Admin, User)
- 🐳 **Docker Support** - Fully containerized for easy deployment

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit 1.41+ |
| **Backend** | Python 3.13+ async |
| **Database** | SQLite (development) + Alembic migrations |
| **ORM** | SQLAlchemy 2.0+ async |
| **Caching** | Redis 5.2+ |
| **API Client** | httpx 0.28+ (async) |
| **Auth** | Fernet encryption + pwdlib argon2 |
| **Container** | Docker + Docker Compose |

## 📑 Table of Contents

1. [Installation](#-installation)
   - [For End Users](#for-end-users)
   - [For Developers](#for-developers)
2. [Configuration](#-configuration)
3. [Running the Application](#-running-the-application)
4. [Project Structure](#-project-structure)
5. [Usage Guide](#-usage-guide)
6. [Jira API Setup](#-jira-api-setup)
7. [Troubleshooting](#-troubleshooting)
8. [Development & Contributing](#-development--contributing)

---

## 🚀 Installation

### For End Users

#### Prerequisites

- **Python 3.13+** ([download](https://www.python.org/downloads/))
- **Jira Cloud Account** with API token access
- **Git** (optional, for cloning)
- **uv** package manager (faster than pip) - [install guide](https://docs.astral.sh/uv/getting-started/)

#### Quick Start (Linux/macOS/Windows PowerShell)

1. **Clone or Download the Project**

   ```bash
   git clone <repository-url>
   cd JiraAutomation
   ```

2. **Create & Activate Virtual Environment**

   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # macOS/Linux
   # or
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

3. **Install Dependencies**

   ```bash
   uv sync
   ```

4. **Configure Environment** (See [Configuration](#-configuration) section)

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize Database** (Automatic on first run)

   ```bash
   uv run streamlit run app/main.py
   ```

6. **Access the App**
   - Open browser to: `http://localhost:8501`
   - Login with your registered account

---

### For Developers

#### Prerequisites

- **Python 3.13+**
- **uv** package manager
- **Redis** (local or Docker)
- **Git**
- **Docker + Docker Compose** (optional, for containerized development)

#### Development Setup

1. **Clone and Setup Repository**

   ```bash
   git clone <repository-url>
   cd JiraAutomation

   # Create virtual environment with uv
   uv venv
   source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows

   # Install all dependencies including dev tools (with dev group)
   uv sync --all-groups
   ```

2. **Set Up Environment Variables**

   ```bash
   cp .env.example .env
   # Edit .env with local development settings
   ```

3. **Start Redis (Required for Caching)**

   ```bash
   # Option 1: Using Docker (recommended)
   docker run -d -p 6379:6379 redis:latest

   # Option 2: Install Redis locally and run
   redis-server
   ```

4. **Initialize Database with Alembic**

   ```bash
   # Create initial migration
   uv run alembic upgrade head
   ```

5. **Run Application in Dev Mode**

   ```bash
   # With auto-reload on file changes
   uv run streamlit run app/main.py --logger.level=debug
   ```

6. **Pre-commit Hooks** (Optional but recommended)

   ```bash
   uv run pre-commit install
   uv run pre-commit run --all-files  # Run formatters
   ```

#### Project Structure for Development

```
JiraAutomation/
├── app/
│   ├── core/              # Configuration & constants
│   │   ├── config.py      # Settings via pydantic-settings
│   │   ├── constants.py   # Roles, enums
│   │   └── exceptions/    # Domain & HTTP exceptions
│   ├── models/            # SQLAlchemy ORM models
│   │   ├── base.py        # Base model with auto-timestamp
│   │   ├── user.py        # User model
│   │   ├── team_member.py # Team members with labels
│   │   ├── user_project.py # Multi-project assignments
│   │   ├── session.py     # Auth sessions
│   │   └── ignored_*.py   # User preferences (ignored tickets/types)
│   ├── schemas/           # Pydantic models for validation
│   │   ├── user.py        # Request/response schemas
│   │   └── jira/          # Jira API response models
│   ├── repos/             # SQLAlchemy repositories
│   │   └── base.py        # Base CRUD repo
│   ├── services/          # Business logic
│   │   ├── auth_service.py     # User auth & session mgmt
│   │   ├── jira_client.py      # Jira API client (httpx)
│   │   └── cache.py            # Redis caching layer
│   ├── pages/             # Streamlit multi-page app
│   │   ├── login.py       # Authentication
│   │   ├── register.py    # User registration
│   │   ├── dashboard.py   # Main team dashboard
│   │   ├── project_setup.py   # Project/board selection
│   │   ├── member_detail.py   # Team member details
│   │   ├── ticket_detail.py   # Jira issue details
│   │   ├── admin.py       # Admin panel
│   │   ├── settings.py    # User settings & logout
│   │   └── insights.py    # Analytics & reporting
│   ├── utils/             # Helper functions
│   │   ├── async_helpers.py   # Event loop management
│   │   ├── metrics.py     # Calculation utilities
│   │   └── cookies.py     # Session cookie management
│   └── main.py            # Entry point & navigation
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
├── tests/                 # Unit & integration tests (optional)
├── docker-compose.yml     # Development DB + Redis
├── Dockerfile             # Production container
├── pyproject.toml         # Project metadata & dependencies
└── README.md              # This file
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# ══════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════
DATABASE_URL=sqlite+aiosqlite:///./data/jirahub.db
# For production, use PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/jirahub

# ══════════════════════════════════════════════════════════════
# REDIS CACHE
# ══════════════════════════════════════════════════════════════
REDIS_URL=redis://localhost:6379/0
# For Docker containers:
# REDIS_URL=redis://redis:6379/0

# ══════════════════════════════════════════════════════════════
# STREAMLIT CONFIGURATION
# ══════════════════════════════════════════════════════════════
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
# Session timeout in hours
SESSION_EXPIRY_HOURS=72

# ══════════════════════════════════════════════════════════════
# SECURITY
# ══════════════════════════════════════════════════════════════
ENCRYPTION_KEY=your-secret-key-here  # Change this!
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ══════════════════════════════════════════════════════════════
# JIRA API (obtainable from Jira account settings)
# ══════════════════════════════════════════════════════════════
# These are user-provided per account during "Jira Connect" setup
# Not set here - configured in the web UI

# ══════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════
LOG_LEVEL=INFO
# Use DEBUG for development
```

### Environment Variable Details

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `DATABASE_URL` | SQLAlchemy async DB connection string | SQLite local | Yes |
| `REDIS_URL` | Redis connection for caching | `redis://localhost:6379/0` | Yes |
| `SESSION_EXPIRY_HOURS` | User session lifetime in hours | 72 | No |
| `ENCRYPTION_KEY` | Fernet key for token encryption | Generated if missing | Yes (auto) |
| `STREAMLIT_SERVER_PORT` | Web UI port | 8501 | No |
| `LOG_LEVEL` | Logging verbosity | INFO | No |

### Generate Encryption Key

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to ENCRYPTION_KEY in .env
```

---

## ▶️ Running the Application

### Local Development

**Terminal 1 - Start Redis:**

```bash
docker run -d -p 6379:6379 redis:latest
# or if Redis installed locally:
redis-server
```

**Terminal 2 - Run Streamlit App:**

```bash
uv run streamlit run app/main.py
```

Access at: `http://localhost:8501`

### Docker Deployment

#### Option 1: Docker Compose (Development)

```bash
# Start all services (app + Redis + SQLite)
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

#### Option 2: Docker Build (Production)

```bash
# Build image
docker build -t jirahub:latest .

# Run container
docker run -d \
  -p 8501:8501 \
  -e DATABASE_URL="sqlite+aiosqlite:///./data/jirahub.db" \
  -e REDIS_URL="redis://redis:6379/0" \
  -v jirahub_data:/app/data \
  --link redis:redis \
  jirahub:latest

# Access at http://localhost:8501
```

### Database Migrations

```bash
# Create new migration (after model changes)
uv run alembic revision --autogenerate -m "descriptive message"

# Apply migrations
uv run alembic upgrade head

# Downgrade
uv run alembic downgrade -1
```

---

## 📂 Project Structure

### Core Architecture

```
┌─────────────────────────────────────┐
│     Streamlit Frontend (Multi-page) │
│  ├─ Login / Register                │
│  ├─ Dashboard (Main)                │
│  ├─ Project Setup                   │
│  ├─ Member Detail                   │
│  ├─ Ticket Detail                   │
│  └─ Settings / Admin                │
└──────────────┬──────────────────────┘
               │
      ┌────────▼─────────┐
      │  Streamlit State │ (Session mgmt)
      │  + Cookies       │
      └────────┬─────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────────┐     ┌──────▼──────┐
│  Services  │     │ Repositories│
├────────────┤     ├─────────────┤
│ AuthService│────▶│User/Session │
│JiraClient  │────▶│TeamMember   │
│CacheService│────▶│UserProject  │
└────┬───────┘     │Ignored*     │
     │             └──────┬──────┘
     │                    │
┌────▼────────────────────▼──────┐
│    SQLAlchemy ORM Models       │
│  ├─ User                       │
│  ├─ Session                    │
│  ├─ TeamMember                 │
│  ├─ UserProject                │
│  └─ IgnoredTicket/Type         │
└────┬─────────────────────────┬─┘
     │                         │
┌────▼─────────┐     ┌────────▼───┐
│  SQLite DB   │     │ Redis Cache │
│ (async)      │     │   (httpx)   │
└──────────────┘     └─────────────┘
```

### Data Flow

1. User logs in → **AuthService** validates credentials & creates session
2. User connects Jira → Token stored encrypted in database
3. **JiraClient** fetches issues via Jira API (httpx async)
4. Data cached in **Redis** for 24 hours (manual refresh available)
5. **Dashboard** displays filtered, cached data with real-time updates
6. Team members auto-synced from Jira assignees → **TeamMemberRepo** upsert

---

## 📖 Usage Guide

### 1️⃣ First Login

1. Click **Register** to create an account
2. Fill email & password (will be hashed with Argon2)
3. Login with credentials

### 2️⃣ Connect Jira Account

1. Go to **Jira Connect** page
2. Provide:
   - **Jira URL**: `https://your-domain.atlassian.net`
   - **Email**: Your Jira account email
   - **API Token**: Generated in Jira account settings (see [Jira API Setup](#-jira-api-setup))
3. Click **Connect** → Token encrypted & stored securely

### 3️⃣ Select Projects & Boards

1. Go to **Project Setup**
2. **Discover Projects**: Fetches your Jira projects
3. **Select Projects**: Choose which to manage
4. **Select Boards per Project**: Choose which boards' issues to track
5. **Save Configuration**

### 4️⃣ Build Team

1. Go to **Dashboard** → Issues automatically sync assignees to team members
2. Go to **Team Members** to add custom labels (e.g., "Backend", "Frontend", "QA")
3. Use labels in **Dashboard filters** for quick team filtering

### 5️⃣ Dashboard Workflow

#### View & Filter

- **Filter by Project**: Select specific projects (top)
- **Filter by Board**: Per-project board selection
- **Status Filters**: Include/Exclude statuses
- **Date Ranges**: Created & Due dates
- **Assignee/Labels**: Team member filtering
- **Story Points**: Estimate range filtering

#### Analyze

- **Metrics**: Total tickets, overdue, missing story points
- **Workload Distribution**: Bar chart of assignee workload
- **Status Distribution**: Pie/bar chart of status breakdown
- **Overdue Tickets**: Red-flagged table
- **All Tickets**: Full filterable table with details

#### Drill Down

- Click ticket **Key** → **Ticket Detail page**
  - Full issue info
  - Worklogs & time tracking
  - Linked issues & subtasks
  - Sprint info
- Click **Team Member name** → **Member Detail page**
  - Member profile
  - Assigned tickets summary
  - Custom labels

### 6️⃣ Team Management

- **Member Detail Page**: View all member assignments, labels, reporter status
- **Ignore Tickets**: Hide noisy issues from dashboard (per user)
- **Ignore Issue Types**: Hide story, epic, etc. globally

### 7️⃣ Settings & Logout

- **Settings Page**: Update password, manage ignored items, logout
- Session persists across browser refresh (cookie-based)

---

## 🔗 Jira API Setup

### What are API Tokens?

API tokens allow scripts and applications (like JiraHub) to authenticate with your Jira Cloud account using HTTP Basic Authentication. They're more secure than using passwords because:

- You can create tokens with limited permissions (scopes)
- Tokens can expire automatically
- You can revoke them without changing your password
- Multiple tokens for different purposes

**Reference:** [Atlassian API Token Documentation](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)

---

### Create an API Token (Recommended Method - With Scopes)

**Why with scopes?** Scopes limit what the token can do, improving security by following the principle of least privilege.

#### Prerequisites

- Atlassian account with access to Jira Cloud
- Verify your identity (you'll receive a one-time passcode via email)

#### Step-by-Step Instructions

1. **Go to API Token Management**
   - Navigate to: <https://id.atlassian.com/manage-profile/security/api-tokens>
   - Log in if prompted

2. **Create Token with Scopes** (Recommended)
   - Click **Create API token with scopes**
   - Provide a descriptive name (e.g., `JiraHub-Production`)
   - Select expiration date: **1 to 365 days** (default: 1 year)
     - ⚠️ Tokens expire after this period and need renewal
   - Click **Next**

3. **Select App Access**
   - Choose **Jira** (required for JiraHub)
   - Click **Next**

4. **Configure Scopes** (Permissions)
   - **Required scopes for JiraHub:**

     ```
     read:jira-work       (Read issues, boards, sprints)
     read:jira-user       (Read user/assignee data)
     read:jira.user       (Read user info for filtering)
     ```

   - **Optional scopes (if managing/creating issues):**

     ```
     write:jira-work      (Modify issues)
     write:jira-project   (Manage project settings)
     ```

   - [View all Jira Scopes](https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/)

5. **Review & Create**
   - Review scope information
   - Click **Create**

6. **Copy & Save Token**
   - **⚠️ CRITICAL:** Copy the token immediately - it won't be shown again
   - Save in password manager (LastPass, 1Password, etc.)
   - Click **Done**

---

### Alternative: Create API Token Without Scopes

If your app doesn't support scoped tokens:

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Click **Create API token**
3. Give it a descriptive name
4. Set expiration (1-365 days)
5. Click **Create**
6. Copy token and save securely

---

### API Token Settings

| Setting | Details |
|---------|---------|
| **Token Name** | Descriptive name for tracking purpose (e.g., "JiraHub-Production") |
| **Expiration** | Default: 1 year. Range: 1 day to 365 days. ⚠️ Plan renewal before expiration |
| **Scopes** | Permissions the token can use (recommended security practice) |
| **Created Date** | Shows when token was created |

---

### How to Use Token in JiraHub

1. **Copy your API token**
2. Open JiraHub → **Jira Connect** page
3. Fill in:
   - **Jira URL:** `https://your-domain.atlassian.net`
   - **Email:** Your Atlassian account email
   - **API Token:** Paste your generated token
4. Click **Connect**
5. Token is encrypted and stored securely

---

### Test Your Token (Optional)

Test if your token works before configuring JiraHub:

```bash
# Replace with your details
JIRA_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="your.email@company.com"
JIRA_TOKEN="your_api_token_here"

# Test basic connectivity
curl -v "$JIRA_URL" --user "$JIRA_EMAIL:$JIRA_TOKEN"

# Expected response: 200 or 403 (not 401)
# 401 = Invalid token/email
# 200 = Success
```

---

### Revoke an API Token

If token is compromised or no longer needed:

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Find the token in the list
3. Click **Revoke** next to it
4. Confirm - token is permanently deleted

**Alternative:** Revoke all tokens at once for account reset (rare)

---

### Jira Cloud API Details

| Component | Details |
|-----------|---------|
| **Base URL** | `https://{domain}.atlassian.net` |
| **REST API** | v3 for issue operations |
| **Agile API** | v1.0 for board/sprint operations |
| **Authentication** | HTTP Basic Auth: `email:token` in header |
| **Rate Limits** | 60 requests/minute (Jira Cloud) |
| **Rate Limit Headers** | Response includes: `X-RateLimit-Limit`, `X-RateLimit-Remaining` |

---

### Custom Field Discovery

JiraHub auto-discovers custom fields:

- **Story Points Field**: Searches common names (Story Points, Points, Estimates, etc.)
- **Team Field**: Custom "Team" field if configured in Jira
- **Sprint Field**: Standard Jira Sprint field

If fields not auto-discovered:

- Check field names in Jira: **Project Settings → Fields**
- Contact Jira admin if fields are hidden from your account
- Manually specify field IDs in `app/core/config.py` if needed

---

### Security Best Practices

✅ **DO:**

- Use scoped tokens (limit permissions)
- Store token in password manager
- Set reasonable expiration (90-365 days)
- Create separate tokens per tool/integration
- Rotate tokens periodically

❌ **DON'T:**

- Commit tokens to Git
- Share tokens via email or chat
- Use tokens directly in code (use environment variables)
- Use account password instead of token
- Create tokens with unnecessary scopes

---

### Troubleshooting API Token Issues

| Problem | Solution |
|---------|----------|
| **401 Unauthorized** | Token invalid or expired. Regenerate new token |
| **403 Forbidden** | Token valid but lacks required scopes. Check token scopes match requirements |
| **Token Expired** | Recreate token. Old token automatically revokes after expiration |
| **Can't Find API Token Page** | Ensure you're logged in. Go to <https://id.atlassian.com/manage-profile/security/api-tokens> |
| **One-Time Passcode Never Arrives** | Check spam folder. Request new passcode from Atlassian |
| **Can't Create More Tokens** | Account limit reached (varies by org). Revoke unused tokens and try again |

---

### References

- **Official Docs:** [Manage API Tokens - Atlassian Support](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- **Jira Scopes:** [Jira Platform Scopes](https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/)
- **Account Security:** [Keep Your Atlassian Account Secure](https://support.atlassian.com/atlassian-account/docs/keep-your-atlassian-account-secure/)

---

## 🆘 Troubleshooting

### **Streamlit Won't Start**

```bash
# Error: ModuleNotFoundError: No module named 'streamlit'
→ Make sure uv dependencies are synced: uv sync

# Error: Port 8501 already in use
→ Kill process: lsof -ti:8501 | xargs kill -9
  Or run on different port: uv run streamlit run app/main.py --server.port=8502
```

### **Redis Connection Failed**

```bash
# Error: Connection refused (Redis not running)
→ Start Redis: docker run -d -p 6379:6379 redis:latest
  Or check if running: redis-cli ping (should return PONG)

# Error: REDIS_URL wrong format
→ Check .env: Should be redis://localhost:6379/0
  For Docker: redis://redis:6379/0 (use container DNS)
```

### **Jira Connection Failed**

```bash
# Error: 401 Unauthorized
→ Check Jira URL, email, API token are correct
  Verify token hasnt expired (regenerate if > 1 year old)

# Error: 404 Not Found (project/board missing)
→ Verify project key & board ID in Jira
  Ensure user has permission to access them
```

### **Database Locked or Corrupted**

```bash
# Error: database is locked
→ Only one Streamlit dev server can access SQLite at a time
  Stop other Streamlit processes or switch to PostgreSQL for production

# Error: table 'user' already exists
→ Delete data/jirahub.db and restart (fresh DB created)
  Or run: uv run alembic downgrade base && uv run alembic upgrade head
```

### **Session Lost on Browser Refresh**

```bash
# User logged out after Ctrl+R
→ This should NOT happen (cookie persistence is configured)
  Check: .env SESSION_EXPIRY_HOURS is not 0
  Clear browser cookies, try again
  If persistent, check app logs: uv run streamlit run app/main.py --logger.level=debug
```

### **Jira Caching Issues**

```bash
# Old data showing in dashboard
→ Click "Refresh All Projects" button (top right)
  Or: Clear Redis cache: redis-cli FLUSHDB

# Issues not auto-syncing with Jira
→ Manual refresh required (no webhook integration yet)
→ Future: Add Jira webhooks for real-time updates
```

### **Performance / Slowness**

```bash
# Dashboard takes 10+ seconds to load
→ Likely causes:
   1. Redis not running or slow network → Check redis-cli ping
   2. Jira API rate limited → Check rate limit in response headers
   3. Large project (1000+ issues) → Consider filtering by board/status

# Solutions:
   → Restart Redis: docker restart <redis_container_id>
   → Use board/status filters to reduce load
   → Scale Redis if many concurrent users
```

---

## 🔧 Development & Contributing

### Set Up Development Environment

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run formatters before commit
uv run black .
uv run isort .
uv run ruff check . --fix

# Run tests (if tests exist)
uv run pytest tests/
```

### Code Standards

- **Python**: PEP 8, type hints recommended
- **Git**: Conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- **Style**: Black (line length 100)
- **Linting**: Ruff (E, F, I, UP rules)

### Testing

```bash
# Unit tests (create in tests/ directory)
uv run pytest tests/ -v

# Test Jira connectivity
uv run python -c "from app.services.jira_client import JiraClient; print('Import OK')"

# Test database
uv run python -c "from app.models.db import engine; print('DB OK')"
```

### Common Development Tasks

#### Add New Page

```python
# app/pages/new_feature.py
import streamlit as st

def render():
    st.title("New Feature")
    st.write("Your feature here")

render()  # Streamlit auto-discovers as page
```

Then reference in `app/main.py` navigation.

#### Add New Database Model

```python
# app/models/my_model.py
from app.models.base import Base
from sqlalchemy import Column, String

class MyModel(Base):
    __tablename__ = "my_model"

    name = Column(String, nullable=False)

# Then run:
uv run alembic revision --autogenerate -m "add my_model"
uv run alembic upgrade head
```

#### Add New Jira API Endpoint

```python
# In app/services/jira_client.py
async def get_custom_endpoint(self, endpoint: str) -> dict:
    return await self._request("GET", f"/rest/api/3/{endpoint}")
```

#### Cache a Custom Result

```python
# In your service/page
cache = get_cache_service()
cached_data = run_async(cache.get_cached(user_email, "MyKey"))
if not cached_data:
    # Fetch from API
    await cache.set_cached(user_email, "MyKey", data)
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feat/my-feature

# Make changes, test locally
# ...

# Commit with conventional message
git add .
git commit -m "feat: add new filter to dashboard"

# Push and create PR
git push origin feat/my-feature
# Create Pull Request on GitHub
```

---

## 📋 Roadmap & Future Features

- [ ] Jira webhooks for real-time issue updates
- [ ] Team velocity & sprint burndown charts
- [ ] Scheduled reports & email delivery
- [ ] Slack integration for notifications
- [ ] Time tracking insights & billing
- [ ] Custom KPI dashboards
- [ ] Dark mode support
- [ ] Multi-language support

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) file for details.

---

## 🤝 Support & Contact

- **Issues**: Create a GitHub issue for bugs or feature requests
- **Questions**: Check Troubleshooting section first
- **Contributions**: See [Development & Contributing](#-development--contributing) section

---

## 🏆 Acknowledgments

Built with:

- [Streamlit](https://streamlit.io) - Web app framework
- [SQLAlchemy](https://sqlalchemy.org) - Database ORM
- [Jira Cloud REST API](https://developer.atlassian.com/cloud/jira/rest/) - Issue tracking data
- [httpx](https://www.python-httpx.org) - Async HTTP client
- [Redis](https://redis.io) - In-memory cache

---

**JiraHub v0.1.0** • Last updated: February 2026
