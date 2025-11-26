import fastapi
from fastapi.middleware.cors import CORSMiddleware
import io
import base64
from typing import List
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont

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
async def annotate_image_for_download(annotation: Annotation):
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

    # Draw boxes and names
    for i, box in enumerate(annotation.boxes):
        # Draw rectangle
        draw.rectangle([box.x1, box.y1, box.x2, box.y2], outline=box_color, width=2)

        # Draw text with a background
        text = box.name
        # Calculate text bounding box to draw background
        text_bbox_coords = draw.textbbox((box.x1, box.y1), text, font=font)
        text_width = text_bbox_coords[2] - text_bbox_coords[0]
        text_height = text_bbox_coords[3] - text_bbox_coords[1]

        # Adjust position to be above the box
        text_x = box.x1
        text_y = box.y1 - text_height - 5 # 5 pixels padding above
        
        # If text goes above image, place it inside the box
        if text_y < 0:
            text_y = box.y1 + 5 # 5 pixels padding inside

        # Draw background rectangle for text
        draw.rectangle([text_x, text_y, text_x + text_width, text_y + text_height], fill=bg_color)
        draw.text((text_x, text_y), text, fill=text_color, font=font)


    # Draw latitude, longitude, and date (using date from the first box for simplicity)
    info_text_lines = []
    if annotation.latitude is not None and annotation.longitude is not None:
        info_text_lines.append(f"Lat: {annotation.latitude:.4f}, Lon: {annotation.longitude:.4f}")
    if annotation.boxes and annotation.boxes[0].date:
         info_text_lines.append(f"Date: {annotation.boxes[0].date}")

    if info_text_lines:
        info_text = "\n".join(info_text_lines)
        info_x = 10
        info_y = 10
        
        # Draw text with a background
        info_text_bbox_coords = draw.textbbox((info_x, info_y), info_text, font=font)
        info_text_width = info_text_bbox_coords[2] - info_text_bbox_coords[0]
        info_text_height = info_text_bbox_coords[3] - info_text_bbox_coords[1]
        
        draw.rectangle([info_x, info_y, info_x + info_text_width, info_y + info_text_height], fill=bg_color)
        draw.text((info_x, info_y), info_text, fill=text_color, font=font)

    # Encode the annotated image back to base64
    buffered = io.BytesIO()
    original_image.save(buffered, format="PNG") # Save as PNG
    encoded_annotated_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"annotated_image": f"data:image/png;base64,{encoded_annotated_image}"}

@app.get("/")
def read_root():
    return {"Hello": "World"}