from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from npv_studio.core.runtime import bundled_resource_root


PROJECT_ROOT = bundled_resource_root()
TEMPLATE_ROOT = PROJECT_ROOT / "templates"


class TemplateRenderer:
    def __init__(self, template_root: Path = TEMPLATE_ROOT) -> None:
        self.environment = Environment(
            loader=FileSystemLoader(str(template_root)),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        self.environment.filters["lua_string"] = lambda value: json.dumps(
            str(value), ensure_ascii=False
        )

    def render(self, name: str, **context: object) -> str:
        return self.environment.get_template(name).render(**context)
