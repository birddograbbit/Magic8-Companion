import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
import datetime
from ..modules.ib_client import IBClient # Assuming IBClient is needed for type hinting or direct calls

DB_PATH = Path('data/positions.db')
DB_PATH.parent.mkdir(parents=True, exist_ok=True) # Ensure data directory exists

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # DB_PATH.parent.mkdir(parents=True, exist_ok=True) # Moved to top for module load
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

            # Fields from guide for more detailed tracking if needed:
            # center_strike REAL,
            # wing_width REAL,
            # short_put_strike REAL,
            # short_call_strike REAL,
            # entry_credit REAL, # This could be entry_price_total if always credit
            # max_loss REAL, # Calculated or from order

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
    except sqlite3.IntegrityError as e: # Handles UNIQUE constraint violation for con_id
        print(f"Error adding position (con_id {pos_details.get('con_id')} might already exist): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error adding position to DB: {e}")
        return None
    finally:
        conn.close()

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

def update_position_in_db(con_id: int, pnl: Optional[float] = None, status: Optional[str] = None) -> bool:
    """
    Updates P&L and/or status for a position identified by con_id.
    Returns True if update was successful, False otherwise.
    """
    if pnl is None and status is None:
        return False # Nothing to update

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
        return cur.rowcount > 0 # Check if any row was actually updated
    except Exception as e:
        print(f"Error updating position {con_id} in DB: {e}")
        return False
    finally:
        conn.close()

async def sync_positions_with_ib(ib_client: IBClient):
    """
    Synchronizes positions in the local DB with those from IB.
    - Updates P&L for open positions.
    - Marks positions closed in DB if they are no longer in IB.
    - Logs new positions found in IB but not in DB (does not add them automatically yet).
    """
    print("Starting position synchronization with IB...")
    try:
        # ib_client.get_positions() currently returns basic position info.
        # For P&L, we ideally need ib.portfolio() which gives unrealizedPNL.
        # Let's assume ib_client.get_positions() is enhanced or we call portfolio items here.
        # For this subtask, we'll use ib_client.ib.portfolio() directly for richer data.
        # This requires ib_client to have an active and connected `ib` instance.
        await ib_client._ensure_connected() # Ensure connection
        ib_portfolio_items = ib_client.ib.portfolio()
    except ConnectionError as e:
        print(f"IB Connection Error during sync_positions: {e}")
        return
    except Exception as e:
        print(f"Error fetching portfolio from IB for sync: {e}")
        return

    db_open_positions = get_db_positions(status='OPEN')
    db_pos_map_by_conid = {pos['con_id']: pos for pos in db_open_positions if pos['con_id'] is not None}

    ib_pos_conids_synced = set()

    for item in ib_portfolio_items:
        contract = item.contract
        if contract.secType != 'OPT': # Focus on options
            continue

        con_id = contract.conId
        ib_pos_conids_synced.add(con_id)

        unrealized_pnl = item.unrealizedPNL
        # market_price = item.marketPrice # also available

        if con_id in db_pos_map_by_conid:
            # Position exists in IB and in our DB as OPEN
            print(f"Updating P&L for position con_id {con_id}: New P&L = {unrealized_pnl}")
            update_position_in_db(con_id, pnl=unrealized_pnl, status='OPEN') # Keep status OPEN
        else:
            # Position exists in IB but not in our DB (or not as OPEN)
            # This could be a new position opened outside Magic8-Companion, or one previously closed by us.
            # For now, just log it. Future enhancement: add it to DB if truly new.
            existing_db_pos = get_db_positions(status=None) # Check all statuses
            if not any(p['con_id'] == con_id for p in existing_db_pos):
                 print(f"Info: Position con_id {con_id} (Symbol: {contract.symbol} {contract.lastTradeDateOrContractMonth} {contract.strike} {contract.right}) " +
                       f"found in IB but not in local DB. P&L: {unrealized_pnl}. Consider manual review or future auto-add feature.")


    # Check for positions in DB that are no longer in IB (i.e., closed in IB)
    for con_id, db_pos in db_pos_map_by_conid.items():
        if con_id not in ib_pos_conids_synced:
            print(f"Position con_id {con_id} (Symbol: {db_pos['symbol']}) is OPEN in DB but not found in IB. Marking as CLOSED.")
            update_position_in_db(con_id, status='CLOSED', pnl=db_pos.get('current_pnl')) # Keep last known PNL or set to 0 if desired

    print("Finished position synchronization.")

# (The old mark_position_closed function can be removed if update_position_in_db with status='CLOSED' replaces it)
# def mark_position_closed(pos_id: int): # Old function by primary key 'id'
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute("UPDATE positions SET status='CLOSED' WHERE id=?", (pos_id,))
#     conn.commit()
#     conn.close()
