import os, asyncpg

class MissingDatabaseDetails(Exception):

    def __init__(self, message, data=None):
        super().__init__(message)
        self.data = data
        self.message = message

class Database:

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

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

    async def insert_device(self, label, category, ip_address):
        
        async with self.pool.acquire() as conn:

            async with conn.transaction():

                await conn.execute(
                    "INSERT INTO device (label, category, ip_address) VALUES ($1, $2, $3)",
                    label, category, ip_address
                )

        