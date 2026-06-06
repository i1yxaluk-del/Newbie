import { useEffect, useState } from 'react'
import AdminShell from '../components/AdminShell.jsx'
import { api } from '../api.js'

const STATUSES = ['new', 'in_progress', 'confirmed', 'closed', 'spam']
const LABELS = { new: 'Новая', in_progress: 'В работе', confirmed: 'Подтверждена', closed: 'Закрыта', spam: 'Спам' }

export default function AdminLeads() {
  const [leads, setLeads] = useState([])
  const [err, setErr] = useState('')

  async function load() {
    try { setLeads(await api.listLeads()) } catch (e) { setErr(String(e.message || e)) }
  }
  useEffect(() => { load() }, [])

  async function setStatus(id, status) {
    await api.updateLeadStatus(id, status)
    load()
  }
  async function del(id) {
    if (!confirm('Удалить заявку?')) return
    await api.deleteLead(id)
    load()
  }

  return (
    <AdminShell>
      <h2>Заявки</h2>
      {err && <div className="form__error">{err}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>#</th><th>Дата</th><th>Имя</th><th>Контакты</th>
            <th>Гостей / Даты</th><th>Сообщение</th><th>Статус</th><th></th>
          </tr>
        </thead>
        <tbody>
          {leads.length === 0 && <tr><td colSpan={8} style={{ textAlign: 'center', padding: 28 }}>Заявок пока нет</td></tr>}
          {leads.map(l => (
            <tr key={l.id}>
              <td>{l.id}</td>
              <td>{new Date(l.created_at).toLocaleString('ru-RU')}</td>
              <td>{l.name}</td>
              <td>
                <div>{l.phone}</div>
                {l.email && <div style={{ color: '#777' }}>{l.email}</div>}
              </td>
              <td>
                {l.guests ? <div>{l.guests} гостей</div> : null}
                {(l.date_from || l.date_to) && <div style={{ color: '#777' }}>{l.date_from || '?'} → {l.date_to || '?'}</div>}
              </td>
              <td style={{ maxWidth: 280 }}>{l.message}</td>
              <td>
                <select value={l.status} onChange={e => setStatus(l.id, e.target.value)}>
                  {STATUSES.map(s => <option key={s} value={s}>{LABELS[s]}</option>)}
                </select>
                <div><span className={'status status--' + l.status}>{LABELS[l.status]}</span></div>
              </td>
              <td><button className="btn btn--ghost" onClick={() => del(l.id)}>Удалить</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </AdminShell>
  )
}
