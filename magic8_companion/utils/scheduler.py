"""
Simple scheduler for Magic8-Companion checkpoints.
"""
import asyncio
import logging
from datetime import datetime, time
from typing import Callable, List
import pytz

logger = logging.getLogger(__name__)


class SimpleScheduler:
    """Simple time-based scheduler for checkpoint execution."""
    
    def __init__(self, timezone_str: str = "America/New_York"):
        self.timezone = pytz.timezone(timezone_str)
        self.checkpoints = []
        self.running = False
        self.task = None
        
    def add_checkpoint(self, time_str: str, callback: Callable):
        """Add a scheduled checkpoint."""
        try:
            # Parse time string (format: "HH:MM")
            hour, minute = map(int, time_str.split(":"))
            checkpoint_time = time(hour, minute)
            
            self.checkpoints.append({
                "time": checkpoint_time,
                "time_str": time_str,
                "callback": callback,
                "last_executed": None
            })
            
            logger.info(f"Added checkpoint: {time_str} ET")
            
        except ValueError as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        self.running = True
        self.task = asyncio.create_task(self._schedule_loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def _schedule_loop(self):
        """Main scheduling loop."""
        while self.running:
            try:
                current_time = datetime.now(self.timezone)
                
                # Check each checkpoint
                for checkpoint in self.checkpoints:
                    if self._should_execute_checkpoint(checkpoint, current_time):
                        await self._execute_checkpoint(checkpoint, current_time)
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def _should_execute_checkpoint(self, checkpoint: dict, current_time: datetime) -> bool:
        """Check if checkpoint should be executed."""
        checkpoint_time = checkpoint["time"]
        last_executed = checkpoint["last_executed"]
        
        # Create checkpoint datetime for today
        checkpoint_dt = current_time.replace(
            hour=checkpoint_time.hour,
            minute=checkpoint_time.minute,
            second=0,
            microsecond=0
        )
        
        # Check if we're within execution window (current time >= checkpoint time)
        if current_time < checkpoint_dt:
            return False
        
        # Check if we haven't executed this checkpoint today
        if last_executed is None:
            return True
        
        # Check if last execution was on a different day
        if last_executed.date() != current_time.date():
            return True
        
        # Check if last execution was before today's checkpoint time
        if last_executed < checkpoint_dt:
            return True
        
        return False
    
    async def _execute_checkpoint(self, checkpoint: dict, current_time: datetime):
        """Execute a checkpoint."""
        time_str = checkpoint["time_str"]
        callback = checkpoint["callback"]
        
        try:
            logger.info(f"Executing checkpoint: {time_str}")
            
            # Execute callback
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
            
            # Update last executed time
            checkpoint["last_executed"] = current_time
            
            logger.info(f"Checkpoint {time_str} completed successfully")
            
        except Exception as e:
            logger.error(f"Error executing checkpoint {time_str}: {e}")
