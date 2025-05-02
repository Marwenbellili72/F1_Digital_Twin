import streamlit as st
import fastf1
import fastf1.plotting
import fastf1.core
import matplotlib.pyplot as plt
from crate import client
from crate.client.exceptions import ProgrammingError 
import os
import time
import logging
import pandas as pd
import datetime
import numpy as np

CRATE_HOSTS = os.getenv("CRATE_HOSTS")
LAYOUT_YEAR = 2023
LAYOUT_GP = "Monza"
LAYOUT_SESSION = "R"
REFRESH_INTERVAL = 5
FASTF1_CACHE_PATH = "./fastf1_cache_streamlit"


logging.basicConfig(level="DEBUG", format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"Log level set to: {logging.getLevelName(logger.level)}")
logger.info(f"CrateDB Host: {CRATE_HOSTS}")

try:
    if not os.path.exists(FASTF1_CACHE_PATH): os.makedirs(FASTF1_CACHE_PATH)
    fastf1.Cache.enable_cache(FASTF1_CACHE_PATH)
    logger.info(f"FastF1 cache enabled at: {FASTF1_CACHE_PATH}")
except Exception as e: logger.warning(f"Could not configure FastF1 cache: {e}")

try:
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme=None, misc_mpl_mods=True)
    logger.info("Applied FastF1 Matplotlib base styles.")
except Exception as e: logger.warning(f"Could not apply FastF1 base plotting style: {e}")


@st.cache_data(ttl=3600)
def get_circuit_info_and_session(year, gp, session_id):
    logger.info(f"Loading session and circuit layout for {year} {gp} {session_id}")
    try:
        session = fastf1.get_session(year, gp, session_id)
        session.load(laps=True, telemetry=True, weather=False, messages=False, livedata=None)
        logger.info("Session data loaded (laps, telemetry).")
        circuit_info = session.get_circuit_info()
        fastest_lap = session.laps.pick_fastest()
        if fastest_lap is None or not isinstance(fastest_lap, fastf1.core.Lap):
             logger.warning(f"No fastest lap for {year} {gp} {session_id}. Trying quick lap.")
             laps_with_telemetry = session.laps.pick_quicklaps()
             if not laps_with_telemetry.empty:
                 fastest_lap = laps_with_telemetry.iloc[0]
                 if not isinstance(fastest_lap, fastf1.core.Lap): raise ValueError("Invalid fallback lap.")
             else: raise ValueError("No suitable laps found.")
        if fastest_lap is None: raise ValueError("Failed to get valid lap.")
        pos_data = fastest_lap.get_pos_data(pad=1)
        if pos_data is None or 'X' not in pos_data or 'Y' not in pos_data: raise ValueError("Missing X/Y in pos_data.")
        track_x = pos_data['X']; track_y = pos_data['Y']
        logger.info(f"Loaded layout for {session.event['EventName']}")
        return circuit_info, track_x, track_y, session
    except Exception as e:
        logger.error(f"FastF1 load/processing failed for {year} {gp} {session_id}: {e}", exc_info=True)
        st.error(f"Failed to load FastF1 data: {e}")
        return None, None, None, None

def connect_crate(crate_hosts):
    """Establishes connection to CrateDB."""
    try:
        logger.info(f"Attempting to connect to CrateDB at: {crate_hosts}")
        connection = client.connect(crate_hosts, error_trace=True)
        logger.info("Successfully connected/reconnected to CrateDB.")
        return connection
    except Exception as e:
        logger.error(f"CrateDB Connection Error to {crate_hosts}: {e}", exc_info=True)
        return None

def get_db_connection():
    """Gets or creates a CrateDB connection stored in session state."""
    if 'crate_conn' not in st.session_state or st.session_state.crate_conn is None:
        logger.info("No active CrateDB connection found in session_state, creating new one.")
        st.session_state.crate_conn = connect_crate(CRATE_HOSTS)
    if st.session_state.crate_conn is None:
        st.error("Failed to establish CrateDB connection.")
        st.stop()
    return st.session_state.crate_conn

def close_db_connection():
    """Closes the connection stored in session state."""
    if 'crate_conn' in st.session_state and st.session_state.crate_conn is not None:
        logger.info("Closing CrateDB connection from session_state.")
        try: st.session_state.crate_conn.close()
        except Exception as e: logger.error(f"Error closing CrateDB connection: {e}")
        st.session_state.crate_conn = None

def get_latest_driver_position(conn, entity_id):
    """Queries CrateDB for the latest X, Y coords. Assumes conn is valid."""
    if conn is None: return None, None
    cursor = None
    try:
        cursor = conn.cursor()
        sql = """ SELECT x, y, "time_index" FROM "etcar" WHERE entity_id = ? ORDER BY "time_index" DESC LIMIT 1 """
        logger.debug(f"Executing query: {sql.strip()} with entity_id: {entity_id}")
        cursor.execute(sql, (entity_id,))
        result = cursor.fetchone()
        if result:
            timestamp = pd.to_datetime(result[2], utc=True)
            return (result[0], result[1]), timestamp
        else:
            logger.debug(f"No position data found for entity_id: {entity_id} using table 'etcar'")
            return None, None
    except Exception as e:
        if "RelationUnknown" in str(e):
             logger.error(f"CrateDB Query Error: Relation 'etcar' not found for entity '{entity_id}'. Check CrateDB. Error: {e}")
             st.error(f"Error: The required table 'etcar' was not found in CrateDB.")
        else:
             logger.error(f"CrateDB Query Error for entity_id '{entity_id}': {e}", exc_info=True)
             st.warning(f"Error querying CrateDB for position: {e}")
        # Let ProgrammingError ("Connection closed") propagate up
        if isinstance(e, ProgrammingError): raise e
        return None, None
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass

def get_driver_info(entity_id, session):
    default_abbr = "UNK"; default_color = "#CCCCCC"
    driver_abbr = default_abbr; driver_color = default_color
    if not entity_id or not session: return default_abbr, default_color
    try:
        parts = entity_id.split(':')
        if len(parts) >= 4 and parts[0].lower() == 'urn' and parts[1].lower() == 'ngsi-v2' and parts[2].lower() == 'car':
            driver_abbr = parts[3].upper()
            try:
                color_from_plotting = fastf1.plotting.driver_color(driver_abbr)
                if color_from_plotting: driver_color = color_from_plotting
                else:
                     driver_detail = session.get_driver(driver_abbr)
                     if driver_detail is not None and 'TeamColor' in driver_detail and driver_detail['TeamColor']:
                        color_code = driver_detail['TeamColor']
                        driver_color = "#" + color_code if not color_code.startswith('#') else color_code
                     else: driver_color = default_color
            except KeyError: driver_color = default_color
            except Exception as e: logger.error(f"Error resolving color for {driver_abbr}: {e}"); driver_color = default_color
        else: logger.warning(f"Could not parse driver abbr from {entity_id}")
        return driver_abbr, driver_color
    except Exception as e: logger.error(f"Error in get_driver_info: {e}"); return "ERR", "#FF0000"

st.set_page_config(page_title="F1 Driver Position Tracker", layout="wide")

background_color = "#111217"
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {background_color};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Live Position Tracker")
st.subheader("Track a Driver's Position")

TARGET_ENTITY_ID = st.text_input(
    "Enter NGSI Entity ID (e.g., urn:ngsi-v2:Car:VER:2023):",
    value="urn:ngsi-v2:Car:NOR:20240115"
)

if not TARGET_ENTITY_ID: st.error("Please provide a valid NGSI Entity ID."); st.stop()

circuit_info, track_x, track_y, f1_session = get_circuit_info_and_session(LAYOUT_YEAR, LAYOUT_GP, LAYOUT_SESSION)
if circuit_info is None: logger.critical("Failed to load FastF1 data."); st.stop() 

driver_abbr, driver_color = get_driver_info(TARGET_ENTITY_ID, f1_session)
st.caption(f"Using {LAYOUT_YEAR} {LAYOUT_GP} {LAYOUT_SESSION} layout. Tracking: **{driver_abbr}** (Color: {driver_color})")

fig, ax = plt.subplots(figsize=(12, 12))
fig.patch.set_facecolor(background_color)
ax.patch.set_facecolor(background_color)
ax.axis('off'); ax.set_aspect('equal', adjustable='box')

try:
    rotation_angle = circuit_info.rotation / 180 * np.pi if hasattr(circuit_info, 'rotation') and circuit_info.rotation is not None else 0
    if rotation_angle == 0: logger.warning("CircuitInfo has no 'rotation'. Assuming 0.")
    track_x_rotated = track_x * np.cos(rotation_angle) - track_y * np.sin(rotation_angle)
    track_y_rotated = track_x * np.sin(rotation_angle) + track_y * np.cos(rotation_angle)
    ax.plot(track_x_rotated, track_y_rotated, color='white', linewidth=1.5, solid_capstyle='round')
    x_min, x_max = np.min(track_x_rotated), np.max(track_x_rotated)
    y_min, y_max = np.min(track_y_rotated), np.max(track_y_rotated)
    padding_x = (x_max - x_min) * 0.05; padding_y = (y_max - y_min) * 0.05
    ax.set_xlim(x_min - padding_x, x_max + padding_x); ax.set_ylim(y_min - padding_y, y_max + padding_y)
    logger.info("Track outline plotted.")
except Exception as plot_err: logger.error(f"Error preparing track plot: {plot_err}", exc_info=True); st.error(f"Error plotting track: {plot_err}"); st.stop()

plot_placeholder = st.empty()
status_placeholder = st.empty()

driver_scatter = None; driver_text = None
connection_attempts = 0; MAX_CONNECTION_ATTEMPTS = 3

try:
    while True:
        position, time_idx = None, None
        crate_conn = None

        try:
            crate_conn = get_db_connection()
            position, time_idx = get_latest_driver_position(crate_conn, TARGET_ENTITY_ID)
            connection_attempts = 0 
        except ProgrammingError as e:
            if "Connection closed" in str(e) and connection_attempts < MAX_CONNECTION_ATTEMPTS:
                connection_attempts += 1
                logger.warning(f"CrateDB closed. Reconnecting ({connection_attempts}/{MAX_CONNECTION_ATTEMPTS})...")
                status_placeholder.warning(f"Reconnecting DB ({connection_attempts})...")
                close_db_connection()
                time.sleep(1)
                continue
            else: logger.critical(f"DB ProgrammingError or max retries: {e}", exc_info=True); st.error(f"DB error: {e}"); break
        except Exception as loop_db_err:
            logger.error(f"Unexpected DB query error: {loop_db_err}", exc_info=True)
            st.warning(f"DB query failed: {loop_db_err}")
            time.sleep(REFRESH_INTERVAL)
            continue

        if time_idx:
            now_utc = datetime.datetime.now(datetime.timezone.utc); time_diff = now_utc - time_idx
            time_diff_str = f"{time_diff.total_seconds():.1f}s ago"
            if time_diff.total_seconds() < 0: time_diff_str = f"{abs(time_diff.total_seconds()):.1f}s in future?"
            elif time_diff.total_seconds() > 300: time_diff_str += " (stale?)"
            status_placeholder.info(f"Tracking {driver_abbr} ({driver_color}). Last: {time_idx.strftime('%H:%M:%S.%f')[:-3]} UTC ({time_diff_str})")
        else:
             if connection_attempts == 0: status_placeholder.warning(f"Waiting for {driver_abbr} position data...")

        if driver_scatter:
            try:
                driver_scatter.remove()
            except Exception:
                pass 
            driver_scatter = None

        if driver_text:
            try:
                driver_text.remove()
            except Exception:
                pass 
            driver_text = None

        if position:
            try:
                x, y = position
                rotated_x = x * np.cos(rotation_angle) - y * np.sin(rotation_angle)
                rotated_y = x * np.sin(rotation_angle) + y * np.cos(rotation_angle)
                driver_scatter = ax.scatter(rotated_x, rotated_y, color=driver_color, edgecolor='white', linewidth=0.5, marker='o', s=140, zorder=10)
                plot_width = x_max - x_min; plot_height = y_max - y_min
                padding = (plot_width + plot_height) / 2 * 0.018
                text_offset_x = padding * np.sign(rotated_x) if abs(rotated_x) > 1e-3 else padding
                text_offset_y = padding
                driver_text = ax.text(rotated_x + text_offset_x, rotated_y + text_offset_y, driver_abbr, color='white', fontsize=10, fontweight='bold', ha='center', va='center', zorder=11)
            except Exception as draw_err: logger.error(f"Error plotting driver: {draw_err}", exc_info=True); st.warning(f"Could not plot driver: {draw_err}")

        try: plot_placeholder.pyplot(fig, clear_figure=False)
        except Exception as redraw_err: logger.error(f"Error redrawing plot: {redraw_err}", exc_info=True)

        time.sleep(REFRESH_INTERVAL)

except KeyboardInterrupt: logger.info("App interrupted.")
except Exception as main_loop_err: logger.critical(f"Main loop error: {main_loop_err}", exc_info=True); st.error(f"App Error: {main_loop_err}")
finally: logger.info("Closing plot & DB connection."); plt.close(fig); close_db_connection(); logger.info("App exited.")