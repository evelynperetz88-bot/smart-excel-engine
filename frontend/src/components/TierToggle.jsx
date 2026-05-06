import React from 'react'
import { useT } from '../i18n/index.jsx'

export default function TierToggle({ tier, onChange }) {
  const { t } = useT()
  return (
    <div className="tier-toggle" title={t('tier.pro_features')}>
      <span className="tier-label">{t('tier.title')}:</span>
      <button
        className={`tier-pill ${tier === 'free' ? 'active' : ''}`}
        onClick={() => onChange('free')}
        type="button"
      >
        {t('tier.free')}
      </button>
      <button
        className={`tier-pill pro ${tier === 'pro' ? 'active' : ''}`}
        onClick={() => onChange('pro')}
        type="button"
      >
        ★ {t('tier.pro')}
      </button>
    </div>
  )
}
