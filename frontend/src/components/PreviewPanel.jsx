import React from 'react'

export default function PreviewPanel({ loading, headers, rows, rtl, onExport, exporting, disabled }) {
  return (
    <section className="panel">
      <h2><span className="badge">5</span> תצוגה מקדימה וייצוא</h2>

      {headers.length === 0 ? (
        <div className="muted" style={{ padding: '12px 4px' }}>
          {loading ? 'טוען תצוגה מקדימה…' : 'בחרו לפחות עמודה אחת כדי לראות תצוגה מקדימה.'}
        </div>
      ) : (
        <div className="preview-wrap" dir={rtl ? 'rtl' : 'ltr'}>
          <table className="preview-table">
            <thead>
              <tr>{headers.map((h, i) => <th key={i}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {r.map((c, j) => <td key={j}>{c}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rows.length > 0 && (
        <div className="muted" style={{ marginTop: 6 }}>
          מציג {rows.length} שורות ראשונות (התצוגה המקדימה מוגבלת — הייצוא כולל את כל הנתונים).
        </div>
      )}

      <div className="toolbar">
        <button
          className="btn"
          disabled={disabled || exporting !== null}
          onClick={() => onExport('pdf')}
        >
          ייצוא חכם ל-PDF
          {exporting === 'pdf' && <span className="spinner" />}
        </button>
        <button
          className="btn secondary"
          disabled={disabled || exporting !== null}
          onClick={() => onExport('word')}
        >
          ייצוא חכם ל-Word
          {exporting === 'word' && <span className="spinner" />}
        </button>
        <button
          className="btn secondary"
          disabled={disabled || exporting !== null}
          onClick={() => window.print()}
        >
          הדפסת תצוגה מקדימה
        </button>
      </div>
    </section>
  )
}
