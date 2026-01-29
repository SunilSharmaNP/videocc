# Telegram Thumbnail Bot

एक Telegram bot जो videos में custom thumbnails add करता है। Heroku और VPS दोनों पर deploy किया जा सकता है।

## Features

✅ Photo को thumbnail के रूप में save करो
✅ Video के साथ thumbnail add करो
✅ Thumbnail को remove करो
✅ Heroku और VPS support
✅ Production-ready code

## Requirements

- Python 3.9+
- python-telegram-bot
- python-dotenv

## Installation

### Local Development

```bash
# Clone या extract करो
cd fcc

# Virtual environment create करो
python -m venv venv

# Activate करो (Windows)
venv\Scripts\activate

# Dependencies install करो
pip install -r requirements.txt

# .env file create करो
echo TELEGRAM_BOT_TOKEN=your_token_here > .env

# Bot चलाओ
python main.py
```

## Deployment

### Heroku पर Deploy करना

```bash
# Heroku CLI install करो
# https://devcenter.heroku.com/articles/heroku-cli

# Login करो
heroku login

# New app create करो
heroku create your-bot-name

# Token set करो
heroku config:set TELEGRAM_BOT_TOKEN=your_token_here

# Deploy करो
git push heroku main
```

### VPS पर Deploy करना

```bash
# VPS में SSH करो
ssh user@your_vps_ip

# Folder create करो
mkdir telegram-bot
cd telegram-bot

# Files copy करो (Git से)
git clone https://github.com/your_username/your_repo.git
cd your_repo

# Virtual environment setup करो
python3 -m venv venv
source venv/bin/activate

# Dependencies install करो
pip install -r requirements.txt

# .env file create करो
nano .env
# Add: TELEGRAM_BOT_TOKEN=your_token_here

# Bot को systemd service के रूप में run करो
sudo nano /etc/systemd/system/telegram-bot.service
```

**/etc/systemd/system/telegram-bot.service** content:

```ini
[Unit]
Description=Telegram Thumbnail Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/telegram-bot
ExecStart=/home/your_username/telegram-bot/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Service enable करो:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## Docker (Container)

Bot को Docker container में चलाने के लिए नीचे दिए steps follow करें:

### Build the image

```bash
docker build -t telegram-thumbnail-bot .
```

### Run the container (use local `.env`)

```bash
docker run --env-file .env --restart unless-stopped --name thumb-bot telegram-thumbnail-bot
```

यदि आप `.env` नहीं रखना चाहते, तो token को सीधे provide कर सकते हैं:

```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token_here --restart unless-stopped --name thumb-bot telegram-thumbnail-bot
```

### docker-compose (recommended for VPS)

Create a `docker-compose.yml` with the following content:

```yaml
version: '3.8'
services:
	thumb-bot:
		image: telegram-thumbnail-bot
		build: .
		restart: unless-stopped
		env_file:
			- .env
		container_name: thumb-bot
```

Then build and start:

```bash
docker-compose up -d --build
```

Docker उपयोग करने से deployment आसान हो जाता है — Heroku, VPS या किसी भी container host पर चलाया जा सकता है।

## Configuration

### Environment Variables

`.env` file में निम्न variables set करो:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

Bot token कैसे प्राप्त करें:
1. Telegram में @BotFather को search करो
2. `/newbot` command भेजो
3. Bot का नाम दो
4. Token प्राप्त करो

## Commands

- `/start` - Bot को start करो
- `/help` - Help दिखाओ
- `/remove` - Saved thumbnail को delete करो

## Usage

1. Bot को private message करो
2. एक photo भेजो (thumbnail)
3. एक video भेजो
4. Bot automatically thumbnail add करके video भेजेगा

## Bot Structure

```
telegram-bot/
├── main.py                 # Main bot file
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment file
├── .gitignore             # Git ignore file
├── Procfile               # Heroku configuration
├── runtime.txt            # Python version for Heroku
└── README.md              # This file
```

## Troubleshooting

### "TELEGRAM_BOT_TOKEN not found"
- Check कि `.env` file में token सही है
- VPS पर: `source venv/bin/activate` करो फिर manually test करो

### Bot offline है
- Heroku: `heroku logs --tail`
- VPS: `sudo systemctl status telegram-bot`

### Logs देखना

**Heroku:**
```bash
heroku logs --tail
```

**VPS:**
```bash
sudo journalctl -u telegram-bot -f
```

## Development

Improvements और bug fixes के लिए:

1. Branch create करो
2. Changes करो
3. Pull request भेजो

## License

MIT License

## Support

Issues के लिए GitHub पर issue create करो या admins से contact करो।
