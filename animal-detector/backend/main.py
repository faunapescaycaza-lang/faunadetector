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

            # Draw name (top-left, outside the box)
            name_text = box.name
            name_text_bbox_coords = draw.textbbox((box.x1, box.y1), name_text, font=font)
            name_text_width = name_text_bbox_coords[2] - name_text_bbox_coords[0]
            name_text_height = name_text_bbox_coords[3] - name_text_bbox_coords[1]

            name_x = box.x1
            name_y = box.y1 - name_text_height - 5 # 5 pixels padding above
            if name_y < 0: # If text goes above image, put it inside the box
                name_y = box.y1 + 5
            
            draw.rectangle([name_x, name_y, name_x + name_text_width, name_y + name_text_height], fill=bg_color)
            draw.text((name_x, name_y), name_text, fill=text_color, font=font)

            # Draw date (top-right, outside the box, aligned with name_y)
            if box.date:
                date_text = f"Fecha: {box.date}"
                date_text_bbox_coords = draw.textbbox((box.x2, box.y1), date_text, font=font)
                date_text_width = date_text_bbox_coords[2] - date_text_bbox_coords[0]
                date_text_height = date_text_bbox_coords[3] - date_text_bbox_coords[1]

                date_x = box.x2 - date_text_width # Align right
                date_y = name_y # Align with name_y

                draw.rectangle([date_x, date_y, date_x + date_text_width, date_y + date_text_height], fill=bg_color)
                draw.text((date_x, date_y), date_text, fill=text_color, font=font)


            # Draw latitude and longitude (inside the box, top-right)
            if annotation.latitude is not None and annotation.longitude is not None:
                coords_text = f"Lat: {annotation.latitude:.4f}, Lon: {annotation.longitude:.4f}"
                coords_text_bbox_coords = draw.textbbox((box.x2, box.y1), coords_text, font=font)
                coords_text_width = coords_text_bbox_coords[2] - coords_text_bbox_coords[0]
                coords_text_height = coords_text_bbox_coords[3] - coords_text_bbox_coords[1]

                coords_x = box.x2 - coords_text_width - 5 # 5 pixels padding from right
                coords_y = box.y1 + 5 # 5 pixels padding from top, inside box

                # Ensure it doesn't overlap with name/date if box is very small and name/date are inside
                if name_y >= box.y1 and coords_y < name_y + name_text_height: # if name is inside and overlaps
                    coords_y = name_y + name_text_height + 5

                draw.rectangle([coords_x, coords_y, coords_x + coords_text_width, coords_y + coords_text_height], fill=bg_color)
                draw.text((coords_x, coords_y), coords_text, fill=text_color, font=font)


    # Encode the annotated image back to base64
    buffered = io.BytesIO()
    original_image.save(buffered, format="PNG") # Save as PNG
    encoded_annotated_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"annotated_image": f"data:image/png;base64,{encoded_annotated_image}"}

@app.get("/")
def read_root():
    return {"Hello": "World"}