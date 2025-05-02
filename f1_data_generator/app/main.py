import os
import logging
import random 
import datetime
import requests
import time
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
import fastf1
import fastf1.core
import fastf1.api


load_dotenv() 

app_start_time = time.time()


ORION_URL = os.getenv("ORION_URL", "http://localhost:1026") 
SESSION_KEY = int(os.getenv("SESSION_KEY", 12345))
RACE_SESSION_ID = f"urn:ngsi-v2:RaceSession:{SESSION_KEY}"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

SCHEDULE_INTERVAL_SECONDS = int(os.getenv("SCHEDULE_INTERVAL_SECONDS", 10))

GENERATOR_YEAR = int(os.getenv("GENERATOR_YEAR", 2023))
GENERATOR_GP = os.getenv("GENERATOR_GP", "Monza")
GENERATOR_SESSION = os.getenv("GENERATOR_SESSION", "R")

TARGET_DRIVER_CODE = os.getenv("TARGET_DRIVER_CODE")
if not TARGET_DRIVER_CODE:
    logging.basicConfig(level="ERROR", format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.getLogger(__name__).error("FATAL: TARGET_DRIVER_CODE environment variable must be set.")
    raise ValueError("TARGET_DRIVER_CODE environment variable must be set. Example: TARGET_DRIVER_CODE=NOR")

ACTIVE_DRIVER_CODES = [TARGET_DRIVER_CODE.upper()] 

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"F1 Data Generator initializing...")
logger.info(f"Target Orion URL: {ORION_URL}")
logger.info(f"Generator Interval: {SCHEDULE_INTERVAL_SECONDS} seconds")
logger.info(f"Generator Source Data: {GENERATOR_YEAR} {GENERATOR_GP} {GENERATOR_SESSION}")
logger.info(f"--- TARGETING SINGLE DRIVER ---")
logger.info(f"Target driver: {ACTIVE_DRIVER_CODES[0]}")
logger.info(f"Simulation Session Key: {SESSION_KEY}")
logger.info(f"Simulation t=0 (App Start Time): {datetime.datetime.fromtimestamp(app_start_time).isoformat()}")


cache_path_env = os.getenv("FASTF1_CACHE_PATH")
default_cache_path_local = './fastf1_cache' 
cache_path = None

if cache_path_env:
    cache_path = cache_path_env
    logger.info(f"Using cache path from FASTF1_CACHE_PATH env var: {cache_path}")
else:
    if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ or 'FUNCTION_TARGET' in os.environ or 'K_SERVICE' in os.environ or 'RUNNING_IN_DOCKER' in os.environ: 
        cache_path = '/tmp/fastf1_cache'
        logger.info(f"Detected container/serverless environment, using cache path: {cache_path}")
    else:
        cache_path = default_cache_path_local
        logger.info(f"Using default local cache path: {cache_path}")
try:
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)
        logger.info(f"Created cache directory: {cache_path}")
    else:
        if not os.access(cache_path, os.W_OK):
             logger.warning(f"Cache directory '{cache_path}' exists but is NOT WRITABLE by the current user. Cache will likely fail.")
        else:
            logger.info(f"Using existing cache directory: {cache_path}")
    fastf1.Cache.enable_cache(cache_path)
    logger.info(f"FastF1 cache enabled at path: {cache_path}")
except PermissionError as e:
     logger.error(f"Permission denied configuring FastF1 cache at {cache_path}: {e}. Ensure the directory is writable by user '{os.getuid()}'. Caching disabled, performance severely impacted.")
except Exception as e:
    logger.warning(f"Could not configure FastF1 cache at {cache_path}: {e}. Performance might be impacted.")

generator_f1_session_cache = None
generator_laps_cache = {} 

app = FastAPI(title="F1 Data Generator and Simulation Service (Single Driver)")
scheduler = BackgroundScheduler(daemon=True)

def get_telemetry_at_simulated_time(
    driver_code: str,
    year: int,
    gp: str,
    session_identifier: str,
    simulated_race_time_seconds: float,
    cached_session: Optional[fastf1.core.Session] = None,
    cached_laps_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Fetches historical telemetry including X/Y position corresponding to a simulated race time.
    """
    logger.debug(f"Getting telemetry for {driver_code} at simulated time {simulated_race_time_seconds:.3f}s for {year} {gp} {session_identifier}")

    f1_session = cached_session
    laps_with_timing = cached_laps_df
    telemetry = None

    try:
        if f1_session is None:
            logger.debug(f"Cache miss for session {year} {gp} {session_identifier}. Loading...")
            f1_session = fastf1.get_session(year, gp, session_identifier)
            f1_session.load(laps=True, telemetry=False, weather=False, messages=False)
            logger.info(f"Session laps loaded for {year} {gp} {session_identifier}")

        if laps_with_timing is None:
            logger.debug(f"Cache miss for {driver_code}'s laps. Processing...")
            all_driver_laps_df = f1_session.laps[f1_session.laps['Driver'] == driver_code]
            if all_driver_laps_df.empty:
                return {"status": "error", "message": f"No laps found for driver '{driver_code}' in this session."}
            laps_with_timing = all_driver_laps_df[pd.notna(all_driver_laps_df['LapTime']) & pd.notna(all_driver_laps_df['LapStartTime'])].copy()
            if laps_with_timing.empty:
                return {"status": "error", "message": f"No laps with valid timing found for driver '{driver_code}'. Cannot determine race progression."}
            laps_with_timing['LapStartTime_seconds'] = laps_with_timing['LapStartTime'].dt.total_seconds()
            laps_with_timing['LapEndTime_seconds'] = laps_with_timing['LapStartTime_seconds'] + laps_with_timing['LapTime'].dt.total_seconds()
            laps_with_timing = laps_with_timing.sort_values(by='LapStartTime_seconds')
            logger.debug(f"Processed laps with timing for {driver_code}")

        if laps_with_timing.empty:
             return {"status": "error", "message": f"No valid laps found for driver '{driver_code}' after filtering."}

        first_lap_historical_start_seconds = laps_with_timing['LapStartTime_seconds'].iloc[0]
        last_lap_historical_end_seconds = laps_with_timing['LapEndTime_seconds'].iloc[-1]
        historical_target_time_seconds = first_lap_historical_start_seconds + simulated_race_time_seconds
        logger.debug(f"Driver {driver_code}: First lap start={first_lap_historical_start_seconds:.3f}s. Target historical time={historical_target_time_seconds:.3f}s")

        target_lap_row = None
        possible_laps = laps_with_timing[(laps_with_timing['LapStartTime_seconds'] <= historical_target_time_seconds) & (laps_with_timing['LapEndTime_seconds'] > historical_target_time_seconds)]
        status_message = "Data found"
        target_lap_number = -1
        target_lap_historical_start_time = 0.0
        final_historical_target_time_seconds = historical_target_time_seconds

        if not possible_laps.empty:
            target_lap_row = possible_laps.iloc[0]
            target_lap_number = int(target_lap_row['LapNumber'])
            target_lap_historical_start_time = target_lap_row['LapStartTime_seconds']
            logger.debug(f"Driver {driver_code}: Mapped to historical Lap {target_lap_number} (Starts: {target_lap_historical_start_time:.3f}s)")
        else:
            if historical_target_time_seconds < first_lap_historical_start_seconds:
                status_message = "Simulation at historical race start (Lap 1, Time 0)."
                target_lap_row = laps_with_timing.iloc[0]
                target_lap_number = int(target_lap_row['LapNumber'])
                target_lap_historical_start_time = first_lap_historical_start_seconds
                final_historical_target_time_seconds = first_lap_historical_start_seconds
                logger.debug(f"Driver {driver_code}: Simulation time before first lap. Using start of Lap {target_lap_number}.")
            elif historical_target_time_seconds >= last_lap_historical_end_seconds:
                status_message = "Simulated time is after the historical race finish."
                target_lap_row = laps_with_timing.iloc[-1]
                target_lap_number = int(target_lap_row['LapNumber'])
                target_lap_historical_start_time = target_lap_row['LapStartTime_seconds']
                final_historical_target_time_seconds = max(target_lap_historical_start_time, last_lap_historical_end_seconds - 0.001)
                logger.debug(f"Driver {driver_code}: Simulation time after last lap. Using end of Lap {target_lap_number}.")
            else:
                logger.error(f"Logic error for driver {driver_code}: Could not map historical_target_time_seconds ({historical_target_time_seconds:.3f}) to any lap.")
                return {"status": "error", "message": "Internal logic error mapping time to lap."}

        if target_lap_row is None:
             return {"status": "error", "message": "Failed to identify target lap row."}

        time_within_target_lap = final_historical_target_time_seconds - target_lap_historical_start_time
        lap_duration = target_lap_row['LapTime'].total_seconds()
        time_within_target_lap = max(0.0, min(time_within_target_lap, lap_duration))
        logger.debug(f"Driver {driver_code}: Calculated time within target Lap {target_lap_number}: {time_within_target_lap:.3f} seconds.")

        session_for_telemetry = cached_session if cached_session else f1_session
        if not hasattr(session_for_telemetry, 'telemetry') or session_for_telemetry.telemetry is None:
             logger.debug(f"Loading telemetry explicitly for session {year} {gp} {session_identifier} as it wasn't cached/preloaded.")
             session_for_telemetry.load(telemetry=True, laps=False) 

        target_lap_object = session_for_telemetry.laps.loc[target_lap_row.name]

        try:
            telemetry = target_lap_object.get_telemetry()
            if telemetry.empty:
                 raise fastf1.core.DataNotLoadedError(f"Telemetry data frame is empty for Lap {target_lap_number}.")
            logger.debug(f"Driver {driver_code}: Telemetry loaded for Lap {target_lap_number}.")
        except Exception as e:
            logger.warning(f"Could not get telemetry for driver {driver_code}, Lap {target_lap_number}: {e}. Returning partial data.")
            return {
                "status": "partial_no_telemetry",
                "message": f"Telemetry data not available for Lap {target_lap_number}: {e}",
                "simulated_elapsed_race_time_seconds": round(simulated_race_time_seconds, 3),
                "driver_code": driver_code,
                "year": year,
                "gp": session_for_telemetry.event['EventName'] if hasattr(session_for_telemetry, 'event') else gp,
                "session": session_identifier,
                "target_lap_number": target_lap_number,
                "calculated_time_within_lap_seconds": round(time_within_target_lap, 3),
            }

        if 'Time' not in telemetry.columns:
             logger.error(f"Driver {driver_code}, Lap {target_lap_number}: 'Time' column missing from telemetry data.")
             return {"status": "error", "message": "'Time' column missing from telemetry data."}
        if 'X' not in telemetry.columns or 'Y' not in telemetry.columns:
            logger.error(f"Driver {driver_code}, Lap {target_lap_number}: 'X' or 'Y' position columns missing from telemetry data.")
            return {"status": "error", "message": "'X'/'Y' position columns missing from telemetry."}

        if not pd.api.types.is_timedelta64_dtype(telemetry['Time']):
             telemetry['Time'] = pd.to_timedelta(telemetry['Time'])

        telemetry['Seconds'] = telemetry['Time'].dt.total_seconds()
        closest_index = (telemetry['Seconds'] - time_within_target_lap).abs().idxmin()
        closest_row = telemetry.loc[closest_index]

        actual_second_in_lap = float(closest_row.get('Seconds', 0.0))
        speed = float(closest_row.get('Speed', 0.0))
        distance = float(closest_row.get('Distance', 0.0))
        drs_value = closest_row.get('DRS', 0)
        drs_active = bool(drs_value and drs_value > 0) if isinstance(drs_value, (int, float)) else bool(drs_value)
        gear = int(closest_row.get('nGear', 0))
        rpm = int(closest_row.get('RPM', 0))
        brake_value = closest_row.get('Brake', False)
        brake_applied = int(brake_value) if isinstance(brake_value, (bool, int, float)) else 0
        throttle = int(closest_row.get('Throttle', 0))
        pos_x = float(closest_row.get('X', 0.0)) 
        pos_y = float(closest_row.get('Y', 0.0)) 

        logger.debug(f"Driver {driver_code}: Telemetry at {actual_second_in_lap:.3f}s in Lap {target_lap_number}: Speed={speed:.1f}, X={pos_x:.1f}, Y={pos_y:.1f}, DRS={drs_active}, Gear={gear}, RPM={rpm}, Brake={brake_applied}, Throttle={throttle}")

        return {
            "status": status_message,
            "simulated_elapsed_race_time_seconds": round(simulated_race_time_seconds, 3),
            "driver_code": driver_code,
            "year": year,
            "gp": session_for_telemetry.event['EventName'] if hasattr(session_for_telemetry, 'event') else gp,
            "session": session_identifier,
            "target_lap_number": target_lap_number,
            "calculated_time_within_lap_seconds": round(time_within_target_lap, 3),
            "closest_actual_second_in_lap": round(actual_second_in_lap, 3),
            "distance": round(distance, 1),
            "speed": round(speed, 1),
            "drs": drs_active,
            "gear": gear,
            "rpm": rpm,
            "brake": brake_applied,
            "throttle": throttle,
            "x": round(pos_x, 2), 
            "y": round(pos_y, 2), 
            "_session_ref": f1_session if cached_session is None else None,
            "_laps_ref": laps_with_timing if cached_laps_df is None else None
        }

    except (fastf1.api.SessionNotAvailableError, fastf1.ergast.ErgastError) as e:
        logger.error(f"Session data not available for {driver_code} ({year} {gp} {session_identifier}): {e}")
        return {"status": "error", "message": f"Session data not available: {e}"}
    except fastf1.core.DataNotLoadedError as e:
        logger.error(f"FastF1 data loading error for {driver_code} ({year} {gp} {session_identifier}): {e}")
        return {"status": "error", "message": f"FastF1 data loading error: {e}"}
    except KeyError as e:
        detail = f"Missing expected data column: '{e}'."
        if telemetry is not None and hasattr(telemetry, 'columns'): 
             detail += f" Available telemetry columns: {list(telemetry.columns)}"
        elif laps_with_timing is not None:
             detail += f" Available lap columns: {list(laps_with_timing.columns)}"
        logger.error(f"Missing expected column during processing for {driver_code}: {detail}")
        return {"status": "error", "message": detail}
    except Exception as e:
        logger.exception(f"Unexpected error fetching telemetry for {driver_code} ({year} {gp} {session_identifier}): {e}")
        return {"status": "error", "message": f"Unexpected error: {e}"}


@app.get("/live_race_simulation", response_model=Dict[str, Any])
async def get_simulated_live_telemetry(
    driver: str = Query(..., description="Driver code (e.g., VER, HAM)", min_length=3, max_length=3, example="VER"),
    year: int = Query(..., description="Race year", ge=1950, example=2023),
    gp: str = Query(..., description="Grand Prix name or round number", example="Monza"),
    session: str = Query(..., description="Session identifier (R, Q, FP1, etc.)", example="R")
) -> Dict[str, Any]:
    """
    Simulates race time elapsed since the API server started (t=0).
    Returns historical telemetry data (including X/Y position) corresponding
    to that simulated time point for the specified driver and race session.
    """
    current_time = time.time()
    simulated_race_time_seconds = max(0.0, current_time - app_start_time)

    driver_code = driver.upper()
    logger.info(f"Live Simulation Request: driver={driver_code}, year={year}, gp='{gp}', session='{session}'")
    logger.info(f"Simulated race time since API start: {simulated_race_time_seconds:.3f} seconds.")

    result = get_telemetry_at_simulated_time(
        driver_code=driver_code,
        year=year,
        gp=gp,
        session_identifier=session,
        simulated_race_time_seconds=simulated_race_time_seconds,
        cached_session=None,
        cached_laps_df=None
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=404 if "not available" in result.get("message", "").lower() or "no laps found" in result.get("message", "").lower() else 500,
                            detail=result.get("message", "Unknown error fetching telemetry"))
    elif result.get("status") == "partial_no_telemetry":
         result.pop("_session_ref", None)
         result.pop("_laps_ref", None)
         return JSONResponse(content=result, status_code=206)

    result.pop("_session_ref", None)
    result.pop("_laps_ref", None)

    return result

def format_to_ngsi_v2(telemetry_data: Dict[str, Any], current_timestamp: datetime.datetime) -> Optional[Dict[str, Any]]:
    """Formats the fetched telemetry data (including X,Y) into an NGSI-v2 entity."""
    required_keys = ["driver_code", "speed", "rpm", "gear", "throttle", "brake", "drs", "distance", "target_lap_number", "calculated_time_within_lap_seconds", "x", "y"]
    if not all(key in telemetry_data for key in required_keys):
        logger.warning(f"Missing essential keys in telemetry data for driver {telemetry_data.get('driver_code', 'N/A')}. Cannot format to NGSI-v2. Data: {telemetry_data}")
        return None

    entity_id = f"urn:ngsi-v2:Car:{telemetry_data['driver_code']}:{SESSION_KEY}"
    entity_type = "Car"

    ngsi_entity = {
        "id": entity_id,
        "type": entity_type,
        "speed": {"type": "Number", "value": telemetry_data["speed"]},
        "rpm": {"type": "Number", "value": telemetry_data["rpm"]},
        "gear": {"type": "Number", "value": telemetry_data["gear"]},
        "throttle": {"type": "Number", "value": telemetry_data["throttle"]},
        "brake": {"type": "Boolean", "value": bool(telemetry_data["brake"])},
        "drs": {"type": "Boolean", "value": telemetry_data["drs"]},
        "distance": {"type": "Number", "value": telemetry_data["distance"], "metadata": {"unitCode": {"value": "MTR"}}},
        "driverCode": {"type": "Text", "value": telemetry_data["driver_code"]},
        "lapNumber": {"type": "Number", "value": telemetry_data["target_lap_number"]},
        "timeWithinLap": {
            "type": "Number",
            "value": telemetry_data["calculated_time_within_lap_seconds"],
            "metadata": {"unitCode": {"value": "SEC"}}
        },
        "simulatedElapsedTime": {
             "type": "Number",
             "value": telemetry_data["simulated_elapsed_race_time_seconds"],
             "metadata": {"unitCode": {"value": "SEC"}}
        },
        "x": {"type": "Number", "value": telemetry_data["x"], "metadata": {"unitCode": {"value": "MTR"}}},
        "y": {"type": "Number", "value": telemetry_data["y"], "metadata": {"unitCode": {"value": "MTR"}}},
        "sourceSession": {
            "type": "StructuredValue",
            "value": {
                "year": telemetry_data["year"],
                "gp": telemetry_data["gp"],
                "session": telemetry_data["session"]
            }
        },
        "dateObserved": {
            "type": "DateTime",
            "value": current_timestamp.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        },
        "simulationSessionKey": {"type": "Number", "value": SESSION_KEY},
        "refRaceSession": {
            "type": "Relationship",
            "value": RACE_SESSION_ID
        }
    }
    return ngsi_entity

def send_to_orion(entities: List[Dict[str, Any]]):
    """Sends a batch of entities to Orion Context Broker using /v2/op/update."""
    if not entities:
        logger.info("No valid entities to send to Orion.")
        return

    orion_update_url = f"{ORION_URL}/v2/op/update"
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "actionType": "APPEND",
        "entities": entities
    }
    response = None 

    try:
        response = requests.post(orion_update_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        if entities:
             logger.info(f"Successfully sent update for car {entities[0].get('id', 'N/A')} to Orion. Status: {response.status_code}")
    except requests.exceptions.Timeout:
         logger.error(f"Timeout error sending data to Orion at {orion_update_url}")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error sending data to Orion at {orion_update_url}. Is Orion running/accessible?")
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if response is not None else 'N/A'
        entity_id = entities[0].get('id', 'N/A') if entities else 'N/A'
        logger.error(f"Error sending data to Orion ({status_code}) for entity {entity_id}: {e}")
        if response is not None and response.text:
            logger.error(f"Orion Response Body: {response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Orion update: {e}")


def generate_and_push_data():
    """Generates data for the single target driver and pushes to Orion."""
    global generator_f1_session_cache, generator_laps_cache

    if not ACTIVE_DRIVER_CODES:
        logger.error("No active driver code configured. Skipping generation.")
        return
    driver_code = ACTIVE_DRIVER_CODES[0]

    current_time = time.time()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    simulated_race_time_seconds = max(0.0, current_time - app_start_time)

    logger.info(f"--- Running Generator Cycle for {driver_code} (Simulated Time: {simulated_race_time_seconds:.3f}s) ---")

    try:
        if generator_f1_session_cache is None:
            logger.info(f"Generator cache empty. Loading base session data for {GENERATOR_YEAR} {GENERATOR_GP} {GENERATOR_SESSION}...")
            generator_f1_session_cache = fastf1.get_session(GENERATOR_YEAR, GENERATOR_GP, GENERATOR_SESSION)
            generator_f1_session_cache.load(laps=True, telemetry=False, weather=False, messages=False)
            logger.info("Base session laps loaded into generator cache.")
            generator_laps_cache = {} 
        elif not hasattr(generator_f1_session_cache, 'f1_api_support') or not generator_f1_session_cache.f1_api_support:
             logger.warning("Cached session reports no F1 API support or invalid. Reloading...")
             generator_f1_session_cache = None
             return 
    except Exception as e:
        logger.error(f"Failed to load or prepare generator session data: {e}. Skipping cycle.")
        generator_f1_session_cache = None
        generator_laps_cache = {}
        return

    logger.debug(f"Processing driver: {driver_code}")
    driver_laps_df = generator_laps_cache.get(driver_code)

    raw_data = get_telemetry_at_simulated_time(
        driver_code=driver_code,
        year=GENERATOR_YEAR,
        gp=GENERATOR_GP,
        session_identifier=GENERATOR_SESSION,
        simulated_race_time_seconds=simulated_race_time_seconds,
        cached_session=generator_f1_session_cache,
        cached_laps_df=driver_laps_df
    )

    ngsi_entity = None
    if raw_data.get("status") == "error":
        logger.warning(f"Generator: Failed to get data for {driver_code}: {raw_data.get('message')}")
    elif raw_data.get("status") == "partial_no_telemetry":
         logger.warning(f"Generator: Partial data (no telemetry) for {driver_code} at lap {raw_data.get('target_lap_number', 'N/A')}.")
    else:
        if driver_laps_df is None and raw_data.get("_laps_ref") is not None:
             logger.debug(f"Caching laps dataframe for driver {driver_code}")
             generator_laps_cache[driver_code] = raw_data.get("_laps_ref")

        ngsi_entity = format_to_ngsi_v2(raw_data, now_utc)
        if not ngsi_entity:
             logger.warning(f"Generator: Could not format NGSI entity for {driver_code}, likely missing data in result.")

    if ngsi_entity:
        logger.debug(f"Pushing update for entity {ngsi_entity.get('id')} to Orion.")
        send_to_orion([ngsi_entity]) 
    else:
        logger.info(f"No valid data generated for {driver_code} in this cycle to push to Orion.")

    logger.info(f"--- Generator Cycle Finished for {driver_code} ---")

@app.on_event("startup")
async def startup_event():
    """Starts the background scheduler when the app starts."""
    logger.info("Application startup...")
    logger.info("Scheduling background data generation job...")
    scheduler.add_job(
        generate_and_push_data,
        trigger=IntervalTrigger(seconds=SCHEDULE_INTERVAL_SECONDS),
        id="f1_data_job",
        name="F1 Data Generation and Push",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=10 
    )
    scheduler.start()
    time.sleep(1)
    if scheduler.running:
        logger.info(f"Scheduler started. Job 'f1_data_job' scheduled to run every {SCHEDULE_INTERVAL_SECONDS} seconds.")
    else:
        logger.error("Scheduler failed to start.")

@app.on_event("shutdown")
async def shutdown_event():
    """Shuts down the background scheduler gracefully."""
    logger.info("Application shutdown...")
    logger.info("Shutting down background scheduler...")
    try:
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully.")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")


@app.get("/", summary="Service Information")
async def root():
    global generator_f1_session_cache
    session_loaded = generator_f1_session_cache is not None
    cache_status = "Enabled" if fastf1.Cache.is_enabled() else "Disabled"
    return {
        "service": "F1 Data Generator and Simulation Service (Single Driver)",
        "status": "running",
        "generator_config": {
            "source_year": GENERATOR_YEAR,
            "source_gp": GENERATOR_GP,
            "source_session": GENERATOR_SESSION,
            "interval_seconds": SCHEDULE_INTERVAL_SECONDS,
            "target_driver": ACTIVE_DRIVER_CODES[0], # Show the target driver
            "simulation_session_key": SESSION_KEY,
            "base_session_data_loaded": session_loaded
        },
        "fastf1_cache": {
            "status": cache_status,
            "path": fastf1.Cache.get_cache_path() if fastf1.Cache.is_enabled() else "N/A"
        },
        "scheduler_running": scheduler.running,
        "simulation_time_origin_utc": datetime.datetime.fromtimestamp(app_start_time, tz=datetime.timezone.utc).isoformat()
    }

@app.get("/health", summary="Health Check")
async def health_check():
    orion_status = "unknown"
    try:
        response = requests.get(f"{ORION_URL}/version", timeout=2)
        if response.ok:
            orion_status = "ok"
        else:
            orion_status = f"error_{response.status_code}"
    except requests.exceptions.RequestException:
        orion_status = "unreachable"
    return {
        "status": "ok",
        "scheduler_running": scheduler.running,
        "orion_status": orion_status
        }

@app.get("/api/v1/f1data/debug_single_point", summary="Generate Single Data Point (Debug)")
async def get_debug_data_point(
    simulated_time: float = Query(600.0, description="Simulated seconds since start")
):
     """Generates one data point for the TARGET driver at specific time."""
     driver_code = ACTIVE_DRIVER_CODES[0] 
     logger.debug(f"Generating debug data sample for {driver_code} at time {simulated_time}s.")
     now_utc = datetime.datetime.now(datetime.timezone.utc)

     session_to_use = generator_f1_session_cache
     laps_to_use = generator_laps_cache.get(driver_code)

     raw_data = get_telemetry_at_simulated_time(
         driver_code=driver_code,
         year=GENERATOR_YEAR,
         gp=GENERATOR_GP,
         session_identifier=GENERATOR_SESSION,
         simulated_race_time_seconds=simulated_time,
         cached_session=session_to_use,
         cached_laps_df=laps_to_use
     )

     if raw_data.get("status") in ["error", "partial_no_telemetry"]:
         raise HTTPException(status_code=404, detail=raw_data.get("message", "Could not generate debug data point."))

     ngsi_entity = format_to_ngsi_v2(raw_data, now_utc)
     if ngsi_entity:
         return ngsi_entity
     else:
          raise HTTPException(status_code=500, detail="Failed to format generated data into NGSI-v2.")


if __name__ == "__main__":
    if not TARGET_DRIVER_CODE:
        logger.error("Cannot start: TARGET_DRIVER_CODE environment variable is not set.")
    else:
        import uvicorn
        logger.info("Starting Uvicorn server directly...")
        app_host = os.getenv("APP_HOST", "127.0.0.1")
        app_port = int(os.getenv("APP_PORT", 8000))
        uvicorn.run(app, host=app_host, port=app_port, log_level=LOG_LEVEL.lower())