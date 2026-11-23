import type { RiskResult } from './types'

function formatValue(result: RiskResult): string {
  // No data is shown as "no data", never as 0 or Low.
  return result.value === null ? 'no data' : `${result.value} ${result.unit}`
}

export function ResultsList({ results }: { results: RiskResult[] }) {
  return (
    <ul className="results">
      {results.map((result) => (
        <li key={result.risk}>
          <strong>{result.risk}</strong>{' '}
          <span className={`level level-${result.level}`}>{result.level}</span>
          <div>Value: {formatValue(result)}</div>
          <div>{result.summary}</div>
          <small>
            {result.date_range.start} to {result.date_range.end} ·{' '}
            {result.sources.map((s) => s.name).join(', ')}
          </small>
        </li>
      ))}
    </ul>
  )
}
