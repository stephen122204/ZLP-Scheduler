# ZLP-Scheduler
Python CLI that flags course‑section conflicts and finds 100‑time windows for the Zachry Leadership Program. Supports 08:00‑16:10 starts, 5‑minute grid, per‑day availability, and minimum‑conflict fallback.
# ZLP‑Scheduler

Python CLI that flags course‑section conflicts and finds **100‑minute** study
windows for the Zachry Leadership Program.  
Supports 08 : 00 – 16 : 10 starts, 5‑minute grid, per‑day availability, and
minimum‑conflict fallback.

---

## Table of Contents
1. [Purpose](#purpose)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [Input Format](#input-format)
5. [Example Session](#example-session)
6. [Algorithms & Complexity](#algorithms--complexity)
7. [Assumptions & Limitations](#assumptions--limitations)
8. [Code Walk‑Through](#code-walk-through)
9. [Contributing](#contributing)
10. [License](#license)

---

## Purpose
Students in the Zachry Leadership Program juggle tightly‑packed lectures **and**
labs. This tool:

* **Detects time conflicts** among all entered sections  
* **Prints every 100‑minute gap** (per weekday) suitable for study/meetings  
* When no gap exists, suggests the **start time(s) with the fewest overlaps**

---

## Features
| ✔ | Description |
|---|-------------|
| Conflict detection | Flags overlapping sections on any common weekday |
| Lab support | Accepts codes like `MEEN 221L` as distinct from `MEEN 221` |
| Flexible grid | 5‑minute start grid, 08 : 00 – 17 : 00 inclusive |
| Greedy fallback | Picks one viable section per course to build the gap grid |
| Min‑conflict hint | Lists best start‑time(s) when a day is fully booked |
| Pure CLI | Runs in any terminal—no GUI or extra dependencies |

---

## Quick Start
```bash
git clone https://github.com/<your‑user>/ZLP-Scheduler.git
cd ZLP-Scheduler
python schedule.py
