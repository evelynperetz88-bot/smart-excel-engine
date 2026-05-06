import React from 'react'
import { useT } from '../i18n/index.jsx'

const NUMERIC_OPS = new Set(['gt', 'gte', 'lt', 'lte', 'between'])
const NEEDS_VALUE = (op) => op !== 'is_empty' && op !== 'not_empty'

export default function FilterPanel({ sheet, selectedIndices, filters, onChange }) {
  const { t } = useT()

  const visibleColumns = sheet.columns.filter((c) => selectedIndices.includes(c.index))

  const addFilter = () => {
    const first = visibleColumns[0]
    if (!first) return
    onChange([...filters, { column_index: first.index, op: 'contains', value: '', value2: null }])
  }

  const updateFilter = (i, patch) => {
    const next = filters.slice()
    next[i] = { ...next[i], ...patch }
    onChange(next)
  }

  const removeFilter = (i) => {
    const next = filters.slice()
    next.splice(i, 1)
    onChange(next)
  }

  return (
    <section className="panel">
      <h2><span className="badge">5</span> {t('step.filters')}</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filters.length === 0 && (
          <div className="muted">{t('filters.title')} — {t('filters.add')} ↓</div>
        )}
        {filters.map((f, i) => {
          const op = f.op
          return (
            <div key={i} className="row" style={{ flexWrap: 'wrap' }}>
              <select
                value={f.column_index}
                onChange={(e) => updateFilter(i, { column_index: parseInt(e.target.value, 10) })}
                style={{ minWidth: 160 }}
              >
                {visibleColumns.map((c) => (
                  <option key={c.index} value={c.index}>{c.header}</option>
                ))}
              </select>
              <select value={op} onChange={(e) => updateFilter(i, { op: e.target.value })} style={{ minWidth: 130 }}>
                {['contains', 'not_contains', 'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'between', 'is_empty', 'not_empty'].map((o) => (
                  <option key={o} value={o}>{t(`filters.op.${o}`)}</option>
                ))}
              </select>
              {NEEDS_VALUE(op) && (
                <input
                  type={NUMERIC_OPS.has(op) ? 'number' : 'text'}
                  value={f.value ?? ''}
                  onChange={(e) => updateFilter(i, { value: e.target.value })}
                  style={{ minWidth: 120 }}
                />
              )}
              {op === 'between' && (
                <>
                  <span className="muted">{t('filters.value2')}</span>
                  <input
                    type="number"
                    value={f.value2 ?? ''}
                    onChange={(e) => updateFilter(i, { value2: e.target.value })}
                    style={{ minWidth: 120 }}
                  />
                </>
              )}
              <button className="btn danger" onClick={() => removeFilter(i)}>{t('filters.remove')}</button>
            </div>
          )
        })}
        <div>
          <button className="btn secondary" onClick={addFilter} disabled={visibleColumns.length === 0}>
            + {t('filters.add')}
          </button>
        </div>
      </div>
    </section>
  )
}
