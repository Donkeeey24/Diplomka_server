from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncpg
import os
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from auth import authenticate_user, create_access_token, get_current_user

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "postgres"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "postgres"),
    "database": os.getenv("PG_DATABASE", "postgres"),
}
pool = None

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=120)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(**DB_CONFIG)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

def parse_time(ts):
    if ts is None:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M")
        except Exception:
            return None

@app.get("/data")
async def get_data(
    from_time: Optional[str] = Query(None),
    to_time: Optional[str] = Query(None),
    sensor_uuid: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    where = []
    params = []
    from_dt = parse_time(from_time)
    to_dt = parse_time(to_time)
    if from_dt:
        where.append("time >= $%d" % (len(params)+1))
        params.append(from_dt)
    if to_dt:
        where.append("time <= $%d" % (len(params)+1))
        params.append(to_dt)
    if sensor_uuid:
        where.append("sensor_uuid = $%d" % (len(params)+1))
        params.append(sensor_uuid)
    sql = "SELECT * FROM sensor_data"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY time DESC LIMIT 500;"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]

@app.get("/sensors")
async def get_sensors(current_user: dict = Depends(get_current_user)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT sensor_uuid FROM sensor_data ORDER BY sensor_uuid;")
        return [row["sensor_uuid"] for row in rows]

@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"msg": f"Hello {current_user['username']}"}

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# --- NOVÉ ENDPOINTY PRO SPRÁVU METADAT SENZORŮ ---

@app.get("/sensor-metadata")
async def get_sensor_metadata(current_user: dict = Depends(get_current_user)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM sensor_metadata")
        return [dict(row) for row in rows]

@app.post("/sensor-metadata/{sensor_uuid}")
async def update_sensor_metadata(
    sensor_uuid: str,
    name: str = Body(...),
    value_type: str = Body(...),
    unit: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sensor_metadata(sensor_uuid, name, value_type, unit)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT(sensor_uuid) DO UPDATE
            SET name = EXCLUDED.name,
                value_type = EXCLUDED.value_type,
                unit = EXCLUDED.unit
            """,
            sensor_uuid, name, value_type, unit
        )
    return {"ok": True}