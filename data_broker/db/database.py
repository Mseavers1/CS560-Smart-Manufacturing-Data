# app/database_singleton.py
import asyncio
import os
import asyncpg
from datetime import datetime, timezone
from pathlib import Path
from app import loggers
import subprocess
from package.client import Client
from app.connection_manager import camera_manager, imu_manager, robot_manager, misc_manager


class SessionNotStarted(Exception):

    def __init__(self, message, data=None):
        super().__init__(message)
        self.data = data
        self.message = message

class ExistingSessionLabel(Exception):

    def __init__(self, message, data=None):
        super().__init__(message)
        self.data = data
        self.message = message


class MissingDatabaseDetails(Exception):

    def __init__(self, message, data=None):
        super().__init__(message)
        self.data = data
        self.message = message

class DatabaseSingleton:
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.devices = {}
        self.current_session_id = None
        self.history = set()
        self._last_check = 0

        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.name = os.getenv("DB_NAME")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")

    @classmethod
    async def get_instance(cls, min_size: int = 1, max_size: int = 50):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    pool = await asyncpg.create_pool(
                        host=os.getenv("DB_HOST"),
                        port=int(os.getenv("DB_PORT")),
                        database=os.getenv("DB_NAME"),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD"),
                        min_size=min_size,
                        max_size=max_size,
                    )
                    cls._instance = cls(pool)
                    loggers.log_system_logger("Database pool initialized (singleton).")
        return cls._instance
    
    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.pool.close()
            cls._instance = None
            loggers.log_system_logger("Database pool closed.")


    def get_time(self):
        try:
            return datetime.now(timezone.utc).timestamp()
        except (ValueError, IOError) as e:
            loggers.log_system_logger(f"DB could not get UTC time: {e}")
            return 0

    async def get_latest_session(self):

        if self.current_session_id and (datetime.now(timezone.utc).timestamp() - self._last_check < 10):
            return self.current_session_id

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, ended_at
                FROM session
                ORDER BY started_at DESC, id DESC
                LIMIT 1
            """)

        if row and row["ended_at"] is None:
            self.current_session_id = row["id"]
            self._last_check = datetime.now(timezone.utc).timestamp()
            return row["id"]

        self.current_session_id = None
        return None

    async def restore_backup(self, file_path: str):

        await misc_manager.broadcast_json({
            "type": "normal",
            "text": "Recovery Started..."
        })

        try: 

            # Kill all connections
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = $1
                    AND pid <> pg_backend_pid();
                """, self.name)


            # Close current DB connections
            await self.pool.close()

            env = {**os.environ, "PGPASSWORD": self.password}

            # Drop + recreate the database
            subprocess.run(
                ["dropdb", "-h", self.host, "-p", self.port, "-U", self.user, self.name],
                env=env, check=True
            )

            subprocess.run(
                ["createdb", "-h", self.host, "-p", self.port, "-U", self.user, self.name],
                env=env, check=True
            )

            # Restore
            subprocess.run(
                ["pg_restore", "-h", self.host, "-p", self.port, "-U", self.user, "-d", self.name, file_path],
                env=env, check=True
            )

            await misc_manager.broadcast_json({
                "type": "normal",
                "text": "Recovery Sucessful"
            })
        
        except Exception as e:
            await misc_manager.broadcast_json({
                "type": "error",
                "text": f"Failed Recovery: {e}"
            })

        finally:

            await misc_manager.broadcast_json({
                "type": "normal",
                "text": "DB Pool Connecting..."
            })

            try:
                self.pool = await asyncpg.create_pool(
                    host=self.host,
                    port=int(self.port),
                    database=self.name,
                    user=self.user,
                    password=self.password,
                    min_size=1,
                    max_size=100,
                )

                await misc_manager.broadcast_json({
                    "type": "normal",
                    "text": "DB Pool Connected"
                })

                self.devices.clear()
                self.history.clear()
                self.current_session_id = None


            except Exception as e:
                await misc_manager.broadcast_json({
                    "type": "error",
                    "text": "DB Pool Failed to Connect... Container needs restarting."
                })




    def create_backup(self):
        backup_dir = Path("/db_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.fromtimestamp(self.get_time(), tz=timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
        db = os.environ["PGDATABASE"]
        out = backup_dir / f"{db}_{ts}.dump"

        cmd = [
            "pg_dump",
            "-h", os.environ.get("PGHOST", "database"),
            "-p", os.environ.get("PGPORT", "5432"),
            "-U", os.environ["PGUSER"],
            "-d", db,
            "-F", "c",
            "-f", str(out),
        ]
        env = {**os.environ, "PGPASSWORD": os.environ["PGPASSWORD"]}
        subprocess.run(cmd, check=True, env=env)
        return str(out)

    async def get_latest_imu(self):

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *
                FROM imu_measurement
                ORDER BY recorded_at DESC
                LIMIT 5
            """)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data

    async def get_latest_camera(self):

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *
                FROM image_detection
                ORDER BY recorded_at DESC
                LIMIT 5
            """)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data

    async def get_latest_robot(self):

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *
                FROM robot
                ORDER BY recorded_at DESC
                LIMIT 5
            """)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data

    async def retrieve_imu(self, session_label):

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT imu.*
                FROM imu_measurement AS imu
                JOIN session AS s ON imu.session_id = s.id
                WHERE s.label = $1
            """, session_label)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data
    
    async def retrieve_camera(self, session_label):
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT img.*
                FROM image_detection AS img
                JOIN session AS s ON img.session_id = s.id
                WHERE s.label = $1
            """, session_label)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data

    async def retrieve_robot(self, session_label): 
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT robt.*
                FROM robot AS robt
                JOIN session AS s ON robt.session_id = s.id
                WHERE s.label = $1
            """, session_label)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data
    
    async def retrieve_sessions(self): 
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT label
                FROM session
            """)
        
        # Convert to json
        data = [dict(r) for r in rows]

        return data

    
    async def get_or_create_device_id(self, device_label, category, ip="0.0.0.0") -> int:
        
        # Check if in Cache
        if device_label in self.devices:
            await self.insert_session_device(self.devices[device_label])
            return self.devices[device_label]

        # Search DB
        device_id = await self.check_device(device_label)

        # If does not exist, create a new device
        if device_id is None:
            device_id = await self.insert_device(device_label, category, ip)

        # Cache and Return id
        self.devices[device_label] = device_id

        # Insert combo
        await self.insert_session_device(self.devices[device_label])

        return device_id

    async def insert_robot_batch(self, batch):

        session_id = await self.get_latest_session()

        # If session doesn't exist, throw error
        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        # Get device ID & Session ID
        device_id = await self.get_or_create_device_id("main", "robot")

        insert_time = self.get_time()

        records = [
            (
                d["ts"], d["joint1"], d["joint2"], d["joint3"], d["joint4"], d["joint5"], d["joint6"],
                d["x"], d["y"], d["z"], d["w"], d["p"], d["r"], d["recorded_at"],
                self.get_time(), device_id, session_id
            )
            for d in batch
        ]

        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.executemany(
                    """INSERT INTO robot (
                        ts_epoch, joint_1, joint_2, joint_3, joint_4, joint_5, joint_6,
                        x, y, z, w, p, r, recorded_at, ingested_at, device_id, session_id
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17
                    )""",
                    records
                )




    async def insert_robot_data(self, ts_int, j1, j2, j3, j4, j5, j6, x, y, z, w, p, r, recorded_at):
        
        session_id = await self.get_latest_session()

        # If session doesn't exist, throw error
        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        # Get device ID & Session ID
        device_id = await self.get_or_create_device_id("main", "robot")

        # Insert into robot table
        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.execute(
                    "INSERT INTO robot (ts_epoch, joint_1, joint_2, joint_3, joint_4, joint_5, joint_6, x, y, z, w, p, r, recorded_at, ingested_at, device_id, session_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)",
                    ts_int, j1, j2, j3, j4, j5, j6, x, y, z, w, p, r, recorded_at, self.get_time(), device_id, session_id
                )

    async def insert_imu_batch(self, batch):
        session_id = await self.get_latest_session()

        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                records = []
                for d in batch:
                    device_id = await self.get_or_create_device_id(d["device_label"], "imu")
                    
                    records.append((
                        device_id, session_id,
                        d["accel_x"], d["accel_y"], d["accel_z"],
                        d["gyro_x"], d["gyro_y"], d["gyro_z"],
                        d["mag_x"], d["mag_y"], d["mag_z"],
                        d["yaw"], d["pitch"], d["roll"],
                        d["recorded_at"], self.get_time()
                    ))

                await conn.executemany("""
                    INSERT INTO imu_measurement (
                        device_id, session_id,
                        accel_x, accel_y, accel_z,
                        gyro_x, gyro_y, gyro_z,
                        mag_x, mag_y, mag_z,
                        yaw, pitch, roll,
                        recorded_at, ingested_at
                    )
                    VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16
                    )
                """, records)



    async def insert_imu_data(self, device_label, recorded_at, accel_x, accel_y, accel_z, gryo_x, gryo_y, gryo_z, mag_x, mag_y, mag_z, yaw, pitch, roll):

        session_id = await self.get_latest_session()

        # If session doesn't exist, throw error
        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        # Get device ID & Session ID
        device_id = await self.get_or_create_device_id(device_label, "imu")

        # Insert into imu table
        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.execute(
                    "INSERT INTO imu_measurement (device_id, session_id, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, mag_x, mag_y, mag_z, yaw, pitch, roll, recorded_at, ingested_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)",
                    device_id, session_id, accel_x, accel_y, accel_z, gryo_x, gryo_y, gryo_z, mag_x, mag_y, mag_z, yaw, pitch, roll, recorded_at, self.get_time()
                )

    async def insert_camera_batch(self, batch):

        session_id = await self.get_latest_session()

        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.executemany("""
                    INSERT INTO image_detection (
                        frame_idx, marker_idx, rvec_x, rvec_y, rvec_z,
                        tvec_x, tvec_y, tvec_z, image_path,
                        recorded_at, device_id, session_id, ingested_at
                    )
                    VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13
                    )
                """, [
                    (
                        d["frame_idx"], d["marker_idx"],
                        d["rvec_x"], d["rvec_y"], d["rvec_z"],
                        d["tvec_x"], d["tvec_y"], d["tvec_z"],
                        d["image_path"], d["recorded_at"],
                        await self.get_or_create_device_id(d["device_label"], "camera"),
                        session_id, self.get_time()
                    )
                    for d in batch
                ])


    # Insert into Camera Table in DB
    async def insert_camera_data(self, device_label, frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at):
        
        session_id = await self.get_latest_session()

        # If session doesn't exist, throw error
        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        # Get device ID & Session ID
        device_id = await self.get_or_create_device_id(device_label, "camera")

        # Insert into image detection
        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.execute(
                    "INSERT INTO image_detection (frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at, device_id, session_id, ingested_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)",
                    frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at, device_id, session_id, self.get_time()
                )

    # Insert into session device
    async def is_in_session_device(self, device_id, session_id):

        # Check cache
        if (device_id, session_id) in self.history:
            return True

        async with self.pool.acquire() as conn:

            return await conn.fetchval(
                "SELECT 1 FROM session_device WHERE device_id=$1 AND session_id=$2",
                device_id, session_id
            ) is not None

    # Insert into session device
    async def insert_session_device(self, device_id): 

        session_id = await self.get_latest_session()

        # Check if already inserted
        if await self.is_in_session_device(device_id, session_id):
            return

        # Insert
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO session_device (device_id, session_id)
                VALUES ($1, $2)
                ON CONFLICT (device_id, session_id) DO NOTHING
                RETURNING device_id
                """,
                device_id, session_id
            )

        # Update cache
        if row is not None:
            self.history.add((device_id, session_id))
        

    # Return the device_id if found or None 
    async def check_device(self, device_label) -> int | None:

        async with self.pool.acquire() as conn:

            device_id = await conn.fetchval(
                "SELECT id FROM device WHERE label = $1",
                device_label
            )

        return device_id

    # Return True if session label already exists
    async def existing_session(self, label):

        async with self.pool.acquire() as conn:

            found = await conn.fetchval(
                "SELECT label FROM session WHERE label = $1",
                label
            )

        return found is not None

    # Call to create a new session in DB & update current session
    async def create_session(self, label):

        session_id = await self.get_latest_session()

        # Ensure the session doesn't already exist
        if await self.existing_session(label):
            raise ExistingSessionLabel(f"Session label [{label}] already exist. Please select another one.")

        async with self.pool.acquire() as conn:

            session_id = await conn.fetchval(
                """
                INSERT INTO session (label, started_at) VALUES ($1, $2) RETURNING id
                """,
                label, self.get_time()
            )

        self.current_session_id = session_id

    # Call to end the current active session
    async def end_session(self):

        session_id = await self.get_latest_session()

        # Ensure a session is active
        if not session_id:
            raise SessionNotStarted("No active sesssions. You need to start one first.")
        
        # Update record
        async with self.pool.acquire() as conn:

            await conn.execute(
                """
                UPDATE "session"
                SET ended_at = $1
                WHERE id = $2
                """,
                self.get_time(),
                session_id
            )
        
        self.current_session_id = None

    # Inserts a new device into the DB & Return the id
    async def insert_device(self, label, category, ip_address) -> int:

        async with self.pool.acquire() as conn:

            return await conn.fetchval(
                """
                INSERT INTO device (label, category, ip_address, registered_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (label) DO UPDATE SET label = EXCLUDED.label
                RETURNING id
                """,
                label, category, ip_address, self.get_time()
            )
