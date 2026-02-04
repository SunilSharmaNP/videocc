import os
import subprocess
import logging
import sys

logger = logging.getLogger(__name__)

UPSTREAM_REPO = os.environ.get("UPSTREAM_REPO")
UPSTREAM_BRANCH = os.environ.get("UPSTREAM_BRANCH", "main")


def run_cmd(cmd: str):
    """Run command and return (return_code, output)"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stderr or result.stdout
    except subprocess.TimeoutExpired:
        return 1, "Command timeout"
    except Exception as e:
        return 1, str(e)


def update_from_upstream() -> bool:
    """Update bot from upstream repository"""
    if not UPSTREAM_REPO:
        logger.error("❌ UPSTREAM_REPO not configured in config.env")
        return False
    
    if not UPSTREAM_BRANCH:
        logger.error("❌ UPSTREAM_BRANCH not configured in config.env")
        return False

    logger.info(f"🔄 Starting upstream update from {UPSTREAM_REPO} (branch: {UPSTREAM_BRANCH})...")

    cmds = [
        # Skip git init - use git config directly to avoid hook permission issues
        ("git config user.name 'bot-updater' || git config --global user.name 'bot-updater'", "Set git user"),
        ("git config user.email 'bot@localhost' || git config --global user.email 'bot@localhost'", "Set git email"),
        (f"git remote remove origin 2>/dev/null || true", "Remove old remote"),
        (f"git remote add origin {UPSTREAM_REPO}", "Add upstream repository"),
        (f"git fetch origin {UPSTREAM_BRANCH}", "Fetch latest code from upstream"),
        (f"git reset --hard origin/{UPSTREAM_BRANCH}", "Apply upstream changes"),
    ]
    
    # Initialize git if not already initialized
    if not os.path.isdir(".git"):
        logger.info("  Running: Initialize git repository with no templates")
        return_code, output = run_cmd("git init --template='' 2>/dev/null || git init")
        
        if return_code != 0:
            logger.warning(f"  ⚠️ Git init had issues: {output}")
            # Continue anyway - might work with fetch/reset

    for cmd, desc in cmds:
        logger.info(f"  Running: {desc}")
        return_code, output = run_cmd(cmd)
        
        if return_code != 0:
            logger.error(f"  ❌ Failed: {desc}")
            logger.error(f"  Error output: {output}")
            return False
        else:
            logger.info(f"  ✅ Success: {desc}")

    logger.info("✅ Upstream update completed successfully!")
    return True


def restart_bot():
    logger.info("Restarting bot process...")
    os.execv(sys.executable, [sys.executable] + sys.argv)
