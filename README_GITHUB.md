# 🎬 Telegram Media Downloader Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()
[![Version](https://img.shields.io/badge/Version-1.1.0-orange.svg)](CHANGELOG.md)

> 🚀 A powerful Telegram bot that downloads media from YouTube, Instagram, Terabox, and more - instantly!

![Demo](https://via.placeholder.com/800x200/0088cc/ffffff?text=Telegram+Media+Downloader+Bot)

## ✨ Features

- 🎥 **Multi-Platform Support** - YouTube, Instagram, Terabox, and more
- 📥 **Instant Downloads** - Get your files in seconds
- 🎨 **Beautiful UI** - Artistic interface with rich formatting
- 🔐 **Secure** - Token protection with `.env` file
- 📊 **Smart Handling** - Automatic file size detection
- 🌐 **Universal** - Works with many social media platforms
- 📱 **Easy to Use** - Just send a link!

## 🎯 Demo

```
You: /start

Bot: ╔═══════════════════════════════════════╗
     ║  🎬 MEDIA DOWNLOADER BOT 🎬         ║
     ╚═══════════════════════════════════════╝
     
     Welcome to your personal media downloader!
     
     📥 Supported Platforms:
       • 🎥 YouTube Videos
       • 📸 Instagram Reels & Posts
       • 📦 Terabox Files
       • 🌐 Many Other Platforms
     
     🚀 How to Use:
       1️⃣ Copy any media URL
       2️⃣ Send it to me
       3️⃣ Get your file instantly!

You: https://youtube.com/watch?v=...

Bot: ⏳ Processing your request...
     🔍 Analyzing URL
     ⚙️ Fetching data
     📥 Preparing download
     
     ✅ Download Ready!
     📁 File: video.mp4
     📊 Size: 3.45 MB
     
     [Sends file]
```

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/telegram-media-bot.git
cd telegram-media-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Bot Token

Create a `.env` file:

```bash
TELEGRAM_TOKEN=your_bot_token_here
```

> Get your token from [@BotFather](https://t.me/BotFather) on Telegram

### 4. Run Bot

**Windows:**
```powershell
.\start_bot.ps1
```

**Linux/Mac:**
```bash
python bot.py
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message with usage guide |
| `/help` | Get detailed help and FAQ |
| `/about` | View bot information and statistics |
| `/supported` | List all supported platforms |

## 🌐 Supported Platforms

| Platform | Status | Features |
|----------|--------|----------|
| YouTube | ✅ | Videos, Music, Shorts |
| Instagram | ✅ | Reels, Posts, IGTV |
| Terabox | ✅ | Large file support |
| Generic | ✅ | Many other platforms |

## 📸 Screenshots

### Welcome Screen
Beautiful ASCII art welcome message with clear instructions.

### Download Process
Professional progress indicators with emoji feedback.

### Error Handling
Helpful error messages with solutions.

## 🛠️ Technical Details

- **Language:** Python 3.8+
- **Framework:** pyTelegramBotAPI
- **Configuration:** Environment variables (.env)
- **Logging:** Enhanced with timestamps
- **Parse Mode:** HTML for rich formatting
- **File Limit:** 2GB for direct upload

## 📁 Project Structure

```
telegram-media-bot/
├── bot.py                 # Main bot application
├── requirements.txt       # Python dependencies
├── .env                   # Configuration (not in repo)
├── .env.example          # Configuration template
├── .gitignore            # Git ignore rules
├── start_bot.ps1         # Quick start script (Windows)
├── test_apis.py          # API testing script
│
├── README.md             # This file
├── QUICKSTART.md         # Quick start guide
├── DEPLOYMENT.md         # Deployment instructions
├── CHANGELOG.md          # Version history
└── CONTRIBUTING.md       # Contribution guidelines
```

## 🔐 Security

This bot uses secure token management:

- ✅ Token stored in `.env` file (not in code)
- ✅ `.env` file in `.gitignore` (protected from commits)
- ✅ Safe to share repository publicly
- ✅ Environment variable fallback support

See [DEPLOYMENT.md](DEPLOYMENT.md) for security best practices.

## 🚢 Deployment

Multiple deployment options available:

- **Local Development** - Run on your computer
- **VPS** - Deploy to DigitalOcean, AWS, etc.
- **Heroku** - Free tier available
- **Docker** - Containerized deployment
- **Webhook Mode** - Production-ready setup

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 📊 Statistics

- **Platforms:** 4+ supported
- **Commands:** 4 main commands
- **File Size Limit:** 2GB direct upload
- **Processing Time:** ~5-10 seconds average
- **Uptime:** 24/7 when deployed

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m '✨ Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

## 🆘 Support

- 📚 Check [QUICKSTART.md](QUICKSTART.md) for setup help
- 🐛 Report bugs via [GitHub Issues](../../issues)
- 💡 Request features via [GitHub Issues](../../issues)
- 📖 Read [DEPLOYMENT.md](DEPLOYMENT.md) for deployment help

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) - Telegram Bot API wrapper
- API providers for media download services
- All contributors and users

## ⭐ Show Your Support

Give a ⭐️ if this project helped you!

## 🔗 Links

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [Python Telegram Bot Guide](https://core.telegram.org/bots)
- [@BotFather](https://t.me/BotFather) - Create your bot

---

<div align="center">

**Made with ❤️ for seamless media downloads**

[Report Bug](../../issues) · [Request Feature](../../issues) · [Documentation](../../wiki)

</div>
