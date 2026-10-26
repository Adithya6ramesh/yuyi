# What the data showed: national wind forecasts, January 2026

*Elexon WINDFOR forecasts against actual wind output (FUELHH), at every on-the-hour time
in January 2026 (744 hours). All times are UTC, which is UK time in January. For how this
was built, see [DESIGN.md](DESIGN.md).*

Words used here:
- **miss:** how far off the forecast was, ignoring direction.
- **lean:** the average of (actual − forecast). **Negative means the forecast ran too
  high**, i.e. less wind came than expected.
- **wobble:** how much the error jumps around once the lean is taken out.
- **cushion:** how much wind to plan as "missing", so the buyer is covered most of the
  time.
- **caught short:** less wind came than even the cushion allowed for.
- **Decision day:** what the buyer really saw, i.e. the newest forecast available at
  **09:50 UTC the day before** delivery (Nord Pool GB day-ahead gate closure).

---

## 1. Headline: three things to take away

1. **Don't take the wind forecast at face value.**
   - In January 2026, actual wind came in **below** the day-ahead forecast in **84% of
     hours**, by about **1,700 MW** on average.
   - When the forecast said "very windy" (17 GW or more), it was too high in **every
     single hour**, by about 3,200 MW.
2. **Plan with a cushion of about 4–6 GW.**
   - At the 90% caution level, plan for about **4,900 MW less wind** than the Decision day
     forecast says.
   - On a week the cushion had never seen, it covered **88%** of hours (target 90%).
   - With **no cushion at all**, the buyer would have been caught short in **99%** of
     those hours.
3. **Don't shrink the cushion on calm-looking days, and keep re-checking it.**
   - In the test week, calm-looking forecasts were badly too high as well.
   - The size of the over-forecast changes from week to week, so the cushion needs
     re-learning as new data comes in.

## 2. The forecast leans too high

| | Newest forecast (H = 0) | Made 24 h ahead | **Decision day** |
|---|---|---|---|
| Average miss | 1,794 MW | 2,050 MW | **1,996 MW** |
| Typical miss (median) | 1,392 MW | 1,728 MW | **1,626 MW** |
| Bad-hour miss (1 hour in 10 is worse) | 3,764 MW | 4,129 MW | **4,184 MW** |
| Lean | −1,592 MW | −1,854 MW | **−1,728 MW** |
| Forecast too high in… | 87% of hours | 87% | **84%** |
| Wobble | 1,633 MW | 1,704 MW | **1,805 MW** |
| Share of the problem: lean / wobble | 49% / 51% | 54% / 46% | **48% / 52%** |
| Worst shortfall (less wind than forecast) | −7,305 MW, 12 Jan 01:00 | −6,804 MW, 12 Jan 01:00 | **−6,857 MW, 12 Jan 01:00** |
| Worst overshoot (more wind than forecast) | +2,033 MW, 4 Jan 16:00 | +2,655 MW, 6 Jan 20:00 | **+3,967 MW, 8 Jan 19:00** |

*The "share" splits the overall error exactly: overall miss² = lean² + wobble².*

- **About half of the miss is a steady lean, and half is wobble.**
  - The lean is predictable, and can be planned for.
  - The wobble is what the cushion is for.
- **Even the newest forecast, published shortly before the hour, misses by about
  1,800 MW.** How far ahead the forecast was made matters less than the steady
  over-forecast.
- **The errors are lopsided.** The worst shortfalls (about −7,000 MW) are 2–3 times
  bigger than the worst overshoots. When the forecast is wrong, it's usually wrong in the
  expensive direction.
- **Same scale, different level.** Over the month the newest forecast averaged
  13,174 MW against 11,581 MW actual (1.14×). The two measure the same kind of thing, so
  the gap is real, not a units mix-up.

**Likely reason (not proven): curtailment.**
- On windy days the grid can't always carry all the power, so some wind farms are paid
  to switch off.
- The forecast predicts what the wind *could* produce; FUELHH records what was *actually*
  produced.
- Actual output never went above about 17,800 MW all month, while forecasts reached
  about 21,350 MW. That fits this explanation.
- **We have no curtailment data, so this isn't proven.**

## 3. Miss vs hours ahead

| Hours ahead | Average miss | Bad-hour miss | Lean | Wobble | Real age of the forecast |
|---|---|---|---|---|---|
| 0 | 1,794 | 3,764 | −1,592 | 1,633 | 1.6 h |
| 3 | 1,829 | 3,839 | −1,627 | 1,660 | 4.6 h |
| 6 | 1,871 | 3,879 | −1,683 | 1,640 | 7.6 h |
| 12 | 1,898 | 3,897 | −1,704 | 1,660 | 13.6 h |
| 18 | 1,980 | 3,941 | −1,791 | 1,675 | 19.6 h |
| 24 | 2,050 | 4,129 | −1,854 | 1,704 | 25.6 h |
| 30 | 2,186 | 4,375 | −1,897 | 1,848 | 31.6 h |
| 36 | 2,259 | 4,263 | −1,951 | 1,938 | 37.6 h |
| 43 | 2,317 | 4,463 | −1,930 | 2,095 | 44.6 h |

*All values in MW, over all 744 January hours (every row has a forecast for every hour).
The desk shows every hour from 0 to 43.*

- From 0 to 43 hours ahead, the average miss grows by only about **500 MW (about 30%)**.
- **Up to about 24 hours ahead, the growth is mostly lean.** The wobble barely moves.
- **Beyond 24 hours, the wobble grows** (1,700 → 2,100 MW), while the lean levels off.
- **Decision day forecasts are 14.5–37.5 hours old** (26 hours on average), and they
  behave much like "24 hours ahead".

## 4. When it's worst

### By wind level (grouped by the forecast, which is what you know at decision time; 24 h ahead)

| Forecast says… | Hours | Average miss | Lean | Too high in… | Wobble |
|---|---|---|---|---|---|
| Low: under 10,457 MW | 248 | 1,375 | −988 | 76% | 1,379 |
| Medium: 10,457–17,021 MW | 248 | 1,556 | −1,354 | 85% | 1,437 |
| **High: 17,021 MW or more** | 248 | **3,220** | **−3,220** | **100%** | 1,368 |

- When the forecast said 17 GW or more, actual wind came in below it in **every hour of
  January**, by about 3,200 MW on average.
- The wobble is about the same at every wind level. **The extra miss on windy hours is
  all lean**: a steady over-forecast, not extra unpredictability.

### By time of day (24 h ahead)

| Hours (UTC) | Average miss | Lean | Too high in… |
|---|---|---|---|
| 00–03 | 2,375 | −2,366 | 98% |
| **03–06** | **2,495** | **−2,455** | 94% |
| 06–09 | 2,323 | −2,229 | 91% |
| 09–12 | 2,046 | −1,820 | 80% |
| 12–15 | 1,778 | −1,413 | 76% |
| 15–18 | **1,722** | −1,390 | 77% |
| 18–21 | 1,837 | −1,440 | 86% |
| 21–24 | 1,826 | −1,721 | 92% |

- **The night and early morning (00:00–09:00) are worst**, about 2,200–2,500 MW too
  high.
- **The afternoon is best.**
- A possible reason: demand is lowest at night, so the grid is more likely to switch wind
  farms off. This is unproven.

## 5. The safety cushion

**How it works:**
- Look at how far off past forecasts were.
- For a caution level C, find the shortfall that only (100 − C)/2 % of hours were worse
  than.
- That shortfall is the **cushion**: plan as if that much wind won't arrive.

**What the desk shows (learned from the training weeks only):**

| Caution level | Made 24 h ahead (learned 1–24 Jan) | **Decision day** (learned 2–24 Jan) |
|---|---|---|
| 80% ("8 hours in 10") | 4,302 MW | **4,067 MW** |
| 90% ("9 hours in 10") | 5,096 MW | **4,899 MW** |
| 95% ("19 hours in 20") | 5,735 MW | **5,802 MW** |

- **Example** (Decision day, 90%): the forecast says 12,000 MW, so plan as if only about
  **7,100 MW** of wind will arrive.
- **The ranges are lopsided.**
  - At 90% (Decision day) the range runs from **forecast − 4,899 MW to forecast +
    1,201 MW**.
  - So there's little chance of much more wind than forecast, and a real chance of much
    less.
- **Why only up to 24 January?** That keeps 25–31 January as a fair test of the cushion
  (next section).
  - Learned from all of January instead, the Decision day cushions would be 4,184 /
    5,319 / 5,797 MW, because the last week was the worst.
  - For purchases after January, re-learn from all the data available.

## 6. Does it hold up?

**The test:**
- The cushion was learned from **1–24 January** only, then applied to **25–31 January**:
  168 hours it had never seen.
- **Inside** = the actual landed inside the range. It should be close to the target.
- **Caught short** = the actual came in below the range (the costly side).

| Forecast used | Target | One-size: inside | One-size: caught short | Per wind level: inside | Per wind level: caught short | **With no cushion: caught short** |
|---|---|---|---|---|---|---|
| Newest (H = 0) | 80% | 94.6% ✅ | 5.4% | 79.2% ≈ | 13.1% | 97.6% |
| | 90% | 97.6% ✅ | 2.4% | 85.1% ❌ | 9.5% | 97.6% |
| | 95% | 99.4% ✅ | 0.6% | 89.9% ❌ | 6.0% | 97.6% |
| 24 h ahead | 80% | 92.3% ✅ | 7.7% | 69.0% ❌ | 28.0% | 99.4% |
| | 90% | 94.6% ✅ | 5.4% | 82.1% ❌ | 16.7% | 99.4% |
| | 95% | 98.8% ✅ | 1.2% | 91.1% ❌ | 8.3% | 99.4% |
| 43 h ahead | 80% | 79.8% ≈ | 20.2% | 48.2% ❌ | 46.4% | 100% |
| | 90% | 82.7% ❌ | 17.3% | 63.1% ❌ | 34.5% | 100% |
| | 95% | 91.7% ❌ | 8.3% | 81.0% ❌ | 19.0% | 100% |
| **Decision day** | 80% | **83.9%** ✅ | 16.1% | 67.9% ❌ | 28.0% | **99.4%** |
| | 90% | **88.1%** ≈ | 11.9% | 76.8% ❌ | 20.8% | **99.4%** |
| | 95% | **97.6%** ✅ | 2.4% | 83.9% ❌ | 15.5% | **99.4%** |

*✅ = at or above target · ≈ = within about 3 points · ❌ = clearly short*

**Honest verdict**

1. **Without a cushion, the buyer is caught short almost every hour:** 96–100% of the
   test week.
2. **The one-size cushion mostly held up.**
   - For Decision day it landed close to target: 84% vs 80%, 88% vs 90%, 98% vs 95%.
   - For forecasts made 0–24 hours ahead it covered *more* than its target. That's safe,
     but also bigger (and so more expensive) than that week needed.
   - It fell short for forecasts made 43 hours ahead (83% instead of 90%).
3. **The per-wind-level cushion failed, even though windy hours clearly miss more.**
   - In the learning weeks, calm-looking hours were only about 500–950 MW too high, so they
     got a *small* cushion.
   - In the test week they were about **1,950–2,650 MW** too high. On **28 January** the
     Decision day forecast averaged 11,135 MW, and only 5,806 MW came.
   - The one-size cushion is larger for everyone, so it absorbed the surprise.
   - The desk still shows the per-wind-level version, clearly labelled
     **"experimental, failed the test"**.

## 7. Caveats

- **One month only.** Other months and seasons may behave differently.
- **One storm dominates the extremes.**
  - The cushion is set by the worst 5% of learning hours (about 29 of 576), and at
    24 hours ahead 25 of those 29 come from the storm of **11–12 January**.
  - So small differences between settings are noise. For example, the 90% cushion is
    5,050 MW at 43 h ahead but 5,100 MW at 24 h ahead, even though misses grow with time.
    Learned from all of January, the expected order returns (5,614 vs 5,097 MW).
- **The test week was unusual.**
  - Its lean was −2,508 MW, against −1,531 MW in the learning weeks (Decision day).
  - Forecasts were higher than usual (14,332 vs 12,874 MW on average), while actual wind
    was similar (11,824 vs 11,343 MW).
  - The over-forecast **isn't stable even within one month**.
- **Treat the back-test percentages as rough.** 168 hours is small, and weather lasts for
  days, so neighbouring hours aren't independent. Nothing was tuned to improve these
  results.
- **Curtailment is the likely reason for the lean, but it isn't proven.**
- **The 09:50 deadline is Nord Pool's** GB day-ahead gate closure; confirm which auction
  the client uses.
- **No prediction model was built.** These figures only measure and summarise the
  existing forecasts.
