from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from datetime import datetime
from ..modules.magic8_client import get_latest_magic8_data
from ..modules.market_analysis import get_market_analysis
from ..modules.combo_scorer import score_combo_types, generate_recommendation
from ..modules.position_monitor import check_exit_signals
from ..modules.alert_manager import send_discord_alert
from ..modules.ib_client import IBClient
from ..config import settings
from .db_client import init_db, get_db_positions


ib_client = IBClient(settings.ib_host, settings.ib_port, settings.ib_client_id)


async def run_checkpoint():
    magic8_data = await get_latest_magic8_data()
    if not magic8_data:
        return

    market_analysis = await get_market_analysis(ib_client)
    positions = get_db_positions()

    if positions:
        for pos in positions:
            signals = check_exit_signals(pos, magic8_data)
            for sig in signals:
                send_discord_alert(f"🚨 EXIT SIGNAL - {pos['combo_type']} - {sig['reason']}")
    else:
        scores = score_combo_types(magic8_data, market_analysis)
        rec = generate_recommendation(scores)
        if rec.get('recommendation') != 'NONE':
            msg = (
                f"🎯 Magic8-Companion Checkpoint\n"
                f"Recommendation: {rec['recommendation'].upper()} (Score: {rec['score']})"
            )
            send_discord_alert(msg)


def setup_scheduler():
    scheduler = AsyncIOScheduler()
    est = pytz.timezone('America/New_York')

    scheduler.add_job(run_checkpoint, 'cron', hour=10, minute=30, timezone=est, id='cp_1030')
    scheduler.add_job(run_checkpoint, 'cron', hour=11, minute=0, timezone=est, id='cp_1100')
    scheduler.add_job(run_checkpoint, 'cron', hour=12, minute=30, timezone=est, id='cp_1230')
    scheduler.add_job(run_checkpoint, 'cron', hour=14, minute=45, timezone=est, id='cp_1445')

    return scheduler


def start():
    init_db()
    scheduler = setup_scheduler()
    scheduler.start()
