import discord
import openai
from discord import app_commands
from discord.ext import commands
from config import IGNORE_PREFIX
from conversation_manager import ConversationManager
from openai_client import get_openai_response
from utils import send_response, setup_logger
from gemini_client import generate_shirt_designs
from rate_limiter import rate_limiter
import io
import aiohttp

logger = setup_logger(__name__)

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info('The bot is online and ready to chat!')
    await bot.tree.sync()

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.content.startswith(IGNORE_PREFIX):
        return

    if bot.user not in message.mentions:
        return

    async with message.channel.typing():
        try:
            conversation = await ConversationManager.build_conversation(message)
            response = await get_openai_response(conversation)
            await send_response(message, response)
        except ValueError as e:
            logger.error(f"Error processing message: {e}")
            await message.reply(f"Yo, I couldn't process that image. {str(e)}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            await message.reply("Yo, I'm having some technical difficulties with processing that image. Can you try again with a different one?")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await message.reply("Something weird just happened. Let me catch my breath and we can try this again.")


@bot.tree.command(name="design", description="Create a new t-shirt design for the Kannakickback.")
@app_commands.describe(
    prompt="A description of the design you want to add to the shirt.",
    side="Which side of the shirt to design: 'front' or 'back' (defaults to front)",
    reference_image="Optional: Attach an image to use as reference for the design"
)
async def design(interaction: discord.Interaction, prompt: str, side: str = "front", reference_image: discord.Attachment = None):
    """Creates a t-shirt design using user's prompt, optionally with a reference image."""
    await interaction.response.defer() # Defer the response to avoid timeouts

    # Check rate limit
    rate_check = rate_limiter.check_rate_limit(interaction.user.id)
    if not rate_check["allowed"]:
        await interaction.followup.send(rate_check["message"])
        return

    # Validate the side parameter
    side = side.lower()
    if side not in ["front", "back"]:
        await interaction.followup.send("Yo, pick either 'front' or 'back' for the side.")
        return

    try:
        # Download reference image if provided
        reference_image_bytes = None
        if reference_image:
            # Validate it's an image
            if not reference_image.content_type or not reference_image.content_type.startswith('image/'):
                await interaction.followup.send("Yo, that attachment ain't an image. Upload a PNG, JPG, or similar.")
                return

            logger.info(f"Downloading reference image: {reference_image.filename}")
            async with aiohttp.ClientSession() as session:
                async with session.get(reference_image.url) as resp:
                    if resp.status == 200:
                        reference_image_bytes = await resp.read()
                        logger.info(f"Reference image downloaded: {len(reference_image_bytes)} bytes")
                    else:
                        await interaction.followup.send("Couldn't download that image. Try again.")
                        return

        # Generate the image
        image = await generate_shirt_designs(prompt, side, reference_image_bytes)

        if not image:
            await interaction.followup.send("Sorry, I couldn't create the design. Something went wrong with the image generation.")
            return

        # Record the generation
        rate_limiter.record_generation(interaction.user.id)

        # Create discord.File object
        file = discord.File(image, filename=f"design_{side}.png")

        # Send the image
        response_msg = f"Aight, here's the {side} design for '{prompt}'."
        if reference_image_bytes:
            response_msg += " (Based on your reference image)"

        # Add donation message if at soft limit
        if rate_check["message"]:
            response_msg += f"\n\n{rate_check['message']}"

        await interaction.followup.send(response_msg, file=file)

    except Exception as e:
        logger.error(f"Error in /design command: {e}", exc_info=True)
        await interaction.followup.send("Man, something went sideways. I couldn't finish the design. Try again in a bit.")


@bot.tree.context_menu(name="Design from Image")
async def design_from_image(interaction: discord.Interaction, message: discord.Message):
    """Right-click context menu to create a t-shirt design from an image in a message."""
    await interaction.response.send_modal(DesignModal(message))


class DesignModal(discord.ui.Modal, title="T-Shirt Design"):
    """Modal to collect prompt and side for context menu design command."""

    prompt_input = discord.ui.TextInput(
        label="Design Description",
        placeholder="Describe what you want on the shirt...",
        required=True,
        max_length=500
    )

    side_input = discord.ui.TextInput(
        label="Side (front or back)",
        placeholder="front",
        required=False,
        default="front",
        max_length=5
    )

    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Check rate limit
        rate_check = rate_limiter.check_rate_limit(interaction.user.id)
        if not rate_check["allowed"]:
            await interaction.followup.send(rate_check["message"])
            return

        prompt = self.prompt_input.value

        # Handle side input - default to front if empty or invalid
        side_value = self.side_input.value
        if side_value and side_value.strip():
            side = side_value.strip().lower()
            if side not in ["front", "back"]:
                side = "front"  # Default to front if invalid
        else:
            side = "front"  # Default to front if empty

        # Extract image from the message
        reference_image_bytes = None
        if self.message.attachments:
            for attachment in self.message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    logger.info(f"Downloading image from message: {attachment.filename}")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status == 200:
                                reference_image_bytes = await resp.read()
                                logger.info(f"Image downloaded: {len(reference_image_bytes)} bytes")
                                break
                            else:
                                await interaction.followup.send("Couldn't download that image. Try again.")
                                return

        if not reference_image_bytes:
            await interaction.followup.send("Yo, that message don't have an image attached. Right-click on a message with an image.")
            return

        try:
            # Generate the design
            logger.info(f"Generating design from context menu: prompt='{prompt}', side='{side}'")
            image = await generate_shirt_designs(prompt, side, reference_image_bytes)

            if not image:
                await interaction.followup.send("Sorry, I couldn't create the design. Something went wrong with the image generation.")
                return

            # Record the generation
            rate_limiter.record_generation(interaction.user.id)

            # Create discord.File object
            file = discord.File(image, filename=f"design_{side}.png")

            # Send the image
            response_msg = f"Aight, here's the {side} design based on that image: '{prompt}'"

            # Add donation message if at soft limit
            if rate_check["message"]:
                response_msg += f"\n\n{rate_check['message']}"

            await interaction.followup.send(response_msg, file=file)

        except Exception as e:
            logger.error(f"Error in context menu design command: {e}", exc_info=True)
            await interaction.followup.send("Man, something went sideways. I couldn't finish the design. Try again in a bit.")
