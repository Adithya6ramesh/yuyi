/*
  Small fake API answers for the tests, shaped exactly like the real ones
  (see the backend's /docs page). Tests use these instead of a running backend.
*/

export const config = {
  horizon_slider: { min: 0, max: 43, default: 24, why_max: '' },
  confidence_levels: [80, 90, 95],
  default_confidence: 90,
  default_mode: 'horizon',
  date_ranges: {
    horizon: { start: '2026-01-01', end: '2026-01-31' },
    decision_day: { start: '2026-01-02', end: '2026-02-01' },
  },
  decision_deadline: { time_utc: '09:50', day: 'the day before delivery', why: '' },
  backtest: {
    train_period: { start: '2026-01-01', end: '2026-01-24', hours: 576, label: '1-24 January 2026' },
    test_period: { start: '2026-01-25', end: '2026-01-31', hours: 168, label: '25-31 January 2026' },
  },
  cushion_learned_from: { start: '2026-01-01', end: '2026-01-24', hours: 576, label: '1-24 January 2026' },
}

const learned = config.cushion_learned_from

const row = (hour, actual, forecast) => ({
  time: `2026-01-14T${String(hour).padStart(2, '0')}:00:00Z`,
  actual_mw: actual,
  forecast_mw: forecast,
  publish_time: '2026-01-12T22:30:00Z',
  deadline: '2026-01-13T00:00:00Z',
  lead_time_h: 25.5,
  error_mw: actual - forecast,
  range_low_mw: forecast - 5000,
  range_high_mw: forecast + 1000,
})

export const series = {
  mode: 'horizon',
  horizon: 24,
  confidence: 90,
  start: '2026-01-14',
  end: '2026-01-14',
  cushion_mw: 5000,
  cushion_learned_from: learned,
  hours: 3,
  rows: [row(0, 9000, 11000), row(1, 9500, 11500), row(2, 10000, 10500)],
}

export const summary = {
  mode: 'horizon',
  horizon: 24,
  confidence: 90,
  start: '2026-01-01',
  end: '2026-01-31',
  hours_counted: 744,
  average_miss_mw: 2050,
  typical_miss_mw: 1728,
  bad_hour_miss_mw: 4129,
  worst_shortfall_mw: -6804,
  worst_shortfall_time: '2026-01-12T01:00:00Z',
  worst_overshoot_mw: 2655,
  worst_overshoot_time: '2026-01-06T20:00:00Z',
  lean_mw: -1854,
  pct_hours_too_high: 87,
  wobble_mw: 1704,
  overall_miss_mw: 2518,
  lean_share_pct: 54,
  average_lead_time_h: 25.6,
  cushion_mw: 5096,
  range_lower_mw: -5096,
  range_upper_mw: 980,
  cushion_learned_from: learned,
  plain_english: 'Forecasts made 24 hours ahead missed by about 2,050 MW on average.',
}

export const horizonCurve = {
  start: '2026-01-01',
  end: '2026-01-31',
  points: Array.from({ length: 44 }, (_, h) => ({
    hours_ahead: h,
    hours_matched: 744,
    average_miss_mw: 1800 + h * 12,
    bad_hour_miss_mw: 3800 + h * 15,
    lean_mw: -1600 - h * 8,
    wobble_mw: 1630 + h * 10,
    average_lead_time_h: h + 1.6,
  })),
}

const breakdownRow = (group, miss) => ({
  group,
  hours_counted: 93,
  average_miss_mw: miss,
  typical_miss_mw: miss * 0.8,
  bad_hour_miss_mw: miss * 2,
  lean_mw: -miss * 0.9,
  pct_hours_too_high: 85,
  wobble_mw: 1400,
})

export const breakdowns = {
  mode: 'horizon',
  horizon: 24,
  start: '2026-01-01',
  end: '2026-01-31',
  time_of_day: ['00-03', '03-06', '06-09', '09-12', '12-15', '15-18', '18-21', '21-24'].map((g, i) =>
    breakdownRow(g, 1700 + i * 50),
  ),
  wind_level: [breakdownRow('high', 3220), breakdownRow('low', 1375), breakdownRow('medium', 1556)],
  wind_level_thresholds: { low_to_medium_mw: 10457, medium_to_high_mw: 17021, grouped_by: 'forecast', rule: '' },
}

export const backtest = {
  mode: 'horizon',
  horizon: 24,
  confidence: 90,
  method: 'one_size',
  experimental: false,
  method_label: 'One-size cushion',
  train_period: config.backtest.train_period,
  test_period: config.backtest.test_period,
  target_pct: 90,
  actual_coverage_pct: 94.6,
  caught_short_pct: 5.4,
  above_range_pct: 0,
  below_raw_forecast_pct: 99.4,
  average_cushion_mw: 5096,
  honest_verdict: 'The one-size cushion held up.',
}

export const decisionDay = {
  delivery_date: '2026-01-02',
  deadline: '2026-01-01T09:50:00Z',
  confidence: 90,
  cushion_mw: 4899,
  cushion_learned_from: learned,
  rows: series.rows,
  daily: {
    hours_counted: 3,
    average_actual_mw: 9500,
    average_forecast_mw: 11000,
    average_miss_mw: 1500,
    lean_mw: -1500,
    pct_hours_too_high: 100,
  },
}

export const quality = {
  actuals: { found_half_hours: 1728, expected_half_hours: 1728, missing_half_hours: [], duplicates_removed: 0, clean_rows: 1728 },
  forecasts: {
    duplicates_removed: 0,
    clean_rows: 19272,
    versions_per_january_target_hour: { min: 16, max: 32, typical: 24 },
    usable_versions_per_january_target_hour: { min: 15, max: 23, typical: 19 },
  },
  lead_time: {
    counts_by_group: { 'negative (published after target)': 3961 },
    january_targets: { longest_lead_available_for_every_hour: 43.5 },
  },
  scale_check: { forecast_to_actual_ratio: 1.138 },
}
