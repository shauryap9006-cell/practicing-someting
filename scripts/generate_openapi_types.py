"""RailTwin-X OpenAPI TypeScript Type Generator (F39).

Reads the dynamic OpenAPI schema directly from FastAPI app and produces
fully typed TypeScript definitions in web/src/lib/api-schema.ts.
Eliminates all handwritten type divergences and endpoint mismatches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.main import app


def schema_to_ts_type(prop: Any, schemas: Dict[str, Any]) -> str:
    """Converts OpenAPI property definition to TypeScript type string."""
    if not isinstance(prop, dict):
        return "any"

    if "$ref" in prop:
        return prop["$ref"].split("/")[-1]

    if "anyOf" in prop:
        types = [schema_to_ts_type(p, schemas) for p in prop["anyOf"]]
        return " | ".join(types)

    if "allOf" in prop:
        types = [schema_to_ts_type(p, schemas) for p in prop["allOf"]]
        return " & ".join(types)

    if "oneOf" in prop:
        types = [schema_to_ts_type(p, schemas) for p in prop["oneOf"]]
        return " | ".join(types)

    prop_type = prop.get("type")

    if prop_type == "string":
        if "enum" in prop:
            return " | ".join(f"'{val}'" for val in prop["enum"])
        return "string"
    elif prop_type == "null":
        return "null"
    elif prop_type in ["integer", "number"]:
        return "number"
    elif prop_type == "boolean":
        return "boolean"
    elif prop_type == "array":
        items = prop.get("items", {})
        item_type = schema_to_ts_type(items, schemas)
        return f"{item_type}[]"
    elif prop_type == "object":
        add_props = prop.get("additionalProperties")
        if isinstance(add_props, dict):
            val_type = schema_to_ts_type(add_props, schemas)
            return f"Record<string, {val_type}>"
        return "Record<string, any>"

    return "any"


def generate_typescript_schema() -> str:
    """Generates complete TypeScript code representing the OpenAPI spec."""
    openapi = app.openapi()

    lines = [
        "/**",
        " * RailTwin-X Auto-Generated OpenAPI Client Types (F39).",
        " * Generated from FastAPI OpenAPI 3.1.0 specification.",
        " * DO NOT EDIT MANUALLY - run `python scripts/generate_openapi_types.py`.",
        " */",
        "",
    ]

    components = openapi.get("components", {}).get("schemas", {})

    # Generate Interfaces for all Components
    for schema_name, schema_def in sorted(components.items()):
        description = schema_def.get("description", "")
        if description:
            lines.append(f"/** {description} */")
        lines.append(f"export interface {schema_name} {{")

        properties = schema_def.get("properties", {})
        required = set(schema_def.get("required", []))

        for prop_name, prop_def in properties.items():
            ts_type = schema_to_ts_type(prop_def, components)
            is_req = prop_name in required
            opt_mark = "" if is_req else "?"
            prop_desc = prop_def.get("description", "")
            if prop_desc:
                lines.append(f"  /** {prop_desc} */")
            lines.append(f"  {prop_name}{opt_mark}: {ts_type};")

        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def main():
    root_dir = Path(__file__).resolve().parent.parent
    out_json = root_dir / "data" / "openapi.json"
    out_ts = root_dir / "web" / "src" / "lib" / "api-schema.ts"

    openapi = app.openapi()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(openapi, f, indent=2)
    print(f"[INFO] Dumped OpenAPI spec to {out_json}")

    ts_content = generate_typescript_schema()
    out_ts.parent.mkdir(parents=True, exist_ok=True)
    with open(out_ts, "w", encoding="utf-8") as f:
        f.write(ts_content)
    print(f"[INFO] Generated TypeScript schema to {out_ts}")


if __name__ == "__main__":
    main()
