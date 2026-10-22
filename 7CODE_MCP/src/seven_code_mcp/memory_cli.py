"""Local-only CLI for 7CODE project memory. No MCP toggle is registered."""
import argparse
from pathlib import Path

from .guard import Guard


def main() -> None:
    p = argparse.ArgumentParser(description="7CODE local project-memory controls")
    p.add_argument("action", choices=["Status", "Enable", "Disable"])
    p.add_argument("--state", required=True, help="Dedicated local .local service directory")
    args = p.parse_args()
    memory = Guard(Path(args.state).resolve()).memory
    if args.action == "Enable":
        result = memory.configure_local(True)
    elif args.action == "Disable":
        result = memory.configure_local(False)
    else:
        result = memory.status()
    print("7CODE MEMORY: " + ("ENABLED" if result["enabled"] else "DISABLED"))
    print("Local database: " + result["database"])
    print("Database exists: " + str(result["database_exists"]))
    if result["enabled"]:
        print("Projects: " + str(result["projects"]))
        print("Checkpoints: " + str(result["checkpoints"]))
        print("Recorded activities: " + str(result["activities"]))


if __name__ == "__main__":
    main()
