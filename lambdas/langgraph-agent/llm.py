import logging
import os

from langchain_aws import ChatBedrock
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')

_llm = None
_MAX_LOG_CHARS = 2000


def _format_content(content) -> str:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'image':
                parts.append('[image omitted]')
            elif isinstance(part, dict) and 'text' in part:
                parts.append(part['text'])
            else:
                parts.append(str(part))
        text = ' '.join(parts)
    else:
        text = str(content)

    if len(text) > _MAX_LOG_CHARS:
        return f'{text[:_MAX_LOG_CHARS]}... [truncated, {len(text)} chars total]'
    return text


class _LoggingCallbackHandler(BaseCallbackHandler):
    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        call_id = str(run_id)[:8]
        for batch in messages:
            for msg in batch:
                logger.info('LLM prompt call=%s role=%s: %s', call_id, msg.type, _format_content(msg.content))

    def on_llm_end(self, response, *, run_id, **kwargs):
        call_id = str(run_id)[:8]
        for generation_batch in response.generations:
            for generation in generation_batch:
                text = getattr(generation, 'text', '') or _format_content(generation.message.content)
                logger.info('LLM response call=%s: %s', call_id, _format_content(text))

    def on_llm_error(self, error, *, run_id, **kwargs):
        logger.error('LLM call=%s failed: %s', str(run_id)[:8], error)


def get_llm() -> ChatBedrock:
    global _llm
    if _llm is None:
        region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        logger.info('Initializing Bedrock LLM model=%s region=%s', MODEL_ID, region)
        _llm = ChatBedrock(
            model_id=MODEL_ID,
            region_name=region,
            model_kwargs={'maxTokens': 1024},
            callbacks=[_LoggingCallbackHandler()],
        )
    return _llm
