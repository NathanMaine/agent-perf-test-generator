import yaml
from typing import Dict


def spec_to_config(spec: str) -> Dict:
    """
    Very naive mapping from free text to config.
    In a real project, you would parse the spec more robustly or use an LLM.
    """
    return {
        "execution": [
            {
                "concurrency": 100,
                "hold-for": "2m",
                "scenario": "simple-get",
            }
        ],
        "scenarios": {
            "simple-get": {
                "requests": [
                    {
                        "url": "http://localhost:8001/api/demo",
                        "method": "GET",
                    }
                ]
            }
        },
    }


def write_yaml_config(config: Dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)
