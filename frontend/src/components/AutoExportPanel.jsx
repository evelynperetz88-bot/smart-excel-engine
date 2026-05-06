import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useT } from '../i18n/index.jsx'
import PdfPreview from './PdfPreview.jsx'
import OutputMode from './OutputMode.jsx'
import SuccessPanel from './SuccessPanel.jsx'
import UpgradePrompt from './UpgradePrompt.jsx'
import { autoPlan, autoPreviewPdf, autoExport, downloadBlob } from '../api.js'

export default function AutoExportPanel({
  fileId,
  defaultTitle,
  defaultSubtitle,
  logoDataUrl,
  tier,
  onUpgrade,
  watermark,
  pdfA,
  outputMode,
  onOutputMode,
  showAdvanced,
  onShowAdvanced,
  onDownloaded,
  onError,
}) {
  const { t, locale } = useT()

  const [plan, setPlan] = useState(null)
  const [previewBlob, setPreviewBlob] = useState(null)
  const [working, setWorking] = useState(false)
  const [exporting, setExporting] = useState(null)
  const [generatedOnce, setGeneratedOnce] = useState(false)
  const [lastPdfaStatus, setLastPdfaStatus] = useState('off')

  const payload = useMemo(() => ({
    file_id: fileId,
    locale,
    tier,
    document_title: defaultTitle || null,
    document_subtitle: defaultSubtitle || null,
    logo_data_url: logoDataUrl || null,
    watermark,
    pdf_a: pdfA,
    output_mode: outputMode || null,
    row_limit: 80,
  }), [fileId, locale, tier, defaultTitle, defaultSubtitle, logoDataUrl, watermark, pdfA, outputMode])

  const lastReq = useRef(0)

  const generate = async () => {
    setWorking(true)
    setPlan(null)
    setPreviewBlob(null)
    const myReq = ++lastReq.current
    try {
      const planRes = await autoPlan(payload)
      if (myReq !== lastReq.current) return
      setPlan(planRes)
      const blob = await autoPreviewPdf(payload)
      if (myReq !== lastReq.current) return
      setPreviewBlob(blob)
      setGeneratedOnce(true)
    } catch (e) {
      onError?.(e.message)
    } finally {
      if (myReq === lastReq.current) setWorking(false)
    }
  }

  useEffect(() => { if (fileId) generate() }, [fileId]) // eslint-disable-line

  // Re-render preview when settings change
  useEffect(() => {
    if (!fileId || !plan) return
    const myReq = ++lastReq.current
    setWorking(true)
    autoPreviewPdf(payload)
      .then((blob) => {
        if (myReq === lastReq.current) setPreviewBlob(blob)
      })
      .catch((e) => onError?.(e.message))
      .finally(() => {
        if (myReq === lastReq.current) setWorking(false)
      })
  }, [locale, tier, watermark.preset, watermark.text, watermark.opacity, watermark.color, pdfA, logoDataUrl, outputMode]) // eslint-disable-line

  const doExport = async (kind) => {
    setExporting(kind)
    try {
      const { blob, filename, headers } = await autoExport(kind, { ...payload, row_limit: null })
      downloadBlob(blob, filename)
      const status = headers?.['x-pdfa-status'] || 'off'
      setLastPdfaStatus(status)
      onDownloaded?.(filename, { pdfaStatus: status, message: headers?.['x-pdfa-message'] })
    } catch (e) {
      onError?.(e.message)
    } finally {
      setExporting(null)
    }
  }

  const detection = plan?.detection
  const typeLabel = detection ? t(`auto.detection.${detection.type}`) : null
  const planMeta = plan ? {
    groups_count: 1,
    merged_cells_handled: false,
  } : null

  return (
    <section className="panel panel-hero">
      <div className="hero-row">
        <div className="hero-left">
          <h2 className="hero-title">{t('auto.title')}</h2>
          <div className="muted">{t('auto.subtitle')}</div>
          {detection && (
            <div className={`detection-badge type-${detection.type}`}>
              <span className="muted">{t('auto.detection.label')}</span>
              <b>{typeLabel}</b>
              <span className="muted">·</span>
              <span>{t('auto.detection.confidence')} {Math.round((detection.confidence || 0) * 100)}%</span>
            </div>
          )}
        </div>
        <div className="hero-right">
          <button
            className="btn btn-mega"
            disabled={working || exporting !== null}
            onClick={generate}
          >
            {working ? t('auto.cta_loading') : t('auto.cta')}
          </button>
        </div>
      </div>

      <OutputMode value={outputMode} onChange={onOutputMode} tier={tier} />

      <PdfPreview blob={previewBlob} loading={working} height={620} />

      <div className="toolbar">
        <button className="btn" disabled={!previewBlob || exporting !== null} onClick={() => doExport('pdf')}>
          {exporting === 'pdf' ? t('export.preparing') : t('auto.export_pdf')}
        </button>
        <button className="btn secondary" disabled={!previewBlob || exporting !== null} onClick={() => doExport('word')}>
          {exporting === 'word' ? t('export.preparing') : t('auto.export_word')}
        </button>
        <button className="btn secondary" disabled={working} onClick={generate}>
          ↻ {t('auto.regenerate')}
        </button>
        <div style={{ flex: 1 }} />
        <button className="btn secondary" onClick={() => onShowAdvanced(!showAdvanced)}>
          {showAdvanced ? t('auto.advanced_close') : t('auto.advanced')}
        </button>
      </div>

      <SuccessPanel
        visible={generatedOnce && !working}
        detection={detection}
        plan={planMeta}
        pdfaStatus={lastPdfaStatus}
        onDownload={() => doExport('pdf')}
      />

      {plan?.plan?.explanations?.length > 0 && (
        <div className="explain-box">
          <b>{t('explain.title')}:</b>
          <ul className="explain-list">
            {plan.plan.explanations.map((line, i) => <li key={i}>{line}</li>)}
          </ul>
        </div>
      )}

      <UpgradePrompt tier={tier} onUpgrade={onUpgrade} />
    </section>
  )
}
