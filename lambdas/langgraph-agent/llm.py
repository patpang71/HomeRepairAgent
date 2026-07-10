import logging
import os
from langchain_aws import ChatBedrock

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')

_llm = None


def get_llm() -> ChatBedrock:
    global _llm
    if _llm is None:
        region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        logger.info('Initializing Bedrock LLM model=%s region=%s', MODEL_ID, region)
        _llm = ChatBedrock(
            model_id=MODEL_ID,
            region_name=region,
            model_kwargs={'maxTokens': 1024},
        )
    return _llm
