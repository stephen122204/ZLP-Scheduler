# ZLP‑Scheduler

A Python CLI tool that helps the Zachry Leadership Program (ZLP) students find viable 100-minute weekly meeting windows 
given a set of class sections. It detects conflicts, accounts for inseparable lecture+lab bundles, and produces 
both a terminal summary and an Excel report (heatmap + top meeting-time ranges).

---

## Table of Contents
1. [Purpose](#purpose)
2. [Design Rationale](#design-rationale)
3. [Quick Start](#quick-start)
4. [Spreadsheet Input Format](#spreadsheet-input-format)
5. [Outputs](#outputs)

---

## Purpose

ZLP students often operate under dense course schedules with limited flexibility across sections.
The ZLP-Scheduler is designed to make these constraints visible and actionable by answering a single, practical question:
   
   **_When can a 100-minute cohort meeting fit, and what tradeoffs does each possible time impose?_**

Rather than optimizing for personal preferences, the scheduler only evaluates which meeting times are feasible. It does not rank instructors, honors sections, or convenience; all courses are weighted as equal. Rather, the goal of this script is to simply determine whether and how a meeting time can fit between everyone's course schedules.

---

<a id="design-rationale"></a>
## Design Rationale

Trying every possible combination of courses by hand is tedious, and trying every possible combination of sections across courses quickly becomes exponential in time complexity, which is computationally infeasable. 
Instead of choosing a full schedule directly, the ZLP-Scheduler evaluates specific 100-minute meeting windows and measures conflicts relative to each window. 
This avoids a greedy approach where early course selections are locked in and never reevaluated as additional courses introduce new conflicts.

- **Bundled Options**  
   * Each spreadsheet row is treated as a single option for a course.
   * An option may include both lecture and lab meetings, which are treated as inseparable.
 
- **Cracking-Based Evaluation (Meeting-Centric)**  
  * The scheduler does not construct a full course schedule or lock in section choices.
  * For each 100-minute meeting window, courses are allowed to shift between available options when possible.
  * A course is counted as a conflict only if **every** option overlaps the meeting window.
  * This approach avoids greedy placement entirely and ensures that meeting times are evaluated independently and fairly.

- **Cracking-Based Reporting**
  
   For every 100-minute meeting start time (every 5-minutes Mon-Fri), the report shows:
   * _Unavoidable Conflicts_: Courses where every option overlaps the meeting block
   * _Blocked courses_: Courses that remain possible but with reduced option flexibility due to the meeting time
   * A ranked list of best meeting-time ranges and a **heatmap** of conflict scores


 - **Scope & Assumptions** 
   * The scheduler focuses *exclusively* on fitting a single weekly 100-minute cohort meeting.
   * It does not rank instructors, honors sections, or personal preferences.
   * Evaluation is based solely on whether a section’s timing preserves viable meeting windows.

   This logic gives a practical view of “best meeting times” even when the schedule is constraint-heavy.
   
---

<a id="quick-start"></a>
## Quick Start

**1) Clone**
```bash
git clone https://github.com/stephen122204/ZLP-Scheduler.git
cd ZLP-Scheduler
```
**2) Install Dependencies**
```bash
python -m pip install pandas openpyxl
```
**3) Add Your Spreadsheet**

Place your input file in the same folder as `zlp_scheduler.py`:
- `sections.xlsx` (default)
- or `.xls` / `.csv`

**Note:** If a file named `sections.xlsx` is not found, the terminal interface will prompt you to enter the name of the spreadsheet to load.

**4) Run**
```bash
python zlp_scheduler.py
```
**Note:** If no spreadsheet is found or provided, the script exits (manual entry has been removed).

---

<a id="spreadsheet-input-format"></a>
## Spreadsheet Input Format

*Note:* A sample template is included in this repository titled `sections.xlsx`.

**Required Columns (case-sensitive)**
|  Column  | Example |                Notes                |
|----------|---------|-------------------------------------|
| Subject  | ECEN    | 4-letter subject code               |
| Number   | 214     | may include trailing L (e.g., 214L) |
| Days     | MWF, TR | any combo of M, T, W, R, F          |
| Start    | 09:10   | 24-hour HH:MM format                |
| Duration | 50      | minutes                             |


**Optional Lab Bundling Columns (recommended for lecture+lab courses)**

If your course has a lab that must be taken with the lecture, include these columns:

|    Column     | Example |              Notes              |
|---------------|---------|---------------------------------|
| Lab           | Y       | truthy values: Y, YES, TRUE, 1  |
| Lab_Days      | R       | required if Lab is truthy       |
| Lab_Start     | 15:00   | required if Lab is truthy       |
| Lab_Duration  | 170     | required if Lab is truthy       |

**Interpretation:** Each row becomes one “Option.” If `Lab=Y`, the lecture and lab are treated as an inseparable bundle; if `Lab=N`, blank, or otherwise falsy, the row is treated as a lecture-only option and any lab columns are ignored.

**Important:** Time fields (`Start`, `Lab_Start`) must be entered as **plain text in 24-hour `HH:MM` format** (e.g., `13:30`). Do not use Excel's built-in time formatting, as automatic time objects are not supported.

---

<a id="outputs"></a>
## Outputs

**Terminal Output**
- Prints a *Top 10* ranked set of top meeting-time ranges (day, start range, and score only)
- If additional meeting times have **≤ 2 unavoidable conflicts**, all such times are printed, even if this exceeds the top 10
- Highlights meeting ranges with low unavoidable conflict scores

**Excel Output**

Creates `zlp_results.xlsx` containing:

1. **Heatmap** (rows = start times, columns = weekdays)  
   Values = number of unavoidable conflicts (score)

2. **Best Meeting-Time Ranges Table** including:
   - Score (unavoidable conflicts)
   - Conflicting courses
   - Blocked course count
   - Blocked courses list

---
*Happy scheduling! :D* 
