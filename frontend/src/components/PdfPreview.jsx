import React, { useEffect, useState } from 'react'
import { useT } from '../i18n/index.jsx'

export default function PdfPreview({ blob, loading, height = 720 }) {
  const { t } = useT()
  const [url, setUrl] = useState(null)

  useEffect(() => {
    if (!blob) {
      setUrl(null)
      return
    }
    const u = URL.createObjectURL(blob)
    setUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [blob])

  return (
    <div className="pdf-preview-frame" style={{ height }}>
      {loading && (
        <div className="pdf-overlay">
          <div className="spinner-big" /> {t('preview.loading')}
        </div>
      )}
      {!url && !loading && (
        <div className="pdf-empty">{t('preview.empty')}</div>
      )}
      {url && (
        <iframe title="pdf-preview" src={url} width="100%" height="100%" style={{ border: 0 }} />
      )}
    </div>
  )
}
