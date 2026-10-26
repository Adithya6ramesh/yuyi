/*
  "DOES THE RANGE HOLD UP?" (/api/backtest): the cushion was learned on the training
  weeks, then checked on a week it never saw. Shows an ASCII coverage bar against the
  target, how often the buyer was caught short, and what happens with no cushion at all.
  A toggle shows the experimental per-wind-level cushion (which failed the test).
*/

import { useState } from 'react'
import { getBacktest } from '../../api.js'
import { fmtAbout } from '../../art/ascii.js'
import { ErrorNote, Loading } from '../../components/Status.jsx'
import { dateSpan } from '../../dates.js'
import { useApi } from '../../hooks/useApi.js'

const WIDTH = 30 // characters in the coverage bar
const CLOSE_ENOUGH = 3 // points below target that still count as "close"

const METHODS = [
  { value: 'one_size', label: 'One-size cushion' },
  { value: 'per_group', label: 'Per wind level · experimental, failed the test' },
]

function coverageBar(coverage, target) {
  const filled = Math.round((coverage / 100) * WIDTH)
  const marker = Math.round((target / 100) * WIDTH)
  return [
    `[${'█'.repeat(filled)}${'░'.repeat(WIDTH - filled)}] ${Math.round(coverage)}%`,
    `${' '.repeat(marker)}▲ target ${target}%`,
  ].join('\n')
}

export default function Backtest({ query }) {
  const [method, setMethod] = useState('one_size')
  const params = { mode: query.mode, horizon: query.horizon, confidence: query.confidence, method }
  const key = JSON.stringify(params)
  const test = useApi(() => getBacktest(params), [key])

  let body
  if (test.error) body = <ErrorNote message={test.error} />
  else if (!test.data) body = <Loading />
  else {
    const r = test.data
    const held = r.actual_coverage_pct >= r.target_pct - CLOSE_ENOUGH
    const dots = (name) => `${name} `.padEnd(22, '.') + ' '
    body = (
      <>
        <p className="section-sub">
          Learned {dateSpan(r.train_period.start, r.train_period.end)} · tested{' '}
          {dateSpan(r.test_period.start, r.test_period.end)} ({r.test_period.hours} hours it never saw)
        </p>
        {r.experimental && (
          <p className="experimental">
            [!!] Experimental: this cushion failed the back-test. Shown for comparison only; the desk uses
            the one-size cushion.
          </p>
        )}
        <p className="sr-only">
          The range covered {Math.round(r.actual_coverage_pct)}% of the unseen hours against a target of{' '}
          {r.target_pct}%.
        </p>
        <pre className={`coverage${held ? '' : ' coverage--short'}`} aria-hidden="true">
          {coverageBar(r.actual_coverage_pct, r.target_pct)}
        </pre>
        <pre className="terminal">
          {[
            dots('caught short') + `${Math.round(r.caught_short_pct)}% of hours (below the range)`,
            dots('with no cushion') + `${Math.round(r.below_raw_forecast_pct)}% of hours caught short`,
            dots('average cushion') + `${fmtAbout(r.average_cushion_mw)} MW`,
          ].join('\n')}
        </pre>
        <p className={`verdict${held ? '' : ' verdict--short'}`}>→ {r.honest_verdict}</p>
      </>
    )
  }

  return (
    <section className="panel panel--half" aria-labelledby="backtest-title">
      <h2 id="backtest-title" className="mono-heading">
        Does the range hold up?
      </h2>
      <div className="toggle toggle--2 toggle--method" role="group" aria-label="Which cushion to test">
        {METHODS.map((m) => (
          <button
            key={m.value}
            type="button"
            className="toggle__button"
            aria-pressed={method === m.value}
            onClick={() => setMethod(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>
      {body}
    </section>
  )
}
