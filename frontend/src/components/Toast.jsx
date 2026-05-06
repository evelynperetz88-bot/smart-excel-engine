import React from 'react'

export default function Toast({ msg, kind }) {
  return <div className={`toast ${kind === 'error' ? 'error' : ''}`}>{msg}</div>
}
