import openai
from config import OPENAI_API_KEY, OPENAI_MODEL
from utils import setup_logger

logger = setup_logger(__name__)
openai_client = openai.AsyncClient(api_key=OPENAI_API_KEY)

async def get_openai_response(conversation: list) -> str:
    try:
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=conversation,
            temperature=0.7
        )
        return response.choices[0].message.content
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in OpenAI call: {e}")
        raise