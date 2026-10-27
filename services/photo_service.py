import os
import uuid
import datetime
from pathlib import Path
from PIL import Image, ImageOps
import exifread
import cv2
import numpy as np

from config import Config

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _convert_to_degrees(value):
    """Helper function to convert GPS coordinates stored in EXIF to degrees in float."""
    try:
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def extract_exif(image_path: str):
    """
    Extracts latitude, longitude, and timestamp from image EXIF metadata.
    Returns:
        dict: {
            "lat": float or None,
            "lng": float or None,
            "taken_at": datetime or None
        }
    """
    result = {"lat": None, "lng": None, "taken_at": None}
    
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            
        lat_tag = tags.get("GPS GPSLatitude")
        lat_ref = tags.get("GPS GPSLatitudeRef")
        lng_tag = tags.get("GPS GPSLongitude")
        lng_ref = tags.get("GPS GPSLongitudeRef")
        
        if lat_tag and lat_ref and lng_tag and lng_ref:
            lat = _convert_to_degrees(lat_tag)
            lng = _convert_to_degrees(lng_tag)
            
            if lat is not None and lng is not None:
                if str(lat_ref).strip().upper() == "S":
                    lat = -lat
                if str(lng_ref).strip().upper() == "W":
                    lng = -lng
                result["lat"] = round(lat, 6)
                result["lng"] = round(lng, 6)
                
        # Timestamp
        date_str = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if date_str:
            try:
                result["taken_at"] = datetime.datetime.strptime(str(date_str).strip(), "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
                
    except Exception as e:
        print(f"Error reading EXIF from {image_path}: {e}")
        
    return result


def blur_faces_and_plates(cv_image):
    """
    Detects faces and vehicle plates using OpenCV Haar Cascades and applies Gaussian blur
    for privacy protection (UU PDP compliance & PRD Section 13/14).
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # 1. Frontal face cascade
    face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if os.path.exists(face_cascade_path):
        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        for (x, y, w, h) in faces:
            sub_face = cv_image[y:y+h, x:x+w]
            # Gaussian blur face region
            ksize = (w // 3) | 1
            if ksize >= 3:
                cv_image[y:y+h, x:x+w] = cv2.GaussianBlur(sub_face, (ksize, ksize), 30)

    # 2. Plate cascade (if available) or lower-third car detection
    plate_cascade_path = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
    if os.path.exists(plate_cascade_path):
        plate_cascade = cv2.CascadeClassifier(plate_cascade_path)
        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=3, minSize=(40, 20))
        for (x, y, w, h) in plates:
            sub_plate = cv_image[y:y+h, x:x+w]
            ksize = (w // 3) | 1
            if ksize >= 3:
                cv_image[y:y+h, x:x+w] = cv2.GaussianBlur(sub_plate, (ksize, ksize), 30)
                
    return cv_image


def process_and_save_photo(file_storage):
    """
    Saves an uploaded photo in two versions:
    1. Original: with full EXIF (stored in uploads/photos/original/)
    2. Public: EXIF stripped, faces & plates blurred (stored in uploads/photos/public/)
    Returns:
        dict: {
            "file_name": str,
            "public_name": str,
            "width": int,
            "height": int,
            "exif": dict
        }
    """
    ext = file_storage.filename.rsplit(".", 1)[1].lower() if "." in file_storage.filename else "jpg"
    unique_id = uuid.uuid4().hex
    original_name = f"orig_{unique_id}.{ext}"
    public_name = f"pub_{unique_id}.jpg"
    
    original_path = Config.UPLOAD_FOLDER_ORIGINAL / original_name
    public_path = Config.UPLOAD_FOLDER_PUBLIC / public_name
    
    # Ensure dirs exist
    Config.UPLOAD_FOLDER_ORIGINAL.mkdir(parents=True, exist_ok=True)
    Config.UPLOAD_FOLDER_PUBLIC.mkdir(parents=True, exist_ok=True)
    
    # Save original
    file_storage.save(str(original_path))
    
    # Extract EXIF from original
    exif_data = extract_exif(str(original_path))
    
    # Open with PIL to get dimensions and normalize rotation
    with Image.open(original_path) as img:
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        # Convert to RGB if necessary (e.g. RGBA or WebP)
        rgb_img = img.convert("RGB")
        
        # Convert PIL to OpenCV BGR for blurring
        cv_img = cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)
        
    # Apply face & plate blur
    blurred_cv = blur_faces_and_plates(cv_img)
    
    # Resize public image if too large (e.g. max 1600px width/height for fast loading)
    max_dim = 1600
    h, w = blurred_cv.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        blurred_cv = cv2.resize(blurred_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        
    # Save public image without EXIF metadata (cv2.imwrite doesn't write EXIF)
    cv2.imwrite(str(public_path), blurred_cv, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    
    return {
        "file_name": original_name,
        "public_name": public_name,
        "width": width,
        "height": height,
        "exif": exif_data
    }
