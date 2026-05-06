import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function SheetTabs({ sheets, activeIdx, onChange, mergeAll, onMergeAll }) {
  const { t } = useT()
  return (
    <section className="panel">
      <h2><span className="badge">3</span> {t('step.sheets')}</h2>
      <div className="muted" style={{ marginBottom: 8 }}>{t('sheets.tabs_help')}</div>
      <div className="row" style={{ marginBottom: 10 }}>
        <label className="checkbox">
          <input type="checkbox" checked={mergeAll} onChange={(e) => onMergeAll(e.target.checked)} />
          {t('sheets.merge_into_one')}
        </label>
      </div>
      <div className="tabs">
        {sheets.map((s, i) => (
          <button
            key={s.sheet_name}
            className={`tab ${i === activeIdx ? 'active' : ''}`}
            onClick={() => onChange(i)}
          >
            {s.sheet_name}
            <span className="muted" style={{ marginInlineStart: 6 }}>
              ({s.total_rows} × {s.total_columns})
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
