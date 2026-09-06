from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from pathlib import Path
import sysconfig


class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data["infer_tag"] = True
        build_data["pure_python"] = False

        package_root = Path(self.root) / "package"
        suffix = sysconfig.get_config_var("EXT_SUFFIX")
        if not suffix:
            raise RuntimeError("Python did not provide a native extension suffix")
        artifact = package_root / f"pocketsocket_server{suffix}"
        if not artifact.is_file():
            if version == "editable":
                return
            raise RuntimeError(
                f"Missing native extension for this interpreter: {artifact.name}. "
                "Run server/compile.py pyd with this Python before building the wheel."
            )
        build_data.setdefault("force_include", {})[str(artifact)] = artifact.name
