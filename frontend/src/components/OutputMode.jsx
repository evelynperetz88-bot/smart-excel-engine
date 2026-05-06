import React from 'react'
import { useT } from '../i18n/index.jsx'

const MODES = [
  { id: 'draft', proOnly: false, icon: '📝' },
  { id: 'official', proOnly: true, icon: '📄' },
  { id: 'court_ready', proOnly: true, icon: '⚖️' },
]

export default function OutputMode({ value, onChange, tier }) {
  const { t } = useT()
  return (
    <div className="output-mode">
      <div className="output-mode-label">{t('output_mode.title')}:</div>
      <div className="output-mode-grid">
        {MODES.map((m) => {
          const disabled = m.proOnly && tier !== 'pro'
          const active = value === m.id
          return (
            <button
              key={m.id}
              type="button"
              className={`output-mode-card ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
              disabled={disabled}
              onClick={() => onChange(m.id)}
              title={disabled ? t('output_mode.pro_only') : ''}
            >
              <div className="output-mode-icon">{m.icon}</div>
              <div className="output-mode-name">
                {t(`output_mode.${m.id}`)}
                {m.proOnly && <span className="badge-pro">Pro</span>}
              </div>
              <div className="output-mode-desc">{t(`output_mode.${m.id}_desc`)}</div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
