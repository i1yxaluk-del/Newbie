import { useEffect, useState } from 'react'
import AdminShell from '../components/AdminShell.jsx'
import { api } from '../api.js'

const ORDER = [
  'hero.title', 'hero.subtitle', 'hero.cta',
  'about.title', 'about.text',
  'rooms.title', 'rooms.text',
  'amenities.title', 'amenities.items',
  'gallery.title',
  'location.title', 'location.address', 'location.note',
  'contacts.title', 'contacts.owner_name', 'contacts.owner_role',
  'contacts.phone', 'contacts.vk', 'contacts.vk_personal', 'contacts.owner_photo',
  'footer.note',
]

const HINTS = {
  'amenities.items': 'Список через точку с запятой: Wi-Fi;Парковка;Кондиционер',
  'contacts.phone': 'Формат: +7 918 212-96-01',
  'contacts.vk': 'Ссылка на группу VK',
  'contacts.owner_photo': 'URL фото руководителя (можно из VK)',
}

export default function LandingEdit() {
  const [data, setData] = useState({})
  const [active, setActive] = useState(ORDER[0])
  const [saved, setSaved] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getContent().then(setData).catch(e => setErr(String(e.message || e)))
  }, [])

  function set(k, v) { setData(d => ({ ...d, [k]: v })); setSaved(false) }

  async function save() {
    setBusy(true); setErr(''); setSaved(false)
    try {
      const items = Object.entries(data).map(([key, value]) => ({ key, value: String(value ?? '') }))
      await api.updateContent(items)
      setSaved(true)
    } catch (e) {
      setErr(String(e.message || e))
    } finally { setBusy(false) }
  }

  const keys = Array.from(new Set([...ORDER, ...Object.keys(data)]))

  return (
    <AdminShell>
      <h2>Landing-edit</h2>
      <p className="form__hint">Редактируйте тексты лендинга. Изменения применяются сразу после сохранения.</p>

      {err && <div className="form__error">{err}</div>}
      {saved && <div className="form__success">Сохранено</div>}

      <div className="editor__grid">
        <div className="editor__list">
          {keys.map(k => (
            <button key={k} className={active === k ? 'active' : ''} onClick={() => setActive(k)}>{k}</button>
          ))}
        </div>
        <div className="editor__pane">
          <label style={{ fontSize: 13, color: '#777' }}>Ключ</label>
          <div style={{ fontWeight: 600, marginBottom: 10 }}>{active}</div>
          {HINTS[active] && <p className="form__hint">{HINTS[active]}</p>}
          <textarea value={data[active] || ''} onChange={e => set(active, e.target.value)} />
          <div className="editor__bar">
            <button className="btn btn--primary" disabled={busy} onClick={save}>{busy ? 'Сохраняем...' : 'Сохранить'}</button>
            <a className="btn btn--ghost" href="/" target="_blank" rel="noreferrer">Открыть сайт</a>
          </div>
        </div>
      </div>
    </AdminShell>
  )
}
