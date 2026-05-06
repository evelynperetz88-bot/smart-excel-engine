import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function TemplatesPanel({ templates, selected, onApply }) {
  const { t, locale } = useT()
  if (!templates?.length) return null
  return (
    <section className="panel">
      <h2><span className="badge">2</span> {t('step.template')}</h2>
      <div className="row">
        <select
          value={selected || ''}
          onChange={(e) => onApply(e.target.value || null)}
          style={{ minWidth: 240 }}
        >
          <option value="">{t('templates.none')}</option>
          {templates.map((tpl) => (
            <option key={tpl.id} value={tpl.id}>
              {locale === 'he' ? tpl.name_he : tpl.name_en}
            </option>
          ))}
        </select>
        {selected && (
          <span className="muted">
            {(() => {
              const tpl = templates.find((x) => x.id === selected)
              return tpl ? (locale === 'he' ? tpl.description_he : tpl.description_en) : ''
            })()}
          </span>
        )}
      </div>
    </section>
  )
}
