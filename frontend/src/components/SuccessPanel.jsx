import React from 'react'
import { useT } from '../i18n/index.jsx'

const TYPE_EXPLAIN_KEY = {
  legal: 'success.legal_explain',
  financial: 'success.financial_explain',
  inventory: 'success.inventory_explain',
  general: 'success.general_explain',
}

export default function SuccessPanel({ visible, detection, plan, pdfaStatus, onDownload }) {
  const { t } = useT()
  if (!visible) return null

  const detectedType = detection?.type || 'general'
  const groups = (plan?.groups_count) || 1
  const merged = plan?.merged_cells_handled || false

  return (
    <div className="success-panel">
      <div className="success-row">
        <div className="success-mark">✔</div>
        <div className="success-body">
          <h3>{t('success.title')}</h3>
          <div className="muted">{t('success.subtitle')}</div>
        </div>
        <div className="success-badge">{t('success.badge_pro')}</div>
      </div>

      <ul className="success-points">
        <li>{t(TYPE_EXPLAIN_KEY[detectedType] || 'success.general_explain')}</li>
        {groups > 1 && <li>{t('success.layout_split')}</li>}
        {merged && <li>{t('success.merged_cells')}</li>}
      </ul>

      {pdfaStatus && pdfaStatus !== 'off' && (
        <div className={`pdfa-status pdfa-${pdfaStatus}`}>
          {t(`pdfa.${pdfaStatus}`)}
        </div>
      )}

      {onDownload && (
        <button className="btn" onClick={onDownload}>
          ⬇ {t('success.download_now')}
        </button>
      )}
    </div>
  )
}
