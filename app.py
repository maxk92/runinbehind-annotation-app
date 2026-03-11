"""
RIB Annotation App — manually annotate runs-in-behind from DFL position data.

Usage:
    cd rib-annotation-app
    python app.py
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from annotation_timeline import AnnotationTimeline
from config import AWAY_COLOR, FPS, HOME_COLOR
from data_manager import DataManager
from pitch_panel import PitchPanel
from video_panel import VideoPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RIB Annotation App")
        self.resize(1400, 900)

        self._dm = DataManager()

        # Annotation state
        self._annotating:    bool = False
        self._pending_start: int  = -1
        self._pending_player: dict | None = None   # player clicked while annotating

        # Post-annotation state
        self._active_seg_idx: int = -1   # segment activated for player assignment

        # Team colours (mutable)
        self._home_color = HOME_COLOR
        self._away_color = AWAY_COLOR

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # ── Row 1: file pickers ────────────────────────────────────────
        file_row = QHBoxLayout()
        file_row.setSpacing(6)

        self._pos_edit = QLineEdit(self)
        self._pos_edit.setPlaceholderText("Positions XML…")
        self._pos_edit.setMinimumWidth(200)
        btn_pos = QPushButton("…", self)
        btn_pos.setFixedWidth(28)
        btn_pos.clicked.connect(self._browse_positions)
        file_row.addWidget(QLabel("Positions:", self))
        file_row.addWidget(self._pos_edit)
        file_row.addWidget(btn_pos)

        file_row.addSpacing(8)

        self._mat_edit = QLineEdit(self)
        self._mat_edit.setPlaceholderText("Matchinfo XML…")
        self._mat_edit.setMinimumWidth(200)
        btn_mat = QPushButton("…", self)
        btn_mat.setFixedWidth(28)
        btn_mat.clicked.connect(self._browse_matinfo)
        file_row.addWidget(QLabel("Matchinfo:", self))
        file_row.addWidget(self._mat_edit)
        file_row.addWidget(btn_mat)

        file_row.addSpacing(8)

        self._vid_edit = QLineEdit(self)
        self._vid_edit.setPlaceholderText("Video file…")
        self._vid_edit.setMinimumWidth(160)
        btn_vid = QPushButton("…", self)
        btn_vid.setFixedWidth(28)
        btn_vid.clicked.connect(self._browse_video)
        file_row.addWidget(QLabel("Video:", self))
        file_row.addWidget(self._vid_edit)
        file_row.addWidget(btn_vid)

        root.addLayout(file_row)

        # ── Row 2: load controls + colour pickers + save ───────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        ctrl_row.addWidget(QLabel("Half:", self))
        self._half_combo = QComboBox(self)
        self._half_combo.addItems(["firstHalf", "secondHalf"])
        self._half_combo.setFixedWidth(110)
        ctrl_row.addWidget(self._half_combo)

        btn_load = QPushButton("Load", self)
        btn_load.setFixedWidth(80)
        btn_load.clicked.connect(self._on_load)
        ctrl_row.addWidget(btn_load)

        ctrl_row.addSpacing(16)

        # Team colour pickers
        self._btn_home_color = QPushButton("Home colour", self)
        self._btn_home_color.setFixedWidth(100)
        self._btn_home_color.clicked.connect(self._pick_home_color)
        self._apply_btn_color(self._btn_home_color, self._home_color)
        ctrl_row.addWidget(self._btn_home_color)

        self._btn_away_color = QPushButton("Away colour", self)
        self._btn_away_color.setFixedWidth(100)
        self._btn_away_color.clicked.connect(self._pick_away_color)
        self._apply_btn_color(self._btn_away_color, self._away_color)
        ctrl_row.addWidget(self._btn_away_color)

        ctrl_row.addStretch()

        self._btn_undo = QPushButton("Undo", self)
        self._btn_undo.setFixedWidth(70)
        self._btn_undo.setToolTip("Remove the last completed segment (or cancel in-progress)")
        self._btn_undo.clicked.connect(self._on_undo)
        ctrl_row.addWidget(self._btn_undo)

        btn_load_annot = QPushButton("Load Annotations", self)
        btn_load_annot.setFixedWidth(130)
        btn_load_annot.setToolTip("Load a previously saved annotation CSV")
        btn_load_annot.clicked.connect(self._on_load_annotations)
        ctrl_row.addWidget(btn_load_annot)

        btn_save = QPushButton("Save", self)
        btn_save.setFixedWidth(80)
        btn_save.clicked.connect(self._on_save)
        ctrl_row.addWidget(btn_save)

        root.addLayout(ctrl_row)

        # ── Main splitter: top (video+pitch) / bottom (timeline) ──────
        v_splitter = QSplitter(Qt.Orientation.Vertical, self)
        v_splitter.setStretchFactor(0, 7)
        v_splitter.setStretchFactor(1, 3)

        # Top: video container (left) + pitch (right)
        self._video_panel = VideoPanel(self)
        self._pitch_panel = PitchPanel(self)

        # Wrap video panel so we can add the annotate button below it
        vid_container = QWidget(self)
        vid_layout    = QVBoxLayout(vid_container)
        vid_layout.setContentsMargins(0, 0, 0, 0)
        vid_layout.setSpacing(4)
        vid_layout.addWidget(self._video_panel, stretch=1)

        # ── Annotate button row (below video, with the offset controls) ─
        annot_row = QHBoxLayout()
        self._btn_annotate = QPushButton("▶  Start Segment", self)
        self._btn_annotate.setMinimumHeight(38)
        self._btn_annotate.setMinimumWidth(150)
        self._btn_annotate.setStyleSheet("font-size: 13px;")
        self._btn_annotate.clicked.connect(self._on_annotate)
        annot_row.addWidget(self._btn_annotate)
        annot_row.addStretch()
        vid_layout.addLayout(annot_row)

        h_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        h_splitter.addWidget(vid_container)
        h_splitter.addWidget(self._pitch_panel)
        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 2)
        v_splitter.addWidget(h_splitter)

        # Bottom: timeline + info label
        bottom        = QWidget(self)
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 2, 0, 2)
        bottom_layout.setSpacing(2)

        self._timeline = AnnotationTimeline(self)
        bottom_layout.addWidget(self._timeline, stretch=1)

        self._seg_info = QLabel("No segments yet", self)
        self._seg_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(self._seg_info)

        v_splitter.addWidget(bottom)
        v_splitter.setSizes([660, 240])

        root.addWidget(v_splitter, stretch=1)

        # ── Signal wiring ─────────────────────────────────────────────
        self._video_panel.frame_changed.connect(self._on_frame_changed)
        self._timeline.seek_requested.connect(self._video_panel.seek_to_frame)
        self._timeline.segment_activated.connect(self._on_segment_activated)
        self._timeline.boundary_dragged.connect(self._on_boundary_dragged)
        self._timeline.boundary_committed.connect(self._on_boundary_committed)
        self._timeline.delete_requested.connect(self._on_delete_requested)
        self._pitch_panel.player_clicked.connect(self._on_player_clicked)

        self.setStatusBar(QStatusBar(self))

    # ------------------------------------------------------------------
    # Colour utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_btn_color(btn: QPushButton, hex_color: str) -> None:
        """Style a button to reflect the chosen colour."""
        qc   = QColor(hex_color)
        text = "black" if qc.lightness() > 128 else "white"
        btn.setStyleSheet(
            f"background-color: {hex_color}; color: {text}; font-size: 12px;"
        )

    def _pick_home_color(self) -> None:
        qc = QColorDialog.getColor(QColor(self._home_color), self, "Home team colour")
        if qc.isValid():
            self._home_color = qc.name()
            self._apply_btn_color(self._btn_home_color, self._home_color)
            self._pitch_panel.set_team_colors(self._home_color, self._away_color)
            self._refresh_segment_colors()

    def _pick_away_color(self) -> None:
        qc = QColorDialog.getColor(QColor(self._away_color), self, "Away team colour")
        if qc.isValid():
            self._away_color = qc.name()
            self._apply_btn_color(self._btn_away_color, self._away_color)
            self._pitch_panel.set_team_colors(self._home_color, self._away_color)
            self._refresh_segment_colors()

    def _refresh_segment_colors(self) -> None:
        """Repaint all segment boxes whose colour was team-derived."""
        for i, seg in enumerate(self._dm.segments):
            if seg.team:
                color = self._home_color if seg.team == "Home" else self._away_color
                self._timeline.update_segment(i, seg.player_jid, color)

    def _team_color(self, team: str) -> str:
        return self._home_color if team == "Home" else self._away_color

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------

    def _browse_positions(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Positions XML", "", "XML files (*.xml);;All files (*)"
        )
        if path:
            self._pos_edit.setText(path)

    def _browse_matinfo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Matchinfo XML", "", "XML files (*.xml);;All files (*)"
        )
        if path:
            self._mat_edit.setText(path)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video", "",
            "Video files (*.mp4 *.mkv *.avi *.mov);;All files (*)"
        )
        if path:
            self._vid_edit.setText(path)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def _on_load(self) -> None:
        pos_path = self._pos_edit.text().strip()
        mat_path = self._mat_edit.text().strip()
        vid_path = self._vid_edit.text().strip()
        half     = self._half_combo.currentText()

        if not pos_path or not mat_path:
            self.statusBar().showMessage("Select both Positions XML and Matchinfo XML.", 4000)
            return

        self.statusBar().showMessage("Loading position data — please wait…")
        QApplication.processEvents()

        try:
            self._dm.load(pos_path, mat_path, half)
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", str(exc))
            self.statusBar().showMessage("Load failed.", 4000)
            return

        # Sync half combo
        current = self._half_combo.currentText()
        self._half_combo.blockSignals(True)
        self._half_combo.clear()
        self._half_combo.addItems(self._dm.available_halves)
        if current in self._dm.available_halves:
            self._half_combo.setCurrentText(current)
        self._half_combo.blockSignals(False)

        # Reset state
        self._annotating     = False
        self._pending_start  = -1
        self._pending_player = None
        self._active_seg_idx = -1
        self._btn_annotate.setText("▶  Start Segment")
        self._btn_annotate.setStyleSheet("font-size: 13px;")

        # Init pitch
        home_jids = self._dm.get_jersey_ids("Home")
        away_jids = self._dm.get_jersey_ids("Away")
        self._pitch_panel.initialize(home_jids, away_jids,
                                     self._home_color, self._away_color)

        # Init timeline
        self._timeline.set_range(self._dm.first_frame, self._dm.last_frame)

        # Load video (offset calibrated interactively via "Set offset here")
        if vid_path and os.path.exists(vid_path):
            self._video_panel.load_video(vid_path, offset_frames=0)
        elif vid_path:
            self.statusBar().showMessage(
                f"Video not found: {vid_path} — data loaded, no video.", 6000
            )

        n = self._dm.n_frames
        self.statusBar().showMessage(
            f"Loaded {half} — {n} frames ({n / FPS:.1f} s)   "
            "Use 'Set offset here' to align video with tracking frame 0.", 6000
        )
        self._update_seg_info()

    # ------------------------------------------------------------------
    # Frame update
    # ------------------------------------------------------------------

    def _on_frame_changed(self, frame: int) -> None:
        if self._dm.xy_home is None:
            return
        frame_idx = max(self._dm.first_frame, min(self._dm.last_frame, frame))
        home_x, home_y, away_x, away_y, ball_x, ball_y = \
            self._dm.get_trail_positions(frame_idx)
        if home_x is not None:
            self._pitch_panel.update_frame(
                home_x, home_y, away_x, away_y, ball_x, ball_y
            )
        self._timeline.update_cursor(frame_idx)

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def _on_annotate(self) -> None:
        if self._dm.xy_home is None:
            self.statusBar().showMessage("Load data first.", 3000)
            return

        if not self._annotating:
            # Start
            self._pending_start  = max(self._dm.first_frame,
                                       min(self._dm.last_frame,
                                           self._video_panel.current_frame()))
            self._pending_player = None
            self._annotating     = True
            self._active_seg_idx = -1        # deactivate any active segment
            self._timeline.set_active_segment(-1)
            self._btn_annotate.setText("■  End Segment")
            self._btn_annotate.setStyleSheet(
                "background-color: #C0392B; color: white; "
                "font-size: 13px; font-weight: bold;"
            )
            self._timeline.set_pending_start(self._pending_start)
            self.statusBar().showMessage(
                f"Recording… start frame {self._pending_start}.  "
                "Click a player on the pitch to assign, then 'End Segment'.", 0
            )
        else:
            # End
            end_frame = max(self._dm.first_frame,
                            min(self._dm.last_frame,
                                self._video_panel.current_frame()))
            start = min(self._pending_start, end_frame)
            end   = max(self._pending_start, end_frame)

            seg = self._dm.add_segment(start, end)
            seg_idx = len(self._dm.segments) - 1

            # Determine label and color from pending player
            color = "#AAAAAA"
            label = ""
            if self._pending_player:
                pp  = self._pending_player
                color = self._team_color(pp["team"])
                label = pp["jID"]
                self._dm.assign_player(seg_idx, pp["player"], pp["jID"], pp["team"])

            self._timeline.clear_pending_start()
            self._timeline.add_segment(start, end, seg.segment_id, label, color)

            self._annotating     = False
            self._pending_start  = -1
            self._pending_player = None
            self._btn_annotate.setText("▶  Start Segment")
            self._btn_annotate.setStyleSheet("font-size: 13px;")

            dur = (end - start) / FPS
            player_str = f"  [{label}]" if label else ""
            self.statusBar().showMessage(
                f"Segment #{seg.segment_id} added{player_str}: "
                f"frames {start}–{end} ({dur:.2f} s)", 5000
            )
            self._update_seg_info()

    def _on_undo(self) -> None:
        if self._annotating:
            self._annotating     = False
            self._pending_start  = -1
            self._pending_player = None
            self._btn_annotate.setText("▶  Start Segment")
            self._btn_annotate.setStyleSheet("font-size: 13px;")
            self._timeline.clear_pending_start()
            self.statusBar().showMessage("Annotation cancelled.", 3000)
            return

        seg = self._dm.remove_last_segment()
        if seg is not None:
            if self._active_seg_idx == len(self._dm.segments):
                self._active_seg_idx = -1
            self._timeline.remove_last_segment()
            self.statusBar().showMessage(f"Removed segment #{seg.segment_id}.", 3000)
        else:
            self.statusBar().showMessage("No segments to undo.", 3000)
        self._update_seg_info()

    # ------------------------------------------------------------------
    # Player assignment
    # ------------------------------------------------------------------

    def _on_player_clicked(self, team: str, player_idx: int) -> None:
        info = self._dm.get_player_at_index(team, player_idx)
        if not info:
            return

        if self._annotating:
            # Store for when End Segment is pressed
            self._pending_player = info
            self.statusBar().showMessage(
                f"Player selected: {info['player']} (#{info['jID']}, {team})  "
                "— click 'End Segment' to finalise.", 0
            )
            return

        if self._active_seg_idx >= 0:
            seg_idx = self._active_seg_idx
            self._dm.assign_player(seg_idx, info["player"], info["jID"], team)
            color = self._team_color(team)
            self._timeline.update_segment(seg_idx, info["jID"], color)
            self.statusBar().showMessage(
                f"Segment #{self._dm.segments[seg_idx].segment_id} → "
                f"{info['player']} (#{info['jID']}, {team})", 4000
            )
            self._update_seg_info()

    # ------------------------------------------------------------------
    # Segment activation (click on body in timeline)
    # ------------------------------------------------------------------

    def _on_segment_activated(self, seg_idx: int) -> None:
        self._active_seg_idx = seg_idx
        if 0 <= seg_idx < len(self._dm.segments):
            seg = self._dm.segments[seg_idx]
            self.statusBar().showMessage(
                f"Segment #{seg.segment_id} active  "
                f"[{seg.start_frame}–{seg.end_frame}]  "
                f"Player: {seg.player_name or '—'}  "
                "Click a player to assign.", 0
            )

    # ------------------------------------------------------------------
    # Segment deletion
    # ------------------------------------------------------------------

    def _delete_segment(self, seg_idx: int) -> None:
        if not (0 <= seg_idx < len(self._dm.segments)):
            return
        seg = self._dm.remove_segment(seg_idx)
        self._timeline.remove_segment(seg_idx)
        if self._active_seg_idx == seg_idx:
            self._active_seg_idx = -1
        elif self._active_seg_idx > seg_idx:
            self._active_seg_idx -= 1
        self.statusBar().showMessage(f"Deleted segment #{seg.segment_id}.", 3000)
        self._update_seg_info()

    def _on_delete_requested(self, seg_idx: int) -> None:
        menu = QMenu(self)
        act_delete = menu.addAction("Delete segment")
        if menu.exec(QCursor.pos()) == act_delete:
            self._delete_segment(seg_idx)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete and self._active_seg_idx >= 0:
            self._delete_segment(self._active_seg_idx)
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Boundary drag
    # ------------------------------------------------------------------

    def _on_boundary_dragged(self, seg_idx: int, side: str, frame: int) -> None:
        self._dm.update_boundary(seg_idx, side, frame)
        self._video_panel.seek_to_frame(frame)

    def _on_boundary_committed(self, seg_idx: int, side: str, frame: int) -> None:
        self._dm.update_boundary(seg_idx, side, frame)
        self._update_seg_info()

    # ------------------------------------------------------------------
    # Load annotations
    # ------------------------------------------------------------------

    def _on_load_annotations(self) -> None:
        if self._dm.xy_home is None:
            self.statusBar().showMessage("Load position data first.", 3000)
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Load Annotation CSV", "", "CSV files (*.csv);;All files (*)"
        )
        if not path:
            return

        try:
            new_segs = self._dm.load_annotations(path)
        except Exception as exc:
            QMessageBox.critical(self, "Load annotations failed", str(exc))
            return

        for seg in new_segs:
            color = self._team_color(seg.team) if seg.team else "#AAAAAA"
            label = seg.player_jid or ""
            self._timeline.add_segment(
                seg.start_frame, seg.end_frame, seg.segment_id, label, color
            )

        self.statusBar().showMessage(
            f"Loaded {len(new_segs)} annotation(s) from {os.path.basename(path)}", 5000
        )
        self._update_seg_info()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        if self._dm.xy_home is None:
            self.statusBar().showMessage("Load data first.", 3000)
            return
        if not self._dm.segments:
            self.statusBar().showMessage("No segments to save.", 3000)
            return
        try:
            out_path = self._dm.save()
            self.statusBar().showMessage(
                f"Saved {len(self._dm.segments)} segments → {out_path}", 6000
            )
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_seg_info(self) -> None:
        n = len(self._dm.segments)
        if n == 0:
            self._seg_info.setText("No segments yet")
            return
        last = self._dm.segments[-1]
        dur  = (last.end_frame - last.start_frame) / FPS
        player_str = f"  Player: {last.player_name} (#{last.player_jid}, {last.team})" \
                     if last.player_name else ""
        self._seg_info.setText(
            f"{n} segment{'s' if n != 1 else ''}  |  "
            f"Last: #{last.segment_id}  {last.start_frame}–{last.end_frame}"
            f"  ({dur:.2f} s){player_str}"
        )


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main() -> None:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from PySide6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(40,  40,  40))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base,            QColor(30,  30,  30))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(50,  50,  50))
    palette.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button,          QColor(60,  60,  60))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(42,  130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
