import json
import os
import uuid

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
BUCKET = os.environ['UPLOAD_BUCKET_NAME']


def handler(event, context):
    claims = event['requestContext']['authorizer']['jwt']['claims']
    user_id = claims['sub']
    image_key = f"uploads/{user_id}/{uuid.uuid4()}.jpg"

    try:
        upload_url = s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET, 'Key': image_key, 'ContentType': 'image/jpeg'},
            ExpiresIn=300,
        )
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': str(e)}),
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'uploadUrl': upload_url, 'imageKey': image_key}),
    }
