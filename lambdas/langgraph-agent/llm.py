import os
from langchain_aws import ChatBedrock

MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')

_llm = None


def get_llm() -> ChatBedrock:
    global _llm
    if _llm is None:
        _llm = ChatBedrock(
            model_id=MODEL_ID,
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
            model_kwargs={'maxTokens': 1024},
        )
    return _llm
