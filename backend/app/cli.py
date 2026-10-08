import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db import SessionLocal
from app.models import Match, MatchResult
from app.schemas import MatchResultsResponse

def import_results(file_path: str, name: str = None, db: Session = None):
    """Imports an external results.json file after validating against Pydantic schema."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        results = MatchResultsResponse.model_validate(data)
    except ValidationError as ve:
        print(f"Validation Error in '{file_path}':", file=sys.stderr)
        for err in ve.errors():
            loc = " -> ".join(str(p) for p in err['loc'])
            print(f"  - [{loc}]: {err['msg']}", file=sys.stderr)
        sys.exit(1)

    db_created = False
    if db is None:
        db = SessionLocal()
        db_created = True
    try:
        match_id = uuid.uuid4()
        filename = name or os.path.basename(file_path)

        match_obj = Match(
            id=match_id,
            original_filename=filename,
            video_path=None,
            status="completed",
            progress=100,
            progress_message="Imported results JSON",
            pipeline_mode="imported",
            video_fps=results.meta.sample_fps,
            video_width=results.meta.frame_size[0],
            video_height=results.meta.frame_size[1],
            video_duration_s=results.meta.duration_s,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(match_obj)

        result_row = MatchResult(
            match_id=match_id,
            schema_version=results.schema_version,
            calibration=results.meta.calibration,
            summary=results.possession.summary.model_dump(),
            tracks=[t.model_dump() for t in results.tracks],
            heatmaps=results.heatmaps.model_dump(),
            possession=results.possession.model_dump(),
            artifacts=[artifact.model_dump() for artifact in results.artifacts],
            trajectories=None
        )
        db.add(result_row)
        db.commit()

        print(f"Successfully imported '{filename}' as match ID: {match_id}")
    finally:
        if db_created:
            db.close()

def export_schema():
    """Generates and writes docs/results.schema.json from MatchResultsResponse schema."""
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    schema_path = os.path.abspath(os.path.join(docs_dir, "results.schema.json"))

    schema_json = MatchResultsResponse.model_json_schema()
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema_json, f, indent=2)

    print(f"Exported JSON schema to: {schema_path}")

def main():
    parser = argparse.ArgumentParser(description="Football Intelligence Dashboard CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # import-results
    import_parser = subparsers.add_parser("import-results", help="Import external results JSON file")
    import_parser.add_argument("--file", required=True, help="Path to results.json file")
    import_parser.add_argument("--name", required=False, help="Optional display name for match")

    # export-schema
    subparsers.add_parser("export-schema", help="Export Pydantic results schema to docs/results.schema.json")

    args = parser.parse_args()

    if args.command == "import-results":
        import_results(args.file, args.name)
    elif args.command == "export-schema":
        export_schema()

if __name__ == "__main__":
    main()
