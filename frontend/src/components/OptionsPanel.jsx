import React, { useRef } from 'react'
import { useT } from '../i18n/index.jsx'

const MAX_LOGO_BYTES = 1024 * 1024

export default function OptionsPanel({ options, onChange, header, onHeader }) {
  const { t } = useT()
  const fileRef = useRef(null)
  const set = (k, v) => onChange({ ...options, [k]: v })
  const setHeader = (k, v) => onHeader({ ...header, [k]: v })

  const onLogoFile = async (file) => {
    if (!file) return
    if (file.size > MAX_LOGO_BYTES) {
      alert('Logo too large (max 1MB)')
      return
    }
    const reader = new FileReader()
    reader.onload = () => setHeader('logo_data_url', reader.result)
    reader.readAsDataURL(file)
  }

  return (
    <section className="panel">
      <h2><span className="badge">6</span> {t('step.options')}</h2>
      <div className="fields">
        <div className="field">
          <label>{t('options.doc_title')}</label>
          <input type="text" value={header.title} onChange={(e) => setHeader('title', e.target.value)} />
        </div>
        <div className="field">
          <label>{t('options.doc_subtitle')}</label>
          <input type="text" value={header.subtitle} onChange={(e) => setHeader('subtitle', e.target.value)} />
        </div>
        <div className="field">
          <label>{t('options.page_size')}</label>
          <select value={options.page_size} onChange={(e) => set('page_size', e.target.value)}>
            <option value="A4">A4</option>
            <option value="A3">A3</option>
          </select>
        </div>
        <div className="field">
          <label>{t('options.orientation')}</label>
          <select value={options.orientation} onChange={(e) => set('orientation', e.target.value)}>
            <option value="portrait">{t('options.portrait')}</option>
            <option value="landscape">{t('options.landscape')}</option>
          </select>
        </div>
        <div className="field">
          <label>{t('options.margin')}</label>
          <input
            type="number" min="5" max="40"
            value={options.margin_mm}
            onChange={(e) => set('margin_mm', e.target.value)}
          />
        </div>
        <div className="field" style={{ justifyContent: 'flex-end' }}>
          <label className="checkbox">
            <input type="checkbox" checked={options.rtl} onChange={(e) => set('rtl', e.target.checked)} />
            {t('options.rtl')}
          </label>
        </div>
        <div className="field" style={{ justifyContent: 'flex-end' }}>
          <label className="checkbox">
            <input type="checkbox" checked={options.smart_layout} onChange={(e) => set('smart_layout', e.target.checked)} />
            {t('options.smart_layout')}
          </label>
        </div>
        <div className="field" style={{ justifyContent: 'flex-end' }}>
          <label className="checkbox">
            <input type="checkbox" checked={header.show_page_numbers} onChange={(e) => setHeader('show_page_numbers', e.target.checked)} />
            {t('options.page_numbers')}
          </label>
        </div>
        <div className="field" style={{ justifyContent: 'flex-end' }}>
          <label className="checkbox">
            <input type="checkbox" checked={header.show_generated_date} onChange={(e) => setHeader('show_generated_date', e.target.checked)} />
            {t('options.gen_date')}
          </label>
        </div>
        <div className="field">
          <label>{t('options.logo')}</label>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
            <button className="btn secondary" type="button" onClick={() => fileRef.current?.click()}>
              {t('options.logo')}
            </button>
            {header.logo_data_url && (
              <>
                <img src={header.logo_data_url} alt="" style={{ height: 32, borderRadius: 4 }} />
                <button className="btn secondary" type="button" onClick={() => setHeader('logo_data_url', null)}>
                  {t('options.logo_clear')}
                </button>
              </>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/svg+xml"
              style={{ display: 'none' }}
              onChange={(e) => {
                const f = e.target.files?.[0]
                onLogoFile(f)
                e.target.value = ''
              }}
            />
          </div>
          <span className="muted" style={{ fontSize: 11 }}>{t('options.logo_help')}</span>
        </div>
      </div>
    </section>
  )
}
