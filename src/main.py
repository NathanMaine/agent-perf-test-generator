import argparse
from .generator import spec_to_config, write_yaml_config


def main():
    parser = argparse.ArgumentParser(description="Perf Test Generator")
    parser.add_argument("--spec", required=True, help="Natural language spec")
    parser.add_argument("--output", required=True, help="Output YAML path")
    args = parser.parse_args()

    config = spec_to_config(args.spec)
    write_yaml_config(config, args.output)
    print(f"Wrote config to {args.output}")


if __name__ == "__main__":
    main()
