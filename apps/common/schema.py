"""Describe the wire format applied by EventHub's renderer and error handler."""


def document_envelope(result, **kwargs):
    for path, methods in result["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = operation["responses"]
            for status, response in responses.items():
                media = response.get("content", {}).get("application/json")
                if status.startswith("2") and media and "schema" in media:
                    media["schema"] = {
                        "type": "object",
                        "required": ["data"],
                        "properties": {"data": media["schema"]},
                    }
            errors = {"429": "Rate limit exceeded"}
            if operation.get("security") and {} not in operation["security"]:
                errors.update({"401": "Authentication required", "403": "Access denied"})
            if "{" in path:
                errors["404"] = "Object missing or not visible"
            if method in {"post", "put", "patch"}:
                errors["400"] = "Invalid request or authentication mode"
            if method == "delete" or path.endswith(
                ("/register/", "/publish/", "/cancel/", "/complete/")
            ):
                if "/users/" not in path:
                    errors["409"] = "Operation conflicts with the current resource state"
            for status, description in errors.items():
                responses.setdefault(
                    status,
                    {
                        "description": description,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/EventHubError"}
                            }
                        },
                    },
                )
    result["components"]["schemas"]["EventHubError"] = {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                    "details": {},
                },
            }
        },
    }
    return result
