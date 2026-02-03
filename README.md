<div align="center">

<img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python" alt="Python">
<img src="https://img.shields.io/badge/Telegram-Bot-0088cc?style=flat-square&logo=telegram" alt="Telegram">
<img src="https://img.shields.io/badge/MongoDB-Latest-13aa52?style=flat-square&logo=mongodb" alt="MongoDB">
<img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker" alt="Docker">
<img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">

# 🎬 Instant Video Cover Bot

### ✨ Professional Telegram Bot for Adding Custom Covers to Videos ✨

<br>

[🚀 Quick Start](#quick-start) • [✨ Features](#features) • [⚙️ Setup](#setup) • [🌐 Deploy](#deployment) • [📖 Guide](VPS_DEPLOYMENT.md)

</div>

---

---

## 📋 About

<table align="center">
  <tr>
    <td><b>Instant Video Cover Bot</b> helps you apply custom thumbnail covers to videos instantly.</td>
  </tr>
  <tr>
    <td>Perfect for content creators who want professional-looking videos with custom covers.</td>
  </tr>
</table>

### 🎯 Key Features

| Feature | Benefit |
|---------|---------|
| 📸 **Upload Photo** | Save custom covers for your videos |
| 🎥 **Instant Apply** | Add covers to any video in seconds |
| 🔒 **Secure Access** | Force subscribe verification |
| 👥 **Admin Tools** | Full user management & controls |
| 📊 **Analytics** | Track users & system metrics |
| 💾 **Persistent** | MongoDB database integration |
| 🐳 **Containerized** | Docker deployment ready |

---

## ✨ Features

<details open>
<summary><b>📸 Core Features</b></summary>

| Feature | Description |
|---------|-------------|
| 📸 **Set Cover** | Upload photo as video thumbnail |
| 🎬 **Apply Cover** | Add cover to videos instantly |
| ✏️ **Change Cover** | Update cover anytime |
| 🗑️ **Remove Cover** | Delete saved cover |

</details>

<details open>
<summary><b>🔐 Security & Control</b></summary>

| Feature | Description |
|---------|-------------|
| 🔒 **Force Subscribe** | Require channel membership |
| ✅ **Verification** | Auto-verify users |
| 🚫 **Ban System** | Manage banned users |
| 👨‍💼 **Admin Panel** | Full control dashboard |

</details>

<details open>
<summary><b>📊 Admin Features</b></summary>

| Feature | Description |
|---------|-------------|
| 👥 **Users Stats** | Total, active, banned count |
| 📈 **Ban Rate** | Monitor ban statistics |
| 💻 **System Monitor** | CPU & RAM usage |
| 📢 **Broadcast** | Send messages to all users |
| ⏱️ **Uptime** | Bot status & performance |

</details>

---

## 🚀 Quick Start

### 📋 Prerequisites

| Requirement | Details |
|------------|---------|
| 🐍 **Python** | 3.8 or higher |
| 🤖 **Bot Token** | From [@BotFather](https://t.me/BotFather) |
| 🗄️ **MongoDB** | Local or [Atlas Cloud](https://mongodb.com/cloud/atlas) |
| 📚 **Git** | For cloning repository |

### ⚡ Quick Installation

```bash
# 1️⃣ Clone repository
git clone https://github.com/yourusername/video-cover-bot.git
cd video-cover-bot

# 2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3️⃣ Install dependencies
pip install -r requirements.txt

# 4️⃣ Setup configuration
cp ,env.example config.env
nano config.env  # Edit with your details

# 5️⃣ Run bot
python bot.py
```

✅ **Bot is running!**

---

## ⚙️ Setup

### 1️⃣ Get Bot Token

```
🤖 Open @BotFather in Telegram
📤 Send: /newbot
📝 Follow prompts to create bot
🔑 Copy your token
```

### 2️⃣ Configure Environment

```ini
# 🔓 Edit config.env

BOT_TOKEN=your_token_from_botfather
OWNER_ID=your_telegram_user_id
FORCE_SUB_CHANNEL_ID=-1002659719637
LOG_CHANNEL_ID=-1002659719637
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=video_cover_bot
```

### 3️⃣ Setup MongoDB

<div align="left">

**☁️ Cloud Option (Recommended):**
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free account
3. Create M0 free cluster
4. Copy connection string
5. Add to config.env

**💻 Local Option:**
```bash
# Ubuntu/Debian
sudo apt-get install mongodb

# macOS
brew install mongodb-community
```

</div>

### 4️⃣ Create Telegram Channels

```
📌 Create 2 private channels:
   1. Force Subscribe Channel
   2. Log Channel

🤖 Add your bot as ADMIN in both

📨 Forward any message from channel → check bot logs for ID
🔧 Update config.env with IDs
```

### 5️⃣ Run Bot

```bash
python bot.py
```

🎉 **Done! Your bot is live!**

---

## Commands

### User
- `/start` - Main menu
- `/help` - How to use
- `/settings` - Preferences
- `/remove` - Delete cover

### Admin
- `/admin` - Admin panel
- `/ban userid reason` - Ban user
- `/unban userid` - Unban user
- `/stats` - User statistics
- `/status` - System status
- `/broadcast message` - Send to all users

---

## Deployment

### Docker (Easiest)

```bash
docker build -t video-bot .

docker run -d \
  --name video-bot \
  -e BOT_TOKEN=your_token \
  -e OWNER_ID=your_id \
  -e MONGODB_URI=mongodb://mongo:27017 \
  -e FORCE_SUB_CHANNEL_ID=your_channel_id \
  -e LOG_CHANNEL_ID=your_log_channel_id \
  video-bot
```

### VPS Deployment

See [VPS_DEPLOYMENT.md](VPS_DEPLOYMENT.md) for step-by-step guide.

### Heroku

```bash
heroku login
heroku create your-bot-name
heroku config:set BOT_TOKEN=your_token OWNER_ID=your_id MONGODB_URI=your_uri
git push heroku main
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot not responding | Check BOT_TOKEN, restart bot |
| MongoDB error | Verify MONGODB_URI, ensure MongoDB running |
| Force-sub fails | Check channel ID, bot must be admin |
| Logs not sent | Verify LOG_CHANNEL_ID, bot admin required |

Check logs:
```bash
# Local
python bot.py

# Docker
docker logs -f video-bot

# VPS
sudo journalctl -u video-bot -f
```

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Support

Found an issue? [Create issue](../../issues) or contact bot owner.

<div align="center">Made with ❤️</div>
