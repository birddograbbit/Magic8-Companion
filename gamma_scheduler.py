"""
Gamma Scheduler for Magic8-Companion.
Schedules and runs gamma analysis at specified times or intervals.
"""
import logging
import schedule
import time
import argparse
import signal
import sys
from datetime import datetime
from typing import List, Dict, Optional

from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis, run_batch_gamma_analysis
from magic8_companion.unified_config import settings

logger = logging.getLogger(__name__)


class GammaScheduler:
    """Scheduler for running gamma analysis at specified times."""
    
    def __init__(self, mode: str = "scheduled", symbols: Optional[List[str]] = None):
        """
        Initialize gamma scheduler.
        
        Args:
            mode: 'scheduled' for specific times, 'interval' for regular intervals
            symbols: List of symbols to analyze. Uses settings if None.
        """
        self.mode = mode
        self.symbols = symbols or settings.gamma_symbols
        self.running = False
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping scheduler...")
        self.running = False
        sys.exit(0)
    
    def run_analysis(self):
        """Run gamma analysis for all configured symbols."""
        logger.info(f"Running scheduled gamma analysis at {datetime.now()}")
        
        results = run_batch_gamma_analysis(self.symbols)
        
        # Log summary
        for symbol, result in results.items():
            if result:
                net_gex = result.get('net_gex', 0)
                regime = result.get('regime', 'unknown')
                logger.info(f"{symbol}: Net GEX ${net_gex:,.0f}, Regime: {regime}")
            else:
                logger.warning(f"{symbol}: Analysis failed")
        
        return results
    
    def schedule_jobs(self):
        """Schedule gamma analysis jobs based on mode."""
        if self.mode == "scheduled":
            # Schedule at specific times
            for time_str in settings.gamma_scheduler_times:
                schedule.every().day.at(time_str).do(self.run_analysis)
                logger.info(f"Scheduled gamma analysis at {time_str}")
        
        elif self.mode == "interval":
            # Schedule at regular intervals
            interval_minutes = settings.gamma_scheduler_interval
            schedule.every(interval_minutes).minutes.do(self.run_analysis)
            logger.info(f"Scheduled gamma analysis every {interval_minutes} minutes")
        
        else:
            raise ValueError(f"Unknown scheduler mode: {self.mode}")
    
    def start(self):
        """Start the scheduler."""
        logger.info(f"Starting gamma scheduler in {self.mode} mode")
        logger.info(f"Analyzing symbols: {', '.join(self.symbols)}")
        
        # Schedule jobs
        self.schedule_jobs()
        
        # Run once immediately
        self.run_analysis()
        
        # Start scheduler loop
        self.running = True
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(10)  # Wait before retrying
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping gamma scheduler")
        self.running = False


def main():
    """Main entry point for gamma scheduler."""
    parser = argparse.ArgumentParser(description="Gamma Analysis Scheduler")
    parser.add_argument(
        "--mode",
        choices=["scheduled", "interval"],
        default=settings.gamma_scheduler_mode,
        help="Scheduler mode: scheduled (specific times) or interval (regular intervals)"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Symbols to analyze (default: from settings)"
    )
    parser.add_argument(
        "--times",
        nargs="+",
        help="Times to run analysis (for scheduled mode, format: HH:MM)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Interval in minutes (for interval mode)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run analysis once and exit"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/gamma_scheduler.log')
        ]
    )
    
    # Override settings if provided
    if args.times and args.mode == "scheduled":
        settings.gamma_scheduler_times = args.times
    
    if args.interval and args.mode == "interval":
        settings.gamma_scheduler_interval = args.interval
    
    # Run once if requested
    if args.run_once:
        logger.info("Running gamma analysis once")
        results = run_batch_gamma_analysis(args.symbols)
        for symbol, result in results.items():
            if result:
                print(f"{symbol}: Success")
            else:
                print(f"{symbol}: Failed")
        return
    
    # Create and start scheduler
    scheduler = GammaScheduler(
        mode=args.mode,
        symbols=args.symbols
    )
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
