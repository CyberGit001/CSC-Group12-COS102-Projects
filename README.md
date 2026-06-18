
# CSC-Group 12 — COS 102 Python Projects

This repository contains two Python desktop applications built by **CSC Group 12**: **CALCX**, an advanced graphical calculator, and **Quiz Forge**, a trivia quiz application. Since both projects were not presented live, this document is written to stand in for that walkthrough — covering not just what each app does, but how it's built internally.

## Group Members

| S/N | Name | Matric Number |
| --- | --- | --- |
| 1 | Abdulgaffar Raheemah Moyosore | 25/52HA006 |
| 2 | Aiyedofe David Oluwaseyi | 25/52HA037 |
| 3 | Jubril Faridat Ayomide | 25/52HA090 |
| 4 | Bashir Amir Kehinde | 25/52HA057 |
| 5 | Damisa AbdulHafeez Onoruoiza | 25/52HA066 |
| 6 | Abdus-salam Aisha Adeola | 25/52HA016 |
| 7 | Yusuf Abdulmalik Ogirima | 24/25PJ151 |
| 8 | Musa Muhammed Labalah | 25/52HA100 |
| 9 | Abdulkareem Shamsudeen | 25/52HA011 |
| 10 | Omokore Samuel Adeola | 25/52HA123 |

## Repository Structure

```
Group12-COS102-Projects/
├── CALCX/
│   └── Calcx-csc_G12.py
├── QuizForge/
│   ├── g12Quiz.py
│   └── questions.json
└── README.md
```

> **Important:** `questions.json` must stay in the same folder as `g12Quiz.py`. Quiz Forge loads its local question bank from this file using a relative path — moving it elsewhere will break offline question loading.

## Requirements

- Python 3.10 or higher (developed on Python 3.14.5)
- Tkinter (included with standard Python installations)
- An internet connection is recommended for Quiz Forge (optional — see below)

No external/third-party packages are required. Both projects use only Python's standard library.

## 1. CALCX — Advanced Calculator

A feature-rich graphical calculator with standard and scientific modes, a built-in unit converter, persistent calculation history, and dark/light theming.

### Architecture

The entire application is built around a single `CalculatorApp` class that owns all UI state and logic — there is no separate file per screen. Instead, the calculator uses a **tabbed single-window design**: Standard, Scientific, Converter, and History are each built as a separate "page" frame, and `_show_page()` switches between them by raising the relevant frame, rather than opening new windows. This keeps the app lightweight and avoids window-management overhead.

Key internal building blocks:

| Component | Responsibility |
| --- | --- |
| `_build_ui()` / `_build_header()` / `_build_tabs()` | Construct the overall window layout and tab bar |
| `_build_standard_page()` | Basic arithmetic layout (digits, +, −, ×, ÷, =) |
| `_build_scientific_page()` | Scientific function grid (sin, cos, tan, log, ln, powers, roots, constants) |
| `_build_converter_page()` | Unit converter UI and conversion logic |
| `_build_history_page()` / `_refresh_history()` | Displays saved calculation history |
| `_digit()`, `_op()`, `_equals()`, `_sci_fn()` | Core calculation engine — builds the expression string and evaluates it |
| `_apply_theme()` / `_toggle_theme()` | Repaints all widgets when switching between Dark and Light themes |
| `_load_history()` / `_save_history()` | Persists calculation history to `calc_history.json` |

Themes are stored as plain Python dictionaries (`THEMES["dark"]`, `THEMES["light"]`) mapping semantic keys (e.g. `display_bg`, `btn_op`, `hover_eq`) to hex colors. `_apply_theme()` reads from whichever dictionary is active and re-applies colors across every widget, so adding a new theme later is just a matter of adding one more dictionary.

### Key Features

- **Standard mode:** basic arithmetic (+, −, ×, ÷, %, parentheses)
- **Scientific mode:** trigonometric functions (sin, cos, tan), logarithms (log, ln), powers (x², x³, xʸ), roots (√x), reciprocal (1/x), and constants (π, e)
- **Unit Converter** across five categories:
  - Length (m, km, cm, mm, ft, in, mi, yd)
  - Weight (kg, g, mg, lb, oz, t)
  - Temperature (°C, °F, K — handled with dedicated conversion formulas, not a fixed ratio, since temperature scales don't share a zero point)
  - Speed (m/s, km/h, mph, ft/s, knot)
  - Area (m², km², cm², ft², acre, ha)
- **Persistent History:** every calculation is auto-saved to `calc_history.json`, capped at the last 100 entries, and can be cleared from within the app
- **Dynamic Theming:** Dark and Light themes with hover-state styling on every button
- **Keyboard Support:** digits, operators, and Enter/Backspace are bound to physical keys via `_keyboard_input()`, so the calculator can be used without touching the mouse

**How to Run**
```bash
cd CALCX
python Calcx-csc_G12.py
```

## 2. Quiz Forge

A desktop trivia quiz application covering 14 categories and 420 locally-stored questions, with Practice, Timed, and Sudden Death game modes.

### Architecture

`QuizForge` is the master controller class, inheriting directly from `tk.Tk`. Rather than opening separate pop-up windows for each screen (Home, Setup, Quiz, Results, Leaderboard), the app uses a **single-window, switchable-frame pattern**: every screen is a `tk.Frame` subclass, and the `_switch()` method destroys whatever frame is currently showing and replaces it with the next one. This keeps the whole experience inside one consistent window instead of spawning multiple windows.

**Hybrid Question Sourcing (Priority-Fallback system):**
1. **API Primary:** on starting a quiz, the app first tries to fetch live questions from the [Open Trivia Database](https://opentdb.com) API over `urllib.request`
2. **Local Fallback:** if the API call fails (no internet, timeout, or the category/amount can't be satisfied), the app silently falls back to `questions.json`, the local question bank, so the quiz still works completely offline
3. Local questions are shuffled (`random.shuffle`) on every load so repeat plays don't show questions in the same order, and answer options are also shuffled independently

**Game Modes:**
- **Practice:** no timer, no penalty — pure self-testing
- **Timed:** each question runs on a countdown using `self.after(1000, self._tick)`, a 1-second interval loop; running out of time auto-submits a "TIMEOUT" answer
- **Sudden Death:** the quiz ends immediately (`self._finish()`) on the first wrong answer, regardless of how many questions remain

**Other implementation details:**
- HTML entities returned by the live API (e.g. `&amp;`, `&quot;`) are decoded back into readable text using Python's `html` module
- Scores factor in streaks: each correct answer is worth `100 + (streak × 10)`, rewarding consecutive correct answers
- A local leaderboard (`quiz_leaderboard.json`) stores the top 20 scores across sessions, sorted by score then completion time
- Keyboard shortcuts (A/B/C/D keys) let users answer without touching the mouse

| Module/Concept | Purpose |
| --- | --- |
| `tkinter` | Powers the GUI — windows, widgets, and the event loop |
| `urllib` | Handles network requests to the trivia API |
| `json` | Persists the local question bank and leaderboard data |
| Event-driven design | `mainloop()` waits for user interaction and triggers callbacks |
| Dynamic theming | Switches between `DARK_THEME` / `LIGHT_THEME` dictionaries and redraws the active frame |

### Question Bank

The local `questions.json` fallback contains **420 questions across 14 categories**: General Knowledge, Books, Film, Music, Science & Nature, Computers, Mathematics, History, Geography, Politics, Art, Animals, Vehicles, and Sports — each tagged with a difficulty level (Easy/Medium/Hard) so the app can filter appropriately even when offline.

**How to Run**
```bash
cd QuizForge
python g12Quiz.py
```
Quiz Forge works fully offline using the local question bank if no internet connection is available.

## Development Environment

- **IDE:** Visual Studio Code (VS Code) 1.124.2
- **Language:** Python 3.14.5
