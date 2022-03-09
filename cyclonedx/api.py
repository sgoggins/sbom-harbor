"""
This module serves as the external API for CycloneDX Python Module
"""

import os
from uuid import uuid4
from json import loads, dumps
from boto3 import resource
from jsonschema.exceptions import ValidationError

from cyclonedx.core import CycloneDxCore


def __get_bom_obj(event) -> dict:

    """
    If the request context exists, then there will
    be a 'body' key, and it will contain the JSON object
    as a **string** that the POST body contained.
    """

    return loads(event["body"]) if "requestContext" in event else event


def __create_response_obj(bucket_name: str, key: str) -> dict:

    """
    Creates a dict that is used as the response from the Lambda
    call.  It has all the necessary elements to satisfy AWS's criteria.
    """

    return {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": dumps({"valid": True, "s3BucketName": bucket_name, "s3ObjectKey": key}),
    }


def store_handler(event, context) -> dict:

    """
    This is the Lambda Handler that validates an incoming SBOM
    and if valid, puts the SBOM into the S3 bucket associated
    to the application.
    """

    bom_obj = __get_bom_obj(event)

    # Get the bucket name from the environment variable
    # This is set during deployment
    bucket_name = os.environ["SBOM_BUCKET_NAME"]
    print(f"Bucket name from env(SBOM_BUCKET_NAME): {bucket_name}")

    # Generate the name of the object in S3
    key = f"aquia-{uuid4()}"
    print(f"Putting object in S3 with key: {key}")

    # Create an instance of the Python CycloneDX Core
    core = CycloneDxCore()

    # Create a response object to add values to.
    response_obj = __create_response_obj(bucket_name, key)

    try:

        # Validate the BOM here
        core.validate(bom_obj)

        # Get S3 Bucket
        bucket = resource("s3").Bucket(bucket_name)

        # Actually put the object in S3
        bom_bytes = bytearray(dumps(bom_obj), "utf-8")
        bucket.put_object(Key=key, Body=bom_bytes)

    except ValidationError as validation_error:
        response_obj["statusCode"] = 400
        response_obj["body"] = str(validation_error)

    return response_obj
