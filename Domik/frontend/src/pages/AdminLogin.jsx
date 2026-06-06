import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api.js'

export default function AdminLogin() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await api.login(email, password)
      setToken(r.access_token)
      nav('/admin/leads')
    } catch {
      setErr('Неверные email или пароль')
    } finally { setBusy(false) }
  }

  return (
    <div className="login">
      <form className="login__box" onSubmit={submit}>
        <h2>Вход в админку</h2>
        {err && <div className="form__error">{err}</div>}
        <label>Email</label>
        <input value={email} onChange={e => setEmail(e.target.value)} required />
        <label>Пароль</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
        <div style={{ marginTop: 18 }}>
          <button className="btn btn--primary" disabled={busy} type="submit">{busy ? 'Входим...' : 'Войти'}</button>
        </div>
      </form>
    </div>
  )
}
