import os
from google import genai
from google.genai import types
import io
from utils import setup_logger

logger = setup_logger(__name__)

# --- Configuration ---
try:
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
except KeyError:
    raise ValueError("GEMINI_API_KEY environment variable not set. Please add it to your .env file.")

async def generate_shirt_designs(user_prompt: str, side: str = "front"):
    """
    Generates a single t-shirt design image using Gemini 2.5 Flash.

    Args:
        user_prompt: The user's creative direction for the design.
        side: Which side of the shirt to design - "front" or "back" (default: "front").

    Returns:
        A BytesIO object containing the generated image, or None if generation fails.
    """

    # --- Prompt Engineering ---

    if side == "front":
        # Create a detailed and specific prompt for the front of the shirt.
        prompt = (
            f"Generate a photorealistic image of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"On the chest of the shirt, there must be a high-quality, professional graphic. "
            f"This graphic must be based on the following creative description: '{user_prompt}'. "
            f"The design must also prominently and stylistically feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )
    else:  # back
        # Create a prompt for the back of the shirt.
        prompt = (
            f"Generate a photorealistic image of the back of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"Across the shoulder blades, there should be a high-quality, professional graphic. "
            f"This graphic must be based on the following creative description: '{user_prompt}'. "
            f"The design must also feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )

    try:
        logger.info(f"Generating {side} design...")

        # Use Gemini 2.5 Flash to generate the image
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="1:1"),
            ),
        )

        # Extract the image from the response
        for part in response.parts:
            if part.inline_data:
                # Get the raw image data and convert to BytesIO
                image_data = part.inline_data.data
                img_bytes = io.BytesIO(image_data)
                img_bytes.seek(0)
                logger.info(f"{side.capitalize()} design generated successfully.")
                return img_bytes

        # If we get here, no image was found in the response
        logger.error("No image data found in Gemini response.")
        return None

    except Exception as e:
        # Log the error for debugging.
        logger.error(f"An error occurred during image generation with Gemini 2.5 Flash: {e}", exc_info=True)
        return None
