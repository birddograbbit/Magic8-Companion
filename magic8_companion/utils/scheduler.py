from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from datetime import datetime
from typing import Optional
import logging

from ..modules.magic8_client import get_latest_magic8_data
from ..modules.market_analysis import get_market_analysis
from ..modules.combo_scorer import score_combo_types, generate_recommendation
from ..modules.position_monitor import check_exit_signals, format_exit_alert
from ..modules.alert_manager import send_discord_alert
from ..modules.ib_client import IBClient
from ..config import settings
from .db_client import init_db, get_db_positions, sync_positions_with_ib

# Module logger
logger = logging.getLogger(__name__)

# Global reference to IB client (set by setup_scheduler)
_ib_client: Optional[IBClient] = None


async def run_checkpoint():
    """Execute scheduled checkpoint logic."""
    logger.info("Running scheduled checkpoint...")
    
    if not _ib_client:
        logger.error("IB client not initialized for checkpoint")
        return
        
    magic8_data = await get_latest_magic8_data()
    if not magic8_data:
        logger.warning("No Magic8 data available, skipping checkpoint")
        return

    try:
        # Market analysis with error handling
        market_analysis_data = await get_market_analysis(_ib_client, magic8_data)
    except Exception as e:
        logger.error(f"Market analysis failed: {e}")
        # Use default values if market analysis fails
        market_analysis_data = {
            'iv_percentile': 50,
            'gex_flip': magic8_data.get('levels', {}).get('gamma', 0),
            'spread_avg': 2.0,
            'current_avg_atm_iv': 0.15
        }

    # Get current positions from DB
    db_positions = get_db_positions(status='OPEN')

    if db_positions:
        logger.info(f"Found {len(db_positions)} open positions. Checking exit signals...")
        
        for pos in db_positions:
            try:
                # Check exit signals for each position
                signals = check_exit_signals(pos, magic8_data)
                
                if signals:
                    logger.warning(f"Exit signals detected for position {pos.get('con_id')}: {signals}")
                    
                    # Format and send alert
                    alert_msg = format_exit_alert(pos, signals)
                    send_discord_alert(alert_msg)
                    
            except Exception as e:
                logger.error(f"Error checking exit signals for position {pos.get('con_id')}: {e}")
                
    else:
        logger.info("No open positions. Generating combo type recommendation...")
        
        try:
            # Score combo types
            scores = score_combo_types(magic8_data, market_analysis_data)
            rec = generate_recommendation(scores)
            
            if rec.get('recommendation') != 'NONE':
                # Format recommendation message
                msg = format_checkpoint_alert(magic8_data, market_analysis_data, rec, scores)
                send_discord_alert(msg)
                logger.info(f"Sent recommendation: {rec['recommendation']} (score: {rec['score']})")
            else:
                logger.info(f"No clear recommendation. Reason: {rec.get('reason')}")
                
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")


def format_checkpoint_alert(magic8_data, market_analysis, rec, scores):
    """Format checkpoint recommendation into Discord alert."""
    current_time = datetime.now(pytz.timezone('America/New_York')).strftime('%I:%M %p ET')
    
    lines = [
        f"🎯 **Magic8-Companion Checkpoint** - {current_time}",
        f"SPX: ${magic8_data.get('spot_price', 'N/A'):,.2f}",
        "",
        f"**Recommendation: {rec['recommendation'].upper()}**",
        f"Score: {rec['score']} | Confidence: {rec.get('confidence', 'N/A')}",
        "",
        "**Market Conditions:**",
        f"• Magic8 Trend: {magic8_data.get('trend', 'N/A')} (Strength: {magic8_data.get('strength', 0):.2f})",
        f"• Predicted Range: {magic8_data.get('range', 0):.1f} points",
        f"• IV Environment: {market_analysis.get('iv_percentile', 0)}% (ATM IV: {market_analysis.get('current_avg_atm_iv', 0):.3f})",
        f"• Gamma Level: {market_analysis.get('gex_flip', 'N/A')}",
        "",
        "**All Scores:**",
        f"• Butterfly: {scores.get('butterfly', 0)}",
        f"• Iron Condor: {scores.get('iron_condor', 0)}",
        f"• Vertical: {scores.get('vertical', 0)}"
    ]
    
    return "\n".join(lines)


async def scheduled_sync_positions():
    """Dedicated function to sync positions with IB."""
    if not _ib_client:
        logger.error("IB client not initialized for position sync")
        return
        
    logger.info("Running scheduled position synchronization...")
    
    try:
        await sync_positions_with_ib(_ib_client)
        logger.info("Position synchronization completed")
    except ConnectionError as e:
        logger.error(f"IB connection error during position sync: {e}")
    except Exception as e:
        logger.error(f"Error in scheduled position sync: {e}", exc_info=True)


def setup_scheduler(ib_client: Optional[IBClient] = None) -> AsyncIOScheduler:
    """
    Setup and configure the scheduler with all checkpoints.
    
    Args:
        ib_client: IB client instance to use for market data and positions
        
    Returns:
        Configured AsyncIOScheduler instance
    """
    global _ib_client
    _ib_client = ib_client
    
    scheduler = AsyncIOScheduler()
    est = pytz.timezone('America/New_York')

    # Schedule checkpoints for recommendations or position monitoring
    checkpoint_times = [
        (10, 30, 'cp_1030'),
        (11, 0, 'cp_1100'),
        (12, 30, 'cp_1230'),
        (14, 45, 'cp_1445')
    ]
    
    for hour, minute, job_id in checkpoint_times:
        scheduler.add_job(
            run_checkpoint,
            'cron',
            hour=hour,
            minute=minute,
            timezone=est,
            id=job_id,
            misfire_grace_time=600,
            max_instances=1
        )
        logger.info(f"Scheduled checkpoint at {hour:02d}:{minute:02d} ET")

    # Schedule position synchronization every 2 minutes
    scheduler.add_job(
        scheduled_sync_positions,
        'interval',
        minutes=2,
        timezone=est,
        id='sync_ib_positions',
        misfire_grace_time=120,
        max_instances=1
    )
    logger.info("Scheduled position sync every 2 minutes")

    return scheduler


# Legacy start function for backward compatibility
def start():
    """Legacy start function - use setup_scheduler instead."""
    logger.warning("Using legacy start() function. Please use setup_scheduler() instead.")
    init_db()
    
    # Create IB client with settings
    from ..modules.ib_client import IBClient
    ib_client = IBClient(settings.ib_host, settings.ib_port, settings.ib_client_id)
    
    scheduler = setup_scheduler(ib_client)
    scheduler.start()
    
    return scheduler
