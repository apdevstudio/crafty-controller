import sys
import subprocess


class Install:
    @staticmethod
    def is_venv():
        return hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

    def do_install(self):
        # are we in a venv?
        if not self.is_venv():
            print("Crafty Requires a venv to install")
            sys.exit(1)

        # do our pip install
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("Crafty has installed it's dependencies, please restart Crafty")
        sys.exit(0)


installer = Install()
