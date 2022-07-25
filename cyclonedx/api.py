"""
This module serves as the external API for CycloneDX Python Module
"""
from time import sleep

import boto3
import datetime
import importlib.resources as pr

import requests

import cyclonedx.schemas as schemas

from io import StringIO
from os import environ
from json import loads, dumps
from uuid import uuid4
from boto3.dynamodb.conditions import Attr
from boto3 import resource
from dateutil.relativedelta import relativedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from decimal import Decimal
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from cyclonedx.constants import (
    EVENT_BUS_NAME,
    S3_META_CODEBASE_KEY,
    S3_META_PROJECT_KEY,
    S3_META_TEAM_KEY,
    S3_META_TIMESTAMP_KEY,
    SBOM_BUCKET_NAME_KEY,
    SBOM_S3_KEY,
    TEAM_MEMBER_TABLE_NAME,
    TEAM_TOKEN_TABLE_NAME,
    USER_POOL_CLIENT_ID_KEY,
    USER_POOL_NAME_KEY,
    TEAM_TABLE_NAME,
)

from cyclonedx.core import CycloneDxCore
from cyclonedx.util import (
    ICClient,
    __create_project,
    __create_pristine_response_obj,
    __create_team_response,
    __create_user_search_response_obj,
    __delete_project,
    __get_all_s3_obj_data,
    __get_body_from_event,
    __get_query_string_params_from_event,
    __get_body_from_first_record,
    __get_findings,
    __get_login_failed_response,
    __get_login_success_response,
    __get_records_from_event,
    __get_team_by_team_id,
    __handle_delete_token_error,
    __token_response_obj,
    __upload_sbom,
    __validate,
)

cognito_client = boto3.client('cognito-idp')
dynamodb_resource = boto3.resource('dynamodb')
dynamodb_serializer = TypeSerializer()
dynamodb_deserializer = TypeDeserializer()

team_schema = loads(
    pr.read_text(
        schemas, "team.schema.json"
    )
)

def pristine_sbom_ingress_handler(event: dict=None, context: dict=None) -> dict:

    """
    This is the Lambda Handler that validates an incoming SBOM
    and if valid, puts the SBOM into the S3 bucket associated
    to the application.
    """

    s3 = resource("s3")

    # Extract the path parameters and get the team
    path_params = event["pathParameters"]
    team = path_params["team"]
    project = path_params["project"]
    codebase = path_params["codebase"]

    bom_obj = __get_body_from_event(event)

    # Get the bucket name from the environment variable
    # This is set during deployment
    bucket_name = environ[SBOM_BUCKET_NAME_KEY]
    print(f"Bucket name from env(SBOM_BUCKET_NAME_EV): {bucket_name}")

    # Generate the name of the object in S3
    key = f"sbom-{uuid4()}"
    print(f"Putting object in S3 with key: {key}")

    # Create an instance of the Python CycloneDX Core
    core = CycloneDxCore()

    # Create a response object to add values to.
    response_obj = __create_pristine_response_obj(bucket_name, key)

    try:

        # Validate the BOM here
        core.validate(bom_obj)

        # Extract the actual SBOM.
        bom_bytes = bytearray(dumps(bom_obj), "utf-8")
        timestamp = datetime.datetime.now().timestamp()
        s3.Object(bucket_name, key).put(
            Body=bom_bytes,
            Metadata={
                S3_META_TEAM_KEY: team,
                S3_META_PROJECT_KEY: project,
                S3_META_CODEBASE_KEY: codebase,
                S3_META_TIMESTAMP_KEY: str(timestamp),
            },
        )

    except ValidationError as validation_error:
        response_obj["statusCode"] = 400
        response_obj["body"] = str(validation_error)

    return response_obj


def enrichment_ingress_handler(event: dict=None, context: dict=None):

    """
    Handler that listens for S3 put events and routes the SBOM
    to the enrichment code
    """

    if not event:
        raise ValidationError("event should never be none")

    records: list = __get_records_from_event(event)

    print(f"<Records records={records}>")

    for record in records:

        s3_obj = record["s3"]
        bucket_obj = s3_obj["bucket"]
        bucket_name = bucket_obj["name"]
        sbom_obj = s3_obj["object"]
        key: str = sbom_obj["key"]

        eb_client = boto3.client('events')


        # s3_object = s3.Object(bucket_name, key).get()

        # try:
        #     enrichment_id = s3_object["Metadata"][ENRICHMENT_ID]
        # except KeyError as key_err:
        #     print(f"<s3Object object={s3_object} />")
        #     enrichment_id = f"ERROR: {key_err}"

        response = eb_client.put_events(
            Entries=[
                {
                    'Source': 'enrichment.lambda',
                    'DetailType': 'test_detail_type_string',
                    'Detail': dumps(
                        {
                            SBOM_BUCKET_NAME_KEY: bucket_name,
                            SBOM_S3_KEY: key,
                            'results': {},
                            'output': {},
                        },
                    ),
                    'EventBusName': EVENT_BUS_NAME,
                },
            ],
        )

        print(f"<PutEventsResponse response='{response}' />")


def dt_interface_handler(event: dict=None, context: dict=None):

    """ Dependency Track Ingress Handler
    This code takes an SBOM in the S3 Bucket and submits it to Dependency Track
    to get findings.  To accomplish this, a project must be created in DT, the
    SBOM submitted under that project, then the project is deleted.
    """

    s3_resource = resource("s3")

    print(f"<Event event='{event}' />")

    # Currently making sure it isn't empty
    __validate(event)

    # EventBridge 'detail' key has the data we need.
    bucket_name = event[SBOM_BUCKET_NAME_KEY]
    key: str = event[SBOM_S3_KEY]

    # Get the SBOM from the bucket and stick it
    # into a string based file handle.
    s3_object = s3_resource.Object(bucket_name, key).get()
    sbom: bytes = s3_object["Body"].read()
    d_sbom: str = sbom.decode("utf-8")
    bom_str_file: StringIO = StringIO(d_sbom)

    # Create a new Dependency Track Project to analyze the SBOM
    project_uuid = __create_project()

    # Upload the SBOM to DT into the temp project
    sbom_token: str = __upload_sbom(project_uuid, bom_str_file)

    # Poll DT to see when the SBOM is finished being analyzed.
    # When it's finished, get the findings returned from DT.
    findings: dict = __get_findings(project_uuid, sbom_token)

    # Clean up the project we made to do the processing
    __delete_project(project_uuid)

    # Dump the findings into a byte array and store them
    # in the S3 bucket along with the SBOM the findings
    # came from.
    findings_bytes = bytearray(dumps(findings), "utf-8")
    findings_key: str = f"findings-dt-{key}"
    s3_resource.Object(bucket_name, findings_key).put(
        Body=findings_bytes,
    )

    print(f"Findings are in the s3 bucket: {bucket_name}/{findings_key}")

    return findings_key


def ic_interface_handler(event: dict=None, context: dict=None):

    """
    Ion Channel Ingress Handler
    This code takes an SBOM in the S3 Bucket and submits it to Ion Channel
    to get findings.
    """

    all_data = __get_all_s3_obj_data(event)
    sbom_str_file = all_data['data']
    team = all_data['team']
    project = all_data['project']
    codebase = all_data['codebase']

    # Here is where the SBOM name, or the Ion Channel Team Name
    # is created.
    sbom_name: str = f"{team}-{project}-{codebase}"

    # Create an Ion Channel Request Factory
    # and import the SBOM
    ic_client = ICClient(sbom_name, True)
    ic_client.import_sbom(sbom_str_file)
    ic_client.analyze_sbom()

    return sbom_name


def des_interface_handler(event: dict=None, context: dict=None):

    s3_resource = resource("s3")

    print(f"<event value='{event}' />")
    all_data = __get_all_s3_obj_data(event)
    sbom = loads(all_data['data'].read())
    sbom_name = all_data['s3_obj_name']
    bucket_name = all_data['bucket_name']
    findings_file_name = f"findings-des-{sbom_name}"

    nvd_base_url = "https://services.nvd.nist.gov"
    nvd_api_path = "/rest/json/cpes/1.0"

    findings = []

    components: list = sbom["components"]
    components_seen = 0

    api_keys = [
        '7e762116-c587-4a4b-9eb4-f7b5fef84024',
        '3f501a51-373a-4a11-9a5d-6f691b522adc',
        '2d2a6475-2f19-4876-9a03-ba8de575d477',
        '99eaef67-ca08-423f-92ac-6e79a4a4bae9',
        'd0844f1d-ff53-4a6b-82ab-3ee143198311',
    ]

    for component in components[:100]: # TODO Remove Slice

        components_seen += 1
        print(f"Looking at component# {components_seen} of {len(components)}")

        vendor = "*"
        product = component["name"]
        version = component["version"]

        key = api_keys[ components_seen % len(api_keys) ]
        print(f"Request Key: {key}")
        cpe_search_str = f"cpe:2.3:a:{vendor}:{product}:{version}"
        nvd_query_params = f"?addOns=cves&cpeMatchString={cpe_search_str}&apiKey={key}"
        nvd_url = f"{nvd_base_url}/{nvd_api_path}/{nvd_query_params}"

        nvd_response = requests.get(nvd_url)

        if nvd_response.status_code == 403:
            print("Hit NVD Administrative limit, backing off for 10 seconds.")
            components.append(component)
            sleep(10)
            continue

        nvd_rsp_json = nvd_response.json()
        num_results = nvd_rsp_json['totalResults']

        if num_results > 0:
            print(f"# Results: {num_results}")
            findings.append(nvd_rsp_json)
        else:
            print("No Results")

    print("Made it out of the loop!!!")

    # print(dumps(response.json(), indent=2))
    # Dump the findings into a byte array and store them
    # in the S3 bucket along with the SBOM the findings
    # came from.
    findings_bytes = bytearray(dumps(findings), "utf-8")
    s3_resource.Object(bucket_name, findings_file_name).put(
        Body=findings_bytes,
    )

    return findings_file_name


def summarizer_handler(event: dict=None, context: dict=None):

    compiled_results = []

    ( bucket_name, findings_report_name ) = ( "", "" )

    s3 = resource("s3")
    for result in event:

        bucket_name = result[SBOM_BUCKET_NAME_KEY]
        sbom_name = result[SBOM_S3_KEY]
        findings_report_name = f"report-{sbom_name}"

        results = result["results"]
        findings_s3_obj = results["Payload"]

        s3_obj_wrapper = s3.Object(bucket_name, findings_s3_obj)
        s3_object: dict = s3_obj_wrapper.get()
        sbom = s3_object["Body"].read()
        d_sbom = sbom.decode("utf-8")
        compiled_results.append(loads(d_sbom))

    s3.Object(bucket_name, findings_report_name).put(
        Body=bytearray(dumps(compiled_results), "utf-8"),
    )


def login_handler(event, context):

    body = __get_body_from_first_record(event)

    username = body["username"]
    password = body["password"]

    try:
        resp = cognito_client.admin_initiate_auth(
            UserPoolId=environ.get(USER_POOL_NAME_KEY),
            ClientId=environ.get(USER_POOL_CLIENT_ID_KEY),
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )
    except Exception as err:
        return __get_login_failed_response(401, err)

    jwt = resp['AuthenticationResult']['AccessToken']

    print("Log in success")
    print(f"Access token: {jwt}", )
    print(f"ID token: {resp['AuthenticationResult']['IdToken']}")

    return __get_login_success_response(jwt)


def allow_policy(method_arn: str):
    return {
        "principalId": "apigateway.amazonaws.com",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": "Allow",
                "Resource": method_arn
            },{
                "Action": "cognito-idp:ListUsers",
                "Effect": "Allow",
                "Resource": method_arn
            }]
        }
    }


def deny_policy():
    return {
        "principalId": "*",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "*",
                "Effect": "Deny",
                "Resource": "*"
            }]
        }
    }


def verify_token(token: str):
    return True


def jwt_authorizer_handler(event, context):

    print("<EVENT>")
    print(event)
    print("</EVENT>")

    print("<CONTEXT>")
    print(context)
    print("</CONTEXT>")

    method_arn = event["methodArn"]
    token = event["authorizationToken"]

    return allow_policy(method_arn) if verify_token(token) else deny_policy()


def api_key_authorizer_handler(event, context):

    # Extract the Method ARN and the token from the event
    method_arn = event["methodArn"]
    token = event["authorizationToken"]

    # Extract the path parameters and get the team
    path_params = event["pathParameters"]
    team_id = path_params["team"]

    # Get our Team table from DynamoDB
    team_token_table = dynamodb_resource.Table(TEAM_TOKEN_TABLE_NAME)

    # Get the team from the table
    get_team_tokens_rsp = team_token_table.query(
        Select="ALL_ATTRIBUTES",
        KeyConditionExpression="TeamId = :TeamId",
        ExpressionAttributeValues={
            ":TeamId": team_id,
        },
    )

    try:
        tokens = get_team_tokens_rsp["Items"]
    except KeyError as err:
        print(f"Key error: {err}")
        print(f"Query Response(Team): {get_team_tokens_rsp}")

    # Set the policy to default Deny
    policy = deny_policy()

    # Go through the tokens the team has
    for team_token in tokens:

        # Make sure the token is enabled
        if team_token["token"] == token and team_token["enabled"]:
            now = datetime.datetime.now().timestamp()
            expires = team_token["expires"]

            # Make sure the token is not expired
            if now < float(expires):
                policy = allow_policy(method_arn)

    # If the token exists, is enabled and not expired, then allow
    return policy


def create_token_handler(event=None, context=None):

    """ Handler that creates a token, puts it in
    DynamoDB and returns it to the requester """

    # Get the team from the path parameters
    # and extract the body from the event
    team_id = event["pathParameters"]["team"]
    body = __get_body_from_event(event)

    # Create a new token starting with "sbom-api",
    # create a creation and expiration time
    token = f"sbom-api-{uuid4()}"
    now = datetime.datetime.now()
    later = now + relativedelta(years=1)

    # Get the timestamps to put in the database
    created = now.timestamp()
    expires = later.timestamp()

    # If a token name is given, set that as the name
    # otherwise put in a default
    name = body["name"] if body["name"] else "NoName"

    # Create a data structure representing the token
    # and it's metadata
    token_item = {
        "TeamId": team_id,
        "name": name,
        "created": Decimal(created),
        "expires": Decimal(expires),
        "enabled": True,
        "token": token,
    }

    # Get the dynamodb resource and add the token
    # to the existing team
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TEAM_TOKEN_TABLE_NAME)

    try:
        table.put_item(
            Item=token_item
        )
    except Exception as err:

        # If something happened in AWS that made it where the
        # call could not be completed, send an internal service error.
        return __token_response_obj(
            500, token, f"Request Error from boto3: {err}"
        )

    return __token_response_obj(200, token)


def delete_token_handler(event=None, context=None):

    """ Handler for deleting a token belonging to a given team """

    # Grab the team and the token from the path parameters
    team_id = event["pathParameters"]["team"]
    token = event["pathParameters"]["token"]

    # Get our Team table from DynamoDB
    team_token_table = dynamodb_resource.Table(TEAM_TOKEN_TABLE_NAME)

    try:

        # Delete the token
        team_token_table.delete_item(
            Key={
                "TeamId": team_id,
                "token": token
            },
            ConditionExpression="attribute_exists(TeamId)",
        )

    except ClientError as e:
        return __handle_delete_token_error(
            token, team_id, e
        )

    return __token_response_obj(
        status_code=200,
        token=token,
    )


def update_table(
        key: str,
        team_json: dict,
        team_id: str,
        table: dynamodb_resource.Table,
):
    items = team_json[key]
    for item in items:
        item.update({
            "TeamId": team_id,
        })
        table.put_item(
            Item=item
        )

def register_team_handler(event=None, context=None):

    team_json: dict = __get_body_from_event(event)

    try:
        validate(
            instance=team_json,
            schema=team_schema
        )

        team_id = team_json["Id"]

        # Add the tokens to the token table if there are tokens.
        token_table = dynamodb_resource.Table(TEAM_TOKEN_TABLE_NAME)
        update_table("tokens", team_json, team_id, token_table)
        del team_json["tokens"]

        # Update the members
        member_table = dynamodb_resource.Table(TEAM_MEMBER_TABLE_NAME)
        update_table("members", team_json, team_id, member_table)
        del team_json["members"]

        team_table = dynamodb_resource.Table(TEAM_TABLE_NAME)
        team_table.put_item(Item=team_json)

        return __create_team_response(200, "Team Created")

    except ValidationError as err:
        return __create_team_response(
            500, f"Validation Error: {err}")


def replace_members(team_id: str, new_members: list):

    team_table = dynamodb_resource.Table(TEAM_MEMBER_TABLE_NAME)
    team_query_rsp = team_table.query(
        Select="ALL_ATTRIBUTES",
        KeyConditionExpression="TeamId = :TeamId",
        ExpressionAttributeValues={
            ":TeamId": team_id,
        },
    )

    delete_requests = []
    for item in team_query_rsp["Items"]:
        delete_requests.append({
            'DeleteRequest':{
                'Key': {
                    'TeamId': team_id,
                    'email': item["email"]
                }
            }
        })

    put_requests = []
    for member in new_members:
        put_requests.append({
            'PutRequest': {
                'Item': {
                    'TeamId': team_id,
                    'isTeamLead': member["isTeamLead"],
                    'email': member["email"]
                }
            },
        })

    errors = []

    print(f"Delete Requests: {delete_requests}")
    if len(delete_requests) > 0:
        try:
            dynamodb_resource.batch_write_item(
                RequestItems={
                    'SbomTeamMemberTable': delete_requests
                },
            )
        except ClientError as err:
            errors.append(err)

    print(f"Put Requests: {put_requests}")
    if len(put_requests) > 0:
        try:
            dynamodb_resource.batch_write_item(
                RequestItems={
                    'SbomTeamMemberTable': put_requests
                },
            )
        except ClientError as err:
            errors.append(err)

    return errors if len(errors) < 1 else []


def update_team_handler(event=None, context=None):

    team_json: dict = __get_body_from_event(event)

    print(f"Incoming Team JSON: {team_json}")

    try:
        validate(
            instance=team_json,
            schema=team_schema
        )

        team_id = team_json["Id"]

        if "members" in team_json:
            incoming_members = team_json["members"]
            errors = replace_members(team_id, incoming_members)
            del team_json["members"]
            if len(errors) > 0:
                return __create_team_response(
                    status_code=500,
                    err=dumps(errors)
                )

        team_table = dynamodb_resource.Table(TEAM_TABLE_NAME)
        team_table.delete_item(
            Key={
                "Id": team_id
            }
        )

        team_table.put_item(Item=team_json)

        return __create_team_response(
            status_code=200,
            msg="Team Updated"
        )

    except ValidationError as err:
        return __create_team_response(
            status_code=500,
            err=f"Validation Error: {err}",
        )


def get_team_handler(event=None, context=None):

    team_id = event["pathParameters"]["team"]
    team = __get_team_by_team_id(team_id)

    return __create_team_response(
        status_code=200,
        msg=team
    )


def get_teams_for_id_handler(event=None, context=None):

    """ Handler to get all the teams for a user given their email address """

    user_id = event["queryStringParameters"]['user_id']
    team_table = dynamodb_resource.Table(TEAM_MEMBER_TABLE_NAME)
    team_members_query_rsp = team_table.scan(
        Select="ALL_ATTRIBUTES",
        FilterExpression=Attr("email").eq(user_id),
    )

    teams = team_members_query_rsp["Items"]
    rsp_data = [__get_team_by_team_id(team["TeamId"]) for team in teams]

    return {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body":dumps(rsp_data),
    }


def user_search_handler(event=None, context=None):

    query_params = __get_query_string_params_from_event(event)

    filter_str = query_params["filter"]
    user_filter = f"email ^= \"{filter_str}\""

    response = cognito_client.list_users(
        UserPoolId=environ.get(USER_POOL_NAME_KEY),
        AttributesToGet=[
            'email',
        ],
        Limit=60, # Max is 60
        Filter=user_filter,
    )

    users = response["Users"]
    emails = []
    for user in users:
        attr = user["Attributes"]
        emails.append(attr[0]["Value"])

    return __create_user_search_response_obj(200, dumps(emails))
