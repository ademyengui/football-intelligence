from app.schemas import PossessionData, PossessionInterval, PossessionSummary


def compute_possession_from_frames(
    frame_observations: list[dict],
    total_duration_s: float
) -> PossessionData:
    """
    Computes possession intervals and summary statistics from frame observations.
    frame_observations: list of dicts with keys:
       - 't': float
       - 'ball_pos': Optional[Tuple[float, float]] (x, y)
       - 'candidates': List[dict] with keys 'track_id', 'team', 'role', 'foot_pos', 'box_height'
    """
    if not frame_observations:
        return PossessionData(
            intervals=[PossessionInterval(start_s=0.0, end_s=total_duration_s, state="unknown")],
            summary=PossessionSummary(A_pct=50.0, B_pct=50.0, unknown_pct=100.0)
        )

    frame_states: list[tuple[float, str]] = []
    last_ball_pos: tuple[float, float] | None = None
    last_ball_t: float = -1.0

    for obs in frame_observations:
        t = obs['t']
        ball_pos = obs.get('ball_pos')

        if ball_pos is not None:
            last_ball_pos = ball_pos
            last_ball_t = t
        elif last_ball_pos is not None and (t - last_ball_t) <= 1.0:
            ball_pos = last_ball_pos
        else:
            ball_pos = None

        if ball_pos is None:
            frame_states.append((t, "unknown"))
            continue

        bx, by = ball_pos
        best_dist = float('inf')
        best_team = None
        threshold = 5.0  # default threshold in pitch metres / pixels

        for cand in obs.get('candidates', []):
            if cand.get('role') != "outfield" or not cand.get('team'):
                continue
            fx, fy = cand['foot_pos']
            dist = float(((fx - bx) ** 2 + (fy - by) ** 2) ** 0.5)

            # Max distance threshold: 1.5x box height if present, else 5.0 units
            cand_thresh = cand.get('box_height', 0.0) * 1.5 if cand.get('box_height') else 5.0

            if dist < best_dist:
                best_dist = dist
                best_team = cand['team']
                threshold = cand_thresh

        if best_team and best_dist <= threshold:
            frame_states.append((t, best_team))
        else:
            frame_states.append((t, "unknown"))

    # Initial RLE intervals
    intervals: list[dict] = []
    if frame_states:
        curr_state = frame_states[0][1]
        start_t = frame_states[0][0]

        for i in range(1, len(frame_states)):
            t, state = frame_states[i]
            if state != curr_state:
                intervals.append({"start_s": start_t, "end_s": t, "state": curr_state})
                curr_state = state
                start_t = t
        intervals.append({"start_s": start_t, "end_s": frame_states[-1][0], "state": curr_state})

    # Merge intervals shorter than 1.0 second
    changed = True
    while changed and len(intervals) > 1:
        changed = False
        new_intervals = []
        i = 0
        while i < len(intervals):
            curr = intervals[i]
            dur = curr['end_s'] - curr['start_s']
            if dur < 1.0 and len(intervals) > 1:
                changed = True
                # Pick neighbor to merge into
                left_dur = (intervals[i - 1]['end_s'] - intervals[i - 1]['start_s']) if i > 0 else -1.0
                right_dur = (intervals[i + 1]['end_s'] - intervals[i + 1]['start_s']) if i < len(intervals) - 1 else -1.0

                if left_dur >= right_dur and i > 0:
                    # Merge into left
                    new_intervals[-1]['end_s'] = curr['end_s']
                elif i < len(intervals) - 1:
                    # Merge into right
                    intervals[i + 1]['start_s'] = curr['start_s']
                elif i > 0:
                    new_intervals[-1]['end_s'] = curr['end_s']
            else:
                new_intervals.append(curr)
            i += 1
        intervals = new_intervals

    # Convert to Pydantic objects
    possession_intervals = [
        PossessionInterval(
            start_s=round(inv['start_s'], 1),
            end_s=round(inv['end_s'], 1),
            state=inv['state']
        )
        for inv in intervals
    ]

    # Calculate summary percentages
    time_A = 0.0
    time_B = 0.0
    time_unknown = 0.0

    for inv in intervals:
        dur = inv['end_s'] - inv['start_s']
        if inv['state'] == "A":
            time_A += dur
        elif inv['state'] == "B":
            time_B += dur
        else:
            time_unknown += dur

    total_known = time_A + time_B
    total_time = max(total_duration_s, total_known + time_unknown, 0.1)

    if total_known > 0:
        pct_A = round((time_A / total_known) * 100.0, 1)
        pct_B = round(100.0 - pct_A, 1)
    else:
        pct_A = 50.0
        pct_B = 50.0

    pct_unknown = round((time_unknown / total_time) * 100.0, 1)

    return PossessionData(
        intervals=possession_intervals,
        summary=PossessionSummary(
            A_pct=pct_A,
            B_pct=pct_B,
            unknown_pct=pct_unknown
        )
    )
