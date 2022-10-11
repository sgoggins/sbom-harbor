"""
-> Common Handler Functions
"""

import uuid
from json import dumps, loads
import importlib.resources as pr

import boto3

import cyclonedx.schemas as schemas
from cyclonedx.db.harbor_db_client import HarborDBClient
from cyclonedx.model import EntityType, HarborModel
from cyclonedx.model.codebase import CodeBase
from cyclonedx.model.member import Member
from cyclonedx.model.project import Project
from cyclonedx.model.team import Team

cognito_client = boto3.client("cognito-idp")
team_schema = loads(pr.read_text(schemas, "team.schema.json"))


def _print_values(event: dict, context: dict) -> None:
    print(f"<EVENT event=|{dumps(event, indent=2)}| />")
    print(f"<CONTEXT context=|{context}| />")


def _get_method(event: dict) -> str:
    request_context: dict = event["requestContext"]
    http: dict = request_context["http"]
    return http["method"]


def _extract_id_from_path(param_name: str, event: dict):
    path_params: dict = event["pathParameters"]
    team_id: str = path_params[param_name]
    return team_id


def _extract_team_id_from_qs(event: dict):
    path_params: dict = event["queryStringParameters"]
    team_id: str = path_params["teamId"]
    return team_id


def _extract_project_id_from_qs(event: dict):
    path_params: dict = event["queryStringParameters"]
    team_id: str = path_params["projectId"]
    return team_id


def _should_process_children(event: dict) -> bool:
    try:
        query_params: dict = event["queryStringParameters"]
        return query_params["children"]
    except KeyError:
        return False


def get_db_client():

    """
    -> Get the Db Client.  This has to be done in a function
    -> rather than in module space or Moto can't mock it.
    """

    return HarborDBClient(boto3.resource("dynamodb"))


def _to_codebases(team_id: str, project_id: str, request_body: dict):

    try:
        codebases: list[dict] = request_body["codebases"]
        return [
            CodeBase(
                team_id=team_id,
                codebase_id=codebase.get("id", str(uuid.uuid4())),
                project_id=project_id,
                name=codebase["name"],
                language=codebase["language"],
                build_tool=codebase["buildTool"],
            )
            for codebase in codebases
        ]
    except KeyError as ke:
        print(f"KeyError trying to create CodeBase: {ke}")
        return []


def _to_projects(team_id: str, request_body: dict):

    try:
        projects: list[dict] = request_body["projects"]
        return [
            Project(
                team_id=team_id,
                project_id=project.get("id", str(uuid.uuid4())),
                name=project["name"],
            )
            for project in projects
        ]
    except KeyError:
        return []


def _to_members(team_id: str, request_body: dict):

    try:
        members: list[dict] = request_body["members"]
        return [
            Member(
                team_id=team_id,
                member_id=str(uuid.uuid4()),
                email=member[Member.Fields.EMAIL],
                is_team_lead=member[Member.Fields.IS_TEAM_LEAD],
            )
            for member in members
        ]
    except KeyError:
        return []


def _update_codebases(project: Project, request_body: dict):

    child_key: str = "codebases"
    db_client: HarborDBClient = get_db_client()

    existing_children: dict[str, list[HarborModel]] = project.get_children()
    project.clear_codebases()

    # Extract codebase dicts from the request body in the event
    codebase_dicts: list[dict] = request_body.get(child_key, [])

    # For each codebase dict from the request body.
    for codebase_dict in codebase_dicts:

        # Find the object from DynamoDB in the list of children extracted from
        # -> the Team model object using the child ID from the dict in the request body
        #
        # Pylint complains about the variable 'codebase_id' being declared in a loop and
        # being used in a closure (the lambda in the filter function).  The problem is that
        # codebase_id is changing and Pylint is worried that the lambda is going to contain
        # an old value because it's a closure.  In this case, we are using the value of the
        # lambda immediately, before the next iteration of the loop and therefore the warning
        # is a false positive.
        # pylint: disable=W0640
        codebase_id: str = codebase_dict["id"]
        existing_codebases: list[HarborModel] = existing_children.get(
            EntityType.CODEBASE.value, []
        )

        codebase_filter: filter = filter(
            lambda p: p.entity_id == codebase_id, existing_codebases
        )
        codebases: list[HarborModel] = list(codebase_filter)

        # If no codebases match, then ignore it.
        if codebases:

            # Update the data in the object
            codebase: CodeBase = update_codebase_data(
                team_id=project.team_id,
                project_id=project.entity_id,
                codebase_id=codebase_id,
                codebase_dict=codebase_dict,
                codebase_item=codebases.pop().get_item(),
            )

            # Update the database
            child: CodeBase = db_client.update(codebase)

            # Add the codebase as a child of the project
            project.add_child(child)

    return project


def update_codebase_data(
    team_id: str,
    project_id: str,
    codebase_id: str,
    codebase_dict: dict,
    codebase_item: dict,
):

    """
    -> Update a Codebase
    """

    original_name: str = codebase_item.get(CodeBase.Fields.NAME)
    original_language: str = codebase_item.get(CodeBase.Fields.LANGUAGE)
    original_build_tool: str = codebase_item.get(CodeBase.Fields.BUILD_TOOL)

    # replace only the data in the existing object with the
    # new data from the request body ignoring children
    # Update that object in DynamoDB
    return CodeBase(
        team_id=team_id,
        project_id=project_id,
        codebase_id=codebase_id,
        name=codebase_dict.get(CodeBase.Fields.NAME, original_name),
        language=codebase_dict.get(CodeBase.Fields.LANGUAGE, original_language),
        build_tool=codebase_dict.get(
            CodeBase.Fields.BUILD_TOOL,
            original_build_tool,
        ),
    )


def _update_projects(team: Team, request_body: dict):

    child_key: str = "projects"
    db_client: HarborDBClient = get_db_client()

    existing_children: dict[str, list[HarborModel]] = team.get_children()
    team.clear_child_type(entity_type=EntityType.PROJECT)

    # Extract project dicts from the request body in the event
    project_dicts: list[dict] = request_body.get(child_key, [])

    # For each project dict from the request body:
    for project_dict in project_dicts:

        # Find the object from DynamoDB in the list of children extracted from
        # -> the Team model object using the child ID from the dict in the request body
        #
        # Pylint complains about the variable 'project_id' being declared in a loop and
        # being used in a closure (the lambda in the filter function).  The problem is that
        # project_id is changing and Pylint is worried that the lambda is going to contain
        # an old value because it's a closure.  In this case, we are using the value of the
        # lambda immediately, before the next iteration of the loop and therefore the warning
        # is a false positive.
        # pylint: disable=W0640
        project_id: str = project_dict["id"]
        existing_projects: list[HarborModel] = existing_children.get(
            EntityType.PROJECT.value, []
        )

        project_filter: filter = filter(
            lambda p: p.entity_id == project_id, existing_projects
        )
        projects: list[HarborModel] = list(project_filter)

        # If no projects match, then ignore it.
        if projects:

            # Otherwise, there will only be one matching project
            project_item: dict = projects.pop().get_item()

            original_name: str = project_item.get(Project.Fields.NAME)

            # replace only the data in the existing object with the
            # new data from the request body ignoring children
            # Update that object in DynamoDB
            project: Project = Project(
                team_id=team.team_id,
                project_id=project_id,
                name=project_dict.get(Project.Fields.NAME, original_name),
            )

            team.add_child(db_client.update(project))

    return team


def _update_members(team: Team, request_body: dict):

    child_key: str = "members"
    db_client: HarborDBClient = get_db_client()

    existing_children: dict[str, list[HarborModel]] = team.get_children()
    team.clear_child_type(entity_type=EntityType.MEMBER)

    # Extract project dicts from the request body in the event
    member_dicts: list[dict] = request_body.get(child_key, [])

    # For each member dict from the request body:
    for member_dict in member_dicts:

        # Find the object from DynamoDB in the list of children extracted from
        # -> the Team model object using the child ID from the dict in the request body
        #
        # Pylint complains about the variable 'member_id' being declared in a loop and
        # being used in a closure (the lambda in the filter function).  The problem is that
        # member_id is changing and Pylint is worried that the lambda is going to contain
        # an old value because it's a closure.  In this case, we are using the value of the
        # lambda immediately, before the next iteration of the loop and therefore the warning
        # is a false positive.
        # pylint: disable=W0640
        member_id: str = member_dict["id"]
        existing_members: list[HarborModel] = existing_children.get(child_key, [])
        member_filter: filter = filter(
            lambda p: p.entity_id == member_id, existing_members
        )
        members: list[HarborModel] = list(member_filter)

        # If no members match, then ignore it.
        if members:

            # Otherwise, there will only be one matching member
            member_item: dict = members.pop().get_item()
            original_email: str = member_item.get(Member.Fields.EMAIL)
            original_is_lead: str = member_item.get(Member.Fields.IS_TEAM_LEAD)

            # replace only the data in the existing object with the
            # new data from the request body ignoring children
            # Update that object in DynamoDB
            member: Member = Member(
                team_id=team.team_id,
                member_id=member_id,
                email=member_dict.get(Member.Fields.EMAIL, original_email),
                is_team_lead=member_dict.get(
                    Member.Fields.IS_TEAM_LEAD, original_is_lead
                ),
            )

            team.add_child(db_client.update(member))

    return team