// API base URL.
//   - Local dev: empty string → calls go to '/api/...' which Vite proxies to 127.0.0.1:8765
//   - Production (Vercel): set VITE_API_BASE=https://your-backend.onrender.com at build time
//     so calls go directly to the backend (with CORS).
const API_ORIGIN = (import.meta.env?.VITE_API_BASE || '').replace(/\/+$/, '')
const BASE = `${API_ORIGIN}/api`

async function handle(res) {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data?.detail) msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {}
    throw new Error(msg)
  }
  return res
}

export async function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: fd })
  await handle(res)
  return res.json()
}

export async function fetchTemplates() {
  const res = await fetch(`${BASE}/templates`)
  await handle(res)
  return res.json()
}

export async function fetchOcrStatus() {
  try {
    const res = await fetch(`${BASE}/ocr/status`)
    if (!res.ok) return { available: false }
    return res.json()
  } catch {
    return { available: false }
  }
}

export async function previewData(payload) {
  const res = await fetch(`${BASE}/preview/data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await handle(res)
  return res.json()
}

export async function previewPdf(payload) {
  const res = await fetch(`${BASE}/preview/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await handle(res)
  return res.blob()
}

export async function exportFile(kind, payload) {
  const res = await fetch(`${BASE}/export/${kind}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await handle(res)
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const m = cd.match(/filename="?([^"]+)"?/)
  const fallback = kind === 'pdf' ? 'export.pdf' : 'export.docx'
  const filename = m ? m[1] : fallback
  return { blob, filename }
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

export function blobToObjectUrl(blob) {
  return URL.createObjectURL(blob)
}

export async function autoPlan(payload) {
  const res = await fetch(`${BASE}/auto/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await handle(res)
  return res.json()
}

export async function autoPreviewPdf(payload) {
  const res = await fetch(`${BASE}/auto/preview/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await handle(res)
  return res.blob()
}

export async function autoExport(kind, payload) {
  const res = await fetch(`${BASE}/auto/export/${kind}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await handle(res)
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const m = cd.match(/filename="?([^"]+)"?/)
  const fallback = kind === 'pdf' ? 'export.pdf' : 'export.docx'
  // Surface PDF/A status headers
  const headers = {
    'x-pdfa-status': res.headers.get('X-PDFA-Status') || 'off',
    'x-pdfa-requested': res.headers.get('X-PDFA-Requested') || '0',
  }
  const msg = res.headers.get('X-PDFA-Message')
  if (msg) headers['x-pdfa-message'] = decodeURIComponent(msg)
  return { blob, filename: m ? m[1] : fallback, headers }
}

export async function fetchCapabilities() {
  try {
    const res = await fetch(`${BASE}/capabilities`)
    if (!res.ok) return { ocr: false, pdfa_real: false }
    return res.json()
  } catch {
    return { ocr: false, pdfa_real: false }
  }
}
