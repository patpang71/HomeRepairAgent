import json
import logging
import os
import time
import boto3

logger = logging.getLogger(__name__)

MCP_FUNCTION_NAME = os.environ.get('MCP_FUNCTION_NAME', 'HomeRepairAgent-McpServer')

_lambda_client = None


def _get_client():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client('lambda')
    return _lambda_client


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    logger.info('Calling MCP tool=%s args=%s', tool_name, arguments)
    payload = {
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': arguments},
    }
    start = time.monotonic()
    response = _get_client().invoke(
        FunctionName=MCP_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload).encode(),
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    result = json.loads(response['Payload'].read())

    if 'FunctionError' in response:
        logger.error(
            'MCP tool=%s invocation failed (%.0fms): %s',
            tool_name, elapsed_ms, result,
        )
    else:
        logger.info('MCP tool=%s returned in %.0fms', tool_name, elapsed_ms)

    return json.loads(result['content'][0]['text'])
