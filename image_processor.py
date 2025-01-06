import io
from typing import Optional
import aiohttp
from PIL import Image
import asyncio  # Add this line
from config import MAX_FILE_SIZE, IMAGE_DOWNLOAD_TIMEOUT
from utils import setup_logger

logger = setup_logger(__name__)

class ImageProcessor:
    @staticmethod
    async def resize_image(image_url: str, max_size_bytes: int = MAX_FILE_SIZE) -> Optional[io.BytesIO]:
        # ... rest of the function ...
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=IMAGE_DOWNLOAD_TIMEOUT) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download image. Status: {resp.status}")
                        return None
                    image_data = await resp.read()

            image = Image.open(io.BytesIO(image_data))
            
            quality = 95
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality)
            
            while output.tell() > max_size_bytes and quality > 10:
                output = io.BytesIO()
                quality -= 5
                image.save(output, format='JPEG', quality=quality)
            
            if output.tell() > max_size_bytes:
                width, height = image.size
                while output.tell() > max_size_bytes and (width > 100 and height > 100):
                    width = int(width * 0.9)
                    height = int(height * 0.9)
                    resized_image = image.resize((width, height), Image.LANCZOS)
                    output = io.BytesIO()
                    resized_image.save(output, format='JPEG', quality=quality)

            if output.tell() > max_size_bytes:
                raise ValueError("Image is still too large after resizing")

            output.seek(0)
            return output
        except asyncio.TimeoutError:
            logger.error(f"Timeout while downloading image: {image_url}")
            raise ValueError("Image download timed out")
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise ValueError(f"Error processing image: {str(e)}")