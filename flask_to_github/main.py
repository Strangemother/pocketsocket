from __future__ import annotations

import argparse
from pathlib import Path

from deploy import build_parser as build_deploy_parser, deploy_site
from export import ExportConfig, SiteExportError, build_parser as build_export_parser, export_site, load_config, path_from_config


TOOL_ROOT = Path(__file__).resolve().parent


def config_with_overrides(config: ExportConfig, parsed: argparse.Namespace, config_path: Path | None) -> ExportConfig:
    values = {**config.__dict__}
    for name in ("base_url", "output_dir", "max_pages"):
        value = getattr(parsed, name, None)
        if value is not None:
            values[name] = path_from_config(value, config_path, config.project_root / "github-pages") if name == "output_dir" else value
    return ExportConfig(**values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export or deploy a Flask site to GitHub Pages.")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", parents=[build_export_parser()], add_help=False)
    export.set_defaults(command="export")
    deploy = commands.add_parser("deploy", parents=[build_deploy_parser()], add_help=False)
    deploy.set_defaults(command="deploy")
    return parser


def main(arguments: list[str] | None = None) -> int:
    parsed = build_parser().parse_args(arguments)
    config_path = Path(parsed.config).expanduser().resolve() if parsed.config else TOOL_ROOT / "config.json"
    config = load_config(config_path)
    try:
        config = config_with_overrides(config, parsed, config_path)
        if parsed.command == "export":
            written = export_site(config)
            for path in written:
                print(path.relative_to(config.output_root).as_posix())
            print(f"wrote {len(written)} files")
            return 0
        deploy_site(config, remote=parsed.remote, branch=parsed.branch, message=parsed.message, dry_run=parsed.dry_run)
        return 0
    except SiteExportError as error:
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())