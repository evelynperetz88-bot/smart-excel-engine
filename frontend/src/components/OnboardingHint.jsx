import React, { useState, useEffect } from 'react'
import { useT } from '../i18n/index.jsx'

const KEY = 'sxe.onboarding.dismissed.v1'

export default function OnboardingHint() {
  const { t } = useT()
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(KEY)) setShow(true)
  }, [])

  if (!show) return null

  const dismiss = () => {
    localStorage.setItem(KEY, '1')
    setShow(false)
  }

  return (
    <div className="onboarding-card">
      <div className="onboarding-icon">👋</div>
      <div className="onboarding-body">
        <h3>{t('onboarding.title')}</h3>
        <ol className="onboarding-steps">
          <li>{t('onboarding.step1')}</li>
          <li>{t('onboarding.step2')}</li>
          <li>{t('onboarding.step3')}</li>
        </ol>
        <button className="btn" onClick={dismiss}>{t('onboarding.dismiss')}</button>
      </div>
    </div>
  )
}
