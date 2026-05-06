import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function WatermarkPanel({ tier, watermark, onChange, pdfA, onPdfA }) {
  const { t } = useT()
  const isPro = tier === 'pro'
  const wm = watermark

  const set = (k, v) => onChange({ ...wm, [k]: v })

  return (
    <section className="panel panel-pro">
      <h2>
        <span className="badge">⭐</span> {t('watermark.title')}
        {!isPro && <span className="muted" style={{ fontSize: 12, marginInlineStart: 8 }}>— {t('tier.free_note')}</span>}
      </h2>

      <div className="row" style={{ gap: 6, marginBottom: 8 }}>
        {['none', 'draft', 'official', 'custom'].map((preset) => (
          <button
            key={preset}
            type="button"
            className={`tab ${wm.preset === preset ? 'active' : ''}`}
            onClick={() => set('preset', preset)}
            disabled={!isPro && preset !== 'none'}
            title={!isPro ? t('tier.upgrade') : ''}
          >
            {t(`watermark.preset.${preset}`)}
          </button>
        ))}
      </div>

      {wm.preset === 'custom' && (
        <div className="fields" style={{ marginTop: 4 }}>
          <div className="field">
            <label>{t('watermark.text')}</label>
            <input
              type="text"
              value={wm.text}
              onChange={(e) => set('text', e.target.value)}
              disabled={!isPro}
            />
          </div>
        </div>
      )}

      {wm.preset !== 'none' && (
        <div className="fields">
          <div className="field">
            <label>{t('watermark.opacity')} ({Math.round(wm.opacity * 100)}%)</label>
            <input
              type="range" min="0.05" max="0.6" step="0.01"
              value={wm.opacity}
              onChange={(e) => set('opacity', parseFloat(e.target.value))}
              disabled={!isPro}
            />
          </div>
          <div className="field">
            <label>{t('watermark.color')}</label>
            <input
              type="color"
              value={wm.color}
              onChange={(e) => set('color', e.target.value)}
              disabled={!isPro}
            />
          </div>
        </div>
      )}

      <div className="row" style={{ marginTop: 8 }}>
        <label className="checkbox" title={t('options.pdf_a_help')}>
          <input
            type="checkbox"
            checked={pdfA}
            onChange={(e) => onPdfA(e.target.checked)}
            disabled={!isPro}
          />
          {t('options.pdf_a')}
          {!isPro && <span className="badge-pro">Pro</span>}
        </label>
      </div>
    </section>
  )
}
