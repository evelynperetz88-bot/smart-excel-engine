import React, { useState, useEffect } from 'react'
import { useT } from '../i18n/index.jsx'

const KEY = 'sxe.upgrade_dismissed.v1'

export default function UpgradePrompt({ tier, onUpgrade }) {
  const { t } = useT()
  const [hidden, setHidden] = useState(() => Boolean(localStorage.getItem(KEY)))
  // Re-show whenever tier flips back to free in this session
  useEffect(() => {
    if (tier === 'pro') setHidden(false)
  }, [tier])

  if (tier === 'pro') {
    return (
      <div className="upgrade-pro-active">
        ⭐ {t('upgrade.pro_active')}
      </div>
    )
  }
  if (hidden) return null

  const dismiss = () => {
    localStorage.setItem(KEY, '1')
    setHidden(true)
  }

  return (
    <div className="upgrade-card">
      <div className="upgrade-header">
        <h3>⭐ {t('upgrade.title')}</h3>
      </div>
      <div className="upgrade-subtitle">{t('upgrade.subtitle')}</div>
      <ul className="upgrade-features">
        <li>✔ {t('upgrade.feature_no_wm')}</li>
        <li>✔ {t('upgrade.feature_pdfa')}</li>
        <li>✔ {t('upgrade.feature_custom_wm')}</li>
        <li>✔ {t('upgrade.feature_court')}</li>
        <li>✔ {t('upgrade.feature_ocr')}</li>
      </ul>
      <div className="upgrade-actions">
        <button className="btn btn-pro" onClick={onUpgrade}>{t('upgrade.cta')}</button>
        <button className="btn secondary" onClick={dismiss}>{t('upgrade.dismiss')}</button>
      </div>
    </div>
  )
}
