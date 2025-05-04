# ZLP‑Scheduler

Python CLI that flags course‑section conflicts and finds **100‑minute** study
windows for the Zachry Leadership Program.  
Supports 08 : 00 – 16 : 10 starts, 5‑minute grid, per‑day availability, and a
minimum‑conflict fallback when no gap exists.

---

## Table of Contents
1. [Purpose](#purpose)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [Input Format](#input-format)
5. [Example Session](#example-session)
6. [Algorithms & Complexity](#algorithms--complexity)
7. [Assumptions & Limitations](#assumptions--limitations)
8. [Code Walk‑Through](#code-walk‑through)

---

## Purpose
Students in the Zachry Leadership Program juggle tightly‑packed lectures **and**
labs. This tool:

* **Detects time conflicts** across all entered sections  
* **Prints every 100‑minute gap** (per weekday) suitable for study/meetings  
* When no gap exists, suggests the **start time(s) with the fewest overlaps**

---

## Features
| ✔ | Description |
|---|-------------|
| Conflict detection | Flags overlapping sections on any common weekday |
| Lab support | Accepts codes like `MEEN 221L` in addition to `MEEN 221` |
| Flexible grid | 5‑minute start grid, 08 : 00 – 17 : 00 inclusive |
| Greedy fallback | Picks one viable section per course to build the gap grid |
| Min‑conflict hint | Lists best start time(s) when a day is fully booked |
| Pure CLI | Runs in any terminal—no GUI or external dependencies |

---

## Quick Start
```bash
git clone https://github.com/<your‑user>/ZLP-Scheduler.git
cd ZLP-Scheduler
python schedule.py
```

---

## Input Format
```
<SUBJ> <NUM|NUML> <DAYS> <HH:MM> <DURATION>
```
| Field | Rules |
|-------|-------|
| `SUBJ` | Four letters (e.g. `MEEN`) |
| `NUM`  | Three digits, optional trailing **`L`** for labs (`221`, `221L`) |
| `DAYS` | Any combo of **M T W R F** (`MWF`, `TR`, `R`, …) |
| `HH:MM` | 24‑hour start, **08 : 00 ≤ start ≤ 16 : 10** |
| `DURATION` | Positive integer minutes |

> Type **`done`** on its own line to finish entry.

---

## Example Session
```text
Enter every section …
> MEEN 221   MWF 09:10 50
Success!
> MEEN 221L  R   15:00 170
Success!
> CSCE 222   MWF 10:20 50
Success!
> done

Conflicting sections:
  MEEN 221   MWF  09:10  (conflict)
  CSCE 222   MWF  10:20  (conflict)

100‑minute study blocks (5‑min grid, start 08:00‑17:00):
Monday:
  13:00 – 14:40
  13:05 – 14:45
Thursday:
  no fully free slot; minimum conflicts = 1 at start 11:30, 11:35
```

---

## Algorithms & Complexity
| Phase | Technique | Worst‑Case Time |
|-------|-----------|-----------------|
| Parsing | Regex validation | **O(n)** |
| Conflict detection | Pair‑wise interval overlap (different courses) | **O(n²)** |
| Section selection (grid basis) | Greedy earliest‑fit | **O(n²)** |
| Study‑slot scan | 109 grid points × merged intervals/day | ≈ **O(d)** per day |

`n` = sections; `d` = busy intervals that weekday. Quadratic steps are fine
for typical (< 100) section counts.

---

## Assumptions & Limitations
* **User‑provided data** – You must enter *all* candidate sections; omissions
  aren’t checked.
* **Single‑student scope** – Not a multi‑student or room‑booking optimiser.
* **Fixed window** – Only start times 08:00–17:00 are searched.
* **Greedy section choice** – Another combination *might* yield more gaps; the
  global optimum is NP‑hard, so we use a fast heuristic.
* **Half‑open intervals** – Classes ending exactly when another begins
  (`10:00‑10:50` vs `10:50‑…`) are considered non‑overlapping.

---

## Code Walk‑Through
The key logic lives in **`schedule.py`**.

| Section | What it does |
|---------|--------------|
| **Imports & Regexes** | `re` for validation; `^\d{3}[Ll]?$` allows lab codes (`221L`). |
| **Global constants** | Times in minutes; `BLOCK_LEN = 100`, `STEP_MIN = 5`, start window 08 : 00–16 : 10. |
| **Helper functions** |
| – `to_minutes`, `to_hhmm` | Convert `"HH:MM"` ↔︎ integer minutes. |
| – `overlaps(a,b)` | Half‑open interval overlap test. |
| – `merge()` | Merge overlapping intervals with a sweep pass. |
| – `free_and_min_conflict_slots()` | For one weekday, returns:<br>• all 0‑conflict 100‑min blocks<br>• list of start times with the fewest conflicts. |
| **`main()` workflow** |
| 1. Read & validate input (loop until `done`). |
| 2. **Conflict detection** – naive pair‑wise check between *different* courses. |
| 3. Print conflicts **earliest → latest** (sort by start, course, days). |
| 4. Greedy pass: choose first non‑clashing section per course to populate busy grid. |
| 5. For each weekday:<br>• list free blocks, or<br>• show min‑conflict start(s). |


*Happy scheduling!*
