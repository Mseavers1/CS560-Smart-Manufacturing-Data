import os, asyncpg

class SessionNotStarted(Exception):

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
    
    async def get_or_create_device_id(self, device_label, category, ip="0.0.0.0") -> int:
        
        # Check if in Cache
        if device_label in self.devices:
            return self.devices[device_label]

        # Search DB
        device_id = await self.check_device(device_label)

        # If does not exist, create a new device
        if device_id is None:
            device_id = await self.insert_device(device_label, category, ip)

        # Cache and Return id
        self.devices[device_label] = device_id

        return device_id

    # Insert into Camera Table in DB
    async def insert_camera_data(self, device_label, frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at):
        
        # Get device ID & Session ID
        device_id = await self.get_or_create_device_id(device_label, "camera")

        session_id = self.current_session_id

        # Ensure the device is tied to a session

        # If session doesn't exist, throw error
        if not session_id:
            raise SessionNotStarted("No current active session. Run a GET to start a new session.")

        # Insert into image detection
        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.execute(
                    "INSERT INTO image_detection (frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at, device_id, session_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
                    frame_idx, marker_idx, rvec_x, rvec_y, rvec_z, tvec_x, tvec_y, tvec_z, image_path, recorded_at, device_id, session_id
                )

    # Return the device_id if found or None 
    async def check_device(self, device_label) -> int | None:

        async with self.pool.acquire() as conn:

            device_id = await conn.fetchval(
                "SELECT device_id FROM device WHERE label = $1",
                device_label
            )

        return device_id


    # Call to create a new session in DB & update current session
    async def create_session(self, label):
        
        async with self.pool.acquire() as conn:

            self.current_session_id = await conn.fetchval(
                """
                INSERT INTO session (label)
                VALUES ($1)
                ON CONFLICT (label) DO UPDATE SET label = EXCLUDED.label
                RETURNING session_id
                """,
                label
            )

    async def end_session(self, end_time):

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
                    WHERE session_id = $2
                    """,
                    datetime.now(timezone.utc),  # TODO: Change with end_time
                    self.current_session_id
                )
        
        self.current_session_id = None

    # Inserts a new device into the DB & Return the id
    async def insert_device(self, label, category, ip_address) -> int:

        async with self.pool.acquire() as conn:

            return await conn.fetchval(
                """
                INSERT INTO device (label, category, ip_address)
                VALUES ($1, $2, $3)
                ON CONFLICT (label) DO UPDATE SET label = EXCLUDED.label
                RETURNING device_id
                """,
                label, category, ip_address
            )

        