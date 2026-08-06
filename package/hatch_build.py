from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from pathlib import Path


class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data["infer_tag"] = True
        build_data["pure_python"] = False

        package_root = Path(self.root) / "package"
        for pattern in ("pocketsocket_server*.so", "pocketsocket_server*.pyd"):
            for artifact in package_root.glob(pattern):
                build_data.setdefault("force_include", {})[str(artifact)] = artifact.name
