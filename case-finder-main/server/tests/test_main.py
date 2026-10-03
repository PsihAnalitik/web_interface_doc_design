from app.main import app


def test_start_process_exposes_file_picker_in_openapi():
    schema = app.openapi()

    assert "/start_process" in schema["paths"]
    assert "/upload_info" not in schema["paths"]

    request_body = schema["paths"]["/start_process"]["post"]["requestBody"]
    multipart_schema = request_body["content"]["multipart/form-data"]["schema"]
    form_schema_name = multipart_schema["$ref"].rsplit("/", 1)[-1]
    form_schema = schema["components"]["schemas"][form_schema_name]

    files_schema = form_schema["properties"]["files"]
    assert files_schema["type"] == "array"
    assert files_schema["items"] == {"type": "string", "format": "binary"}
    assert "files" not in form_schema.get("required", [])
