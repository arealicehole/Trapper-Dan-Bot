import os
import aiohttp
import asyncio
import io
from utils import setup_logger

logger = setup_logger(__name__)

# --- Configuration ---
KIE_API_KEY = os.getenv('KIE_API_KEY')
if not KIE_API_KEY:
    logger.warning("KIE_API_KEY not set. Kie.ai features will not work.")

KIE_API_BASE = "https://api.kie.ai/api/v1/jobs"
POLL_INTERVAL = 2  # seconds between status checks
MAX_POLL_TIME = 120  # max seconds to wait for generation


async def _create_task(model: str, input_params: dict) -> str:
    """Create a generation task and return the task ID."""
    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "input": input_params
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{KIE_API_BASE}/createTask", headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Kie.ai create task failed: {resp.status} - {error_text}")
                raise Exception(f"Failed to create task: {resp.status}")

            data = await resp.json()
            if data.get("code") != 200:
                raise Exception(f"Kie.ai error: {data.get('msg')}")

            return data["data"]["taskId"]


async def _poll_task(task_id: str) -> dict:
    """Poll for task completion and return the result."""
    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}"
    }

    start_time = asyncio.get_event_loop().time()

    async with aiohttp.ClientSession() as session:
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > MAX_POLL_TIME:
                raise Exception("Task timed out waiting for completion")

            async with session.get(f"{KIE_API_BASE}/recordInfo", headers=headers, params={"taskId": task_id}) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to poll task: {resp.status}")

                data = await resp.json()
                if data.get("code") != 200:
                    raise Exception(f"Kie.ai error: {data.get('msg')}")

                task_data = data["data"]
                state = task_data.get("state")

                if state == "success":
                    import json
                    result_json = json.loads(task_data.get("resultJson", "{}"))
                    return result_json
                elif state == "fail":
                    raise Exception(f"Task failed: {task_data.get('failMsg')}")

                # Still waiting, poll again
                await asyncio.sleep(POLL_INTERVAL)


async def _download_image(url: str) -> io.BytesIO:
    """Download image from URL and return as BytesIO."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download image: {resp.status}")

            image_data = await resp.read()
            img_bytes = io.BytesIO(image_data)
            img_bytes.seek(0)
            return img_bytes


async def generate_with_pro(prompt: str, side: str = "front", reference_image_url: str = None) -> io.BytesIO:
    """
    Generate t-shirt design using Nano Banana Pro (premium model).

    Args:
        prompt: The user's creative direction for the design.
        side: Which side of the shirt to design - "front" or "back".
        reference_image_url: Optional URL of a reference image.

    Returns:
        BytesIO object containing the generated image, or None if failed.
    """
    # Build the full prompt for t-shirt design
    if side == "front":
        full_prompt = (
            f"Generate a photorealistic image of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"On the chest of the shirt, there must be a high-quality, professional graphic. "
            f"This graphic must be based on: '{prompt}'. "
            f"The design must also prominently feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )
    else:
        full_prompt = (
            f"Generate a photorealistic image of the back of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"Across the shoulder blades, there should be a high-quality, professional graphic. "
            f"This graphic must be based on: '{prompt}'. "
            f"The design must also prominently feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )

    input_params = {
        "prompt": full_prompt,
        "image_input": [reference_image_url] if reference_image_url else [],
        "aspect_ratio": "1:1",
        "resolution": "2K",
        "output_format": "png"
    }

    try:
        logger.info(f"Creating Nano Banana Pro task for {side} design...")
        task_id = await _create_task("nano-banana-pro", input_params)
        logger.info(f"Task created: {task_id}, polling for results...")

        result = await _poll_task(task_id)
        result_urls = result.get("resultUrls", [])

        if not result_urls:
            logger.error("No result URLs in response")
            return None

        logger.info(f"Downloading generated image from {result_urls[0]}")
        return await _download_image(result_urls[0])

    except Exception as e:
        logger.error(f"Error generating with Nano Banana Pro: {e}", exc_info=True)
        return None


async def generate_with_regular(prompt: str, side: str = "front", reference_image_url: str = None) -> io.BytesIO:
    """
    Generate t-shirt design using Nano Banana (standard model).
    Uses 1K resolution instead of 2K for the regular tier.

    Args:
        prompt: The user's creative direction for the design.
        side: Which side of the shirt to design - "front" or "back".
        reference_image_url: Optional URL of a reference image.

    Returns:
        BytesIO object containing the generated image, or None if failed.
    """
    # Build the full prompt for t-shirt design
    if side == "front":
        full_prompt = (
            f"Generate a photorealistic image of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"On the chest of the shirt, there must be a high-quality, professional graphic. "
            f"This graphic must be based on: '{prompt}'. "
            f"The design must also prominently feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )
    else:
        full_prompt = (
            f"Generate a photorealistic image of the back of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"Across the shoulder blades, there should be a high-quality, professional graphic. "
            f"This graphic must be based on: '{prompt}'. "
            f"The design must also prominently feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )

    input_params = {
        "prompt": full_prompt,
        "image_input": [reference_image_url] if reference_image_url else [],
        "aspect_ratio": "1:1",
        "resolution": "1K",  # Lower resolution for regular tier
        "output_format": "png"
    }

    try:
        logger.info(f"Creating Nano Banana (regular) task for {side} design...")
        task_id = await _create_task("nano-banana-pro", input_params)  # Same model, lower res
        logger.info(f"Task created: {task_id}, polling for results...")

        result = await _poll_task(task_id)
        result_urls = result.get("resultUrls", [])

        if not result_urls:
            logger.error("No result URLs in response")
            return None

        logger.info(f"Downloading generated image from {result_urls[0]}")
        return await _download_image(result_urls[0])

    except Exception as e:
        logger.error(f"Error generating with Nano Banana: {e}", exc_info=True)
        return None


async def generate_with_grok(prompt: str, side: str = "front") -> list:
    """
    Generate t-shirt design using Grok Imagine (artistic style).
    Note: Grok doesn't support reference images but returns multiple images.

    Args:
        prompt: The user's creative direction for the design.
        side: Which side of the shirt to design - "front" or "back".

    Returns:
        List of BytesIO objects containing the generated images, or None if failed.
    """
    # Build the full prompt for t-shirt design
    if side == "front":
        full_prompt = (
            f"Generate a photorealistic image of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"On the chest of the shirt, there must be a high-quality, professional graphic. "
            f"This graphic must be based on: '{prompt}'. "
            f"The design must also prominently feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )
    else:
        full_prompt = (
            f"Generate a photorealistic image of the back of a black long-sleeve t-shirt laid flat on a neutral, clean, light-grey background. "
            f"The shirt should be perfectly centered. "
            f"Across the shoulder blades, there should be a high-quality, professional graphic. "
            f"This graphic must be based on: '{prompt}'. "
            f"The design must also prominently feature the text 'Kanna Kickback 6'. "
            f"The overall style should be modern streetwear. This is a product mockup."
        )

    input_params = {
        "prompt": full_prompt,
        "aspect_ratio": "1:1"
    }

    try:
        logger.info(f"Creating Grok Imagine task for {side} design...")
        task_id = await _create_task("grok-imagine/text-to-image", input_params)
        logger.info(f"Task created: {task_id}, polling for results...")

        result = await _poll_task(task_id)
        result_urls = result.get("resultUrls", [])

        if not result_urls:
            logger.error("No result URLs in response")
            return None

        logger.info(f"Grok returned {len(result_urls)} images, downloading all...")

        # Download all images
        images = []
        for i, url in enumerate(result_urls):
            logger.info(f"Downloading image {i+1}/{len(result_urls)}")
            img = await _download_image(url)
            images.append(img)

        return images

    except Exception as e:
        logger.error(f"Error generating with Grok Imagine: {e}", exc_info=True)
        return None


async def edit_image(prompt: str, image_url: str) -> io.BytesIO:
    """
    Edit an existing image using Nano Banana Edit.

    Args:
        prompt: The editing instructions.
        image_url: URL of the image to edit.

    Returns:
        BytesIO object containing the edited image, or None if failed.
    """
    input_params = {
        "prompt": prompt,
        "image_urls": [image_url],
        "output_format": "png",
        "image_size": "1:1"
    }

    try:
        logger.info(f"Creating Nano Banana Edit task...")
        task_id = await _create_task("google/nano-banana-edit", input_params)
        logger.info(f"Task created: {task_id}, polling for results...")

        result = await _poll_task(task_id)
        result_urls = result.get("resultUrls", [])

        if not result_urls:
            logger.error("No result URLs in response")
            return None

        logger.info(f"Downloading edited image from {result_urls[0]}")
        return await _download_image(result_urls[0])

    except Exception as e:
        logger.error(f"Error editing with Nano Banana Edit: {e}", exc_info=True)
        return None


async def generate_shirt_design(prompt: str, side: str = "front", reference_image_url: str = None, model: str = "pro"):
    """
    Main entry point for generating t-shirt designs.
    Routes to the appropriate model based on user choice.

    Args:
        prompt: The user's creative direction.
        side: "front" or "back".
        reference_image_url: Optional reference image URL.
        model: Which model to use - "pro", "grok", or "nano".

    Returns:
        BytesIO object for pro/nano, or list of BytesIO for grok. None if failed.
    """
    if model == "pro":
        return await generate_with_pro(prompt, side, reference_image_url)
    elif model == "grok":
        # Grok doesn't support reference images but returns multiple images
        if reference_image_url:
            logger.warning("Grok Imagine doesn't support reference images, ignoring...")
        return await generate_with_grok(prompt, side)
    else:  # nano
        return await generate_with_regular(prompt, side, reference_image_url)
