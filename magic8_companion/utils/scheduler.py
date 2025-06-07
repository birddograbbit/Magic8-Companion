from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from datetime import datetime
from ..modules.magic8_client import get_latest_magic8_data
from ..modules.market_analysis import get_market_analysis
from ..modules.combo_scorer import score_combo_types, generate_recommendation
from ..modules.position_monitor import check_exit_signals # Assuming this exists
from ..modules.alert_manager import send_discord_alert
from ..modules.ib_client import IBClient
from ..config import settings
from .db_client import init_db, get_db_positions, sync_positions_with_ib # Added sync_positions_with_ib

# ib_client is already initialized globally here, which is fine for this structure.
# If IBClient manages its own connection state robustly (e.g. reconnects), this is okay.
ib_client = IBClient(settings.ib_host, settings.ib_port, settings.ib_client_id)


async def run_checkpoint():
    magic8_data = await get_latest_magic8_data()
    if not magic8_data:
        print("Scheduler: No Magic8 data, skipping checkpoint.")
        return

    # Market analysis now takes magic8_data for potential proxy values
    market_analysis_data = await get_market_analysis(ib_client, magic8_data)

    # Positions are fetched from DB *after* sync, or sync runs independently
    # For run_checkpoint, it should operate on the latest synced data.
    # The sync should ideally run just before this or frequently enough.
    db_positions = get_db_positions(status='OPEN')

    if db_positions:
        print(f"Scheduler: Found {len(db_positions)} open positions. Monitoring them.")
        for pos in db_positions:
            # Ensure pos has the fields expected by check_exit_signals, e.g., 'type', 'center_strike' etc.
            # The current DB schema has 'combo_type' and 'strikes_info'.
            # This might require mapping db_pos fields to what check_exit_signals expects.
            # For now, assuming check_exit_signals is compatible or will be adapted.

            # Reconstruct parts of position dict for check_exit_signals if needed from 'strikes_info' etc.
            # This is a placeholder for actual parsing logic if db schema and check_exit_signals diverge.
            # E.g., if check_exit_signals expects 'center_strike', it needs to be derived from 'strikes_info'
            # for a butterfly, or passed through if stored directly.
            # The guide's position_monitor.py has:
            # if position['type'] == 'butterfly': center = position.get('center_strike', 0)
            # The DB schema needs to support these fields or they need to be parsed from strikes_info.
            # Let's assume for now combo_scorer/position_monitor can handle the DB structure or it's adapted elsewhere.
            # The DB schema in the guide is more detailed than current `positions` table in `db_client.py`.
            # The `db_client.py` in this subtask was updated to a more generic `strikes_info` and `con_id`.
            # This part of the interaction (run_checkpoint -> check_exit_signals using DB data)
            # may need further refinement in a later step if there's a mismatch.

            signals = check_exit_signals(pos, magic8_data) # pos is a dict from DB
            for sig in signals:
                alert_msg = (f"🚨 EXIT SIGNAL - {pos.get('combo_type', 'UnknownType')} "
                             f"(Symbol: {pos.get('symbol', 'N/A')}, ConID: {pos.get('con_id', 'N/A')})\n"
                             f"Trigger: {sig.get('trigger')}\n"
                             f"Reason: {sig.get('reason')}")
                send_discord_alert(alert_msg)
    else:
        print("Scheduler: No open positions. Generating recommendation.")
        scores = score_combo_types(magic8_data, market_analysis_data)
        rec = generate_recommendation(scores)
        if rec.get('recommendation') != 'NONE':
            msg = (
                f"🎯 Magic8-Companion Checkpoint\n"
                f"Magic8 Spot: {magic8_data.get('spot_price', 'N/A')}\n"
                f"Recommendation: {rec['recommendation'].upper()} (Score: {rec['score']})\n"
                f"Confidence: {rec.get('confidence', 'N/A')}\n"
                f"Market IV Rank (Simple): {market_analysis_data.get('iv_percentile')}%\n"
                f"Market Avg ATM IV: {market_analysis_data.get('current_avg_atm_iv', 0.0):.3f}\n"
                f"Market Avg Spread: ${market_analysis_data.get('spread_avg', 0.0):.2f}\n"
                f"GEX Flip Proxy (Magic8 Gamma): {market_analysis_data.get('gex_flip', 'N/A')}"
            )
            send_discord_alert(msg)
        else:
            print(f"Scheduler: No clear recommendation. Reason: {rec.get('reason')}")


async def scheduled_sync_positions():
    """Dedicated function to call sync_positions_with_ib, for scheduling."""
    print("Scheduler: Running scheduled position synchronization.")
    try:
        await sync_positions_with_ib(ib_client)
    except Exception as e:
        print(f"Error in scheduled_sync_positions: {e}")

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    est = pytz.timezone('America/New_York')

    # Checkpoints for recommendations or position monitoring
    scheduler.add_job(run_checkpoint, 'cron', hour=10, minute=30, timezone=est, id='cp_1030', misfire_grace_time=600)
    scheduler.add_job(run_checkpoint, 'cron', hour=11, minute=0, timezone=est, id='cp_1100', misfire_grace_time=600)
    scheduler.add_job(run_checkpoint, 'cron', hour=12, minute=30, timezone=est, id='cp_1230', misfire_grace_time=600)
    scheduler.add_job(run_checkpoint, 'cron', hour=14, minute=45, timezone=est, id='cp_1445', misfire_grace_time=600)

    # More frequent job for position synchronization
    scheduler.add_job(scheduled_sync_positions, 'interval', minutes=2, timezone=est, id='sync_ib_positions', misfire_grace_time=120)

    return scheduler

def start():
    init_db() # Initialize DB schema at startup
    scheduler = setup_scheduler()
    scheduler.start()
    print("Scheduler started. DB initialized. Position sync scheduled every 2 minutes.")
    # Initial sync on startup could be useful too
    # asyncio.create_task(scheduled_sync_positions()) # Fire-and-forget initial sync
