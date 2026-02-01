<div align="center">

# 🎬 Video Cover Bot

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest-blue?style=for-the-badge&logo=telegram)](https://telegram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Ready-green?style=for-the-badge&logo=mongodb)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Professional Telegram Bot for Adding Custom Covers to Videos**

[Demo](#-usage) • [Installation](#-installation) • [Setup Guide](#-setup-guide) • [Features](#-features)

</div>

---

## 📖 About

**Video Cover Bot** is a powerful, production-ready Telegram bot designed to help content creators, video editors, and channel managers easily add professional custom thumbnail covers to their videos. With advanced features like force subscription, admin controls, comprehensive logging, and MongoDB integration, this bot is perfect for scaling your video content workflow.

### 🎯 Why Use This Bot?

- **⚡ Lightning Fast**: Asynchronous processing for instant results
- **🎨 Professional Quality**: High-quality cover-applied videos
- **🔐 Secure**: Force subscribe system prevents unauthorized access
- **👮 Full Admin Control**: Ban users, view stats, monitor system
- **📊 Detailed Analytics**: Track all user actions in real-time
- **💾 Persistent Storage**: MongoDB integration for reliable data
- **🌐 Scalable**: Built for thousands of concurrent users
- **🚀 Easy Deployment**: Docker, Heroku, VPS support

---

## ✨ Features

### 🎨 Core Functionality
| Feature | Description |
|---------|-------------|
| 📸 **Set Custom Cover** | Upload a photo to use as video thumbnail |
| 🎬 **Apply Cover** | Send videos to automatically add the cover |
| ✏️ **Change Cover** | Switch between multiple covers anytime |
| 🗑️ **Remove Cover** | Delete saved covers |
| 💾 **Dump Channel** | Auto-save processed videos to private channel |
| 📝 **Caption Preservation** | Keep original video captions intact |

### 🔐 Security & Control
| Feature | Description |
|---------|-------------|
| 🔒 **Force Subscribe** | Require users to join your channel |
| ✅ **Auto-Verification** | 30-second auto-verify pattern |
| 🚫 **Ban System** | Ban/unban users with reasons |
| 👨‍💼 **Admin Panel** | Comprehensive control dashboard |
| 📋 **User Roles** | Owner/Admin permission system |

### 📊 Monitoring & Logging
| Feature | Description |
|---------|-------------|
| 📈 **User Statistics** | Total users, banned count, daily actives |
| 💻 **System Status** | CPU, RAM, Uptime monitoring |
| 📹 **Video Logging** | All processed videos logged to channel |
| 👤 **User Action Logs** | New users, bans, cover changes, etc. |
| ⏰ **Timestamps** | Every action recorded with exact time |

### 🚀 Advanced Features
| Feature | Description |
|---------|-------------|
| 🤖 **Auto Command Setup** | Bot commands registered on startup |
| 🗄️ **MongoDB Integration** | Scalable document-based database |
| 🔄 **GitHub Auto-Update** | Pull updates from upstream repository |
| 🐳 **Docker Support** | Easy containerized deployment |
| 📱 **Responsive UI** | Inline keyboards and elegant menus |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | python-telegram-bot (async) |
| **Database** | MongoDB + PyMongo |
| **Language** | Python 3.8+ |
| **Container** | Docker |
| **Deployment** | Heroku / VPS / Docker |
| **Monitoring** | psutil |

---

## 📥 Installation

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- MongoDB (local or [MongoDB Atlas](https://mongodb.com/cloud/atlas))
- Git

### Quick Setup (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/video-cover-bot.git
cd video-cover-bot

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup configuration
cp ,env.example config.env
# Edit config.env with your credentials (see Setup Guide below)

# 5. Run bot
python bot.py
```

---

## 🚀 Setup Guide

### Step 1️⃣: Get Bot Token

1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` command
3. Follow prompts to name your bot
4. **Copy the token** (looks like: `123456789:ABCDefGHIjklMNOpqrsTUVwxyz`)

### Step 2️⃣: Configure Environment

```bash
# Copy example file
cp ,env.example config.env

# Edit with your details
nano config.env  # or use VS Code / Notepad++
```

**Required Variables:**
```ini
# Your bot token from @BotFather
BOT_TOKEN=your_token_here

# Your Telegram user ID (get from @userinfobot)
OWNER_ID=123456789

# Force subscribe channel ID (with - prefix)
FORCE_SUB_CHANNEL_ID=-1002659719637

# Log channel ID (where all actions are logged)
LOG_CHANNEL_ID=-1002659719637

# MongoDB connection
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=video_cover_bot
```

### Step 3️⃣: Setup MongoDB

**Option A: Local MongoDB**
```bash
# Windows - Download: https://www.mongodb.com/try/download/community
# Or use Chocolatey:
choco install mongodb-community

# Linux
sudo apt-get install mongodb

# Mac
brew tap mongodb/brew
brew install mongodb-community
```

**Option B: MongoDB Atlas (Recommended for Production)**
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free account
3. Create cluster (M0 free tier)
4. Get connection string
5. Update `MONGODB_URI` in config.env

### Step 4️⃣: Create Telegram Channels

1. Create 2 channels in Telegram:
   - **Force Subscribe Channel** - Users must join this
   - **Log Channel** - All bot actions logged here

2. Get Channel IDs:
   - Forward any message from channel to your bot
   - Check bot logs for channel ID
   - Or use: `@userinfobot` in the channel

3. Update config.env:
```ini
FORCE_SUB_CHANNEL_ID=-1002659719637
LOG_CHANNEL_ID=-1002659719637
```

### Step 5️⃣: Get Your Telegram ID

```
Message @userinfobot in Telegram
It will show your User ID
Copy and set OWNER_ID=your_id in config.env
```

### Step 6️⃣: Run The Bot

```bash
python bot.py
```

✅ **Done!** Your bot is now running.

---

## 💬 User Commands

```
/start          - Start bot & main menu
/help           - Show available commands
/settings       - Configure preferences
/remove         - Delete current cover
```

### Main Menu

After `/start`:

| Button | Action |
|--------|--------|
| 📸 Set Cover | Upload photo as thumbnail |
| ✏️ Change Cover | Replace current cover |
| 🗑️ Remove | Delete cover |
| ⚙️ Settings | Configure dump channel |
| 📊 Stats | View usage statistics |

---

## 👮 Admin Commands

*For bot owner only*

```
/admin              - Open admin panel
/ban userid reason  - Ban user with reason
/unban userid       - Unban user
/stats              - User statistics
/status             - System CPU/RAM/uptime
/restart            - Update & restart bot
```

### Admin Log Channel

All actions logged with:
- 👤 User ID & Username
- 📋 Action type (ban, video, cover, etc.)
- ⏰ Timestamp
- 📝 Additional details

---

## 📖 Usage Workflow

### For End Users

1. **Set Cover**: Send `/start` → Select "📸 Set Cover" → Upload a photo
2. **Apply Cover**: Send any video → Bot adds cover automatically
3. **Get Result**: Video with custom thumbnail cover is sent back
4. *Optional*: Enable dump channel to auto-save videos

### For Admins

```
/admin → Manage users/stats
/ban 123456789 spam → Ban spammer
/stats → View all users & metrics
/status → Check bot health
```

---

## 🐳 Docker Deployment

### Build & Run

```bash
# Build image
docker build -t video-cover-bot .

# Run container
docker run -d \
  --name video-bot \
  -e BOT_TOKEN=your_token \
  -e OWNER_ID=your_id \
  -e MONGODB_URI=mongodb://mongo:27017 \
  --link mongo:mongo \
  video-cover-bot
```

### Docker Compose (Recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  bot:
    build: .
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      OWNER_ID: ${OWNER_ID}
      FORCE_SUB_CHANNEL_ID: ${FORCE_SUB_CHANNEL_ID}
      LOG_CHANNEL_ID: ${LOG_CHANNEL_ID}
      MONGODB_URI: mongodb://mongo:27017
      MONGODB_DATABASE: video_cover_bot
    depends_on:
      - mongo
    restart: unless-stopped

  mongo:
    image: mongo:latest
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

volumes:
  mongo_data:
```

**Run:**
```bash
docker-compose up -d
docker-compose logs -f
```

---

## 🚀 Production Deployment

### Heroku

```bash
# Login
heroku login

# Create app
heroku create your-bot-name

# Set environment variables
heroku config:set BOT_TOKEN=your_token
heroku config:set OWNER_ID=your_id
heroku config:set MONGODB_URI=your_mongodb_uri

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### VPS (Ubuntu/Debian)

```bash
# SSH to VPS
ssh user@your_vps_ip

# Clone repo
git clone https://github.com/yourusername/video-cover-bot.git
cd video-cover-bot

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/video-bot.service
```

Paste this:
```ini
[Unit]
Description=Video Cover Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/video-cover-bot
Environment="PATH=/home/your_username/video-cover-bot/venv/bin"
ExecStart=/home/your_username/video-cover-bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable & start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable video-bot
sudo systemctl start video-bot
sudo systemctl status video-bot

# View logs
sudo journalctl -u video-bot -f
```

---

## 📁 Project Structure

```
video-cover-bot/
├── bot.py                  # Main bot application (1400+ lines)
├── database.py             # MongoDB & logging functions
├── config.py               # Configuration loader
├── updater.py              # GitHub auto-update
├── requirements.txt        # Python dependencies
├── config.env              # Configuration (KEEP SECRET)
├── ,env.example            # Example configuration
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── runtime.txt             # Python version
├── Procfile                # Heroku deployment
├── .gitignore              # Git ignore rules
├── ui/                     # Banner images
└── README.md               # This file
```

---

## 📊 Database Schema

### MongoDB Collections

**users**
```json
{
  "_id": ObjectId,
  "user_id": 123456789,
  "username": "username",
  "thumbnail": "file_id",
  "dump_channel": 987654321,
  "created_at": "2024-01-01T10:00:00Z"
}
```

**banned_users**
```json
{
  "_id": ObjectId,
  "user_id": 123456789,
  "reason": "spam",
  "banned_at": "2024-01-01T10:00:00Z"
}
```

**logs** (optional)
```json
{
  "_id": ObjectId,
  "user_id": 123456789,
  "action": "video_sent",
  "details": {...},
  "timestamp": "2024-01-01T10:00:00Z"
}
```

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| ❌ Bot not responding | Check BOT_TOKEN, ensure bot running: `python bot.py` |
| ❌ MongoDB error | Verify MONGODB_URI, ensure MongoDB running |
| ❌ Force-sub fails | Check FORCE_SUB_CHANNEL_ID, bot must be admin in channel |
| ❌ Videos don't get cover | User must set cover first via "📸 Set Cover" |
| ❌ Logs not sending | Verify LOG_CHANNEL_ID, ensure bot admin in channel |

**Check Logs:**
```bash
# Local
python bot.py  # Errors show in console

# Systemd (VPS)
sudo journalctl -u video-bot -f

# Docker
docker logs -f video-bot

# Heroku
heroku logs --tail
```

---

## 📝 Contributing

Contributions welcome! To contribute:

```bash
# Fork repository
# Create feature branch
git checkout -b feature/your-feature

# Commit changes
git commit -m "Add your feature"

# Push to branch
git push origin feature/your-feature

# Create Pull Request
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🤝 Support

- **GitHub Issues**: [Report bugs](https://github.com/yourusername/video-cover-bot/issues)
- **Telegram**: Contact bot owner
- **Email**: your-email@example.com

---

## 🌟 Show Your Support

If this bot helped you, please:
- ⭐ Star this repository
- 🔄 Share with friends
- 📢 Tell others about it

---

<div align="center">

**Made with ❤️ for the Telegram Community**

[⬆ back to top](#-video-cover-bot)

</div>
