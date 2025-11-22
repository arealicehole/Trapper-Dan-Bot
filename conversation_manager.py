import re
import base64
import discord
from config import MAX_HISTORY, MAX_FILE_SIZE, IGNORE_PREFIX
from image_processor import ImageProcessor
from config import SYSTEM_PROMPT

class ConversationManager:
    @staticmethod
    def create_system_message():
        return {
            'role': 'system',
            'content': SYSTEM_PROMPT
        }

    @staticmethod
    def sanitize_username(username: str) -> str:
        return re.sub(r'[^\w]', '', re.sub(r'\s+', '_', username))

    @staticmethod
    async def process_message(msg: discord.Message, role: str) -> dict:
        username = ConversationManager.sanitize_username(msg.author.name)

        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type.startswith('image/'):
                    # OpenAI only allows images in 'user' role messages, not 'assistant'
                    if role == 'user':
                        image_data = attachment.url
                        if attachment.size > MAX_FILE_SIZE:
                            resized_image = await ImageProcessor.resize_image(attachment.url)
                            if resized_image:
                                image_base64 = base64.b64encode(resized_image.getvalue()).decode('utf-8')
                                image_data = f"data:image/jpeg;base64,{image_base64}"
                            else:
                                raise ValueError("Failed to resize image")

                        return {
                            'role': role,
                            'name': username,
                            'content': [
                                {'type': 'text', 'text': 'Check out this image and tell me what you think about it:'},
                                {'type': 'image_url', 'image_url': {'url': image_data}}
                            ]
                        }
                    else:
                        # For assistant messages with images, just include text reference
                        return {
                            'role': role,
                            'name': username,
                            'content': f"[Posted an image: {attachment.filename}]"
                        }
                else:
                    return {
                        'role': role,
                        'name': username,
                        'content': f"I've attached a file: {attachment.filename}"
                    }
        else:
            return {
                'role': role,
                'name': username,
                'content': msg.content
            }

    @staticmethod
    async def build_conversation(message: discord.Message) -> list:
        conversation = [ConversationManager.create_system_message()]

        # Check if this is a reply to a message with an image
        if message.reference and message.reference.resolved:
            replied_msg = message.reference.resolved
            # Check if the replied-to message has image attachments
            if replied_msg.attachments:
                for attachment in replied_msg.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        # Process the image from the replied-to message
                        image_data = attachment.url
                        if attachment.size > MAX_FILE_SIZE:
                            resized_image = await ImageProcessor.resize_image(attachment.url)
                            if resized_image:
                                image_base64 = base64.b64encode(resized_image.getvalue()).decode('utf-8')
                                image_data = f"data:image/jpeg;base64,{image_base64}"

                        # Add the replied-to image as part of the user's current message context
                        username = ConversationManager.sanitize_username(message.author.name)
                        image_message = {
                            'role': 'user',
                            'name': username,
                            'content': [
                                {'type': 'text', 'text': f"[Replying to an image] {message.content}"},
                                {'type': 'image_url', 'image_url': {'url': image_data}}
                            ]
                        }
                        # Build rest of conversation history
                        async for msg in message.channel.history(limit=MAX_HISTORY):
                            if msg.id == message.id:
                                continue  # Skip the current message, we'll add it with the image
                            if msg.author.bot and msg.author.id != message.guild.me.id:
                                continue
                            if msg.content.startswith(IGNORE_PREFIX):
                                continue

                            role = 'assistant' if msg.author.id == message.guild.me.id else 'user'
                            processed_message = await ConversationManager.process_message(msg, role)
                            conversation.append(processed_message)

                        conversation.reverse()
                        conversation.append(image_message)
                        return conversation

        # Regular conversation building (no reply with image)
        async for msg in message.channel.history(limit=MAX_HISTORY):
            if msg.author.bot and msg.author.id != message.guild.me.id:
                continue
            if msg.content.startswith(IGNORE_PREFIX):
                continue

            role = 'assistant' if msg.author.id == message.guild.me.id else 'user'
            processed_message = await ConversationManager.process_message(msg, role)
            conversation.append(processed_message)

        conversation.reverse()
        return conversation