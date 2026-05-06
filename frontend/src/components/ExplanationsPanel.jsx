import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function ExplanationsPanel({ sections }) {
  const { t } = useT()
  const all = (sections || []).flatMap((s) => s.explanations || [])
  return (
    <section className="panel">
      <h2><span className="badge">!</span> {t('explain.title')}</h2>
      {all.length === 0 ? (
        <div className="muted">{t('explain.empty')}</div>
      ) : (
        <ul className="explain-list">
          {all.map((line, i) => <li key={i}>{line}</li>)}
        </ul>
      )}
      {sections?.some((s) => s.groups?.length > 1) && (
        <div className="muted" style={{ marginTop: 8 }}>
          {sections.map((s, si) =>
            s.groups.length > 1 ? (
              <div key={si}>
                <b>{s.title}:</b> {s.groups.length} page-groups
              </div>
            ) : null
          )}
        </div>
      )}
    </section>
  )
}
