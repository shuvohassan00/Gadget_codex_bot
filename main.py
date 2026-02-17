#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
import asyncio
import importlib.util
import sys
from pathlib import Path
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from utils import LOGGER
from bot import CodeUtilBot, start_bot

HANDLER_DIRS = [
    Path(__file__).parent / "core",
    Path(__file__).parent / "miscs",
    Path(__file__).parent / "modules",
]

shared_edit_sessions = {}

def load_handlers():
    loaded_count = 0
    for directory in HANDLER_DIRS:
        if not directory.is_dir():
            LOGGER.warning(f"{directory.name}/ directory not found, skipping...")
            continue
        
        LOGGER.info(f"Loading handlers from {directory.name}/")
        
        for path in directory.glob("*.py"):
            if path.name == "__init__.py":
                continue
            
            module_name = f"{directory.name}.{path.stem}"
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None:
                    LOGGER.warning(f"Could not load spec for {module_name}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                LOGGER.info(f"✅ Loaded handler module: {module_name}")
                loaded_count += 1
                
            except Exception as e:
                LOGGER.exception(f"❌ Failed to load {module_name}: {e}")
    
    LOGGER.info(f"Total handlers loaded: {loaded_count}")

async def run_api_server():
    try:
        import api.edit_file as api_module
        
        api_module.edit_sessions = shared_edit_sessions
        
        LOGGER.info("Starting FastAPI server on http://0.0.0.0:8000")
        LOGGER.info("API server is using shared edit_sessions")
        
        await api_module.run_server(host="0.0.0.0", port=8000)
    except ImportError as e:
        LOGGER.warning(f"FastAPI server module not found: {e}")
    except Exception as e:
        LOGGER.exception(f"Failed to start API server: {e}")

async def run_bot():
    LOGGER.info("Starting bot initialization...")
    await start_bot()
    
    LOGGER.info("Loading handler modules...")
    load_handlers()
    
    try:
        import modules.edit as edit_module
        edit_module.edit_sessions = shared_edit_sessions
        
        LOGGER.info("Bot is using shared edit_sessions")
    except ImportError:
        LOGGER.warning("Edit module not found")
    
    LOGGER.info("Bot Successfully Started 🎉")
    LOGGER.info("Bot is now running and listening for events...")
    
    await CodeUtilBot.run_until_disconnected()

async def main():
    LOGGER.info("=" * 60)
    LOGGER.info("Starting Code Util Bot with FastAPI Server")
    LOGGER.info("=" * 60)
    
    bot_task = asyncio.create_task(run_bot())
    api_task = asyncio.create_task(run_api_server())
    
    await asyncio.gather(bot_task, api_task, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("Bot and API server stopped by user (KeyboardInterrupt)")
    except Exception as e:
        LOGGER.exception("Fatal startup / runtime error")
        sys.exit(1)