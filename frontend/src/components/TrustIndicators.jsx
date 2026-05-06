import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function TrustIndicators({ pdfaAvailable }) {
  const { t } = useT()
  return (
    <div className="trust-indicators">
      <div className="trust-title">{t('trust.title')}</div>
      <ul className="trust-list">
        <li>✓ {t('trust.print_quality')}</li>
        <li>✓ {t('trust.hebrew_full')}</li>
        <li>✓ {t('trust.layout')}</li>
        <li>✓ {t('trust.privacy')}</li>
        <li className={pdfaAvailable ? 'verified' : 'pending'}>
          {pdfaAvailable ? '✓' : '⚠'} {pdfaAvailable ? t('trust.pdfa_verified') : t('trust.pdfa_install')}
        </li>
      </ul>
    </div>
  )
}
