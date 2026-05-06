import React, { useRef, useState } from 'react'
import { useT } from '../i18n/index.jsx'

export default function Uploader({ uploading, filename, onFile, ocrAvailable }) {
  const { t } = useT()
  const inputRef = useRef(null)
  const [drag, setDrag] = useState(false)

  const onDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files?.[0]
    if (f) onFile(f)
  }

  return (
    <section className="panel">
      <h2><span className="badge">1</span> {t('step.upload')}</h2>
      <div
        className={`dropzone ${drag ? 'drag' : ''}`}
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <div className="icon">📂</div>
        <div>
          {uploading
            ? t('upload.loading')
            : filename
              ? t('upload.replace')
              : t('upload.dropzone')}
        </div>
        {filename && <div className="filename">{filename}</div>}
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.xlsm,.pdf"
          style={{ display: 'none' }}
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onFile(f)
            e.target.value = ''
          }}
        />
      </div>
      {ocrAvailable === false && (
        <div className="muted" style={{ marginTop: 8 }}>{t('upload.ocr_unavailable')}</div>
      )}
    </section>
  )
}
