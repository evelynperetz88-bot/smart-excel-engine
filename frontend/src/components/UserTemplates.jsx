import React, { useEffect, useState } from 'react'
import { useT } from '../i18n/index.jsx'

const KEY = 'sxe.user_templates.v1'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}
function save(items) {
  localStorage.setItem(KEY, JSON.stringify(items))
}

export default function UserTemplates({ getCurrentSnapshot, onLoadSnapshot }) {
  const { t } = useT()
  const [items, setItems] = useState(load())

  useEffect(() => {
    save(items)
  }, [items])

  const handleSave = () => {
    const name = prompt(t('user_tpl.name_prompt'))
    if (!name) return
    const snap = getCurrentSnapshot()
    const item = { id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`, name, savedAt: new Date().toISOString(), snapshot: snap }
    setItems([item, ...items])
  }

  const handleDelete = (id) => {
    setItems(items.filter((x) => x.id !== id))
  }

  const handleLoad = (id) => {
    const it = items.find((x) => x.id === id)
    if (it) onLoadSnapshot(it.snapshot)
  }

  return (
    <section className="panel">
      <h2><span className="badge">★</span> {t('user_tpl.title')}</h2>
      <div className="row" style={{ marginBottom: 8 }}>
        <button className="btn" onClick={handleSave}>{t('user_tpl.save')}</button>
      </div>
      {items.length === 0 ? (
        <div className="muted">{t('user_tpl.empty')}</div>
      ) : (
        <div className="user-tpl-list">
          {items.map((it) => (
            <div key={it.id} className="user-tpl-item">
              <span><b>{it.name}</b></span>
              <span className="muted" style={{ fontSize: 11 }}>{new Date(it.savedAt).toLocaleString()}</span>
              <div className="row">
                <button className="btn secondary" onClick={() => handleLoad(it.id)}>{t('user_tpl.load')}</button>
                <button className="btn danger" onClick={() => handleDelete(it.id)}>{t('user_tpl.delete')}</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
