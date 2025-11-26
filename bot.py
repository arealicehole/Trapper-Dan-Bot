import discord
import openai
from discord import app_commands
from discord.ext import commands
from config import IGNORE_PREFIX
from conversation_manager import ConversationManager
from openai_client import get_openai_response
from utils import send_response, setup_logger
from kie_client import generate_shirt_design, edit_image
from rate_limiter import rate_limiter, MODEL_NAMES
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
            # Check if this is a reply to a bot message with an image (Edit mode)
            if message.reference and message.reference.resolved:
                replied_msg = message.reference.resolved
                # Check if replying to bot's image for editing
                if replied_msg.author.id == bot.user.id and replied_msg.attachments:
                    for attachment in replied_msg.attachments:
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            # This is a reply to edit a bot-generated image
                            logger.info(f"Edit request detected for bot image")

                            # Edits use "nano" model quota
                            rate_check = rate_limiter.check_rate_limit(message.author.id, "nano")
                            if not rate_check["allowed"]:
                                await message.reply(rate_check["message"])
                                return

                            # Get the edit prompt (remove bot mention from message)
                            edit_prompt = message.content.replace(f'<@{bot.user.id}>', '').strip()
                            if not edit_prompt:
                                await message.reply("Yo, tell me what changes you want to make to that design!")
                                return

                            logger.info(f"Editing image with prompt: '{edit_prompt}'")
                            edited_image = await edit_image(edit_prompt, attachment.url)

                            if not edited_image:
                                await message.reply("Couldn't edit that image. Try again with different instructions.")
                                return

                            # Record the generation under nano quota
                            rate_limiter.record_generation(message.author.id, "nano")

                            # Send the edited image
                            file = discord.File(edited_image, filename="edited_design.png")
                            response_msg = f"Aight, here's the edited version: '{edit_prompt}' [Edit]"

                            if rate_check["message"]:
                                response_msg += f"\n\n{rate_check['message']}"

                            await message.reply(response_msg, file=file)
                            return

            # Regular conversation flow
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
    model="Which AI model to use: Pro (5/day), Grok (10/day), or Nano (10/day)",
    side="Which side of the shirt to design: 'front' or 'back' (defaults to front)",
    reference_image="Optional: Attach an image to use as reference (not supported by Grok)"
)
@app_commands.choices(model=[
    app_commands.Choice(name="Pro - Nano Banana Pro (2K, best quality) [5/day]", value="pro"),
    app_commands.Choice(name="Grok - Grok Imagine (artistic style) [10/day]", value="grok"),
    app_commands.Choice(name="Nano - Nano Banana (1K) [10/day]", value="nano"),
])
async def design(interaction: discord.Interaction, prompt: str, model: str = "pro", side: str = "front", reference_image: discord.Attachment = None):
    """Creates a t-shirt design using user's prompt, optionally with a reference image."""
    await interaction.response.defer() # Defer the response to avoid timeouts

    # Check rate limit for selected model
    rate_check = rate_limiter.check_rate_limit(interaction.user.id, model)
    if not rate_check["allowed"]:
        await interaction.followup.send(rate_check["message"])
        return

    # Validate the side parameter
    side = side.lower()
    if side not in ["front", "back"]:
        await interaction.followup.send("Yo, pick either 'front' or 'back' for the side.")
        return

    try:
        # Get reference image URL if provided
        reference_image_url = None
        if reference_image:
            # Validate it's an image
            if not reference_image.content_type or not reference_image.content_type.startswith('image/'):
                await interaction.followup.send("Yo, that attachment ain't an image. Upload a PNG, JPG, or similar.")
                return
            # Warn if using Grok with reference image
            if model == "grok":
                await interaction.followup.send("Heads up: Grok doesn't support reference images, so I'll ignore that attachment. Use Pro or Regular if you need reference image support.")
            else:
                reference_image_url = reference_image.url
                logger.info(f"Using reference image: {reference_image.filename}")

        model_name = MODEL_NAMES.get(model, model)
        remaining = rate_check.get("remaining", "?")
        logger.info(f"Generating {side} design with {model_name} for user {interaction.user.id}")

        # Generate the image using Kie.ai
        result = await generate_shirt_design(prompt, side, reference_image_url, model=model)

        if not result:
            await interaction.followup.send("Sorry, I couldn't create the design. Something went wrong with the image generation.")
            return

        # Record the generation
        rate_limiter.record_generation(interaction.user.id, model)

        # Build response message
        response_msg = f"Aight, here's the {side} design for '{prompt}'."
        if reference_image_url:
            response_msg += " (Based on your reference image)"
        response_msg += f" [{model_name} - {remaining - 1} left]"

        # Add limit message if present
        if rate_check["message"]:
            response_msg += f"\n\n{rate_check['message']}"

        # Handle multiple images from Grok
        if model == "grok" and isinstance(result, list):
            files = [discord.File(img, filename=f"design_{side}_{i+1}.png") for i, img in enumerate(result)]
            response_msg = f"Aight, here's {len(files)} {side} designs for '{prompt}'! [{model_name} - {remaining - 1} left]"
            if rate_check["message"]:
                response_msg += f"\n\n{rate_check['message']}"
            await interaction.followup.send(response_msg, files=files)
        else:
            # Single image
            file = discord.File(result, filename=f"design_{side}.png")
            await interaction.followup.send(response_msg, file=file)

    except Exception as e:
        logger.error(f"Error in /design command: {e}", exc_info=True)
        await interaction.followup.send("Man, something went sideways. I couldn't finish the design. Try again in a bit.")


@bot.tree.context_menu(name="Design from Image")
async def design_from_image(interaction: discord.Interaction, message: discord.Message):
    """Right-click context menu to create a t-shirt design from an image in a message."""
    await interaction.response.send_modal(DesignModal(message))


class DesignModal(discord.ui.Modal, title="T-Shirt Design"):
    """Modal to collect prompt, model, and side for context menu design command."""

    prompt_input = discord.ui.TextInput(
        label="Design Description",
        placeholder="Describe what you want on the shirt...",
        required=True,
        max_length=500
    )

    model_input = discord.ui.TextInput(
        label="Model (nano or pro)",
        placeholder="nano",
        required=False,
        default="nano",
        max_length=10
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

        prompt = self.prompt_input.value

        # Handle model input - default to nano, only allow nano or pro
        model_value = self.model_input.value.strip().lower() if self.model_input.value else "nano"
        if model_value not in ["nano", "pro"]:
            model_value = "nano"

        # Handle side input - default to front if empty or invalid
        side_value = self.side_input.value
        if side_value and side_value.strip():
            side = side_value.strip().lower()
            if side not in ["front", "back"]:
                side = "front"
        else:
            side = "front"

        # Extract image URL from the message
        reference_image_url = None
        is_bot_image = self.message.author.bot

        if self.message.attachments:
            for attachment in self.message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    reference_image_url = attachment.url
                    logger.info(f"Using image from message: {attachment.filename}")
                    break

        if not reference_image_url:
            await interaction.followup.send("Yo, that message don't have an image attached. Right-click on a message with an image.")
            return

        try:
            # If it's a bot-generated image, use Edit API (uses nano quota)
            if is_bot_image:
                rate_check = rate_limiter.check_rate_limit(interaction.user.id, "nano")
                if not rate_check["allowed"]:
                    await interaction.followup.send(rate_check["message"])
                    return

                logger.info(f"Editing bot image with prompt: '{prompt}'")
                image = await edit_image(prompt, reference_image_url)
                response_msg = f"Aight, here's the edited design: '{prompt}' [Edit]"
                rate_limiter.record_generation(interaction.user.id, "nano")
            else:
                # Check rate limit for selected model
                rate_check = rate_limiter.check_rate_limit(interaction.user.id, model_value)
                if not rate_check["allowed"]:
                    await interaction.followup.send(rate_check["message"])
                    return

                model_name = MODEL_NAMES.get(model_value, model_value)
                remaining = rate_check.get("remaining", "?")

                logger.info(f"Generating design from context menu: prompt='{prompt}', side='{side}', model={model_value}")
                image = await generate_shirt_design(prompt, side, reference_image_url, model=model_value)
                response_msg = f"Aight, here's the {side} design based on that image: '{prompt}' [{model_name} - {remaining - 1} left]"
                rate_limiter.record_generation(interaction.user.id, model_value)

            if not image:
                await interaction.followup.send("Sorry, I couldn't create the design. Something went wrong with the image generation.")
                return

            # Create discord.File object
            file = discord.File(image, filename=f"design_{side}.png")

            # Add limit message if present
            if rate_check.get("message"):
                response_msg += f"\n\n{rate_check['message']}"

            await interaction.followup.send(response_msg, file=file)

        except Exception as e:
            logger.error(f"Error in context menu design command: {e}", exc_info=True)
            await interaction.followup.send("Man, something went sideways. I couldn't finish the design. Try again in a bit.")
