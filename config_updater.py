import os
import logging
import subprocess
from dotenv import dotenv_values, load_dotenv

logger = logging.getLogger(__name__)


def _load_config_env():
    """Load config.env values into environment without overwriting existing vars."""
    if os.path.exists("config.env"):
        for k, v in dotenv_values("config.env").items():
            if v is not None and k not in os.environ:
                os.environ[k] = v


def _read_db_config():
    """If DATABASE_URL is set, try to read UPSTREAM_REPO/UPSTREAM_BRANCH and ADMIN_IDS from DB.
    This function intentionally fails quietly and logs warnings only.
    """
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        return None
    try:
        from pymongo import MongoClient
        conn = MongoClient(DATABASE_URL)
        db = conn.get_database()
        bot_id = os.environ.get("TELEGRAM_BOT_TOKEN", "").split(":", 1)[0]
        if not bot_id:
            return None
        config_dict = db.settings.config.find_one({"_id": bot_id})
        if not config_dict:
            return None
        return {
            "UPSTREAM_REPO": config_dict.get("UPSTREAM_REPO"),
            "UPSTREAM_BRANCH": config_dict.get("UPSTREAM_BRANCH"),
            "ADMIN_IDS": config_dict.get("ADMIN_IDS"),
        }
    except Exception as e:
        logger.warning(f"Could not read config from DB: {e}")
        return None


def perform_update(repo: str, branch: str) -> bool:
    """Attempt to update current working tree from the provided repo/branch.
    Returns True on success.
    """
    if not repo:
        return False
    try:
        # remove .git to avoid conflicts
        if os.path.exists(".git"):
            try:
                import shutil

                shutil.rmtree(".git")
            except Exception:
                pass

        # Build shell command to init and hard reset to upstream
        cmd = (
            f"git init -q && git config --global user.email 'dev@local' "
            f"&& git config --global user.name 'bot' "
            f"&& git add . && git commit -sm update -q || true "
            f"&& git remote add origin {repo} || git remote set-url origin {repo} "
            f"&& git fetch origin -q && git reset --hard origin/{branch} -q"
        )
        res = subprocess.run(cmd, shell=True)
        success = res.returncode == 0
        if success:
            logger.info("perform_update: updated code from upstream successfully")
        else:
            logger.warning("perform_update: failed to update from upstream")
        return success
    except Exception as e:
        logger.error(f"perform_update exception: {e}")
        return False


def maybe_update_at_startup():
    """Public helper to be called by the bot startup. Will load config.env, then consult DB (if any),
    then perform an update if UPSTREAM_REPO is configured.
    """
    # load local config.env first
    _load_config_env()

    # prefer env vars already present
    upstream = os.environ.get("UPSTREAM_REPO") or None
    branch = os.environ.get("UPSTREAM_BRANCH") or os.environ.get("UPSTREAM_BRANCH", "master")

    # try DB override
    db_conf = _read_db_config()
    if db_conf:
        if db_conf.get("UPSTREAM_REPO"):
            upstream = db_conf.get("UPSTREAM_REPO")
        if db_conf.get("UPSTREAM_BRANCH"):
            branch = db_conf.get("UPSTREAM_BRANCH") or branch
        if db_conf.get("ADMIN_IDS") and not os.environ.get("ADMIN_IDS"):
            # write ADMIN_IDS into environment for the bot to pick up
            os.environ["ADMIN_IDS"] = db_conf.get("ADMIN_IDS")

    if upstream:
        logger.info(f"maybe_update_at_startup: UPSTREAM_REPO={upstream}, branch={branch}")
        return perform_update(upstream, branch)
    return False
