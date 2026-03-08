#!/usr/bin/env python3
"""
Author - Stephen Abkin, Class of 2027, Cohort J
Date - 05/04/2025

zlp_scheduler.py — ZLP 100-minute window finder with minimum conflict reporting.

Approach:
  Slide a 100-minute window across every weekday in 5-min steps.
  For each window position, assume students can freely re-pick sections
  to dodge overlaps. A conflict is only "unavoidable" when *every* section
  of a course collides with that window.

Key terms:
  - "conflict" --> unavoidable: no section avoids the window.
  - "blocked" --> still doable but some sections are eliminated.
  - " L" suffix --> overlap caused solely by a lab, not the lecture.

Lab rule:
  A lab is only recognized when Lab_Days, Lab_Start, and Lab_Duration
  are ALL filled
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import pandas as pd
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# ── Time grid & validation constants ─────────────────────────
# The window slides from 08:00 to 16:10 in 5-min increments.
# 16:10 is the latest start where a 100-min block still ends
# before a typical 18:00 evening cutoff.
DAY_LETTERS = "MTWRF"
DAY_NAMES = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "R": "Thursday", "F": "Friday"}

GRID_START, GRID_END = 8 * 60, 16 * 60 + 10   # 08:00 – 16:10 in minutes
BLOCK_LEN = 100   # ZLP meeting length (minutes)
STEP_MIN = 5   # sliding-window step size

# Regexes for validating spreadsheet cell values
CRS_RE = re.compile(r"^[A-Z]{4}$")
NUM_RE = re.compile(r"^\d{3}[Ll]?$")
TIME_RE = re.compile(r"^(2[0-3]|1\d|0\d):([0-5]\d)$")
DAYS_RE = re.compile(r"^[MTWRF]+$", re.I)

DEFAULT_SHEET = "sections.xlsx"
OUT_XLSX = "zlp_results.xlsx"

# ── Data model ───────────────────────────────────────────────
# A course has several Options (sections a student could pick).
# Each Option bundles its meetings together (e.g. lecture + lab)
# so they're treated as inseparable when checking overlaps.
@dataclass(frozen=True)
class Meeting:
    days: str
    start: int
    dur: int
    label: str  # e.g. "MEEN 221" or "MEEN 221L"

@dataclass(frozen=True)
class Option:
    course: str
    meetings: Tuple[Meeting, ...]  # all meetings you'd attend if you pick this section

# ── Time helpers ─────────────────────────────────────────────
def to_minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])

def to_hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"

def overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    """Half-open interval overlap: [a0,a1) vs [b0,b1)."""
    return max(a[0], b[0]) < min(a[1], b[1])

# ── Spreadsheet loading ─────────────────────────────────────
# Reads .xlsx/.xls/.csv. Lab columns are optional — a lab is
# only attached when all three Lab_* fields have values, so
# courses without labs just leave those columns blank/missing.
def rows_from_file(path: str) -> List[dict]:
    import pandas as pd

    def norm_cell(x) -> str:
        return "" if pd.isna(x) else str(x).strip()

    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(p, engine="openpyxl")
    elif p.suffix.lower() == ".csv":
        df = pd.read_csv(p)
    else:
        raise ValueError("file must be .xlsx, .xls, or .csv")

    need = ["Subject", "Number", "Days", "Start", "Duration"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise ValueError(f"missing columns: {', '.join(miss)}")

    has_lab_cols = all(c in df.columns for c in ["Lab_Days", "Lab_Start", "Lab_Duration"])

    out: List[dict] = []
    for _, r in df.iterrows():
        subj = norm_cell(r["Subject"]).upper()
        num = norm_cell(r["Number"])
        days = norm_cell(r["Days"]).upper()
        start = norm_cell(r["Start"])

        dur_raw = r["Duration"]
        if pd.isna(dur_raw) or str(dur_raw).strip() == "":
            duration = ""
        else:
            duration = str(int(float(dur_raw))).strip()

        row = {
            "Subject": subj,
            "Number": num,
            "Days": days,
            "Start": start,
            "Duration": duration,
            "Lab_Days": "",
            "Lab_Start": "",
            "Lab_Duration": "",
        }

        if has_lab_cols:
            lab_days_cell = norm_cell(r["Lab_Days"]).upper()
            lab_start_cell = norm_cell(r["Lab_Start"])

            lab_dur_raw = r["Lab_Duration"]
            lab_dur_cell = "" if pd.isna(lab_dur_raw) or str(lab_dur_raw).strip() == "" else str(int(float(lab_dur_raw))).strip()

            # Lab present ONLY if all three are filled
            if lab_days_cell and lab_start_cell and lab_dur_cell:
                row["Lab_Days"] = lab_days_cell
                row["Lab_Start"] = lab_start_cell
                row["Lab_Duration"] = lab_dur_cell

        out.append(row)

    return out

def validate_meeting(days: str, start: str, dur: str) -> Tuple[str, int, int]:
    """Validate and parse a meeting spec: days, start HH:MM, duration minutes."""
    days = days.upper()
    if not DAYS_RE.fullmatch(days):
        raise ValueError("days must be combo of MTWRF")
    if not TIME_RE.fullmatch(start):
        raise ValueError("start must be HH:MM 24-hour")
    if not dur.isdigit() or int(dur) <= 0:
        raise ValueError("duration must be positive int")
    st = to_minutes(start)
    return days, st, int(dur)

def add_row_as_option(row: dict, sections: Dict[str, List[Option]]) -> bool:
    """Parse one spreadsheet row into an Option (with bundled lab if present)."""
    subj = row["Subject"]
    num = row["Number"]
    code = f"{subj} {num}"

    try:
        if not CRS_RE.fullmatch(subj) or not NUM_RE.fullmatch(num):
            raise ValueError("course code malformed (e.g. MEEN 221)")

        lec_days, lec_st, lec_dur = validate_meeting(row["Days"], row["Start"], row["Duration"])
        meetings: List[Meeting] = [Meeting(lec_days, lec_st, lec_dur, code)]

        # Bundle the lab into this option only when all three fields exist
        lab_days = str(row.get("Lab_Days", "")).strip().upper()
        lab_start = str(row.get("Lab_Start", "")).strip()
        lab_dur = str(row.get("Lab_Duration", "")).strip()

        if lab_days and lab_start and lab_dur:
            ld, ls, ldur = validate_meeting(lab_days, lab_start, lab_dur)
            meetings.append(Meeting(ld, ls, ldur, f"{code} (Lab)"))

        sections.setdefault(code, []).append(Option(course=code, meetings=tuple(meetings)))
        return True

    except ValueError as err:
        print(f"Error in {code}: {err}")
        return False

# ── Overlap detection ────────────────────────────────────────
# Because lecture + lab are bundled in the same Option, checking
# any meeting in the bundle catches both kinds of collision.
def option_overlaps_block(opt: Option, day: str, blk: Tuple[int, int]) -> bool:
    """Does any meeting in this option collide with the block on this day?"""
    for m in opt.meetings:
        if day in m.days and overlaps((m.start, m.start + m.dur), blk):
            return True
    return False

# ── Lab-only labeling ────────────────────────────────────────
# When an overlap is caused exclusively by a lab (not the
# lecture), we append " L" so the user knows the conflict
# might be resolvable by swapping lab sections alone.
def is_lab_meeting(m: Meeting) -> bool:
    return "(LAB)" in m.label.upper()

def overlap_type_for_option(opt: Option, day: str, blk: Tuple[int, int]) -> Tuple[bool, bool]:
    """
    Returns (lec_overlaps, lab_overlaps) for this option on this day/block.
    """
    lec_overlaps = False
    lab_overlaps = False
    for m in opt.meetings:
        if day in m.days and overlaps((m.start, m.start + m.dur), blk):
            if is_lab_meeting(m):
                lab_overlaps = True
            else:
                lec_overlaps = True
    return lec_overlaps, lab_overlaps

def should_mark_lab_only(course: str, day: str, blk: Tuple[int, int], sections_all: Dict[str, List[Option]], mode: str) -> bool:
    """Return True when every overlapping option collides only via its lab."""
    opts = sections_all.get(course, [])
    if not opts:
        return False

    info: List[Tuple[bool, bool, bool]] = []
    for opt in opts:
        lec_ov, lab_ov = overlap_type_for_option(opt, day, blk)
        ov = lec_ov or lab_ov
        info.append((ov, lec_ov, lab_ov))

    if mode == "conflict":
        # All options overlap; mark lab-only only if every overlap is lab-only
        if not all(ov for (ov, _, _) in info):
            return False
        return all((not lec_ov) and lab_ov for (_, lec_ov, lab_ov) in info)

    if mode == "blocked":
        # Some overlap + some clear; mark lab-only if ALL overlapping options are lab-only
        any_overlap = any(ov for (ov, _, _) in info)
        any_clear = any((not ov) for (ov, _, _) in info)
        if not (any_overlap and any_clear):
            return False
        overlapping = [(lec_ov, lab_ov) for (ov, lec_ov, lab_ov) in info if ov]
        return all((not lec_ov) and lab_ov for (lec_ov, lab_ov) in overlapping)

    return False

# ── Per-block scoring ────────────────────────────────────────
# For one candidate window, classify every course as clear,
# blocked (some sections lost), or unavoidable conflict (all
# sections lost). The "score" is the count of unavoidable ones.
def best_conflicts_and_blocked_for_block(
    day: str,
    st: int,
    sections_all: Dict[str, List[Option]]
) -> Tuple[int, List[str], List[str]]:
    blk = (st, st + BLOCK_LEN)

    conflicts_raw: List[str] = []
    blocked_raw: List[str] = []

    for course, opts in sections_all.items():
        any_overlap = any(option_overlaps_block(opt, day, blk) for opt in opts)
        any_clear = any(not option_overlaps_block(opt, day, blk) for opt in opts)

        if not any_clear:
            conflicts_raw.append(course)
        elif any_overlap:
            blocked_raw.append(course)

    conflicts_raw = sorted(set(conflicts_raw))
    blocked_raw = sorted(set(blocked_raw))

    conflicts: List[str] = []
    for c in conflicts_raw:
        if should_mark_lab_only(c, day, blk, sections_all, mode="conflict"):
            conflicts.append(f"{c} L")
        else:
            conflicts.append(c)

    blocked: List[str] = []
    for c in blocked_raw:
        if should_mark_lab_only(c, day, blk, sections_all, mode="blocked"):
            blocked.append(f"{c} L")
        else:
            blocked.append(c)

    return len(conflicts_raw), conflicts, blocked

# ── Report generation ────────────────────────────────────────
# Builds two outputs:
#   1. Terminal printout of the best contiguous start-time ranges.
#   2. Excel workbook with a color-scaled heatmap (rows=times,
#      cols=days) and a ranked table of top windows (col H+).
def generate_reports(
    sections_all: Dict[str, List[Option]],
    sheet_name: str = "ScheduleData",
    title: str = ""
) -> None:

    starts = list(range(GRID_START, GRID_END + 1, STEP_MIN))
    time_rows = [to_hhmm(s) for s in starts]

    heat_rows = {d: [] for d in DAY_LETTERS}

    conflict_map: Dict[Tuple[str, int], List[str]] = {}
    blocked_map: Dict[Tuple[str, int], List[str]] = {}
    score_map: Dict[Tuple[str, int], int] = {}

    for d in DAY_LETTERS:
        for s in starts:
            score, conflicts, blocked = best_conflicts_and_blocked_for_block(d, s, sections_all)
            conflict_map[(d, s)] = conflicts
            blocked_map[(d, s)] = blocked
            score_map[(d, s)] = score
            heat_rows[d].append(score)

    df_heat = pd.DataFrame(heat_rows, index=time_rows)
    df_heat.index.name = "StartTime"

    def group_contiguous_starts(
        day: str,
        score: int,
        st_list: List[int]
    ) -> List[Tuple[int, int, str, int, int, int, str, int, str]]:
        """Merge adjacent 5-min starts into contiguous ranges for cleaner output.""" 
        st_list = sorted(st_list)
        out: List[Tuple[int, int, str, int, int, int, str, int, str]] = []
        if not st_list:
            return out

        first = prev = st_list[0]
        count = 1

        for x in st_list[1:]:
            if x == prev + STEP_MIN:
                prev = x
                count += 1
            else:
                conflicts_str = ", ".join(conflict_map[(day, first)])
                blocked_list = blocked_map[(day, first)]
                blocked_count = len(blocked_list)
                blocked_str = ", ".join(blocked_list)
                out.append((score, -count, day, first, prev, count, conflicts_str, blocked_count, blocked_str))
                first = prev = x
                count = 1

        conflicts_str = ", ".join(conflict_map[(day, first)])
        blocked_list = blocked_map[(day, first)]
        blocked_count = len(blocked_list)
        blocked_str = ", ".join(blocked_list)
        out.append((score, -count, day, first, prev, count, conflicts_str, blocked_count, blocked_str))
        return out

    ranges: List[Tuple[int, int, str, int, int, int, str, int, str]] = []
    for d in DAY_LETTERS:
        by_score: Dict[int, List[int]] = {}
        for s in starts:
            sc = score_map[(d, s)]
            by_score.setdefault(sc, []).append(s)
        for sc, st_list in by_score.items():
            ranges.extend(group_contiguous_starts(d, sc, st_list))

    ranges.sort(key=lambda t: (t[0], t[7], t[3], DAY_LETTERS.index(t[2])))

    selected = [t for t in ranges if t[0] <= 2]
    if len(selected) < 10:
        need = 10 - len(selected)
        extras = [t for t in ranges if t[0] > 2]
        selected.extend(extras[:need])

    print(f"\n=== Meeting start-time ranges {title} ===")
    print("Includes all ranges with score <= 2; if fewer than 10, filled with next best ranges.\n")
    for i, (score, _, d, first, last, _, _, _, _) in enumerate(selected, 1):
        start_range = to_hhmm(first) if first == last else f"{to_hhmm(first)}–{to_hhmm(last)}"
        print(f"{i:2d}. {DAY_NAMES[d]:9s}   start: {start_range}    score={score}")

    out_path = Path(__file__).with_name(OUT_XLSX)

    def write_fresh():
        with pd.ExcelWriter(out_path, engine="openpyxl") as w:
            df_heat.to_excel(w, sheet_name=sheet_name)

    # If the file exists but is corrupt, catch the error and recreate it
    if out_path.exists():
        try:
            wb_existing = load_workbook(out_path)
            if sheet_name in wb_existing.sheetnames:
                del wb_existing[sheet_name]
                wb_existing.save(out_path)

            with pd.ExcelWriter(out_path, engine="openpyxl", mode="a") as w:
                df_heat.to_excel(w, sheet_name=sheet_name)

        except Exception as e:
            print(f"[xlsx warning] {out_path.name} is not a valid .xlsx ({e}). Recreating.")
            try:
                out_path.unlink()
            except Exception:
                pass
            write_fresh()
    else:
        write_fresh()

    wb = load_workbook(out_path)
    ws = wb[sheet_name]

    center = Alignment(horizontal="center", vertical="center")

    ws.freeze_panes = "B2"
    ws.cell(row=1, column=1).font = Font(bold=True)
    ws.cell(row=1, column=1).alignment = center

    for c in range(2, 2 + len(DAY_LETTERS)):
        hdr = ws.cell(row=1, column=c)
        day_letter = hdr.value
        if day_letter in DAY_NAMES:
            hdr.value = f"{day_letter} ({DAY_NAMES[day_letter]})"
        hdr.font = Font(bold=True)
        hdr.alignment = center

    ws.column_dimensions["A"].width = 10
    for r in range(2, 2 + len(time_rows)):
        ws.cell(row=r, column=1).alignment = center

    for c in range(2, 2 + len(DAY_LETTERS)):
        ws.column_dimensions[get_column_letter(c)].width = 14
        for r in range(2, 2 + len(time_rows)):
            ws.cell(row=r, column=c).alignment = center

    start_cell = ws.cell(row=2, column=2).coordinate
    end_cell = ws.cell(row=1 + len(time_rows), column=1 + len(DAY_LETTERS)).coordinate
    rng = f"{start_cell}:{end_cell}"

    rule = ColorScaleRule(
        start_type="num", start_value=0, start_color="63BE7B",
        mid_type="percentile", mid_value=50, mid_color="FFEB84",
        end_type="max", end_color="F8696B"
    )
    ws.conditional_formatting.add(rng, rule)

    top_col = 8  # H
    top_row = 1

    max_clear_rows = 300
    max_clear_cols = 20
    for rr in range(top_row, top_row + max_clear_rows):
        for cc in range(top_col, top_col + max_clear_cols):
            ws.cell(row=rr, column=cc).value = None

    headers = [
        "Rank", "Day", "Start range", "End range",
        "Range length (starts)", "Score (conflicts)",
        "Conflicting courses", "# Blocked Courses", "Blocked courses"
    ]
    for j, h in enumerate(headers):
        cell = ws.cell(row=top_row, column=top_col + j, value=h)
        cell.font = Font(bold=True)
        cell.alignment = center

    for i, (score, _, d, first, last, count, conflicts_str, blocked_count, blocked_str) in enumerate(selected, 1):
        if first == last:
            start_range = to_hhmm(first)
            end_range = to_hhmm(first + BLOCK_LEN)
        else:
            start_range = f"{to_hhmm(first)}–{to_hhmm(last)}"
            end_range = f"{to_hhmm(first + BLOCK_LEN)}–{to_hhmm(last + BLOCK_LEN)}"

        row_vals = [
            i,
            DAY_NAMES[d],
            start_range,
            end_range,
            count,
            score,
            conflicts_str,
            blocked_count,
            blocked_str
        ]

        rr = top_row + i
        for j, val in enumerate(row_vals):
            cell = ws.cell(row=rr, column=top_col + j, value=val)
            cell.alignment = center

    widths = [6, 12, 16, 16, 20, 16, 35, 16, 120]
    for j, w in enumerate(widths):
        ws.column_dimensions[get_column_letter(top_col + j)].width = w

    wb.save(out_path)
    print(f"\nExcel report updated: {out_path} (sheet: {sheet_name})")

# ── Entry point ──────────────────────────────────────────────
def main() -> None:
    sections: Dict[str, List[Option]] = {}

    def_sheet = Path(__file__).with_name(DEFAULT_SHEET)
    path_to_use: Optional[Path] = def_sheet if def_sheet.exists() else None

    if not path_to_use:
        p = input("Spreadsheet path (.xlsx/.csv): ").strip()
        if p:
            path_to_use = Path(p)

    if not path_to_use or not path_to_use.exists():
        print("\nNo spreadsheet found/provided; nothing to compute.")
        return

    try:
        rows = rows_from_file(str(path_to_use))
        ok = 0
        for row in rows:
            if add_row_as_option(row, sections):
                ok += 1
        if ok == 0:
            print("\nNo valid rows loaded; nothing to compute.")
            return
        print(f"[spreadsheet] loaded {ok} section rows successfully from {path_to_use.name}")
    except Exception as e:
        print(f"[file-load error] {e}")
        return

    generate_reports(sections, sheet_name="ScheduleData", title="(all courses equal)")

if __name__ == "__main__":
    main()