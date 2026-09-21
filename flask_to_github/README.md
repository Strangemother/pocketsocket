# Flask to GitHub Pages

Copy this directory into a Flask project, edit `config.json`, and run it from
the project root:

```sh
python flask_to_github/main.py export
python flask_to_github/main.py deploy --dry-run
```

`project_root` is the Git working tree used by deployment. Relative paths in
the config are resolved from the directory containing `config.json`.

The exporter writes directory-index pages, rewrites same-site links and the
configured stylesheet to relative paths, and keeps generated files in the
manifest for cleanup on the next export. Use `--base-url`, `--output-dir`, and
`--max-pages` to override the export settings from the command line.