from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "infra" / "template.yaml"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _construct_intrinsic(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    raise TypeError(f"unsupported CloudFormation node: {node!r}")


CloudFormationLoader.add_multi_constructor("!", _construct_intrinsic)


def _load_template():
    return yaml.load(TEMPLATE_PATH.read_text("utf-8"), Loader=CloudFormationLoader)


def _route_events(template):
    routes = []
    for resource in template["Resources"].values():
        if resource.get("Type") != "AWS::Serverless::Function":
            continue
        events = resource.get("Properties", {}).get("Events", {})
        for event in events.values():
            if event.get("Type") != "HttpApi":
                continue
            properties = event["Properties"]
            routes.append(
                (
                    properties["Method"],
                    properties["Path"],
                    properties.get("Auth", {}).get("Authorizer", "NONE"),
                )
            )
    return routes


def test_operational_routes_require_iam_and_reads_remain_public():
    template = _load_template()
    routes = _route_events(template)
    route_auth = {(method, path): authorizer for method, path, authorizer in routes}

    protected_routes = {
        ("PATCH", "/shelters/{id}"),
        ("POST", "/reports"),
        ("POST", "/scenarios/{id}/colonies/{cid}/dispatch"),
        ("POST", "/dispatches/{dispatch_id}/approve"),
        ("GET", "/dispatches"),
        ("POST", "/dispatches/{dispatch_id}/ack"),
    }
    public_read_routes = {
        ("GET", "/scenarios/{id}/roads"),
        ("GET", "/scenarios/{id}/plans"),
        ("GET", "/scenarios/{id}/unreachable"),
        ("GET", "/shelters"),
        ("GET", "/models/card"),
        ("GET", "/scenarios/{id}/forecast"),
        ("GET", "/scenarios/{id}/flood"),
        ("GET", "/scenarios/{id}/whatif"),
    }

    assert len(routes) == 14
    assert len(route_auth) == len(routes)
    assert set(route_auth) == protected_routes | public_read_routes
    assert all(route_auth[route] == "AWS_IAM" for route in protected_routes)
    assert all(route_auth[route] == "NONE" for route in public_read_routes)
    assert template["Globals"]["HttpApi"]["Auth"]["EnableIamAuthorizer"] is True


def test_ml_function_permissions_cover_only_published_artifact_paths():
    template = _load_template()
    function = template["Resources"]["ForecastFunction"]["Properties"]
    statements = [
        statement
        for policy in function["Policies"]
        for statement in policy.get("Statement", [])
    ]
    get_statement = next(statement for statement in statements if statement["Action"] == "s3:GetObject")
    get_resources = set(get_statement["Resource"])
    assert any(resource.endswith("/models/registry.json") for resource in get_resources)
    assert any(resource.endswith("/models/inundation/v1/whatif/*") for resource in get_resources)
    assert any(resource.endswith("/models/inundation/v1/ladder/*") for resource in get_resources)
    assert any(resource.endswith("/scenarios/yamuna-2023-07/forecasts/*") for resource in get_resources)
    assert any(resource.endswith("/scenarios/yamuna-2023-07/depth/*") for resource in get_resources)
    assert len(get_resources) == 5

    list_statement = next(statement for statement in statements if statement["Action"] == "s3:ListBucket")
    assert list_statement["Condition"]["StringLike"]["s3:prefix"] == [
        "scenarios/yamuna-2023-07/forecasts/*"
    ]
