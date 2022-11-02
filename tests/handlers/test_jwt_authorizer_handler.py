"""
-> Module to test the JWT Authorizer
"""
import os

import boto3
import pytest
from moto import mock_cognitoidp

from cyclonedx.clients.ciam import HarborCognitoClient, JwtData
from cyclonedx.constants import USER_POOL_ID_KEY
from cyclonedx.handlers.jwt_authorizer_handler import (
    _get_cognito_user_pool_id,
    jwt_authorizer_handler,
)
from tests.conftest import create_mock_cognito_infra
from tests.handlers import EMAIL, METHOD_ARN, TEAMS

# pylint: disable=C0301
token_part_1: str = "eyJraWQiOiJmYUdKYWR4NDB1UmxLMExyd2ZXQklObjhuaTRWdGZTYzc0ODJ2MmpRQWJFPSIsImFsZyI6IlJTMjU2In0"
token_part_2: str = "eyJzdWIiOiJkYTdlYjRjZS0xYTM5LTRiNWEtOTU3Mi0zNmJkMzI5YzRjODgiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV9Lb1BsVzZ5Y2oiLCJjbGllbnRfaWQiOiIzcnVlNDZmamZ1ZmU4OTdoZG05ODNwM3FzNiIsIm9yaWdpbl9qdGkiOiJiM2Y2NDA4Yy04MTA5LTQyMzktYmQwZi1jMTVlZTVlY2IxOGQiLCJldmVudF9pZCI6ImYyMWM4NDMyLTQ1MTAtNDA4MS1iNmU1LWNiMmYzNWYxNDljMCIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE2NjYwOTQzMzIsImV4cCI6MTY2NjA5NzkzMiwiaWF0IjoxNjY2MDk0MzMyLCJqdGkiOiI2MTQ5OWJiNi1mM2FmLTRlNDEtYWFiYy1kNjc1OGU4N2M0YzYiLCJ1c2VybmFtZSI6ImRhN2ViNGNlLTFhMzktNGI1YS05NTcyLTM2YmQzMjljNGM4OCJ9"
token_part_3: str = "fFertjqRXGrD8tzcfpHDSd1oMJbzLfN0193Q7DAnsJ27EfOqUWQmmUh7Op-vwhvvjRybDEjmCZUIMA2TJQ88FYL8d2ju9FjNk-COoqd070uPCWDBY4vA6qcHo7f6WaW1Xh4A7HQLhKHrp4RitvbBEHhhmzdK7yJlaoJlvs5EjqQnB1laibaBbHWacCO_4WF08Lzh7_DdC-dvPy_IeE-3xbzm30lpxHtX5d3JEGMjXmAvJmmUyf0BDMh0WTOww-ZRkGcpituMZY2Hl-EGUIEF2vdJvM1kJcsEaKtryofqoVe4IT9V2vYY4WNVfQ-_nP8ALr5sLwxlgSlpoUZT52ye4g"
TOKEN: str = f"{token_part_1}.{token_part_2}.{token_part_3}"
USERNAME: str = "da7eb4ce-1a39-4b5a-9572-36bd329c4c88"
USER_POOL_ID: str = "us-east-1_KoPlW6ycj"
aws_lambda_test_event: dict = {
    "version": "1.0",
    "type": "REQUEST",
    "methodArn": METHOD_ARN,
    "identitySource": TOKEN,
    "authorizationToken": TOKEN,
    "resource": METHOD_ARN,
    "path": "/api/v1/project/0dba7774-58e0-4d4e-ac5a-1f2b71b22bc5",
    "httpMethod": "GET",
    "headers": {
        "Content-Length": "0",
        "Host": "hvi0slqerb.execute-api.us-east-1.amazonaws.com",
        "User-Agent": "Amazon CloudFront",
        "X-Amz-Cf-Id": "t86h4FiSbK1_OwNNBDNb5YG1b2GY_IF84RHxMPQA0LY5h-w51VUtpA==",
        "X-Amzn-Trace-Id": "Root=1-634e94fc-358c663b7dbfa6bb281902eb",
        "X-Forwarded-For": "108.3.156.227, 64.252.69.199",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https",
        "accept-encoding": "gzip",
        "authorization": TOKEN,
        "via": "1.1 4e2a7874b5959279490dd3b94b18a312.cloudfront.net (CloudFront)",
    },
    "queryStringParameters": {
        "teamId": "f96ef074-e8ac-4e80-bcb1-54937bc50e16",
    },
    "requestContext": {
        "accountId": "531175407938",
        "apiId": "hvi0slqerb",
        "domainName": "hvi0slqerb.execute-api.us-east-1.amazonaws.com",
        "domainPrefix": "hvi0slqerb",
        "extendedRequestId": "aMw3bjM0IAMEP2Q=",
        "httpMethod": "GET",
        "identity": {
            "accessKey": None,
            "accountId": None,
            "caller": None,
            "cognitoAmr": None,
            "cognitoAuthenticationProvider": None,
            "cognitoAuthenticationType": None,
            "cognitoIdentityId": None,
            "cognitoIdentityPoolId": None,
            "principalOrgId": None,
            "sourceIp": "108.3.156.227",
            "user": None,
            "userAgent": "Amazon CloudFront",
            "userArn": None,
        },
        "path": "/api/v1/project/0dba7774-58e0-4d4e-ac5a-1f2b71b22bc5",
        "protocol": "HTTP/1.1",
        "requestId": "aMw3bjM0IAMEP2Q=",
        "requestTime": "18/Oct/2022:11:58:52 +0000",
        "requestTimeEpoch": 1666094332145,
        "resourceId": "GET /api/v1/project/{project}",
        "resourcePath": "/api/v1/project/{project}",
        "stage": "$default",
    },
    "pathParameters": {"project": "0dba7774-58e0-4d4e-ac5a-1f2b71b22bc5"},
    "stageVariables": {},
}

test_cognito_response: dict = {
    "Username": "da7eb4ce-1a39-4b5a-9572-36bd329c4c88",
    "UserAttributes": [
        {
            "Name": "custom:teams",
            "Value": TEAMS,
        },
        {"Name": "sub", "Value": "da7eb4ce-1a39-4b5a-9572-36bd329c4c88"},
        {"Name": "email", "Value": EMAIL},
    ],
    "UserCreateDate": "DATE",
    "UserLastModifiedDate": "DATE",
    "Enabled": True,
    "UserStatus": "CONFIRMED",
    "ResponseMetadata": {
        "RequestId": "5b483d38-5feb-490e-9f9d-7b4804366ff4",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "date": "Wed, 19 Oct 2022 07:23:27 GMT",
            "content-type": "application/x-amz-json-1.1",
            "content-length": "349",
            "connection": "keep-alive",
            "x-amzn-requestid": "5b483d38-5feb-490e-9f9d-7b4804366ff4",
        },
        "RetryAttempts": 0,
    },
}


def test_get_policy():

    """
    -> _get_policy() isn't testable until it is implemented.
    """

    ...


def test_get_cognito_user_pool_id():

    """
    -> Tests _get_cognito_user_pool_id()
    """

    cupid: str = _get_cognito_user_pool_id(aws_lambda_test_event)
    assert USER_POOL_ID == cupid


def test_get_arn_token_username():

    """
    -> Tests _get_arn_token_username()
    """

    token: str = aws_lambda_test_event["authorizationToken"]
    arn: str = aws_lambda_test_event["methodArn"]

    jwt_data: JwtData = HarborCognitoClient.get_jwt_data(token)
    username = jwt_data.username

    assert METHOD_ARN == arn
    assert TOKEN == token
    assert USERNAME == username


def test_verify_token():

    """
    -> _verify_token() isn't testable until it is implemented.
    """

    ...


@mock_cognitoidp
def test_jwt_authorizer_handler():

    """
    -> Tests the jwt_authorizer_handler
    -> Currently, we can only determine that it is indeed a policy document
    -> We need to improve these tests once we have _verify_token() implemented
    """

    cognito_client = boto3.client("cognito-idp")

    user_pool_id, _, _ = create_mock_cognito_infra(cognito_client)
    os.environ[USER_POOL_ID_KEY] = user_pool_id

    policy: dict = jwt_authorizer_handler(aws_lambda_test_event, {})

    try:
        policy["policyDocument"]
    except KeyError:
        pytest.fail()
