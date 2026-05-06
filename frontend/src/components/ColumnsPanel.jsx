import React from 'react'
import { useT } from '../i18n/index.jsx'

function fillTag(c, t) {
  if (c.is_fully_empty) return <span className="tag empty">{t('columns.empty_tag')}</span>
  const pct = Math.round(c.fill_ratio * 100)
  if (c.is_mostly_empty) return <span className="tag partial">{pct}%</span>
  if (c.fill_ratio >= 0.85) return <span className="tag full">{pct}%</span>
  return <span className="tag partial">{pct}%</span>
}

function typeTag(typ) {
  return <span className={`tag ${typ}`}>{typ}</span>
}

export default function ColumnsPanel({
  sheet,
  selected,
  priorities,
  anchorIndex,
  onToggle,
  onPriority,
  onAnchor,
  onBulk,
  skipEmptyRows,
  onSkipEmptyRows,
  headerRow,
  onHeaderRow,
}) {
  const { t } = useT()

  const total = sheet.columns.length
  const empty = sheet.columns.filter((c) => c.is_fully_empty).length
  const partial = sheet.columns.filter((c) => c.is_mostly_empty).length
  const selectedCount = selected.size
  const dataRows = Math.max(0, sheet.total_rows - sheet.detected_header_row)

  return (
    <section className="panel">
      <h2><span className="badge">4</span> {t('step.columns')}</h2>

      <div className="col-stats">
        <span>{t('stats.total')}: <b>{total}</b></span>
        <span>{t('stats.selected')}: <b>{selectedCount}</b></span>
        <span>{t('stats.empty')}: <b>{empty}</b></span>
        <span>{t('stats.partial')}: <b>{partial}</b></span>
        <span>{t('stats.rows')}: <b>{dataRows}</b></span>
        <span>{t('stats.density')}: <b>{Math.round(sheet.data_density * 100)}%</b></span>
      </div>

      <div className="bulk-actions">
        <button className="btn secondary" onClick={() => onBulk('non_empty')}>{t('columns.bulk_non_empty')}</button>
        <button className="btn secondary" onClick={() => onBulk('mostly_full')}>{t('columns.bulk_full50')}</button>
        <button className="btn secondary" onClick={() => onBulk('all')}>{t('columns.bulk_all')}</button>
        <button className="btn secondary" onClick={() => onBulk('none')}>{t('columns.bulk_none')}</button>
      </div>

      <div className="row" style={{ marginBottom: 10 }}>
        <label className="checkbox">
          <input type="checkbox" checked={skipEmptyRows} onChange={(e) => onSkipEmptyRows(e.target.checked)} />
          {t('columns.skip_empty_rows')}
        </label>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label>{t('columns.header_row')}</label>
          <input
            type="number"
            min="1"
            max={sheet.total_rows}
            value={headerRow}
            onChange={(e) => onHeaderRow(parseInt(e.target.value || '1', 10))}
            style={{ width: 70 }}
          />
        </div>
        <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <label>{t('columns.col_anchor')}:</label>
          <select value={anchorIndex ?? ''} onChange={(e) => onAnchor(e.target.value === '' ? null : parseInt(e.target.value, 10))}>
            <option value="">{t('columns.anchor_none')}</option>
            {sheet.columns
              .filter((c) => !c.is_fully_empty)
              .map((c) => (
                <option key={c.index} value={c.index}>{c.header}</option>
              ))}
          </select>
          <span className="muted" style={{ fontSize: 11 }}>{t('columns.anchor_help')}</span>
        </div>
      </div>

      <div style={{ maxHeight: 320, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 8 }}>
        <table className="cols-table">
          <thead>
            <tr>
              <th style={{ width: 36 }}>{t('columns.col_select')}</th>
              <th style={{ width: 36 }}>#</th>
              <th>{t('columns.col_header')}</th>
              <th>{t('columns.col_type')}</th>
              <th>{t('columns.col_fill')}</th>
              <th>{t('columns.col_priority')}</th>
              <th>{t('columns.col_sample')}</th>
            </tr>
          </thead>
          <tbody>
            {sheet.columns.map((c) => {
              const isSelected = selected.has(c.index)
              const prio = priorities[c.index] || c.suggested_priority || 'medium'
              const isAnchor = anchorIndex === c.index
              return (
                <tr key={c.index} className={c.is_fully_empty ? 'empty' : ''}>
                  <td>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggle(c.index)}
                    />
                  </td>
                  <td><span className="muted">{c.letter}</span></td>
                  <td>
                    <b>{c.header}</b>
                    {isAnchor && <span className="tag full" style={{ marginInlineStart: 6 }}>⚓</span>}
                  </td>
                  <td>{typeTag(c.detected_type)}</td>
                  <td>{fillTag(c, t)}</td>
                  <td>
                    <select
                      value={prio}
                      onChange={(e) => onPriority(c.index, e.target.value)}
                      disabled={!isSelected}
                      className={`prio prio-${prio}`}
                    >
                      <option value="high">{t('columns.priority_high')}</option>
                      <option value="medium">{t('columns.priority_medium')}</option>
                      <option value="low">{t('columns.priority_low')}</option>
                    </select>
                  </td>
                  <td className="muted" style={{ maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {c.sample_values.slice(0, 3).join(' · ')}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
