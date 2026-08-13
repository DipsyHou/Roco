"""python -m server  → GUI；python -m server --console → 命令行。"""

import sys


def _main() -> None:
    if "--console" in sys.argv:
        argv = [a for a in sys.argv[1:] if a != "--console"]
        sys.argv = [sys.argv[0], *argv]
        from .ws_server import main

        main()
    else:
        from .server_app import main

        main()


if __name__ == "__main__":
    _main()
