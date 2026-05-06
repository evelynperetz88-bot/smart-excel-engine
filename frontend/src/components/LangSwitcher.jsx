import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function LangSwitcher() {
  const { locale, setLocale, t } = useT()
  return (
    <div className="lang-switcher">
      <button
        className={`lang-btn ${locale === 'he' ? 'active' : ''}`}
        onClick={() => setLocale('he')}
      >
        {t('lang.he')}
      </button>
      <button
        className={`lang-btn ${locale === 'en' ? 'active' : ''}`}
        onClick={() => setLocale('en')}
      >
        {t('lang.en')}
      </button>
    </div>
  )
}
