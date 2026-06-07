import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api.js'

export default function AdminLogin() {
  const [login, setLogin] = useState('admin')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()

  async function submit(e) {
    e.preventDefault()
    if (!password) return
    setBusy(true); setErr('')
    try {
      const r = await api.login(login.trim(), password)
      setToken(r.access_token)
      nav('/admin/leads')
    } catch {
      setErr('Неверные логин или пароль')
    } finally { setBusy(false) }
  }

  return (
    <main className="login">
      <form className="login__box" onSubmit={submit} autoComplete="off">
        <h1 className="login__title">Вход в админку</h1>
        <p className="login__subtitle">Гостевой дом «АЛиНА» · панель управления</p>
        {err && <div className="form__error">{err}</div>}
        <div className="login__field">
          <label htmlFor="login-input">Логин</label>
          <input
            id="login-input"
            type="text"
            value={login}
            onChange={e => setLogin(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="login__field">
          <label htmlFor="password-input">Пароль</label>
          <input
            id="password-input"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        <button type="submit" className="btn btn--primary login__submit" disabled={busy || !password}>
          {busy ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </main>
  )
}
