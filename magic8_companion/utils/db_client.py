import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
import datetime
import logging
from ..modules.ib_client import IBClient
from ..utils.position_parser import format_strikes_for_db

# Module logger
logger = logging.getLogger(__name__)

DB_PATH = Path('data/positions.db')
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            con_id INTEGER UNIQUE, -- IB's contract ID, should be unique for open positions
            symbol TEXT NOT NULL,
            combo_type TEXT NOT NULL,  -- 'butterfly', 'iron_condor', 'vertical'
            direction TEXT,            -- 'bull', 'bear', 'neutral' (for verticals, or overall bias)
            entry_time TEXT NOT NULL,
            strikes_info TEXT,         -- e.g., "C5000/C5010/C5020" or "P4900/P4905_C5100/C5105"
            quantity INTEGER NOT NULL,
            entry_price_total REAL,    -- Total credit received or debit paid for the combo (per unit)
            current_pnl REAL DEFAULT 0.0,
            status TEXT DEFAULT 'OPEN'  -- 'OPEN', 'CLOSED', 'MONITORING'
        )"""
    )
    # Add index for con_id for faster lookups
    cur.execute("CREATE INDEX IF NOT EXISTS idx_con_id ON positions (con_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON positions (status)")
    conn.commit()
    conn.close()


def add_position_to_db(pos_details: Dict[str, Any]) -> Optional[int]:
    """
    Adds a new position to the database.
    pos_details should include: con_id, symbol, combo_type, direction, strikes_info, quantity, entry_price_total.
    Returns the id of the newly inserted row, or None if failed.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO positions
               (con_id, symbol, combo_type, direction, entry_time, strikes_info, quantity, entry_price_total, status, current_pnl)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0.0)""",
            (
                pos_details.get('con_id'),
                pos_details.get('symbol'),
                pos_details.get('combo_type'),
                pos_details.get('direction'),
                datetime.datetime.now().isoformat(),
                pos_details.get('strikes_info'),
                pos_details.get('quantity'),
                pos_details.get('entry_price_total')
            )
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"Error adding position (con_id {pos_details.get('con_id')} might already exist): {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error adding position to DB: {e}")
        return None
    finally:
        conn.close()


def create_position_from_magic8_recommendation(
    magic8_data: Dict,
    combo_type: str,
    con_id: Optional[int] = None,
    quantity: int = 1
) -> Optional[int]:
    """
    Create a position entry from Magic8 recommendation data.
    
    Args:
        magic8_data: Magic8 prediction data containing example_trades
        combo_type: Type of combo to create ('butterfly', 'iron_condor', 'vertical')
        con_id: Optional IB contract ID (if available from order execution)
        quantity: Number of contracts (default 1)
        
    Returns:
        Position ID if created successfully, None otherwise
    """
    if 'example_trades' not in magic8_data:
        logger.error("No example_trades in Magic8 data")
        return None
        
    trade_info = magic8_data['example_trades'].get(combo_type)
    if not trade_info:
        logger.error(f"No {combo_type} trade in Magic8 example_trades")
        return None
    
    # Parse strikes from Magic8 format (e.g., "5905/5855/5805")
    strikes_str = trade_info.get('strikes', '')
    option_type = trade_info.get('type', 'CALL')
    
    # Create strikes_info in DB format
    if combo_type == 'butterfly':
        # Convert "5905/5855/5805" to "C5805/C5855/C5905" (sorted)
        strikes = sorted([float(s) for s in strikes_str.split('/')])
        prefix = 'C' if 'CALL' in option_type else 'P'
        strikes_info = f"{prefix}{strikes[0]}/{prefix}{strikes[1]}/{prefix}{strikes[2]}"
        direction = 'neutral'
        
    elif combo_type == 'iron_condor':
        # Convert "5905/5910/5780/5775" to "P5775/P5780_C5905/C5910"
        parts = strikes_str.split('/')
        if len(parts) == 4:
            # Assume first two are calls, last two are puts
            call_strikes = sorted([float(parts[0]), float(parts[1])])
            put_strikes = sorted([float(parts[2]), float(parts[3])])
            strikes_info = f"P{put_strikes[0]}/P{put_strikes[1]}_C{call_strikes[0]}/C{call_strikes[1]}"
        else:
            logger.error(f"Invalid iron condor strikes format: {strikes_str}")
            return None
        direction = 'neutral'
        
    elif combo_type == 'vertical':
        # Convert "5820/5815" to "P5815/P5820" (sorted)
        strikes = sorted([float(s) for s in strikes_str.split('/')])
        prefix = 'C' if 'CALL' in option_type else 'P'
        strikes_info = f"{prefix}{strikes[0]}/{prefix}{strikes[1]}"
        # Determine direction based on trade action and option type
        if trade_info.get('action') == 'BUY':
            direction = 'bull' if 'CALL' in option_type else 'bear'
        else:  # SELL
            direction = 'bear' if 'CALL' in option_type else 'bull'
    else:
        logger.error(f"Unknown combo type: {combo_type}")
        return None
    
    # Create position details
    pos_details = {
        'con_id': con_id,
        'symbol': 'SPX',  # Assuming SPX for now
        'combo_type': combo_type,
        'direction': direction,
        'strikes_info': strikes_info,
        'quantity': quantity,
        'entry_price_total': trade_info.get('price', 0.0)
    }
    
    logger.info(f"Creating position from Magic8: {pos_details}")
    return add_position_to_db(pos_details)


def get_db_positions(status: Optional[str] = 'OPEN') -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM positions WHERE status=?", (status,))
    else:
        cur.execute("SELECT * FROM positions")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_position_by_con_id(con_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific position by contract ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM positions WHERE con_id=?", (con_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_position_in_db(con_id: int, pnl: Optional[float] = None, status: Optional[str] = None) -> bool:
    """
    Updates P&L and/or status for a position identified by con_id.
    Returns True if update was successful, False otherwise.
    """
    if pnl is None and status is None:
        return False

    conn = get_db_connection()
    cur = conn.cursor()

    fields_to_update = []
    params = []

    if pnl is not None:
        fields_to_update.append("current_pnl = ?")
        params.append(pnl)
    if status is not None:
        fields_to_update.append("status = ?")
        params.append(status)

    params.append(con_id)

    query = f"UPDATE positions SET {', '.join(fields_to_update)} WHERE con_id = ?"

    try:
        cur.execute(query, tuple(params))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating position {con_id} in DB: {e}")
        return False
    finally:
        conn.close()


def get_daily_pnl() -> float:
    """Calculate total P&L for all positions opened today."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    today = datetime.date.today().isoformat()
    cur.execute(
        """SELECT SUM(current_pnl) as total_pnl 
           FROM positions 
           WHERE DATE(entry_time) = ? AND status IN ('OPEN', 'CLOSED')""",
        (today,)
    )
    
    result = cur.fetchone()
    conn.close()
    
    return result['total_pnl'] if result and result['total_pnl'] else 0.0


def check_daily_loss_limit() -> bool:
    """
    Check if daily loss limit has been exceeded.
    
    Returns:
        True if within limits, False if limit exceeded
    """
    from ..unified_config import settings
    
    daily_pnl = get_daily_pnl()
    if daily_pnl <= -settings.max_daily_loss:
        logger.warning(f"Daily loss limit exceeded: ${abs(daily_pnl):.2f} >= ${settings.max_daily_loss}")
        return False
    return True


async def sync_positions_with_ib(ib_client: IBClient):
    """
    Synchronizes positions in the local DB with those from IB.
    - Updates P&L for open positions.
    - Marks positions closed in DB if they are no longer in IB.
    - Logs new positions found in IB but not in DB.
    """
    logger.info("Starting position synchronization with IB...")
    
    try:
        await ib_client._ensure_connected()
        ib_portfolio_items = ib_client.ib.portfolio()
    except ConnectionError as e:
        logger.error(f"IB Connection Error during sync_positions: {e}")
        return
    except Exception as e:
        logger.error(f"Error fetching portfolio from IB for sync: {e}")
        return

    db_open_positions = get_db_positions(status='OPEN')
    db_pos_map_by_conid = {pos['con_id']: pos for pos in db_open_positions if pos['con_id'] is not None}

    ib_pos_conids_synced = set()

    for item in ib_portfolio_items:
        contract = item.contract
        if contract.secType != 'OPT':
            continue

        con_id = contract.conId
        ib_pos_conids_synced.add(con_id)

        unrealized_pnl = item.unrealizedPNL

        if con_id in db_pos_map_by_conid:
            # Position exists in both IB and DB
            logger.info(f"Updating P&L for position con_id {con_id}: ${unrealized_pnl:.2f}")
            update_position_in_db(con_id, pnl=unrealized_pnl, status='OPEN')
        else:
            # Position in IB but not in DB
            existing_db_pos = get_position_by_con_id(con_id)
            if not existing_db_pos:
                logger.info(
                    f"New position found in IB: con_id {con_id} "
                    f"({contract.symbol} {contract.lastTradeDateOrContractMonth} "
                    f"{contract.strike} {contract.right}) P&L: ${unrealized_pnl:.2f}"
                )

    # Check for positions in DB that are no longer in IB
    for con_id, db_pos in db_pos_map_by_conid.items():
        if con_id not in ib_pos_conids_synced:
            logger.info(
                f"Position con_id {con_id} ({db_pos['symbol']}) "
                f"is OPEN in DB but not found in IB. Marking as CLOSED."
            )
            update_position_in_db(con_id, status='CLOSED')

    logger.info("Position synchronization completed")
