# GitHub Onboarding & Workflow Migration Tool

A comprehensive full-stack web application for managing GitHub organizations, repositories, and workflows with intelligent AI-powered analysis and migration capabilities. Built with FastAPI backend and React frontend.

## 🌟 Key Features

- **AI-Powered Workflow Analysis** - Analyze repositories and detect security scanning gaps
- **Workflow Templates Management** - Auto-initialize security scanning templates (SAST, SCA, IAC)
- **Smart Workflow Enhancement** - Preview and apply security scanning steps to existing workflows
- **Legacy Config Cleanup** - Scan and identify legacy configuration files
- **Repository Onboarding** - Batch scan repositories for security tool keywords
- **Duplicate Detection** - Identify duplicate workflow content vs templates
- **GitHub Enterprise Server Support** - Works with both GitHub.com and GHE Server

📖 See [GITHUB_ENTERPRISE_SUPPORT.md](GITHUB_ENTERPRISE_SUPPORT.md) for GHE configuration details.

## Project Structure

```
├── backend/           # FastAPI backend application
│   ├── main.py       # Main FastAPI application
│   ├── github_service.py # GitHub API integration
│   ├── secrets_crud.py   # Encrypted secrets management
│   ├── templates_crud.py # Template management
│   ├── crypto.py         # Encryption utilities
│   ├── database.py       # Dual database configuration
│   ├── workflow_parser.py # YAML workflow manipulation
│   ├── requirements.txt  # Python dependencies
│   ├── data/             # Database storage (gitignored)
│   │   ├── secrets.db    # Encrypted secrets database
│   │   ├── templates.db  # Workflow templates database
│   │   └── secret.key    # Encryption key (NEVER commit!)
│   ├── templates/        # Template files
│   │   └── blackduck/    # Black Duck security templates
│   └── README.md         # Backend setup instructions
├── frontend/         # React frontend application
│   ├── src/
│   │   ├── App.js                    # Main application component
│   │   ├── GitHubOrganizations.js   # GitHub organizations view
│   │   ├── WorkflowSearch.js        # Workflow search functionality
│   │   ├── AIWorkflowAnalysis.js    # AI-powered workflow analysis
│   │   ├── TemplatesManager.js      # Template management interface
│   │   ├── LegacyConfigCleanup.js   # Legacy config scanner
│   │   ├── OnboardingScanner.js     # Repository onboarding scanner
│   │   ├── SecretsManager.js        # Secrets management interface
│   │   ├── githubAPI.js             # GitHub API client
│   │   ├── secretsAPI.js            # Secrets API client
│   │   ├── templatesAPI.js          # Templates API client
│   │   └── index.css                # Application styles
│   ├── public/       # Static files
│   ├── package.json  # Node.js dependencies
│   └── README.md     # Frontend setup instructions
├── .vscode/          # VS Code tasks and settings
│   └── tasks.json    # VS Code build/run tasks
├── .gitignore        # Git ignore rules (protects secrets & databases)
└── README.md         # This file
```

## Quick Start

### Prerequisites

- **Python 3.8+** installed (3.13 recommended)
- **Node.js 16+** and npm installed (Node 18+ recommended)
- **GitHub Personal Access Token** ([Create one here](https://github.com/settings/tokens))
  - Required scopes: `repo`, `read:org`, `workflow`
- Git (optional)

### Key Dependencies

**Backend:**
- FastAPI 0.115.6
- SQLAlchemy 2.0.36
- Pydantic 2.10.3
- PyYAML 6.0.2
- cryptography 43.0.3
- httpx 0.27.2

**Frontend:**
- React 18.3.1
- Recharts 2.12.7

### 1. Clone or Download the Project

If using Git:
```bash
git clone <repository-url>
cd onboarding-tool
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
python main.py
# OR using uvicorn directly
# python -m uvicorn main:app --reload
```

The backend API will be available at: http://localhost:8000

**On First Startup:**
- Creates `data/secrets.db` for encrypted secrets storage
- Creates `data/templates.db` for workflow templates
- Auto-initializes 8 security scanning templates from `templates/blackduck/`:
  - 3 complete workflow templates (SAST+IAC, SCA+IAC, comprehensive)
  - 3 job templates (Polaris, Coverity, Black Duck SCA)
  - 2 step templates (Polaris, Black Duck SCA)
- Auto-creates `GITHUB_TOKEN` secret (empty - requires configuration via Secrets Management UI)

### 3. Frontend Setup (New Terminal)

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

The frontend application will be available at: http://localhost:3000

### 4. Using VS Code Tasks (Recommended)

Open the project in VS Code and use the built-in tasks:

1. **Ctrl+Shift+P** → "Tasks: Run Task"
2. Choose from:
   - **Start Backend** - Runs the FastAPI server
   - **Start Frontend** - Runs the React dev server
   - **Start Full Stack** - Starts both in separate windows

## Application Features

The application includes multiple powerful sections accessible via tab navigation:

### 1. AI Workflow Analysis 🤖

**Intelligent Repository Analysis:**
- AI-powered detection of security scanning gaps
- Analyze multiple repositories in parallel for performance
- Identify missing Black Duck security tools (Polaris, Coverity, SCA)
- Detect existing workflows and build jobs
- Language and package manager detection
- Smart template recommendations based on project structure

**Workflow Enhancement:**
- Preview changes before applying them
- Insert security scanning steps into existing jobs
- Add new security scanning jobs to workflows
- Side-by-side diff view with syntax highlighting
- Direct commit or Pull Request options
- Duplicate detection to avoid redundant scanning

**Template Management:**
- Pre-built templates for Polaris SAST, Coverity, Black Duck SCA
- Workflow, Job, and Step template types
- Auto-initialization from template files on startup
- Categorized by tools (polaris, coverity, blackduck_sca) and scan types (SAST, SCA)
- Stored in separate templates database (templates.db)

### 2. Repository Onboarding Scanner 📋

**Batch Repository Scanning:**
- Scan multiple repositories for security tool keywords
- Search across multiple branches per repository
- Real-time progress tracking with scan dashboard
- Keyword matching against templates (coverity, polaris, blackduck)
- Export scan results
- Legacy configuration detection

**Dashboard Metrics:**
- Total legacy files found
- Affected repositories count
- Branches scanned
- Keywords matched
- Scan duration tracking

### 3. GitHub Organizations 🐙

**Organization Management:**
- View all organizations the authenticated user has access to
- Switch between organization and user repository scopes
- View organization details (members, repos, followers, creation date)
- Organization avatar and description display

**Repository Management:**
- Browse repositories by organization or user scope
- Filter repositories by programming language
- View repository statistics (stars, forks, watchers, issues)
- Display repository metadata (license, language, last updated)
- Repository topics and badges (private, fork, archived)
- Select multiple repositories for onboarding
- Client-side filtering for user repositories (instant search)

**Repository Details (Modal View):**
- Comprehensive repository information
- Statistics with visual cards (stars, forks, watchers, issues)
- Programming languages breakdown with colored indicators and percentage bars
- Topics display with tag styling
- Custom properties in table format
- Latest release information
- GitHub Actions workflows listing with download links
- Creation, update, and push timestamps

**Advanced Features:**
- Automatic repository and language loading for user scope
- Organization-specific repository browsing
- Language-based filtering with visual language indicators
- Repository selection for batch operations

### 4. Workflow Search 🔍
- Search GitHub Actions workflows across repositories
- Filter by organization or user scope
- Search workflow content by keywords
- View workflow details and download links

### 5. Templates Manager 📝

**Template Operations:**
- View all available workflow templates
- Search templates by name or description
- Filter by template type (Workflow, Job, Step)
- Filter by category (Polaris, Coverity, Black Duck SCA)
- Create custom templates
- Update existing templates
- Delete templates
- View template metadata and requirements

**Template Structure:**
- **Workflows**: Complete GitHub Actions workflow files
- **Jobs**: Reusable job definitions for security scanning
- **Steps**: Individual step fragments to insert into existing jobs
- Auto-populated from `backend/templates/blackduck/` directory
- Supports Polaris SAST, Coverity, and Black Duck SCA tools

### 6. Legacy Config Cleanup 🧹

**Configuration Scanner:**
- Scan repositories for legacy configuration files
- Detect outdated Coverity, Polaris, Black Duck configs
- Multi-branch scanning support
- Real-time progress tracking
- Interactive scan dashboard

**Dashboard Features:**
- Legacy files found count
- Affected repositories
- Branches scanned
- Keywords matched statistics
- Scan duration with timer
- Detailed results per repository

### 7. Secrets Management 🔐  
- **Encrypted storage** of sensitive information using Fernet encryption
- **SQLite database** with SQLAlchemy ORM
- Secure key management with automatic key generation
- Create, read, update, and delete encrypted secrets
- View encrypted and decrypted values
- Essential for storing GitHub Personal Access Token

## Setup for GitHub Integration

1. **Create GitHub Personal Access Token:**
   - Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
   - Click "Generate new token (classic)"
   - Required scopes:
     - `repo` - Full control of private repositories
     - `read:org` - Read organization data
     - `workflow` - Update GitHub Action workflows (optional)

2. **Store Token in Application:**
   - Open the application at http://localhost:3000
   - Go to **🔐 Secrets Management** tab
   - Create a new secret with name: `GITHUB_TOKEN`
   - Paste your GitHub Personal Access Token as the value
   - Save the secret

3. **SSO Authorization (if required):**
   - If your organization requires SAML SSO:
     - Go to [GitHub Settings → Personal Access Tokens](https://github.com/settings/tokens)
     - Find your token and click **"Configure SSO"**
     - Click **"Authorize"** for your organization
     - Complete the SSO authentication flow
   - See [SSO_AUTHENTICATION.md](SSO_AUTHENTICATION.md) for detailed instructions

4. **Access GitHub Features:**
   - Go to **🐙 GitHub Organizations** tab
   - Select scope: "All My Repositories" or choose an organization
   - Browse and manage repositories

## Template System

### Template Types

The application supports three types of security scanning templates:

**1. Workflow Templates (Complete Files)**
- Full GitHub Actions workflow files
- Examples: `SAST,IAC.yml`, `SCA,IAC.yml`, `SAST,SCA,IAC,DAST.yml`
- Use when: Starting from scratch or replacing entire workflow

**2. Job Templates**
- Reusable job definitions for security scanning
- Examples: `polaris-security-scan-job.yml`, `coverity-security-scan-job.yml`
- Use when: Adding new jobs to existing workflows

**3. Step Templates**
- Individual step fragments
- Examples: `polaris-security-scan-step.yml`, `black-duck-sca-scan-step.yml`
- Use when: Enhancing existing jobs with security scanning steps

### Template Categories

Templates are categorized by:
- **Tools**: `polaris`, `coverity`, `blackduck_sca`
- **Scan Types**: `SAST`, `SCA`, `IAC`, `DAST`

### Template Structure

```
backend/templates/blackduck/
├── templates.json          # Template metadata and configuration
├── SAST,IAC.yml           # Workflow: SAST + IAC scanning
├── SCA,IAC.yml            # Workflow: SCA + IAC scanning
├── SAST,SCA,IAC,DAST.yml # Workflow: Comprehensive security
├── jobs/
│   ├── polaris-security-scan-job.yml
│   ├── coverity-security-scan-job.yml
│   └── black-duck-sca-scan-job.yml
└── steps/
    ├── polaris-security-scan-step.yml
    └── black-duck-sca-scan-step.yml
```

### Auto-Initialization

On first startup, the backend automatically:
1. Reads `templates/blackduck/templates.json`
2. Loads all YAML template files
3. Creates database entries with metadata
4. Sets up categories and requirements
5. Makes templates available for AI analysis and workflow enhancement

## GitHub Enterprise Server Support

This application supports both **GitHub.com** and **GitHub Enterprise Server**. 

### Configuration Architecture

**GITHUB_API_URL** - Environment variable (not stored in Secrets Manager):
- Set once before starting the backend
- Defaults to `https://api.github.com` if not set
- This is configuration, not a secret

**GITHUB_TOKEN** - Secret (stored encrypted in database):
- Stored via Secrets Manager UI
- Can be updated at runtime

### Setup for GitHub Enterprise

1. **Set the environment variable** before starting the backend:

   **Windows PowerShell:**
   ```powershell
   $env:GITHUB_API_URL="https://github.enterprise.com/api/v3"
   python backend/main.py
   ```

   **Linux/Mac:**
   ```bash
   export GITHUB_API_URL="https://github.enterprise.com/api/v3"
   python backend/main.py
   ```

2. **Generate a token from your GitHub Enterprise Server** (not GitHub.com)

3. **Store the token** in Secrets Manager as `GITHUB_TOKEN`

📖 For detailed configuration instructions, see [GITHUB_ENTERPRISE_SUPPORT.md](GITHUB_ENTERPRISE_SUPPORT.md)

## Technical Stack

### Backend (FastAPI)
- ✅ RESTful API with FastAPI
- ✅ Automatic API documentation (Swagger UI)
- ✅ CORS enabled for frontend communication
- ✅ Pydantic models for data validation
- ✅ **Dual SQLite databases**:
  - `secrets.db` - Encrypted secrets with Fernet encryption
  - `templates.db` - Workflow templates with metadata
- ✅ **Local database storage with SQLAlchemy 2.0**
- ✅ **GitHub API integration**:
  - User information and token scopes
  - Organizations and repositories
  - Repository details with custom properties
  - Programming languages detection
  - GitHub Actions workflows
  - Workflow content search
  - Workflow file download and parsing
  - Latest releases
- ✅ **AI-Powered Analysis**:
  - Parallel repository analysis
  - Black Duck security tools detection
  - Workflow structure parsing with PyYAML
  - Smart template recommendations
  - Duplicate workflow detection
- ✅ **Template System**:
  - Auto-initialization from YAML files
  - Workflow, Job, and Step templates
  - Template metadata and requirements
  - Category-based organization
- ✅ **Workflow Enhancement**:
  - YAML parsing and manipulation
  - Step insertion into existing jobs
  - Job merging into workflows
  - Preview generation with diff view
  - Direct commit or PR creation
- ✅ **Async HTTP client with httpx**
- ✅ **Comprehensive error handling**

### Frontend (React)
- ✅ Modern React 18.3.1 with hooks (useState, useEffect, useRef)
- ✅ Responsive design with card-based layouts
- ✅ HTTP client with Fetch API
- ✅ Error handling and loading states
- ✅ **Tab-based navigation** (AI Analysis, Onboarding, GitHub, Workflow Search, Templates, Legacy Cleanup, Secrets)
- ✅ **Advanced Modal dialogs**:
  - Repository details
  - Workflow enhancement preview with side-by-side diff
  - Template management
- ✅ **AI Workflow Analysis Interface**:
  - Real-time analysis progress
  - Parallel repository processing
  - Template recommendations display
  - Enhancement preview with YAML syntax highlighting
- ✅ **Onboarding Scanner Dashboard**:
  - Real-time scan progress
  - Interactive metrics cards
  - Scan duration timer with useRef
  - Results filtering and export
- ✅ **Client-side filtering** for instant search
- ✅ **Color-coded language indicators**
- ✅ **Visual repository statistics**
- ✅ **Multi-select repository interface**
- ✅ **YAML diff viewer** with proper indentation
- ✅ Form validation

### Development Features
- ✅ Hot reload for both backend and frontend
- ✅ VS Code tasks for easy development
- ✅ Comprehensive error handling
- ✅ Code formatting and linting support
- ✅ GitHub Copilot integration

## API Endpoints

### Templates Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | Get all templates |
| GET | `/api/templates/{id}` | Get template by ID |
| GET | `/api/templates/search/{query}` | Search templates |
| POST | `/api/templates` | Create new template |
| PUT | `/api/templates/{id}` | Update template |
| DELETE | `/api/templates/{id}` | Delete template |
| POST | `/api/templates/apply` | Apply template to repository |

### AI Workflow Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai-analyze` | Analyze repositories with parallel processing |
| POST | `/api/workflows/preview-enhancement` | Preview workflow enhancement changes |
| POST | `/api/workflows/apply-enhancement` | Apply enhancement to workflow |
| POST | `/api/workflows/detect-duplicates` | Detect duplicate content in workflows |
| POST | `/api/workflows/enhance/search` | Search and analyze workflows with templates |

### Onboarding & Scanning
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/onboarding/scan` | Scan repositories for template keywords |
| GET | `/api/repositories/{owner}/{repo}/workflows` | Get all workflow files |

### Secrets Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/secrets` | Get all secrets (encrypted) |
| GET | `/api/secrets/{id}` | Get secret by ID (encrypted) |
| GET | `/api/secrets/{id}/decrypt` | Get decrypted secret value |
| GET | `/api/secrets/name/{name}` | Get secret by name |
| POST | `/api/secrets` | Create new encrypted secret |
| PUT | `/api/secrets/{id}` | Update secret |
| DELETE | `/api/secrets/{id}` | Delete secret |

### GitHub Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/github/user` | Get authenticated GitHub user info |
| GET | `/api/github/token-status` | Check if GitHub token is configured and valid |
| GET | `/api/github/token-scopes` | Get token scopes |
| GET | `/api/github/organizations` | Get all organizations for authenticated user |
| GET | `/api/github/organizations/{org}` | Get organization details |
| GET | `/api/github/organizations/{org}/languages` | Get available programming languages in org |
| GET | `/api/github/organizations/{org}/repositories` | Get organization repositories (with language filter) |
| GET | `/api/github/user/languages` | Get available programming languages for user repos |
| GET | `/api/github/user/repositories` | Get user repositories (with language filter) |
| GET | `/api/github/repositories/{owner}/{repo}/details` | Get detailed repository information |
| POST | `/api/github/search/workflows` | Search repositories by workflow content |

## API Documentation

When the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development Workflow

### Making Changes

1. **Backend Changes**: Edit files in `backend/`, server auto-reloads
2. **Frontend Changes**: Edit files in `frontend/src/`, browser auto-reloads
3. **Adding Dependencies**:
   - Backend: Add to `backend/requirements.txt` then `pip install -r requirements.txt`
   - Frontend: Use `npm install <package-name>` in `frontend/` directory

### Testing the Application

1. Start both servers (backend on :8000, frontend on :3000)
2. Open http://localhost:3000 in your browser
3. Set up GitHub token in Secrets Management
4. Test GitHub features:
   - Browse organizations and repositories
   - Filter by programming language
   - View repository details
   - Search workflow content

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r backend/requirements.txt`
- Check port 8000 is not in use

**Frontend won't start:**
- Check Node.js version: `node --version` (need 16+)
- Install dependencies: `npm install` in frontend directory
- Check port 3000 is not in use

**CORS errors:**
- Ensure backend is running on port 8000
- Check that CORS is configured in `backend/main.py`

**GitHub API calls failing:**
- Verify GITHUB_TOKEN is stored in Secrets Management
- Check token has required scopes (`repo`, `read:org`)
- Verify token is not expired
- Check network tab in browser developer tools

**SSL/Certificate errors:**
- SSL verification is temporarily disabled for development
- In production, ensure proper SSL certificates are configured

## Security Features

### Encrypted Secrets Storage
- **Fernet symmetric encryption** for all stored secrets
- **Automatic encryption key generation** on first use
- **Separate key storage** from encrypted data
- **Dual SQLite databases** for security isolation:
  - `data/secrets.db` - Encrypted secrets only
  - `data/templates.db` - Workflow templates (separate from secrets)
- **No plaintext storage** of sensitive information

### GitHub Token Security
- Token stored encrypted in database
- Never exposed in frontend code
- Transmitted securely between frontend and backend
- Automatically decrypted only when needed for API calls

### SSO (Single Sign-On) Support
- **Automatic SSO error detection** with helpful messages
- **Built-in authorization guidance** in Secrets Management tab
- **Organization-specific error messages** for easier troubleshooting
- Support for both GitHub.com and GitHub Enterprise SSO
- See [SSO_AUTHENTICATION.md](SSO_AUTHENTICATION.md) for complete guide

## Next Steps

### Potential Enhancements
- Repository batch operations (clone, archive, update settings)
- Workflow execution monitoring and logs
- Advanced pull request management
- Issue tracking integration
- Real-time workflow run status
- Template versioning and history
- Custom template creation wizard
- Workflow test execution before deployment

### Authentication & Authorization
- User authentication with JWT tokens
- Role-based access control
- Multi-user support
- Team management

### Deployment
Deploy to production:
1. **Backend**: Deploy to AWS, Azure, or Railway
2. **Frontend**: Deploy to Netlify, Vercel, or AWS S3
3. Configure environment variables
4. Set up production database (PostgreSQL recommended)
5. Enable SSL/TLS certificates
6. Configure proper CORS origins

### Additional Improvements
- Unit and integration tests
- CI/CD pipeline with GitHub Actions
- Logging and monitoring
- Rate limiting for API calls
- Caching for GitHub API responses
- WebSocket support for real-time updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.