/*
  The desk's controls: view (mode), delivery dates, hours-ahead slider, caution level.
  Every limit and choice comes from /api/config - nothing is hard-coded here.
*/

const CAUTION_NAMES = ['Relaxed', 'Balanced', 'Cautious'] // lowest to highest level

export default function Controls({ config, settings, onChange }) {
  const { mode, start, end, horizon, confidence } = settings
  const range = config.date_ranges[mode]
  const slider = config.horizon_slider
  const deadline = config.decision_deadline.time_utc
  const modes = [
    { value: 'horizon', label: 'Hours ahead' },
    { value: 'decision_day', label: `Decision day (${deadline})` },
  ]

  return (
    <div className="controls">
      <div className="control">
        <p className="control__label" id="view-label">
          View
        </p>
        <div className="toggle toggle--2" role="group" aria-labelledby="view-label">
          {modes.map((m) => (
            <button
              key={m.value}
              type="button"
              className="toggle__button"
              aria-pressed={mode === m.value}
              onClick={() => onChange({ mode: m.value })}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="control">
        <p className="control__label">Delivery dates (UTC)</p>
        <div className="dates">
          <label>
            <span>From</span>
            <input
              type="date"
              value={start}
              min={range.start}
              max={range.end}
              onChange={(e) => onChange({ start: e.target.value })}
            />
          </label>
          <label>
            <span>To</span>
            <input
              type="date"
              value={end}
              min={range.start}
              max={range.end}
              onChange={(e) => onChange({ end: e.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="control">
        {mode === 'horizon' ? (
          <>
            <div className="control__row">
              <label htmlFor="horizon" className="control__label">
                Forecast made ≥
              </label>
              <span className="control__value">{horizon}h ahead</span>
            </div>
            <input
              id="horizon"
              type="range"
              min={slider.min}
              max={slider.max}
              step="1"
              value={horizon}
              onChange={(e) => onChange({ horizon: Number(e.target.value) })}
            />
            <div className="slider-ticks" aria-hidden="true">
              <span>{slider.min}h</span>
              <span>{slider.default}h</span>
              <span>{slider.max}h</span>
            </div>
          </>
        ) : (
          <>
            <p className="control__label">Forecast used</p>
            <p className="control__note">
              The newest forecast out by <strong>{deadline} UTC the day before</strong> delivery: one fixed
              deadline for all 24 hours, as on the real trading desk.
            </p>
          </>
        )}
      </div>

      <div className="control">
        <p className="control__label" id="caution-label">
          Caution level
        </p>
        <div className="toggle toggle--3" role="group" aria-labelledby="caution-label">
          {config.confidence_levels.map((level, i) => (
            <button
              key={level}
              type="button"
              className="toggle__button"
              aria-pressed={confidence === level}
              onClick={() => onChange({ confidence: level })}
            >
              {level}%
              {config.confidence_levels.length === CAUTION_NAMES.length && (
                <span className="toggle__sub">{CAUTION_NAMES[i]}</span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
