# config.py
import os
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')

class Config:
    """
    Configuration class for the bot.
    Reads all the necessary environment variables.
    Raises an error if any critical variable is missing.
    """
    
    # ==================== TELEGRAM BOT CONFIGURATION ====================
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Create singleton instance
config = Config()

# Export commonly used values
BOT_TOKEN = config.BOT_TOKEN
