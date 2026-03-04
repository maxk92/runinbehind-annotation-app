# RIB Annotation App

Desktop GUI for **manually annotating runs-in-behind (RIB)** from raw DFL Bundesliga
position tracking XML files. Loads full both-team tracking data via the `floodlight`
library, shows all players on a pitch with jersey numbers and motion trails, and lets
you mark segment start/end frames, assign players, and save the result to CSV.

---

## Features

- **File pickers** — select Positions XML, Matchinfo XML, and video independently
- **Pitch panel** — all players (home + away + ball) with 25-frame motion trail,
  quadratic alpha ramp, jersey numbers in centre of each dot
- **Segment annotation** — two-click workflow: Start Segment / End Segment
- **Player assignment** — click any player on the pitch during or after annotation
- **Segment timeline** — coloured rectangle blocks with draggable boundaries;
  click a block to activate it for player re-assignment
- **Team colour pickers** — customise home/away colours; segments update live
- **Undo** — removes the last completed segment (or cancels an in-progress annotation)
- **Zoom / pan** — scroll wheel + middle-mouse pan on the timeline strip
- **Video sync** — video and tracking data stay in sync; click the timeline to seek

---

## Requirements

- Python 3.11 or 3.12
- PySide6 ≥ 6.7
- matplotlib ≥ 3.9
- numpy ≥ 1.26
- pandas ≥ 2.2
- floodlight ≥ 1.0
- lxml ≥ 5.0

Install with:
```bash
pip install -r requirements.txt
```

---

## Setup and running

### Linux / macOS

```bash
cd rib-annotation-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows (with Python)

```bat
cd rib-annotation-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

No path configuration is needed — output files are written to an `output/` subfolder
next to `app.py` automatically.

---

## Data requirements

| Input | Description |
|---|---|
| `positions_raw_DFL-COM-*.xml` | DFL position tracking XML (25 fps, x/y in metres) |
| `matchinformation_DFL-COM-*.xml` | DFL match information XML (teamsheets, etc.) |
| Video file (optional) | Full-match video at 25 fps (.mp4, .mkv, .avi, .mov) |

Both XML files are standard DFL Open Data format as distributed by the
Deutsche Fußball Liga (e.g., Bundesliga Open Data 2022/23 season).

---

## Usage

### Loading data

1. Click **…** next to "Positions" and select the positions XML file.
2. Click **…** next to "Matchinfo" and select the matchinfo XML file.
3. Optionally click **…** next to "Video" and select the video file.
4. Select the **Half** (firstHalf / secondHalf).
5. Click **Load**. The pitch panel populates with all players; loading may take a
   few seconds for large XML files.

### Video alignment

The video is loaded with offset = 0 (tracking frame 0 = video start). If the video
does not begin at kick-off, use **"Set offset here"** in the video panel:
seek the video to the moment that corresponds to tracking frame 0, then click the
button. The offset applies for the rest of the session.

### Annotating a run-in-behind

1. Navigate the video to the start of the run. Click **▶ Start Segment**. An orange
   dashed line appears on the timeline at that frame.
2. *(Optional)* Click the player on the pitch panel to assign them immediately.
3. Navigate to the end of the run. Click **■ End Segment**. The segment appears as
   a coloured block on the timeline.
   - If a player was selected, the block shows their jersey number in the team colour.
   - If no player was selected, the block is grey — you can assign one later.

### Assigning or re-assigning a player

- **During annotation**: click the player on the pitch before pressing End Segment.
- **After annotation**: click the segment block in the timeline to activate it (white
  border), then click the player on the pitch.

### Adjusting boundaries

Drag the left or right edge of a segment block in the timeline. The video seeks to
the boundary frame as you drag. Release to commit.

### Customising team colours

Click **Home colour** or **Away colour** to open a colour picker. All segment blocks
assigned to that team update immediately.

### Saving

Click **Save**. The annotations are written to:
```
output/{positions_filename}_{half}_rib.csv
```

### Undo

- If an annotation is in progress, **Undo** cancels it.
- Otherwise, **Undo** removes the last completed segment.

---

## Output CSV format

| Column | Description |
|---|---|
| `segment_id` | Sequential integer starting at 0 |
| `half` | `"firstHalf"` or `"secondHalf"` |
| `start_frame` | Start frame index (0-based within the half) |
| `end_frame` | End frame index (inclusive) |
| `start_time_s` | Start time in seconds (`start_frame / 25`) |
| `end_time_s` | End time in seconds |
| `duration_s` | Segment duration in seconds |
| `player` | Player name from DFL teamsheet (empty if unassigned) |
| `player_jid` | Jersey number |
| `team` | `"Home"` or `"Away"` (empty if unassigned) |
| `annotation_source` | Always `"manual"` |

---

## Packaging for Windows (standalone .exe)

Build the executable **on a Windows machine** using PyInstaller:

```bat
cd rib-annotation-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller rib_annotation_app.spec
```

The output is `dist\RibAnnotationApp\RibAnnotationApp.exe` plus all required DLLs in
the same folder. Copy the entire `dist\RibAnnotationApp\` directory to the target
machine — no Python installation needed there. Output CSVs will be written to
`dist\RibAnnotationApp\output\`.

> **Note**: PyInstaller cross-compilation is not supported — the `.exe` must be built
> on Windows. If you encounter "missing module" errors during the build, add the module
> to `hiddenimports` in `rib_annotation_app.spec` and rebuild.
>
> `lxml` is required by floodlight for DFL XML parsing. If the bundled build fails to
> parse XML files, add `"lxml._elementpath"` and `"lxml.etree"` to `hiddenimports`
> (already included in the provided spec).
