import fastapi
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from pydantic import BaseModel
from typing import List
import base64
import time

app = fastapi.FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_FILE = "annotations.db"
IMAGE_DIR = "annotated_images"

def init_db():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_filename TEXT NOT NULL,
            x1 REAL NOT NULL,
            y1 REAL NOT NULL,
            x2 REAL NOT NULL,
            y2 REAL NOT NULL,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            latitude REAL,
            longitude REAL
        )
    """)
    conn.commit()
    conn.close()

class Box(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    name: str
    date: str

class Annotation(BaseModel):
    image: str  # base64 encoded image
    boxes: List[Box]
    latitude: float | None = None
    longitude: float | None = None

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/save_annotation/")
async def save_annotation(annotation: Annotation):
    # Decode and save the image
    image_data = base64.b64decode(annotation.image.split(",")[1])
    image_filename = f"{int(time.time())}.png"
    image_path = os.path.join(IMAGE_DIR, image_filename)
    with open(image_path, "wb") as f:
        f.write(image_data)

    # Save annotations to the database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for box in annotation.boxes:
        cursor.execute("""
            INSERT INTO annotations (image_filename, x1, y1, x2, y2, name, date, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (image_filename, box.x1, box.y1, box.x2, box.y2, box.name, box.date, annotation.latitude, annotation.longitude))
    conn.commit()
    conn.close()

    return {"message": "Annotation saved successfully"}

@app.get("/")
def read_root():
    return {"Hello": "World"}
