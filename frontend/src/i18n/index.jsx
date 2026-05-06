import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import he from './he.json'
import en from './en.json'

const dicts = { he, en }
const RTL_LANGS = new Set(['he'])

const Ctx = createContext(null)

export function I18nProvider({ children, defaultLocale = 'he' }) {
  const stored = (typeof window !== 'undefined' && localStorage.getItem('locale')) || defaultLocale
  const [locale, setLocale] = useState(stored in dicts ? stored : 'he')

  useEffect(() => {
    const dir = RTL_LANGS.has(locale) ? 'rtl' : 'ltr'
    document.documentElement.setAttribute('lang', locale)
    document.documentElement.setAttribute('dir', dir)
    localStorage.setItem('locale', locale)
  }, [locale])

  const t = useCallback(
    (key, params) => {
      const dict = dicts[locale] || dicts.he
      let s = dict[key] ?? key
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          s = s.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
        }
      }
      return s
    },
    [locale],
  )

  const isRtl = RTL_LANGS.has(locale)

  return <Ctx.Provider value={{ locale, setLocale, t, isRtl }}>{children}</Ctx.Provider>
}

export function useT() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useT() must be used inside I18nProvider')
  return ctx
}
