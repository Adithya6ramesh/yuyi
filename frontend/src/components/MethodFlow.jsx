/*
  THE METHOD FLOW CHART (landing page, section 02).

      FUELHH ─┐
              ├─▶ MATCH ──▶ MEASURE ──▶ CUSHION
      WINDFOR ┘                          ↓
                                      BACK-TEST

  Built from real text and hairlines (not ASCII art), so it reads well, wraps on a
  phone (it turns vertical), and a screen reader can read it as a numbered list.
  A small square "packet" travels along each arrow (CSS animation; it stops when the
  computer asks for reduced motion).
  The numbers come from the API; "…" shows while they load.
*/

import { fmtAbout, fmtMw } from '../art/ascii.js'
import { dateSpan } from '../dates.js'

const LOADING = '…'

/** The arrow between two stages, with a travelling packet. Decoration only. */
function Link({ delay }) {
  return (
    <span className="flow-link" aria-hidden="true">
      <span className="flow-link__line" />
      <span className="flow-link__packet" style={{ animationDelay: `${delay}s` }} />
      <span className="flow-link__head" />
    </span>
  )
}

function Box({ name, children }) {
  return (
    <div className="flow-box">
      <p className="flow-box__name">{name}</p>
      {children}
    </div>
  )
}

export default function MethodFlow({ cfg, quality, summary, backtest }) {
  const actualRows = quality?.actuals?.clean_rows
  const forecastRows = quality?.forecasts?.clean_rows
  const confidence = cfg?.default_confidence
  const tail = confidence != null ? String((100 - confidence) / 2).padStart(2, '0') : null
  const train = backtest?.train_period
  const test = backtest?.test_period
  const held = backtest ? backtest.actual_coverage_pct >= backtest.target_pct - 3 : null

  return (
    <ol className="flow-chart">
      <li className="flow-stage">
        <div className="flow-stage__body">
          <p className="flow-stage__step">01 · Collect</p>
          <div className="flow-stage__boxes">
            <Box name="FUELHH">
              <p className="flow-box__text">Actual wind output</p>
              <p className="flow-box__meta">every 30 min · {actualRows ? fmtMw(actualRows) : LOADING} rows</p>
            </Box>
            <Box name="WINDFOR">
              <p className="flow-box__text">National wind forecasts</p>
              <p className="flow-box__meta">
                every version kept · {forecastRows ? fmtMw(forecastRows) : LOADING} rows
              </p>
            </Box>
          </div>
        </div>
        <Link delay={0} />
      </li>

      <li className="flow-stage">
        <div className="flow-stage__body">
          <p className="flow-stage__step">02 · Match</p>
          <div className="flow-stage__boxes">
            <Box name="LATEST BEFORE DEADLINE">
              <p className="flow-box__text">For each hour T, the newest forecast with</p>
              <p className="flow-box__formula">publishTime ≤ T − H</p>
              <p className="flow-box__ok">
                [ok] {summary ? fmtMw(summary.hours_counted) : LOADING} hours matched
              </p>
              <p className="flow-box__reject">✕ published later → ignored</p>
            </Box>
          </div>
        </div>
        <Link delay={0.8} />
      </li>

      <li className="flow-stage">
        <div className="flow-stage__body">
          <p className="flow-stage__step">03 · Measure</p>
          <div className="flow-stage__boxes">
            <Box name="MISS">
              <p className="flow-box__formula">actual − forecast</p>
              <p className="flow-box__text">average miss · lean · wobble</p>
              <p className="flow-box__meta">
                lean{' '}
                {summary
                  ? `${summary.lean_mw < 0 ? '−' : '+'}${fmtAbout(Math.abs(summary.lean_mw))} MW`
                  : LOADING}{' '}
                at {cfg ? `${cfg.horizon_slider.default}h` : LOADING}
              </p>
            </Box>
          </div>
        </div>
        <Link delay={1.6} />
      </li>

      <li className="flow-stage flow-stage--last">
        <div className="flow-stage__body">
          <p className="flow-stage__step">→ Plan</p>
          <div className="flow-stage__boxes">
            <Box name="CUSHION">
              <p className="flow-box__formula">{tail ? `−p${tail}(miss)` : LOADING}</p>
              <p className="flow-box__meta">
                ≈ {summary ? `${fmtAbout(summary.cushion_mw)} MW` : LOADING} at {confidence ?? LOADING}%
                caution
              </p>
            </Box>
            <span className="flow-down" aria-hidden="true">
              ↓
            </span>
            <Box name="BACK-TEST">
              <p className="flow-box__text">
                learned {train ? dateSpan(train.start, train.end) : LOADING}, tested{' '}
                {test ? dateSpan(test.start, test.end) : LOADING}
              </p>
              {/* [ok] only if it reached (or came within 3 points of) its target; else [!!] */}
              <p className={held === false ? 'flow-box__reject' : 'flow-box__ok'}>
                {held === false ? '[!!]' : '[ok]'}{' '}
                {backtest ? `${Math.round(backtest.actual_coverage_pct)}%` : LOADING} covered (target{' '}
                {backtest ? `${backtest.target_pct}%` : LOADING})
              </p>
            </Box>
          </div>
        </div>
      </li>
    </ol>
  )
}
