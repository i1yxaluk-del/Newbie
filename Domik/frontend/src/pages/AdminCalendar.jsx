import { useEffect, useMemo, useState } from 'react'
import AdminShell from '../components/AdminShell.jsx'
import { api } from '../api.js'

const RU_MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
const RU_DAYS = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']

function pad(n) { return n.toString().padStart(2, '0') }
function isoDate(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` }
function parseISO(s) { const [y, m, dd] = s.split('-').map(Number); return new Date(y, (m || 1) - 1, dd || 1) }
function addMonths(d, n) { return new Date(d.getFullYear(), d.getMonth() + n, 1) }

function buildMonthCells(year, month) {
  const first = new Date(year, month, 1)
  const firstWeekday = (first.getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells = []
  for (let i = 0; i < firstWeekday; i++) cells.push(null)
  for (let day = 1; day <= daysInMonth; day++) cells.push(new Date(year, month, day))
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

export default function AdminCalendar() {
  const [state, setState] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [base, setBase] = useState(() => {
    const d = new Date(); d.setDate(1); return d
  })
  const [selected, setSelected] = useState(() => new Set())
  const [monthsCount] = useState(3)

  async function load() {
    setErr('')
    try { setState(await api.getCalendarAdmin()) }
    catch (e) { setErr(String(e.message || e)) }
  }
  useEffect(() => { load() }, [])

  const blockedSet = useMemo(() => new Set((state?.blocked || []).map(b => b.day)), [state])
  const occupiedMap = state?.occupied || {}

  function toggle(dateIso) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(dateIso)) next.delete(dateIso)
      else next.add(dateIso)
      return next
    })
  }

  function clearSelection() { setSelected(new Set()) }

  async function blockSelected() {
    if (!selected.size) return
    setBusy(true)
    try {
      for (const day of selected) {
        if (!blockedSet.has(day)) await api.blockDay(day)
      }
      await load()
      clearSelection()
    } catch (e) { setErr(String(e.message || e)) }
    finally { setBusy(false) }
  }

  async function unblockSelected() {
    if (!selected.size) return
    setBusy(true)
    try {
      await api.unblockDays(Array.from(selected))
      await load()
      clearSelection()
    } catch (e) { setErr(String(e.message || e)) }
    finally { setBusy(false) }
  }

  async function blockRangeFromTo() {
    const a = prompt('Дата ОТ (ГГГГ-ММ-ДД)', isoDate(new Date()))
    if (!a) return
    const b = prompt('Дата ДО (ГГГГ-ММ-ДД)', a)
    if (!b) return
    setBusy(true)
    try {
      await api.blockRange(a, b, 'Блокировка администратором')
      await load()
    } catch (e) { setErr(String(e.message || e)) }
    finally { setBusy(false) }
  }

  async function toggleBookings() {
    setBusy(true)
    try {
      await api.setBookingsMode(!state.bookings_open)
      await load()
    } catch (e) { setErr(String(e.message || e)) }
    finally { setBusy(false) }
  }

  const months = useMemo(() => {
    const arr = []
    for (let i = 0; i < monthsCount; i++) {
      const d = addMonths(base, i)
      arr.push({ year: d.getFullYear(), month: d.getMonth() })
    }
    return arr
  }, [base, monthsCount])

  return (
    <AdminShell>
      <div className="cal-shell">
        <header className="cal-topbar">
          <div>
            <h2 style={{ margin: 0 }}>Календарь</h2>
            <div className="cal-status">
              {state ? (state.bookings_open ? 'Приём заявок открыт' : 'Приём заявок закрыт') : 'Загружаем…'}
            </div>
          </div>
          <div className="cal-actions">
            <button className="btn btn--ghost" onClick={() => setBase(addMonths(base, -1))} type="button">← пред. месяц</button>
            <button className="btn btn--ghost" onClick={() => { const d = new Date(); d.setDate(1); setBase(d) }} type="button">Сегодня</button>
            <button className="btn btn--ghost" onClick={() => setBase(addMonths(base, 1))} type="button">след. месяц →</button>
            <button className={'btn ' + (state?.bookings_open ? 'btn--ghost' : 'btn--primary')} onClick={toggleBookings} disabled={!state || busy} type="button">
              {state?.bookings_open ? 'Закрыть приём заявок' : 'Открыть приём заявок'}
            </button>
          </div>
        </header>

        {err && <div className="form__error">{err}</div>}

        <section className="cal-toolbar">
          <div className="cal-legend">
            <span><i className="dot dot--free" /> свободно</span>
            <span><i className="dot dot--lead" /> заявка</span>
            <span><i className="dot dot--block" /> заблокировано</span>
            <span><i className="dot dot--select" /> выбрано</span>
          </div>
          <div className="cal-toolbar__actions">
            <span className="cal-toolbar__count">Выбрано: {selected.size}</span>
            <button className="btn btn--ghost" onClick={clearSelection} disabled={!selected.size} type="button">Сбросить</button>
            <button className="btn btn--primary" onClick={blockSelected} disabled={!selected.size || busy} type="button">Заблокировать выбранные</button>
            <button className="btn btn--ghost" onClick={unblockSelected} disabled={!selected.size || busy} type="button">Снять блок</button>
            <button className="btn btn--ghost" onClick={blockRangeFromTo} disabled={busy} type="button">Блок по диапазону…</button>
          </div>
        </section>

        <div className="cal-months">
          {months.map(m => (
            <div className="cal-month" key={`${m.year}-${m.month}`}>
              <div className="cal-month__title">{RU_MONTHS[m.month]} {m.year}</div>
              <div className="cal-month__weekdays">
                {RU_DAYS.map(d => <div key={d}>{d}</div>)}
              </div>
              <div className="cal-month__grid">
                {buildMonthCells(m.year, m.month).map((cell, i) => {
                  if (!cell) return <div key={i} className="cal-cell cal-cell--empty" />
                  const iso = isoDate(cell)
                  const occupied = occupiedMap[iso]
                  const blocked = blockedSet.has(iso)
                  const sel = selected.has(iso)
                  const isToday = iso === state?.today
                  let cls = 'cal-cell'
                  if (occupied) cls += ' cal-cell--lead'
                  if (blocked) cls += ' cal-cell--block'
                  if (sel) cls += ' cal-cell--select'
                  if (isToday) cls += ' cal-cell--today'
                  const title = []
                  if (occupied) title.push(occupied.map(o => `#${o.lead_id} ${o.name} (${o.status})`).join('\n'))
                  if (blocked) title.push('Заблокировано администратором')
                  return (
                    <button key={i} type="button" className={cls} onClick={() => toggle(iso)} title={title.join('\n')}>
                      <span>{cell.getDate()}</span>
                      {occupied && <em>{occupied.length}</em>}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {state && !state.bookings_open && (
          <div className="cal-card">
            <div className="cal-card__title">Сообщение для гостей, пока приём закрыт</div>
            <div className="cal-card__hint">Меняется в Landing-edit → раздел «Подвал и режим работы».</div>
            <div className="cal-card__quote">{state.closed_message}</div>
          </div>
        )}
      </div>
    </AdminShell>
  )
}
