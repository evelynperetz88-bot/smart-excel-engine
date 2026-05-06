import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import Uploader from './components/Uploader.jsx'
import SheetTabs from './components/SheetTabs.jsx'
import ColumnsPanel from './components/ColumnsPanel.jsx'
import OptionsPanel from './components/OptionsPanel.jsx'
import FilterPanel from './components/FilterPanel.jsx'
import PdfPreview from './components/PdfPreview.jsx'
import ExplanationsPanel from './components/ExplanationsPanel.jsx'
import TemplatesPanel from './components/TemplatesPanel.jsx'
import UserTemplates from './components/UserTemplates.jsx'
import LangSwitcher from './components/LangSwitcher.jsx'
import TierToggle from './components/TierToggle.jsx'
import WatermarkPanel from './components/WatermarkPanel.jsx'
import AutoExportPanel from './components/AutoExportPanel.jsx'
import OnboardingHint from './components/OnboardingHint.jsx'
import TrustIndicators from './components/TrustIndicators.jsx'
import Toast from './components/Toast.jsx'
import {
  uploadFile, fetchTemplates, fetchOcrStatus, fetchCapabilities,
  previewData, previewPdf, exportFile, downloadBlob,
} from './api.js'
import { useT } from './i18n/index.jsx'

const DEFAULT_OPTIONS = {
  page_size: 'A4',
  orientation: 'portrait',
  margin_mm: 12,
  rtl: true,
  smart_layout: true,
}
const DEFAULT_HEADER = {
  title: '',
  subtitle: '',
  logo_data_url: null,
  show_page_numbers: true,
  show_generated_date: true,
}
const DEFAULT_WATERMARK = {
  preset: 'none',
  text: '',
  opacity: 0.18,
  color: '#888888',
}

export default function App() {
  const { t, locale, isRtl } = useT()

  const [tier, setTier] = useState(() => localStorage.getItem('sxe.tier') || 'free')
  useEffect(() => { localStorage.setItem('sxe.tier', tier) }, [tier])

  const [uploading, setUploading] = useState(false)
  const [data, setData] = useState(null)
  const [activeSheetIdx, setActiveSheetIdx] = useState(0)
  const [mergeAllSheets, setMergeAllSheets] = useState(false)

  const [selected, setSelected] = useState({})
  const [priorities, setPriorities] = useState({})
  const [filters, setFilters] = useState({})
  const [headerRowOverride, setHeaderRowOverride] = useState({})
  const [skipEmptyRows, setSkipEmptyRows] = useState(true)
  const [anchorPerSheet, setAnchorPerSheet] = useState({})

  const [options, setOptions] = useState(DEFAULT_OPTIONS)
  const [docHeader, setDocHeader] = useState(DEFAULT_HEADER)
  const [watermark, setWatermark] = useState(DEFAULT_WATERMARK)
  const [pdfA, setPdfA] = useState(false)
  const [outputMode, setOutputMode] = useState('draft')
  const [capabilities, setCapabilities] = useState({ ocr: false, pdfa_real: false })

  const [templates, setTemplates] = useState([])
  const [activeTemplate, setActiveTemplate] = useState(null)

  const [previewSections, setPreviewSections] = useState([])
  const [pdfBlob, setPdfBlob] = useState(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [exporting, setExporting] = useState(null)

  const [ocrAvailable, setOcrAvailable] = useState(null)
  const [toast, setToast] = useState(null)

  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => { setOptions((o) => ({ ...o, rtl: isRtl })) }, [isRtl])

  useEffect(() => {
    fetchTemplates().then((res) => setTemplates(res.templates || [])).catch(() => {})
    fetchOcrStatus().then((s) => setOcrAvailable(s.available)).catch(() => setOcrAvailable(false))
    fetchCapabilities().then(setCapabilities).catch(() => {})
  }, [])

  // Output mode → presets for watermark + pdfA on the client too,
  // so the UI stays in sync with what the server will apply.
  useEffect(() => {
    if (outputMode === 'draft') {
      setWatermark((w) => ({ ...w, preset: 'draft' }))
      setPdfA(false)
    } else if (outputMode === 'official' && tier === 'pro') {
      setWatermark((w) => ({ ...w, preset: 'none' }))
      setPdfA(true)
    } else if (outputMode === 'court_ready' && tier === 'pro') {
      setWatermark((w) => ({ ...w, preset: 'none' }))
      setPdfA(true)
    }
  }, [outputMode, tier])

  const showToast = useCallback((msg, kind = 'info') => {
    setToast({ msg, kind })
    setTimeout(() => setToast(null), 3500)
  }, [])

  const activeSheet = data?.analysis?.sheets?.[activeSheetIdx] || null

  const handleFile = async (file) => {
    setUploading(true)
    try {
      const res = await uploadFile(file)
      setData(res)
      const initSel = {}, initPrio = {}, initHdr = {}, initFilt = {}, initAnchor = {}
      for (const sh of res.analysis.sheets) {
        const ids = sh.columns.filter((c) => !c.is_fully_empty).map((c) => c.index)
        initSel[sh.sheet_name] = new Set(ids)
        const prio = {}
        sh.columns.forEach((c) => { prio[c.index] = c.suggested_priority || 'medium' })
        initPrio[sh.sheet_name] = prio
        initHdr[sh.sheet_name] = sh.detected_header_row
        initFilt[sh.sheet_name] = []
        initAnchor[sh.sheet_name] = ids[0] ?? null
      }
      setSelected(initSel)
      setPriorities(initPrio)
      setHeaderRowOverride(initHdr)
      setFilters(initFilt)
      setAnchorPerSheet(initAnchor)
      setActiveSheetIdx(0)
      setShowAdvanced(false)
      setDocHeader((h) => ({ ...h, title: res.filename?.replace(/\.[^.]+$/, '') || h.title }))
      if (res.ocr_used) showToast(t('upload.ocr_used'))
      else showToast(t('upload.success', { name: res.filename }))
    } catch (e) {
      showToast(t('error.generic', { msg: e.message }), 'error')
    } finally {
      setUploading(false)
    }
  }

  const applyTemplate = (tplId) => {
    setActiveTemplate(tplId || null)
    if (!tplId || !data) return
    const tpl = templates.find((x) => x.id === tplId)
    if (!tpl) return

    setOptions((o) => ({
      ...o,
      page_size: tpl.page_size,
      orientation: tpl.orientation,
      smart_layout: tpl.smart_layout,
      rtl: tpl.rtl,
    }))

    const newPrio = { ...priorities }
    for (const sh of data.analysis.sheets) {
      const sheetPrio = { ...(newPrio[sh.sheet_name] || {}) }
      for (const c of sh.columns) {
        const h = (c.header || '').toLowerCase()
        let chosen = null
        for (const p of ['high', 'low', 'medium']) {
          for (const kw of tpl.priority_keywords[p] || []) {
            if (kw && h.includes(kw.toLowerCase())) {
              chosen = p
              break
            }
          }
          if (chosen) break
        }
        if (chosen) sheetPrio[c.index] = chosen
      }
      newPrio[sh.sheet_name] = sheetPrio
    }
    setPriorities(newPrio)
    showToast(t('templates.applied', { name: locale === 'he' ? tpl.name_he : tpl.name_en }))
  }

  const toggleColumn = (idx) => {
    if (!activeSheet) return
    setSelected((prev) => {
      const next = { ...prev }
      const cur = new Set(next[activeSheet.sheet_name] || [])
      cur.has(idx) ? cur.delete(idx) : cur.add(idx)
      next[activeSheet.sheet_name] = cur
      return next
    })
  }

  const setColumnPriority = (idx, prio) => {
    if (!activeSheet) return
    setPriorities((prev) => ({
      ...prev,
      [activeSheet.sheet_name]: { ...(prev[activeSheet.sheet_name] || {}), [idx]: prio },
    }))
  }

  const setAnchor = (idx) => {
    if (!activeSheet) return
    setAnchorPerSheet((prev) => ({ ...prev, [activeSheet.sheet_name]: idx }))
  }

  const setBulk = (mode) => {
    if (!activeSheet) return
    setSelected((prev) => {
      const next = { ...prev }
      let ids = []
      if (mode === 'all') ids = activeSheet.columns.map((c) => c.index)
      else if (mode === 'none') ids = []
      else if (mode === 'non_empty') ids = activeSheet.columns.filter((c) => !c.is_fully_empty).map((c) => c.index)
      else if (mode === 'mostly_full') ids = activeSheet.columns.filter((c) => c.fill_ratio >= 0.5).map((c) => c.index)
      next[activeSheet.sheet_name] = new Set(ids)
      return next
    })
  }

  const selectedIndicesActive = useMemo(() => {
    if (!activeSheet) return []
    const set = selected[activeSheet.sheet_name] || new Set()
    return activeSheet.columns.map((c) => c.index).filter((i) => set.has(i))
  }, [activeSheet, selected])

  const buildExportPayload = useCallback(() => {
    if (!data) return null
    const sheetsToExport = mergeAllSheets ? data.analysis.sheets : (activeSheet ? [activeSheet] : [])
    const sheetsSpec = sheetsToExport
      .map((sh) => {
        const cols = Array.from(selected[sh.sheet_name] || new Set()).sort((a, b) => a - b)
        if (!cols.length) return null
        return {
          sheet_name: sh.sheet_name,
          column_indices: cols,
          priorities: priorities[sh.sheet_name] || {},
          filters: filters[sh.sheet_name] || [],
          skip_empty_rows: skipEmptyRows,
          header_row: headerRowOverride[sh.sheet_name] ?? null,
          section_title: mergeAllSheets ? sh.sheet_name : null,
        }
      })
      .filter(Boolean)
    if (!sheetsSpec.length) return null

    return {
      file_id: data.file_id,
      sheets: sheetsSpec,
      page_size: options.page_size,
      orientation: options.orientation,
      margin_mm: Number(options.margin_mm) || 12,
      rtl: options.rtl,
      locale,
      smart_layout: options.smart_layout,
      anchor_column_index: mergeAllSheets ? null : (anchorPerSheet[activeSheet?.sheet_name] ?? null),
      header: docHeader,
      explain: true,
      template_id: activeTemplate || null,
      watermark,
      pdf_a: pdfA,
      tier,
    }
  }, [data, mergeAllSheets, activeSheet, selected, priorities, filters, skipEmptyRows, headerRowOverride, options, locale, anchorPerSheet, docHeader, activeTemplate, watermark, pdfA, tier])

  // Auto-refresh: data preview + PDF (only when advanced is open — otherwise the AutoExportPanel is the live one)
  const previewTimer = useRef(null)
  const pdfTimer = useRef(null)
  const lastPdfReqId = useRef(0)

  useEffect(() => {
    if (!showAdvanced) return
    const payload = buildExportPayload()
    if (!payload) {
      setPreviewSections([])
      setPdfBlob(null)
      return
    }
    if (previewTimer.current) clearTimeout(previewTimer.current)
    previewTimer.current = setTimeout(async () => {
      try {
        const res = await previewData({ ...payload, row_limit: 80 })
        setPreviewSections(res.sections || [])
      } catch (e) {
        showToast(t('error.generic', { msg: e.message }), 'error')
      }
    }, 250)

    if (pdfTimer.current) clearTimeout(pdfTimer.current)
    pdfTimer.current = setTimeout(async () => {
      const myReq = ++lastPdfReqId.current
      setPdfLoading(true)
      try {
        const blob = await previewPdf({ ...payload, row_limit: 80 })
        if (myReq === lastPdfReqId.current) setPdfBlob(blob)
      } catch (e) {
        if (myReq === lastPdfReqId.current) showToast(t('error.generic', { msg: e.message }), 'error')
      } finally {
        if (myReq === lastPdfReqId.current) setPdfLoading(false)
      }
    }, 600)

    return () => {
      if (previewTimer.current) clearTimeout(previewTimer.current)
      if (pdfTimer.current) clearTimeout(pdfTimer.current)
    }
  }, [buildExportPayload, showToast, t, showAdvanced])

  const doExport = async (kind) => {
    const payload = buildExportPayload()
    if (!payload) {
      showToast(t('error.no_columns'), 'error')
      return
    }
    setExporting(kind)
    try {
      const { blob, filename } = await exportFile(kind, payload)
      downloadBlob(blob, filename)
      showToast(t('export.downloaded', { name: filename }))
    } catch (e) {
      showToast(t('error.generic', { msg: e.message }), 'error')
    } finally {
      setExporting(null)
    }
  }

  const getCurrentSnapshot = () => ({
    options, docHeader, watermark, pdfA, tier,
    activeTemplate,
    selected: Object.fromEntries(Object.entries(selected).map(([k, v]) => [k, Array.from(v)])),
    priorities, filters, headerRowOverride, anchorPerSheet,
    skipEmptyRows, mergeAllSheets,
  })
  const onLoadSnapshot = (snap) => {
    if (!snap) return
    setOptions(snap.options || DEFAULT_OPTIONS)
    setDocHeader(snap.docHeader || DEFAULT_HEADER)
    setWatermark(snap.watermark || DEFAULT_WATERMARK)
    setPdfA(!!snap.pdfA)
    if (snap.tier) setTier(snap.tier)
    setActiveTemplate(snap.activeTemplate || null)
    setSelected(Object.fromEntries(Object.entries(snap.selected || {}).map(([k, v]) => [k, new Set(v)])))
    setPriorities(snap.priorities || {})
    setFilters(snap.filters || {})
    setHeaderRowOverride(snap.headerRowOverride || {})
    setAnchorPerSheet(snap.anchorPerSheet || {})
    setSkipEmptyRows(snap.skipEmptyRows ?? true)
    setMergeAllSheets(!!snap.mergeAllSheets)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>{t('app.title')}</h1>
          <div className="subtitle">{t('app.subtitle')}</div>
        </div>
        <div className="header-right">
          <TierToggle tier={tier} onChange={setTier} />
          <LangSwitcher />
        </div>
      </header>

      <OnboardingHint />

      <Uploader uploading={uploading} filename={data?.filename} onFile={handleFile} ocrAvailable={ocrAvailable} />

      {data && data.analysis.sheets.length > 0 && (
        <>
          <AutoExportPanel
            fileId={data.file_id}
            defaultTitle={docHeader.title || data.filename?.replace(/\.[^.]+$/, '') || ''}
            defaultSubtitle={docHeader.subtitle}
            logoDataUrl={docHeader.logo_data_url}
            tier={tier}
            onUpgrade={() => setTier('pro')}
            watermark={watermark}
            pdfA={pdfA}
            outputMode={outputMode}
            onOutputMode={setOutputMode}
            showAdvanced={showAdvanced}
            onShowAdvanced={setShowAdvanced}
            onDownloaded={(name, meta) => {
              showToast(t('export.downloaded', { name }))
              if (meta?.pdfaStatus && meta.pdfaStatus !== 'off' && meta.pdfaStatus !== 'verified') {
                showToast(t(`pdfa.${meta.pdfaStatus}`), meta.pdfaStatus === 'failed' ? 'error' : 'info')
              }
            }}
            onError={(msg) => showToast(t('error.generic', { msg }), 'error')}
          />

          <TrustIndicators pdfaAvailable={capabilities.pdfa_real} />

          <WatermarkPanel
            tier={tier}
            watermark={watermark}
            onChange={setWatermark}
            pdfA={pdfA}
            onPdfA={setPdfA}
          />

          {showAdvanced && (
            <>
              <TemplatesPanel templates={templates} selected={activeTemplate} onApply={applyTemplate} />

              <SheetTabs
                sheets={data.analysis.sheets}
                activeIdx={activeSheetIdx}
                onChange={setActiveSheetIdx}
                mergeAll={mergeAllSheets}
                onMergeAll={setMergeAllSheets}
              />

              {activeSheet && (
                <>
                  <ColumnsPanel
                    sheet={activeSheet}
                    selected={selected[activeSheet.sheet_name] || new Set()}
                    priorities={priorities[activeSheet.sheet_name] || {}}
                    anchorIndex={anchorPerSheet[activeSheet.sheet_name] ?? null}
                    onToggle={toggleColumn}
                    onPriority={setColumnPriority}
                    onAnchor={setAnchor}
                    onBulk={setBulk}
                    skipEmptyRows={skipEmptyRows}
                    onSkipEmptyRows={setSkipEmptyRows}
                    headerRow={headerRowOverride[activeSheet.sheet_name] || activeSheet.detected_header_row}
                    onHeaderRow={(v) => setHeaderRowOverride((p) => ({ ...p, [activeSheet.sheet_name]: v }))}
                  />
                  <FilterPanel
                    sheet={activeSheet}
                    selectedIndices={selectedIndicesActive}
                    filters={filters[activeSheet.sheet_name] || []}
                    onChange={(next) => setFilters((p) => ({ ...p, [activeSheet.sheet_name]: next }))}
                  />
                  <OptionsPanel
                    options={options}
                    onChange={setOptions}
                    header={docHeader}
                    onHeader={setDocHeader}
                  />
                  <UserTemplates getCurrentSnapshot={getCurrentSnapshot} onLoadSnapshot={onLoadSnapshot} />
                  <ExplanationsPanel sections={previewSections} />

                  <section className="panel">
                    <h2><span className="badge">▶</span> {t('step.preview')}</h2>
                    <PdfPreview blob={pdfBlob} loading={pdfLoading} height={680} />
                    <div className="toolbar">
                      <button
                        className="btn"
                        disabled={!buildExportPayload() || exporting !== null}
                        onClick={() => doExport('pdf')}
                      >
                        {exporting === 'pdf' ? t('export.preparing') : t('export.pdf')}
                      </button>
                      <button
                        className="btn secondary"
                        disabled={!buildExportPayload() || exporting !== null}
                        onClick={() => doExport('word')}
                      >
                        {exporting === 'word' ? t('export.preparing') : t('export.word')}
                      </button>
                    </div>
                  </section>
                </>
              )}
            </>
          )}
        </>
      )}

      {toast && <Toast msg={toast.msg} kind={toast.kind} />}
    </div>
  )
}
