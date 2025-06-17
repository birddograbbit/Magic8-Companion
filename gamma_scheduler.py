#!/usr/bin/env python3
"""
Gamma Analysis Scheduler for Magic8-Companion
Runs integrated gamma analysis on schedule
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime
import pytz
from pathlib import Path

from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis
from magic8_companion.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GammaScheduler:
    """Schedules and runs gamma analysis"""
    
    def __init__(self):
        self.config = get_config()
        self.symbols = self.config.get('M8C_GAMMA_SYMBOLS', ['SPX']).split(',')
        logger.info(f"Gamma scheduler initialized for symbols: {self.symbols}")
    
    def run_analysis(self):
        """Run gamma analysis for all configured symbols"""
        try:
            logger.info("Running scheduled gamma analysis")
            
            for symbol in self.symbols:
                logger.info(f"Analyzing {symbol}")
                results = run_gamma_analysis(symbol)
                
                if results:
                    logger.info(f"{symbol} analysis completed successfully")
                    
                    # Log key metrics
                    logger.info(f"  Net GEX: ${results['gamma_metrics']['net_gex']:,.0f}")
                    logger.info(f"  Gamma Regime: {results['signals']['gamma_regime']}")
                    logger.info(f"  Market Bias: {results['signals']['bias']}")
                else:
                    logger.error(f"{symbol} analysis failed")
                    
        except Exception as e:
            logger.error(f"Error in scheduled analysis: {e}")
    
    def run_continuous(self, interval_minutes=5):
        """Run analysis continuously with specified interval"""
        logger.info(f"Running gamma analysis every {interval_minutes} minutes")
        
        while True:
            try:
                self.run_analysis()
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("Stopping continuous analysis")
                break
            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def run_scheduled(self, times=None):
        """Run analysis on schedule"""
        # Define Eastern timezone and local timezone
        et = pytz.timezone('America/New_York')
        local_tz = datetime.now().astimezone().tzinfo

        # Default schedule times in Eastern Time (matching Magic8-Companion)
        if times is None:
            schedule_times_et = ['10:30', '11:00', '12:30', '14:45']
        else:
            schedule_times_et = times

        logger.info(
            f"Scheduling gamma analysis at: {', '.join(schedule_times_et)} ET"
        )

        # Convert ET times to local timezone strings for schedule module
        local_schedule_times = []
        today = datetime.now(et)
        for time_str in schedule_times_et:
            hour, minute = map(int, time_str.split(':'))
            et_dt = et.localize(
                datetime(today.year, today.month, today.day, hour, minute)
            )
            local_dt = et_dt.astimezone(local_tz)
            local_schedule_times.append(local_dt.strftime('%H:%M'))

        for local_time in local_schedule_times:
            schedule.every().day.at(local_time).do(self.run_analysis)
        
        # Run once on startup if within market hours
        now_et = datetime.now(et)
        if 9 <= now_et.hour <= 16:
            logger.info("Running initial analysis")
            self.run_analysis()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                logger.info("Stopping scheduled analysis")
                break
            except Exception as e:
                logger.error(f"Error in scheduled mode: {e}")
                time.sleep(60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gamma Analysis Scheduler')
    parser.add_argument('--mode', choices=['scheduled', 'continuous', 'once'], 
                       default='once', help='Run mode')
    parser.add_argument('--interval', type=int, default=5,
                       help='Interval in minutes for continuous mode')
    parser.add_argument('--times', type=str,
                       help='Comma-separated times for scheduled mode (e.g., "10:30,14:45")')
    
    args = parser.parse_args()
    
    scheduler = GammaScheduler()
    
    logger.info(f"Starting Gamma Analysis Scheduler in {args.mode} mode")
    
    if args.mode == 'once':
        scheduler.run_analysis()
    elif args.mode == 'continuous':
        scheduler.run_continuous(args.interval)
    elif args.mode == 'scheduled':
        times = args.times.split(',') if args.times else None
        scheduler.run_scheduled(times)


if __name__ == "__main__":
    main()
