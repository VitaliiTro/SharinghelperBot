import asyncpg
import os
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

# Отримуємо URL бази даних з Railway
DATABASE_URL = os.getenv("DATABASE_URL")

async def connect_db():
    """Підключення до бази даних PostgreSQL."""
    try:
        return await asyncpg.create_pool(DATABASE_URL)
    except Exception as e:
        print(f"❌ Помилка підключення до БД: {e}")
        return None

async def create_tables():
    """Створення таблиць у базі даних."""
    pool = await connect_db()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    product TEXT NOT NULL,
                    quantity INT NOT NULL,
                    order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        await pool.close()
        print("✅ Таблиці створено успішно!")
