import json
import os
import boto3

MCP_FUNCTION_NAME = os.environ.get('MCP_FUNCTION_NAME', 'HomeRepairAgent-McpServer')

_lambda_client = None


def _get_client():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client('lambda')
    return _lambda_client


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    payload = {
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': arguments},
    }
    response = _get_client().invoke(
        FunctionName=MCP_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload).encode(),
    )
    result = json.loads(response['Payload'].read())
    return json.loads(result['content'][0]['text'])
