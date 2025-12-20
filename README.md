# ZLP‑Scheduler

Python CLI that flags course‑section conflicts and finds **100‑minute** class meeting
windows for the Zachry Leadership Program.  
Supports 8:00am – 4:10pm start times, 5‑minute grid, per‑day availability, and a
minimum‑conflict fallback when no gap exists.

---

## Table of Contents
1. [Purpose](#purpose)
2. [Design Rationale](#design-rationale)
3. [Features](#features)
4. [Quick Start](#quick-start)
5. [Input Format](#input-format)
6. [Spreadsheet Input](#spreadsheet-input)
7. [Example Session](#example-session)
8. [Algorithms & Complexity](#algorithms-complexity)
9. [Assumptions & Limitations](#assumptions-limitations)
10. [Code Walk‑Through](#code-walkthrough)

---

## Purpose
Students in the Zachry Leadership Program juggle tightly‑packed course schedules in order 
to graduate within a timely manner. This tool:

* **Detects time conflicts** across all entered sections  
* **Prints every 100‑minute gap** (per weekday) suitable for class meetings  
* When no gap exists, suggests the **start time(s) with the fewest overlaps**
* Ran purely through a terminal-no GUI or network utilized

---

<a id="design-rationale"></a>
## Design Rationale —> Greedy Heuristic Algorithm

Many courses (e.g. labs) offer several sections.  
Scanning every combination is exponential, so we use a **gap‑preserving
greedy** heuristic:

1. **Lock singletons first**  
   Courses that have **exactly one** section are non‑negotiable; their
   intervals are placed in the busy grid immediately.

2. **Score each candidate section of the remaining courses**  
   * Temporarily add the section to a copy of the busy grid.  
   * Re‑count how many 100‑minute windows are still free across Monday‑Friday.  
   * Higher score = fewer windows lost.

3. **Pick the section with the highest score** for that course  
   (ties -> earliest start for deterministic output) and permanently add its
   interval to the busy grid.

4. **Repeat** until every multi‑section course has exactly one chosen section.

Because there are only **99 grid points** to test, the score calculation is
cheap:  
`courses × sections × 99` interval checks – typically a few thousand
operations, finishing in milliseconds.

*Trade‑off:* this heuristic is not guaranteed to find the global optimum, but
it reliably maximizes the number of meeting windows left after each decision
and is far faster (and simpler) than an exact search or ILP solver.

**IMPORTANT NOTE!** - The scheduler focuses solely on fitting a single 100‑minute cohort meeting each week. 
It does not weigh honors sections, instructor quality, or personal convenience. Rather, only whether a section’s 
time preserves the meeting window.

---

## Features
| Capability | Description |
|------------|-------------|
| Conflict‑free gaps | Lists every 100‑min block that overlaps *zero* sections |
| Lab support | Accepts codes like `ECEN 214L` as well as `ECEN 214` |
| Flexible grid | 5‑minute start grid, **08:00 – 16:10** inclusive |
| Best‑gap greedy | Chooses **one** section per multi‑section course to keep the most meeting windows |
| Min‑conflict fallback | Shows least‑bad start time(s) only when no gap exists |
| Pure CLI | Runs in any terminal—no GUI, no external services |

---
<a id="quick-start"></a>
## Quick Start
```bash
git clone https://github.com/Stephen-Abkin-TAMU/ZLP-Scheduler.git
cd ZLP-Scheduler
```

---
<a id="input-format"></a>
## Input Format

| Field      | Rules                                                                |
|------------|----------------------------------------------------------------------|
| `SUBJ`     | Four letters (e.g. `ECEN`)                                           |
| `NUM`      | Three digits, optional trailing **`L`** for labs (`214`, `214L`)     |
| `DAYS`     | Any combo of **M T W R F** (`MWF`, `TR`, `R`, …)                     |
| `HH:MM`    | 24‑hour start — **no range limit** (the grid limit applies only to meeting blocks) |
| `DURATION` | Positive integer minutes                                             |

> Type **`done`** on its own line to finish manual entry.

---

<a id="spreadsheet-input"></a>
## Spreadsheet Input

Instead of typing sections line‑by‑line you can place a file named
**`sections.xlsx`**, **`sections.xls`**, or **`sections.csv`** in the **same
folder** as `zlp_scheduler.py`. I have also included a sample **`sections.xlsx`** file
in this repository.
When you run the script it will detect that file and load it automatically.

### Required columns (first worksheet / first sheet)

| Column name | Example value |
|-------------|---------------|
| **Subject** | `ECEN` |
| **Number**  | `214` or `214L` |
| **Days**    | `MWF`, `TR`, `R`, … |
| **Start**   | `09:10` (24‑hour clock) |
| **Duration**| `50` (minutes) |

> Header names are **case‑sensitive** and must match exactly.

If the file has a different name or location, the script will prompt you for
the full path. Press **Enter** to skip the prompt and fall back to manual
entry.

<a id="example-session"></a>
## Example Session
```text
> MEEN 225   MWF 09:10 50
Success!
> ECEN 214L  R   15:00 170
Success!
> CSCE 222   MWF 09:10 50
Success!
> done

100‑minute meeting blocks (5‑min grid, start 08:00‑16:10):
Monday:
  13:00 – 14:40
  13:05 – 14:45
  13:10 – 14:50
Thursday:
  no fully free slot; minimum conflicts = 1 at start 11:30, 11:35
```

---
<a id="algorithms-complexity"></a>
## Algorithms & Complexity

| Phase | Technique | Worst‑Case Time |
|-------|-----------|-----------------|
| Parsing | Regex validation | **O(n)** |
| Busy‑grid merge | Per‑day sort + sweep | **O(n · logn)** |
| **Section selection** | *Best‑gap greedy* —> score every candidate section, pick the one that preserves the most meeting windows | **O(n · m · g)** ≈ **O(n²)**<br>where *m* = avg sections/course, *g* = 99 grid points |
| Meeting‑slot scan | 99 grid points × merged intervals/day | ≈ **O(d · g)** per day |

*`n` = total sections, `d` = merged busy intervals that weekday,
`g` = 99 (08:00 -> 16:10 every 5 min).  
For typical inputs (*n* ≤ 100, *m* ≤ 5) the whole run finishes in < 1 s.*

---

<a id="assumptions-limitations"></a>
## Assumptions & Limitations
* **You supply all candidate sections** – the script can’t fetch catalog data as I currently don't know how to access Aggie Schedule Builder API
* **Fixed meeting grid** – only start times **08:00 – 16:10** are tested (99 possible start points on current grid model).
* **Half‑open intervals** – a class ending at 10:50 and one starting at
  10:50 do **not** overlap.

---

## Known Limitation — Coupled Lecture / Lab Sections 

Some courses (e.g., **ECEN 214**, **CSCE 221**) include a **lecture** and a **lab** that must be taken **together as a matched pair**.  
At present, the scheduler treats every row as an **independent section**, so it may accidentally “mix and match” a lecture from one section with a lab from another.  
For many **small-major** schedules—where there is typically one lecture and labs are effectively "independent"—this behavior is acceptable, but it is not correct for courses where the **lecture choice constrains** the allowed lab times.

### Examples
- Lecture MWF 09:10 + Lab R 15:00 or Lecture MWF 09:10 + Lab W 12:00  (single lecture, multiple labs)  
- Lecture MWF 10:20 + Lab TR at 14:20 or Lecture MWF 10:20 + Lab TR 18:30  (lab tied to that lecture’s section)  
- Some courses split labs across two days --> the **paired meeting times** travel with the section.

### Why It’s Not Handled Yet
The current greedy logic optimizes study-window availability assuming each section is selectable independently.  
It does not model **bundles** (lecture + lab) or rules like *“if lecture A is chosen, then lab must be in {L1, L2}.”*

**Context:**  
For smaller majors that usually have a single lecture and labs that rarely overlap, this behavior has minimal impact.  
If mismatched lecture–lab pairings appear consistently in future inputs, a **bundle-aware patch** will be developed to link lecture–lab sections together and ensure correct selection.


---
<a id="code-walkthrough"></a>
## Code Walk‑Through
The core logic is in **`zlp_scheduler.py`**.

| Section | What it does |
|---------|--------------|
| **Imports & Regexes** | `re` for validation; `^\d{3}[Ll]?$` accepts lab codes (`221L`). |
| **Global constants** | `GRID_START = 08:00`, `GRID_END = 16:10`, `BLOCK_LEN = 100`, `STEP_MIN = 5`. |
| **Helper functions** | |
| – `to_minutes`, `to_hhmm` | Convert `"HH:MM"` ↔︎ integer minutes. |
| – `overlaps()` | Half‑open interval overlap test. |
| – `merge()` | Merge overlapping (start,end) intervals. |
| – `free_and_min_conflict()` | For one weekday, returns <br>• every 0‑conflict 100‑min window <br>• start time(s) with the fewest overlaps. |
| **`rows_from_file()`** | Reads the first worksheet of `.xlsx` / `.xls` / `.csv` into tuples. |
| **`add_section()`** | Validates one CLI/spreadsheet row (no start‑time range check). |
| **Main workflow** | |
| 1. Load spreadsheet (auto) or prompt for path or manual lines. |
| 2. **Split courses** → single‑option vs multi‑option. |
| 3. Add all single‑option sections to the busy grid (mandatory). |
| 4. **Best‑gap greedy loop**: score every candidate section, pick the one that preserves the most meeting windows, add it to the grid; repeat until each course has exactly one section. |
| 5. Merge busy intervals per weekday. |
| 6. Scan the 5‑minute grid (08:00 – 16:10): <br>• If ≥ 1 day has free blocks → print only those blocks per day.<br>• Else → print the start time(s) with the minimum overlaps per day. |


*Happy scheduling! :D* 
