"""
MongoDB Database Module for Video Cover Bot
Handles all database operations for user thumbnails
"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient

# Setup logging
logger = logging.getLogger(__name__)

# MongoDB Connection Setup
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "video_cover_bot")

try:
    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[MONGODB_DATABASE]
    users_collection = db["users"]
    # Test connection
    mongo_client.server_info()
    logger.info("✅ MongoDB connected successfully")
    DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ MongoDB not available: {e}")
    logger.warning("⚠️ Bot will work with limited functionality (thumbnails won't persist)")
    DB_AVAILABLE = False
    users_collection = None


def save_thumbnail(user_id: int, photo_id: str) -> bool:
    """Save or update user's thumbnail to MongoDB"""
    if not DB_AVAILABLE:
        logger.debug(f"Database not available, skipping thumbnail save for user {user_id}")
        return False
    
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "photo_id": photo_id,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        logger.info(f"✅ Thumbnail saved for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving thumbnail: {e}")
        return False


def get_thumbnail(user_id: int) -> str | None:
    """Retrieve user's thumbnail from MongoDB"""
    if not DB_AVAILABLE:
        logger.debug(f"Database not available, cannot get thumbnail for user {user_id}")
        return None
    
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "photo_id" in user_record:
            logger.info(f"✅ Retrieved thumbnail for user {user_id}")
            return user_record["photo_id"]
        logger.info(f"⚠️ No thumbnail found for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Error retrieving thumbnail: {e}")
        return None


def delete_thumbnail(user_id: int) -> bool:
    """Delete user's thumbnail from MongoDB"""
    if not DB_AVAILABLE:
        logger.debug(f"Database not available, skipping thumbnail delete for user {user_id}")
        return False
    
    try:
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"photo_id": ""}}
        )
        if result.modified_count > 0:
            logger.info(f"✅ Thumbnail deleted for user {user_id}")
            return True
        logger.info(f"⚠️ No thumbnail to delete for user {user_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Error deleting thumbnail: {e}")
        return False


def has_thumbnail(user_id: int) -> bool:
    """Check if user has a saved thumbnail"""
    if not DB_AVAILABLE:
        return False
    
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        has_thumb = user_record is not None and "photo_id" in user_record
        logger.debug(f"Thumbnail check for user {user_id}: {has_thumb}")
        return has_thumb
    except Exception as e:
        logger.error(f"❌ Error checking thumbnail: {e}")
        return False


def save_dump_channel(user_id: int, channel_id: str) -> bool:
    """Save user's dump channel ID to MongoDB"""
    if not DB_AVAILABLE:
        logger.debug(f"Database not available, skipping dump channel save for user {user_id}")
        return False
    
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "dump_channel_id": channel_id,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        logger.info(f"✅ Dump channel saved for user {user_id}: {channel_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving dump channel: {e}")
        return False


def get_dump_channel(user_id: int) -> str | None:
    """Retrieve user's dump channel ID from MongoDB"""
    if not DB_AVAILABLE:
        logger.debug(f"Database not available, cannot get dump channel for user {user_id}")
        return None
    
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "dump_channel_id" in user_record:
            logger.info(f"✅ Retrieved dump channel for user {user_id}")
            return user_record["dump_channel_id"]
        logger.info(f"⚠️ No dump channel found for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Error retrieving dump channel: {e}")
        return None


def delete_dump_channel(user_id: int) -> bool:
    """Delete user's dump channel ID from MongoDB"""
    if not DB_AVAILABLE:
        logger.debug(f"Database not available, skipping dump channel delete for user {user_id}")
        return False
    
    try:
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"dump_channel_id": ""}}
        )
        if result.modified_count > 0:
            logger.info(f"✅ Dump channel deleted for user {user_id}")
            return True
        logger.info(f"⚠️ No dump channel to delete for user {user_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Error deleting dump channel: {e}")
        return False
