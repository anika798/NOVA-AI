"""
NOVA Module Entry Point (python -m nova)
"""
import sys
from nova.bootstrap import ApplicationBootstrap


def main() -> None:
    app = ApplicationBootstrap()
    success = app.initialize()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
