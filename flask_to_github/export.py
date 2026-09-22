from __future__ import annotations

import argparse
import fnmatch
import json
import posixpath
import re
import shutil
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen


TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:9050/"
DEFAULT_CONFIG_PATH = TOOL_ROOT / "config.json"
LINK_PATTERN = re.compile(r"\b(?P<attr>href|src)=(?P<quote>['\"])(?P<url>.*?)(?P=quote)", re.IGNORECASE)
DEFAULT_IGNORE_PATTERNS = (".git", ".git/**", "**/.git", "**/.git/**")


class SiteExportError(Exception):
    pass


@dataclass(frozen=True)
class Route:
    path: str
    fragment: str = ""


@dataclass(frozen=True)
class ExportConfig:
    base_url: str = DEFAULT_BASE_URL
    output_dir: Path = Path("github-pages")
    max_pages: int = 300
    stylesheet_path: str = "/static/style.css"
    stylesheet_output: str = "style.css"
    manifest_file: str = ".generated-pages.json"
    ignore_patterns: tuple[str, ...] = DEFAULT_IGNORE_PATTERNS
    project_root: Path = Path(".")

    @property
    def output_root(self) -> Path:
        return self.output_dir.resolve()

    @property
    def manifest_path(self) -> Path:
        return self.output_root / self.manifest_file


def path_from_config(value: str | None, config_path: Path | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    base = config_path.parent if config_path else Path.cwd()
    return (base / path).resolve() if not path.is_absolute() else path


def load_config(config_path: Path | None = None) -> ExportConfig:
    config_path = config_path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        return ExportConfig(
            output_dir=(Path.cwd() / "github-pages").resolve(),
            project_root=Path.cwd(),
        )

    data = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = path_from_config(data.get("project_root"), config_path, config_path.parent)
    return ExportConfig(
        base_url=data.get("base_url", DEFAULT_BASE_URL),
        output_dir=path_from_config(data.get("output_dir"), config_path, project_root / "github-pages"),
        max_pages=int(data.get("max_pages", 300)),
        stylesheet_path=data.get("stylesheet_path", "/static/style.css"),
        stylesheet_output=data.get("stylesheet_output", "style.css"),
        manifest_file=data.get("manifest_file", ".generated-pages.json"),
        ignore_patterns=tuple(data.get("ignore_patterns", DEFAULT_IGNORE_PATTERNS)),
        project_root=project_root,
    )


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "flask-to-github/1.0"})
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def fetch_required_text(url: str) -> str:
    try:
        return fetch_text(url)
    except HTTPError as error:
        raise SiteExportError(f"Could not fetch {url}: HTTP {error.code} {error.reason}") from error
    except URLError as error:
        if isinstance(error.reason, ConnectionRefusedError):
            raise SiteExportError(
                f"Connection refused for {url}.\n"
                "Start the Flask app separately, then retry the export or deploy command."
            ) from error
        raise SiteExportError(f"Could not fetch {url}: {error.reason}") from error


def relative_to_output(path: Path, config: ExportConfig) -> str:
    return path.relative_to(config.output_root).as_posix()


def output_file_for(path: str, config: ExportConfig) -> Path:
    clean_path = path.strip("/")
    return config.output_root / ("index.html" if not clean_path else clean_path + "/index.html")


def is_ignored(relative_path: str, config: ExportConfig) -> bool:
    clean_path = relative_path.strip("/")
    return bool(clean_path) and any(fnmatch.fnmatch(clean_path, pattern) for pattern in config.ignore_patterns)


def normalize_route(raw_url: str, base_url: str, config: ExportConfig) -> Route | None:
    if not raw_url or raw_url.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    base = urlparse(base_url)
    absolute = urlparse(urljoin(base_url, raw_url))
    if absolute.scheme not in {"http", "https"} or absolute.netloc != base.netloc:
        return None
    if absolute.path.startswith(posixpath.dirname(config.stylesheet_path.rstrip("/")) + "/"):
        return None
    clean_url, fragment = urldefrag(absolute.geturl())
    path = urlparse(clean_url).path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") + "/"
    if is_ignored(relative_to_output(output_file_for(path, config), config), config):
        return None
    return Route(path, fragment)


def relative_page_href(from_path: str, to_route: Route) -> str:
    from_dir = from_path.strip("/") or "."
    target_dir = to_route.path.strip("/") or "."
    relative = posixpath.relpath(target_dir, from_dir)
    result = "./" if relative == "." else relative.rstrip("/") + "/"
    return result + (f"#{to_route.fragment}" if to_route.fragment else "")


def relative_asset_href(from_path: str, asset_name: str) -> str:
    from_dir = from_path.strip("/") or "."
    relative = posixpath.relpath(asset_name, from_dir)
    return asset_name if relative == "." else relative


def rewrite_links(html: str, current_path: str, base_url: str, config: ExportConfig) -> str:
    stylesheet_url = urljoin(base_url, config.stylesheet_path)

    def replace(match: re.Match[str]) -> str:
        attr, quote, raw_url = match.group("attr"), match.group("quote"), match.group("url")
        if raw_url in {config.stylesheet_path, stylesheet_url}:
            return f"{attr}={quote}{relative_asset_href(current_path, config.stylesheet_output)}{quote}"
        route = normalize_route(raw_url, base_url, config)
        if route is None:
            return match.group(0)
        return f"{attr}={quote}{relative_page_href(current_path, route)}{quote}"

    return LINK_PATTERN.sub(replace, html)


def page_routes_from(html: str, base_url: str, config: ExportConfig) -> list[Route]:
    return [
        route
        for match in LINK_PATTERN.finditer(html)
        if match.group("attr").lower() == "href"
        for route in [normalize_route(match.group("url"), base_url, config)]
        if route is not None
    ]


def cleanup_previous_run(config: ExportConfig) -> None:
    if not config.manifest_path.is_file():
        return
    for relative_path in json.loads(config.manifest_path.read_text(encoding="utf-8")):
        path = (config.output_root / relative_path).resolve()
        try:
            path.relative_to(config.output_root)
        except ValueError:
            continue
        if path.is_file():
            path.unlink()
    config.manifest_path.unlink(missing_ok=True)


def cleanup_ignored_paths(config: ExportConfig) -> None:
    if not config.output_root.exists():
        return
    for path in sorted(config.output_root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if is_ignored(relative_to_output(path, config), config):
            shutil.rmtree(path) if path.is_dir() else path.unlink(missing_ok=True)


def export_site(config: ExportConfig) -> list[Path]:
    base_url = config.base_url.rstrip("/") + "/"
    css = fetch_required_text(urljoin(base_url, config.stylesheet_path))
    first_page = fetch_required_text(base_url)
    config.output_root.mkdir(parents=True, exist_ok=True)
    cleanup_previous_run(config)
    cleanup_ignored_paths(config)

    stylesheet_path = config.output_root / config.stylesheet_output
    stylesheet_path.parent.mkdir(parents=True, exist_ok=True)
    stylesheet_path.write_text(css, encoding="utf-8")
    written = [stylesheet_path]
    seen: set[str] = set()
    pending: deque[Route] = deque([Route("/")])
    while pending and len(seen) < config.max_pages:
        route = pending.popleft()
        if route.path in seen:
            continue
        try:
            html = first_page if route.path == "/" else fetch_text(urljoin(base_url, route.path.lstrip("/")))
        except (HTTPError, URLError) as error:
            print(f"skip {route.path}: {error}")
            seen.add(route.path)
            continue
        seen.add(route.path)
        output_path = output_file_for(route.path, config)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rewrite_links(html, route.path, base_url, config), encoding="utf-8")
        written.append(output_path)
        pending.extend(next_route for next_route in page_routes_from(html, base_url, config) if next_route.path not in seen)
    if pending:
        print(f"stopped after {config.max_pages} pages; {len(pending)} routes remain")
    cleanup_ignored_paths(config)
    config.manifest_path.write_text(json.dumps(sorted(relative_to_output(path, config) for path in written), indent=2) + "\n", encoding="utf-8")
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a Flask site as static files.")
    parser.add_argument("config", nargs="?", help="JSON configuration file")
    parser.add_argument("--base-url")
    parser.add_argument("--output-dir")
    parser.add_argument("--max-pages", type=int)
    return parser