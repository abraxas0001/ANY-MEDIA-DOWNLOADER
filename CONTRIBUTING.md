# 🎯 CONTRIBUTING GUIDE

Thank you for considering contributing to the Telegram Media Downloader Bot!

## 🚀 Quick Start for Contributors

1. **Fork** the repository
2. **Clone** your fork
3. **Create** `.env` file with your test bot token
4. **Install** dependencies: `pip install -r requirements.txt`
5. **Create** a new branch: `git checkout -b feature/your-feature`
6. **Make** your changes
7. **Test** thoroughly
8. **Commit** with clear messages
9. **Push** to your fork
10. **Open** a Pull Request

## 📋 Development Setup

```powershell
# Clone your fork
git clone https://github.com/yourusername/telegram-media-bot.git
cd telegram-media-bot

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env from example
Copy-Item .env.example .env
# Edit .env and add your test bot token

# Run tests
python test_apis.py

# Start bot
python bot.py
```

## 🎨 Code Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Keep functions small and focused
- Use type hints where helpful
- Comment complex logic

### Example:
```python
def download_media(url: str, platform: str) -> dict:
    """
    Download media from specified platform.
    
    Args:
        url: Media URL to download
        platform: Platform name (youtube, instagram, etc.)
    
    Returns:
        dict with download info or error
    """
    # Implementation here
```

## 🧪 Testing

Before submitting PR:

1. Test all commands (`/start`, `/help`, `/about`, `/supported`)
2. Test with multiple platforms (YouTube, Instagram, Terabox)
3. Test error handling (invalid URLs, unreachable links)
4. Test large files (>2GB)
5. Run `python test_apis.py`
6. Check for Python errors with your IDE

## 📝 Commit Messages

Use clear, descriptive commit messages:

**Good:**
```
✨ Add Instagram Stories support
🐛 Fix YouTube thumbnail extraction
📚 Update deployment documentation
🔐 Improve token security handling
```

**Avoid:**
```
fix bug
update code
changes
```

### Commit Types:
- ✨ `:sparkles:` - New feature
- 🐛 `:bug:` - Bug fix
- 📚 `:books:` - Documentation
- 🎨 `:art:` - Code style/format
- 🔐 `:lock:` - Security fix
- ⚡ `:zap:` - Performance
- ♻️ `:recycle:` - Refactor
- 🧪 `:test_tube:` - Tests

## 🌟 What to Contribute

### High Priority
- [ ] Additional platform support (TikTok, Twitter/X, etc.)
- [ ] Inline keyboard for quality selection
- [ ] Download progress tracking
- [ ] Better error messages
- [ ] Performance improvements
- [ ] Unit tests
- [ ] Documentation improvements

### Medium Priority
- [ ] Playlist/album support
- [ ] Audio extraction
- [ ] Subtitle downloads
- [ ] Custom file naming
- [ ] Download history
- [ ] User statistics

### Nice to Have
- [ ] Multi-language support
- [ ] Admin dashboard
- [ ] Rate limiting
- [ ] Database integration
- [ ] Webhook mode
- [ ] Docker compose setup

## 🔍 Code Review Process

1. **Automated checks** run on PR
2. **Maintainer review** (1-3 days)
3. **Feedback** addressed by contributor
4. **Approval** and merge
5. **Release** in next version

## 🐛 Bug Reports

Use GitHub Issues with this template:

```markdown
**Bug Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Send command /start
2. Send URL: https://...
3. See error

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Screenshots:**
If applicable

**Environment:**
- OS: Windows 11
- Python: 3.11
- Bot Version: 1.1.0
```

## 💡 Feature Requests

Use GitHub Issues with this template:

```markdown
**Feature Description:**
Clear description of the feature

**Use Case:**
Why this feature is needed

**Proposed Solution:**
How it could work

**Alternatives:**
Other approaches considered

**Additional Context:**
Any other relevant info
```

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on what is best for the project
- Show empathy towards others

## 🙏 Recognition

Contributors will be:
- Listed in `CONTRIBUTORS.md`
- Mentioned in release notes
- Credited in commit history

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## 📞 Questions?

- Open a GitHub Issue
- Check existing documentation
- Review closed issues for solutions

---

**Thank you for making this project better!** 🎉
