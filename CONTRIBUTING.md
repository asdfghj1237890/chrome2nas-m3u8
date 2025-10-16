# Contributing to Chrome2NAS M3U8 Downloader

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Getting Started

1. **Read the Documentation**
   - [README.md](README.md) - Project overview
   - [SPECIFICATION.md](SPECIFICATION.md) - Technical specification
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

2. **Set Up Development Environment**
   - Docker & Docker Compose
   - Python 3.11+
   - Chrome browser with Developer mode
   - Code editor of your choice

## Development Workflow

### 1. Fork and Clone
```bash
git clone https://github.com/yourusername/chrome2nas-m3u8.git
cd chrome2nas-m3u8
```

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Changes
- Follow existing code style
- Write clear, descriptive commit messages
- Keep commits focused and atomic
- Add tests for new features
- Update documentation as needed

### 4. Test Your Changes

**Backend (Docker Services):**
```bash
cd docker
docker-compose up --build
# Test API endpoints
./test-api.sh
```

**Chrome Extension:**
```bash
cd chrome-extension
# Load unpacked extension in Chrome
# Test functionality manually
```

### 5. Submit Pull Request
- Push your branch to your fork
- Create a pull request to the main repository
- Describe your changes clearly
- Reference any related issues

## Code Style Guidelines

### Python
- Follow PEP 8
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings for classes and public methods

Example:
```python
def download_segment(url: str, timeout: int = 30) -> bytes:
    """
    Download a single HLS segment.
    
    Args:
        url: The segment URL
        timeout: Request timeout in seconds
        
    Returns:
        The segment content as bytes
        
    Raises:
        DownloadError: If download fails
    """
    pass
```

### JavaScript
- Use ES6+ features
- Use `const` and `let`, avoid `var`
- Use async/await for asynchronous operations
- Keep functions focused and small

Example:
```javascript
async function detectM3u8Urls(details) {
  const url = details.url.toLowerCase();
  if (url.includes('.m3u8')) {
    await notifyUrlDetected(details.url);
  }
}
```

## Project Structure

```
chrome2nas-m3u8/
├── chrome-extension/     # Chrome extension source
│   ├── background.js     # Background service worker
│   ├── popup/           # Extension popup UI
│   └── options/         # Extension options page
├── docker/              # Docker services
│   ├── api/            # FastAPI service
│   └── worker/         # Download worker
└── docs/               # Additional documentation
```

## What to Contribute

### High Priority
- M3U8 parser improvements
- FFmpeg integration enhancements
- Chrome extension features
- Bug fixes
- Performance optimizations
- Documentation improvements

### Medium Priority
- Unit tests
- Integration tests
- Error handling improvements
- Logging enhancements
- UI/UX improvements

### Nice to Have
- Additional NAS platform support
- Advanced retry strategies
- Download resume capability
- Bandwidth throttling
- Scheduled downloads

## Reporting Issues

When reporting issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Docker version, NAS model, etc.)
- Relevant logs or error messages

## Code Review Process

1. Maintainers will review your pull request
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Your contribution will be acknowledged in release notes

## Questions?

- Check existing issues and discussions
- Read the documentation thoroughly
- Ask questions in GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make Chrome2NAS M3U8 Downloader better!

