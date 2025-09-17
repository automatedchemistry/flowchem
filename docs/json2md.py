#!/usr/bin/env python
import json
import os


def openapi_json_to_markdown(json_path: str, output_md_path: str):
    with open(json_path, 'r') as f:
        data = json.load(f)

    lines = []
    # Paths
    lines.append("## Endpoints\n")
    for path, methods in data.get('paths', {}).items():
        for method, details in methods.items():
            lines.append(f"### `{method.upper()} {path}`\n")
            lines.append(f"**Summary:** {details.get('summary', '')}")
            lines.append(f"**Description:** {details.get('description', '')}")
            tags = details.get("tags", [])
            if tags:
                lines.append(f"**Tags:** {', '.join(tags)}")
            lines.append(f"**Operation ID:** `{details.get('operationId', '')}`")
            lines.append("")

            # Parameters
            parameters = details.get("parameters", [])
            if parameters:
                lines.append("**Query Parameters:**")
                for param in parameters:
                    schema = param.get("schema", {})
                    name = param.get("name")
                    param_type = schema.get("type", "string")
                    default = schema.get("default", "")
                    required = param.get("required", False)
                    lines.append(f"- `{name}` ({param_type}, {'required' if required else 'optional'}, default = `{default}`)")
                lines.append("")

            # Responses
            lines.append("**Responses:**")
            for code, resp in details.get("responses", {}).items():
                lines.append(f"- `{code}`: {resp.get('description', '')}")
            lines.append("\n---\n")

    # Components
    components = data.get("components", {}).get("schemas", {})
    if components:
        lines.append("## Components\n")
        for name, schema in components.items():
            lines.append(f"### `{name}` ({schema.get('type', 'object')})\n")
            if schema.get("required"):
                lines.append(f"**Required:** {', '.join(schema['required'])}")
            if schema.get("description"):
                lines.append(f"**Description:** {schema['description']}")
            lines.append("\n**Properties:**")
            for prop_name, prop_details in schema.get("properties", {}).items():
                prop_type = prop_details.get("type", "object")
                default = prop_details.get("default", None)
                lines.append(f"- `{prop_name}`: {prop_type}" + (f" (default: `{default}`)" if default is not None else ""))
            lines.append("\n---\n")

    # Write to file
    with open(output_md_path, 'w') as f:
        f.write("\n".join(lines))

    print(f"Markdown saved to {output_md_path}")


# Example usage
if __name__ == "__main__":
    directory = "user-guides/reference/api"
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                openapi_json_to_markdown(json_path=root + '/' + file,
                                         output_md_path=root + '/' + file.split('.')[0] + '.md')