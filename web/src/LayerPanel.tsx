import { displayValue } from './format'
import type { Health, Layer } from './types'

interface Props {
  health: Health | null
  layers: Layer[] | null
  error: string | null
}

export function LayerPanel({ health, layers, error }: Props) {
  const isSample = health?.sample === true || layers?.some((layer) => layer.sample) === true
  return (
    <aside className="panel">
      <h1>Land Check</h1>
      <p className="lede">Pilot: Pechea, Galați County. Screening only.</p>

      {isSample && (
        <p className="sample-banner" role="status">
          SAMPLE DATA: the API is serving an invented fixture. Nothing shown is a real result.
        </p>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {health && (
        <p className="meta">
          API {health.status} · v{health.version} · dataset {displayValue(health.dataset_id)}{' '}
          {displayValue(health.dataset_version)}
        </p>
      )}

      {layers === null && !error && <p>Loading layers…</p>}
      {layers?.length === 0 && <p>No layers available.</p>}

      {layers && layers.length > 0 && (
        <ul className="layers">
          {layers.map((layer) => (
            <li key={layer.id}>
              <strong>{layer.title}</strong>
              {layer.sample && <span className="badge">Sample</span>}
              <dl>
                <dt>Date</dt>
                <dd>{layer.observation_date}</dd>
                <dt>Sensor</dt>
                <dd>{displayValue(layer.sensor)}</dd>
                <dt>Source</dt>
                <dd>
                  <a href={layer.source_url} target="_blank" rel="noopener noreferrer">
                    {layer.source_name}
                  </a>
                </dd>
                <dt>Features</dt>
                <dd>{layer.feature_count}</dd>
                <dt>Method</dt>
                <dd>
                  {layer.method_version} · dataset {layer.dataset_version}
                </dd>
              </dl>
              <p>{layer.meaning}</p>
              <ul className="limitations">
                {layer.limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
