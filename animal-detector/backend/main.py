import fastapi
from fastapi.middleware.cors import CORSMiddleware
import io
import base64
import os # Added for environment variables
import datetime # Added for handling dates
from typing import List
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session # Added for dependency injection

app = fastapi.FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SQLAlchemy Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # During local development or testing, if you don't have Supabase set up,
    # you might want to print a warning or use a default (e.g., SQLite for local dev)
    # For Vercel deployment, this should always be set.
    print("WARNING: DATABASE_URL environment variable is not set. Database features will not work.")
    # raise ValueError("DATABASE_URL environment variable is not set.") # Commented out for local testing flexibility

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Model for Annotation Entries
class AnnotationEntry(Base):
    __tablename__ = "annotation_entries"
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, index=True) # ID único para cada imagen
    box_name = Column(String, index=True) # Nombre del box
    box_date = Column(String) # Fecha del box
    annotation_latitude = Column(Float) # Latitud de la anotación general
    annotation_longitude = Column(Float) # Longitud de la anotación general
    created_at = Column(DateTime, default=datetime.datetime.now)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_tables():
    Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup_event():
    create_db_tables()


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


@app.post("/annotate_image_for_download/")
async def annotate_image_for_download(annotation: Annotation, db: Session = Depends(get_db)):
    # Decode base64 image
    header, encoded_image = annotation.image.split(",", 1)
    image_data = base64.b64decode(encoded_image)
    image_bytes_io = io.BytesIO(image_data)
    original_image = Image.open(image_bytes_io).convert("RGB") # Ensure RGB for drawing

    draw = ImageDraw.Draw(original_image)
    
    font = ImageFont.load_default()

    # Define colors
    box_color = (255, 0, 0) # Red
    text_color = (255, 255, 255) # White
    bg_color = (0, 0, 0, 128) # Semi-transparent black for text background

    # Generate a unique ID for this image (to link annotations in DB)
    image_id_gen = f"img_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"


    # Draw boxes and their associated info
    for i, box in enumerate(annotation.boxes):
        # Draw the bounding box
        draw.rectangle([box.x1, box.y1, box.x2, box.y2], outline=box_color, width=2)

        # --- Draw Name (top-left, outside the box) ---
        name_text = box.name
        name_text_bbox_coords = draw.textbbox((0,0), name_text, font=font) # Use (0,0) for size calculation
        name_text_width = name_text_bbox_coords[2] - name_text_bbox_coords[0]
        name_text_height = name_text_bbox_coords[3] - name_text_bbox_coords[1]

        name_x = box.x1
        name_y = box.y1 - name_text_height - 5 # 5 pixels padding above
        if name_y < 0: # If text goes above image, put it inside the box
            name_y = box.y1 + 5

        # Draw background and text for name
        draw.rectangle([name_x, name_y, name_x + name_text_width + 5, name_y + name_text_height + 5], fill=bg_color) # Add padding to background
        draw.text((name_x + 2, name_y + 2), name_text, fill=text_color, font=font) # Add padding to text


        # --- Draw Date (top-right, outside the box, aligned with name_y) ---
        date_text_y_offset = 0 # Offset if name is inside the box
        if name_y == box.y1 + 5: # If name was placed inside, date should be slightly below name.
            date_text_y_offset = name_text_height + 5 # Place below name if name is inside

        if box.date:
            date_text = f"Fecha: {box.date}"
            date_text_bbox_coords = draw.textbbox((0,0), date_text, font=font)
            date_text_width = date_text_bbox_coords[2] - date_text_bbox_coords[0]
            date_text_height = date_text_bbox_coords[3] - date_text_bbox_coords[1]

            date_x = box.x2 - date_text_width - 5 # 5 pixels padding from right
            date_y = name_y + date_text_y_offset # Align with name_y, or offset

            # Draw background and text for date
            draw.rectangle([date_x, date_y, date_x + date_text_width + 5, date_y + date_text_height + 5], fill=bg_color)
            draw.text((date_x + 2, date_y + 2), date_text, fill=text_color, font=font)


        # --- Draw Latitude and Longitude (inside the box, top-right) ---
        if annotation.latitude is not None and annotation.longitude is not None:
            coords_text = f"Lat: {annotation.latitude:.4f}, Lon: {annotation.longitude:.4f}"
            coords_text_bbox_coords = draw.textbbox((0,0), coords_text, font=font)
            coords_text_width = coords_text_bbox_coords[2] - coords_text_bbox_coords[0]
            coords_text_height = coords_text_bbox_coords[3] - coords_text_bbox_coords[1]

            coords_x = box.x2 - coords_text_width - 5 # 5 pixels padding from right, inside box
            coords_y = box.y1 + 5 # 5 pixels padding from top, inside box

            # Draw background and text for coordinates
            draw.rectangle([coords_x, coords_y, coords_x + coords_text_width + 5, coords_y + coords_text_height + 5], fill=bg_color)
            draw.text((coords_x + 2, coords_y + 2), coords_text, fill=text_color, font=font)

        # --- Save annotation data to the database ---
        db_entry = AnnotationEntry(
            image_id=image_id_gen,
            box_name=box.name,
            box_date=box.date,
            annotation_latitude=annotation.latitude,
            annotation_longitude=annotation.longitude
        )
        db.add(db_entry)
    
    db.commit() # Commit all entries for this image
    # db.refresh(db_entry) # No need to refresh here, as we are returning the image.

    # Encode the annotated image back to base64
    buffered = io.BytesIO()
    original_image.save(buffered, format="PNG") # Save as PNG
    encoded_annotated_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"annotated_image": f"data:image/png;base64,{encoded_annotated_image}", "message": "Annotation saved to DB and image processed."}

@app.get("/")
def read_root():
    return {"Hello": "World"}