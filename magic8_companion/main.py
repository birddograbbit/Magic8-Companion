"""
Magic8-Companion Main Orchestrator

Manages application lifecycle, handles graceful shutdowns, and coordinates
all components with proper error handling and recovery.
"""
import asyncio
import signal
import sys
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from .utils.scheduler import setup_scheduler, scheduled_sync_positions
from .modules.ib_client import IBClient
from .modules.alert_manager import send_discord_alert
from .utils.db_client import init_db
from .config import settings


# Setup logging
def setup_logging():
    """Configure application logging."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'magic8_companion.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger('ib_async').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


class Magic8CompanionApp:
    """Main application class with lifecycle management."""
    
    def __init__(self):
        self.logger = setup_logging()
        self.scheduler = None
        self.ib_client: Optional[IBClient] = None
        self.shutdown_event = asyncio.Event()
        self.tasks = []
        
    async def initialize(self):
        """Initialize all components."""
        self.logger.info("Initializing Magic8-Companion...")
        
        try:
            # Initialize database
            init_db()
            self.logger.info("Database initialized")
            
            # Initialize IB client
            self.ib_client = IBClient(
                host=settings.ib_host,
                port=settings.ib_port,
                client_id=settings.ib_client_id
            )
            
            # Try to connect to IB
            try:
                await self.ib_client._ensure_connected()
                self.logger.info("Connected to Interactive Brokers")
            except ConnectionError as e:
                self.logger.error(f"Failed to connect to IB: {e}")
                self.logger.warning("Running in degraded mode without IB connection")
                # Don't fail completely - we can still process Magic8 data
            
            # Setup scheduler
            self.scheduler = setup_scheduler()
            self.scheduler.start()
            self.logger.info("Scheduler started with checkpoints at 10:30, 11:00, 12:30, 14:45 ET")
            
            # Send startup notification
            await self._send_startup_alert()
            
            # Initial position sync
            if self.ib_client and self.ib_client.ib.isConnected():
                self.logger.info("Running initial position sync...")
                await scheduled_sync_positions()
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", exc_info=True)
            raise
    
    async def _send_startup_alert(self):
        """Send Discord notification on startup."""
        try:
            startup_msg = (
                "🚀 **Magic8-Companion Started**\n"
                f"• IB Connection: {'✅ Connected' if self.ib_client and self.ib_client.ib.isConnected() else '❌ Disconnected'}\n"
                f"• Checkpoints: 10:30, 11:00, 12:30, 14:45 ET\n"
                f"• Position Sync: Every 2 minutes\n"
                f"• Max Position Loss: ${settings.max_position_loss:,}\n"
                f"• Max Daily Loss: ${settings.max_daily_loss:,}"
            )
            send_discord_alert(startup_msg)
        except Exception as e:
            self.logger.error(f"Failed to send startup alert: {e}")
    
    async def shutdown(self):
        """Graceful shutdown of all components."""
        self.logger.info("Shutting down Magic8-Companion...")
        
        try:
            # Send shutdown notification
            send_discord_alert("🛑 **Magic8-Companion Shutting Down**")
        except:
            pass  # Don't fail shutdown due to alert failure
        
        # Stop scheduler
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Scheduler stopped")
        
        # Disconnect from IB
        if self.ib_client:
            await self.ib_client.disconnect()
            self.logger.info("Disconnected from Interactive Brokers")
        
        # Cancel any running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Set shutdown event
        self.shutdown_event.set()
        
        self.logger.info("Shutdown complete")
    
    async def monitor_ib_connection(self):
        """Monitor IB connection and attempt reconnection if needed."""
        while not self.shutdown_event.is_set():
            try:
                if self.ib_client and not self.ib_client.ib.isConnected():
                    self.logger.warning("IB connection lost, attempting reconnection...")
                    try:
                        await self.ib_client._ensure_connected()
                        self.logger.info("Successfully reconnected to IB")
                        send_discord_alert("✅ **IB Connection Restored**")
                    except Exception as e:
                        self.logger.error(f"IB reconnection failed: {e}")
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def run(self):
        """Main application loop."""
        self.logger.info("Magic8-Companion running...")
        
        # Start connection monitor
        monitor_task = asyncio.create_task(self.monitor_ib_connection())
        self.tasks.append(monitor_task)
        
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()


@asynccontextmanager
async def app_lifespan():
    """Async context manager for app lifecycle."""
    app = Magic8CompanionApp()
    
    try:
        await app.initialize()
        yield app
    finally:
        await app.shutdown()


def handle_signals(app: Magic8CompanionApp):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        app.logger.info(f"Received signal {signum}")
        asyncio.create_task(app.shutdown())
    
    # Handle SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows-specific signal handling
    if sys.platform == 'win32':
        signal.signal(signal.SIGBREAK, signal_handler)


async def async_main():
    """Async main entry point."""
    async with app_lifespan() as app:
        # Setup signal handlers
        handle_signals(app)
        
        # Run the application
        await app.run()


def main():
    """Main entry point."""
    print("Starting Magic8-Companion...")
    print(f"Configuration loaded from: {settings.Config.env_file}")
    
    try:
        # Run the async main
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nShutdown requested via keyboard interrupt")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
