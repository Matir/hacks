import argparse
import asyncio
import contextlib
import json
import os

from google.adk.agents import LlmAgent
from google.adk.sessions.sqlite_session_service import SqliteSessionService

from trashdig.agents.utils.helpers import load_prompt, run_agent
from trashdig.config import get_config


async def seed_vuln(
    agent: LlmAgent, cwe_id: str, session_service: SqliteSessionService, data_dir: str
) -> None:
    """Seeds a single vulnerability entry using the LLM.

    Args:
        agent: The LLM agent to use.
        cwe_id: The CWE ID to seed.
        session_service: The ADK session service.
        data_dir: The base directory for VulnDB.
    """
    print(f"[*] Seeding {cwe_id}...")  # noqa: T201
    prompt_template = load_prompt("seed_vulndb.md")
    prompt = prompt_template.format(cwe_id=cwe_id)

    response = await run_agent(
        agent=agent,
        prompt=prompt,
        session_id=f"seed_{cwe_id}",
        session_service=session_service,
    )

    if "---CONTENT---" not in response:
        print(f"[!] Invalid response for {cwe_id}: Missing separator")  # noqa: T201
        return

    json_part, md_part = response.split("---CONTENT---", 1)

    try:
        metadata = json.loads(json_part.strip())
    except json.JSONDecodeError:
        # Try to find JSON in the part (sometimes LLM adds text before/after)
        try:
            start = json_part.find("{")
            end = json_part.rfind("}") + 1
            metadata = json.loads(json_part[start:end])
        except Exception as e:  # noqa: BLE001
            print(f"[!] Failed to parse JSON for {cwe_id}: {e}")  # noqa: T201
            print(f"Raw JSON part: {json_part}")  # noqa: T201
            return

    vuln_id = metadata["id"]
    content_filename = f"{vuln_id.lower().replace('-', '_')}.md"
    metadata["content_path"] = f"content/{content_filename}"

    # Save Markdown
    content_dir = os.path.join(data_dir, "content")
    os.makedirs(content_dir, exist_ok=True)
    with open(  # noqa: ASYNC230
        os.path.join(content_dir, content_filename), "w", encoding="utf-8"
    ) as f:
        f.write(md_part.strip())

    # Update metadata.json
    metadata_path = os.path.join(data_dir, "metadata.json")
    existing_metadata = []
    if os.path.exists(metadata_path):  # noqa: ASYNC240
        with open(metadata_path, encoding="utf-8") as f, contextlib.suppress(  # noqa: ASYNC230
            json.JSONDecodeError
        ):
            existing_metadata = json.load(f)

    # Remove existing entry if it has the same ID
    existing_metadata = [m for m in existing_metadata if m["id"] != vuln_id]
    existing_metadata.append(metadata)

    with open(metadata_path, "w", encoding="utf-8") as f:  # noqa: ASYNC230
        json.dump(existing_metadata, f, indent=2)

    print(f"[+] Successfully seeded {cwe_id}")  # noqa: T201


async def main() -> None:
    """Main entry point for the seeding script."""
    parser = argparse.ArgumentParser(description="Seed the VulnDB with CWE information.")
    parser.add_argument(
        "cwes", nargs="+", help="List of CWE IDs to seed (e.g. CWE-89 CWE-79)"
    )
    args = parser.parse_args()

    config = get_config()
    agent_config = config.get_agent_config(
        "hunter"
    )  # Use hunter config as default for LLM

    # Base data dir for vulndb
    vulndb_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "vulndb"
    )
    os.makedirs(vulndb_dir, exist_ok=True)

    session_db = os.path.join(config.data_dir, "seed_sessions.db")
    session_service = SqliteSessionService(db_path=session_db)

    agent = LlmAgent(
        name="seeder",
        model=agent_config.model,
        instruction="You are a security research assistant helping to build a vulnerability database.",
    )

    for cwe in args.cwes:
        await seed_vuln(agent, cwe, session_service, vulndb_dir)


if __name__ == "__main__":
    asyncio.run(main())
