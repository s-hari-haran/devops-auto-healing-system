# DevOps Auto Healing Multi Agent System

## Overview

This is an intelligent DevOps multi-agent system that automatically detects, analyzes, and fixes code errors using AI. The application monitors GitHub repositories for errors, uses Claude AI to generate smart fixes, and provides a web interface for reviewing and applying changes. It's designed to be a self-healing DevOps tool that can be integrated into any development workflow.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
**Technology Stack**: HTML/CSS with Flask templating
- **Problem**: Need a simple, accessible UI for reviewing AI-generated fixes
- **Solution**: Server-side rendering with Flask templates and inline CSS styling
- **Rationale**: Minimal complexity, no build process required, easy to deploy and maintain

### Backend Architecture
**Framework**: Flask (Python web framework)
- **Problem**: Need a lightweight web server to handle GitHub integration and AI analysis
- **Solution**: Flask application with modular client architecture
- **Rationale**: Simple to set up, good for rapid prototyping, extensive ecosystem

**Modular Design Pattern**:
- `claude_client.py` - Encapsulates AI analysis logic
- `github_utils.py` - Handles Git operations (clone, pull, commit, push)
- `main.py` - Flask application routes and orchestration
- **Rationale**: Separation of concerns makes testing and maintenance easier

### AI Integration
**Service**: Anthropic Claude API (claude-sonnet-4-20250514)
- **Problem**: Need intelligent error analysis and code fix generation
- **Solution**: Claude API with structured JSON responses
- **Approach**: Send error logs + source code, receive explanation + fixed code
- **Rationale**: Claude excels at code understanding and generation tasks

### Git Workflow Architecture
**Library**: GitPython
- **Problem**: Need automated Git operations (clone, branch, commit, push)
- **Solution**: GitPython wrapper with branch management and token authentication
- **Flow**: 
  1. Clone/pull repository
  2. Create auto-fix branch
  3. Apply fixes
  4. Commit and push changes
- **Rationale**: Programmatic Git control without shell commands, better error handling

### Error Detection & Processing
**Pattern**: Log parsing with regex extraction
- **Problem**: Need to identify errors and map them to source files
- **Solution**: Parse error logs, extract file paths and error messages
- **Current Implementation**: Basic regex-based parsing for file paths and error text
- **Rationale**: Flexible approach that works with various log formats

### State Management
**Pattern**: In-memory dictionary
- **Problem**: Need to track repository state, errors, and fixes across requests
- **Solution**: Global `current_state` dictionary storing repo info, errors, and fixes
- **Limitation**: State is lost on server restart (not persistent)
- **Rationale**: Simple for MVP, can be upgraded to database later

## External Dependencies

### AI Service
- **Anthropic Claude API**: Core AI engine for error analysis and code generation
  - Requires: `ANTHROPIC_API_KEY` environment variable
  - Model: claude-sonnet-4-20250514
  - Package: `anthropic` Python SDK

### Version Control
- **GitHub**: Repository hosting and source code management
  - Optional: `GITHUB_TOKEN` for private repository access
  - Package: `GitPython` for Git operations
  - Authentication: Token-based authentication in repository URLs

### Web Framework
- **Flask**: Web application framework
  - Session management with `SESSION_SECRET` environment variable
  - Template rendering for UI
  - JSON API endpoints for AJAX interactions

### Environment Configuration
- **python-dotenv**: Environment variable management
  - Loads configuration from `.env` file
  - Required variables: `ANTHROPIC_API_KEY`
  - Optional variables: `SESSION_SECRET`, `GITHUB_TOKEN`

### Development Setup
- Local file system for repository cloning (default: `repos/` directory)
- No database required (current implementation uses in-memory state)
- Error logs expected in monitored repositories or uploaded via UI