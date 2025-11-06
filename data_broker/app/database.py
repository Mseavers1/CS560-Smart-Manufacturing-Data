import os, asyncpg
from ntp_facade_smr import TimeBrokerFacade
from pathlib import Path
from datetime import datetime, timezone
import subprocess
from package.client import Client

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

class Database:

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.devices = {}
        self.current_session_id = None
        self.history = set()

        robot_client = Client("192.168.1.76", Client.ROBOT, "minipc2")
        imu_client =  Client("192.168.1.76", Client.IMU, "minipc2")
        camera_client =  Client("192.168.1.76", Client.CAMERA, "minipc2")

    def get_time(self):
        try:
            tbroker = TimeBrokerFacade(ntp_server_ip = '192.168.1.76')
        
            return tbroker.get_synchronized_time()

        except(ValueError, IOError) as e:
            print("error")
            print (e)

    def create_backup(self):
        backup_dir = Path("/db_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.fromtimestamp(self.get_time(), tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
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

    @classmethod
    async def create(cls, min_size=1, max_size=10):
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        missing = [k for k, v in {
            "DB_HOST": host, "DB_PORT": port, "DB_NAME": name,
            "DB_USER": user, "DB_PASSWORD": password
        }.items() if not v]

        # Check to ensure that all connection details are available
        if missing:
            raise MissingDatabaseDetails(f"Missing envs: {', '.join(missing)}")

        pool = await asyncpg.create_pool(
            host=host, port=int(port), database=name, user=user, password=password,
            min_size=min_size, max_size=max_size
        )

        return cls(pool)

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

    async def insert_robot_data(self, ts_int, j1, j2, j3, j4, j5, j6, x, y, z, w, p, r, recorded_at):
        
        session_id = self.current_session_id

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
                    ts_int, j1, j2, j3, j4, j5, j6, x, y, z, w, p, r, recorded_at, self.get_time(), device_id, self.current_session_id
                )


    async def insert_imu_data(self, device_label, recorded_at, accel_x, accel_y, accel_z, gryo_x, gryo_y, gryo_z, mag_x, mag_y, mag_z, yaw, pitch, roll):

        session_id = self.current_session_id

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

    # Insert into Camera Table in DB
    async def insert_camera_data(self, device_label, frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at):
        
        session_id = self.current_session_id

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

        session_id = self.current_session_id

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

        # Ensure the session doesn't already exist
        if await self.existing_session(label):
            raise ExistingSessionLabel(f"Session label [{label}] already exist. Please select another one.")

        async with self.pool.acquire() as conn:

            self.current_session_id = await conn.fetchval(
                """
                INSERT INTO session (label, started_at)
                VALUES ($1, $2)
                ON CONFLICT (label) DO UPDATE SET label = EXCLUDED.label
                RETURNING id
                """,
                label, self.get_time()
            )

    # Call to end the current active session
    async def end_session(self):

        # Ensure a session is active
        if not self.current_session_id:
            raise SessionNotStarted("No active sesssions. You need to start one first.")
        
        # Update record
        async with self.pool.acquire() as conn:

            async with self.pool.acquire() as conn:

                await conn.execute(
                    """
                    UPDATE "session"
                    SET ended_at = $1
                    WHERE id = $2
                    """,
                    self.get_time(),
                    self.current_session_id
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

        