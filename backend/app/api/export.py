import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Match, MatchResult

router = APIRouter(prefix="/matches", tags=["export"])

@router.get("/{match_id}/export.csv")
def export_csv(
    match_id: UUID,
    kind: str = Query(..., regex="^(tracks|possession)$"),
    db: Session = Depends(get_db)
):
    match_obj = db.query(Match).filter(Match.id == match_id).first()
    if not match_obj:
        raise HTTPException(status_code=404, detail="Match not found")

    if match_obj.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"CSV export is only available for 'completed' matches. Current status: '{match_obj.status}'."
        )

    result_row = db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
    if not result_row:
        raise HTTPException(status_code=404, detail="Match results record not found")

    output = io.StringIO()

    if kind == "tracks":
        writer = csv.writer(output)
        writer.writerow([
            "track_id", "team", "role", "detector_hint",
            "duration_s", "distance_m", "avg_x_m", "avg_y_m", "calibration"
        ])
        for track in result_row.tracks:
            writer.writerow([
                track.get("track_id"),
                track.get("team", ""),
                track.get("role", ""),
                track.get("detector_hint", ""),
                track.get("duration_s", 0.0),
                track.get("distance_m", 0.0),
                track.get("avg_pos_m", [0, 0])[0],
                track.get("avg_pos_m", [0, 0])[1],
                result_row.calibration
            ])
        filename = f"match_{match_id}_tracks.csv"

    elif kind == "possession":
        writer = csv.writer(output)
        writer.writerow(["start_s", "end_s", "state"])
        possession = result_row.possession or {}
        for interval in possession.get("intervals", []):
            writer.writerow([
                interval.get("start_s", 0.0),
                interval.get("end_s", 0.0),
                interval.get("state", "unknown")
            ])
        filename = f"match_{match_id}_possession.csv"

    else:
        raise HTTPException(status_code=400, detail="Invalid export kind")

    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
