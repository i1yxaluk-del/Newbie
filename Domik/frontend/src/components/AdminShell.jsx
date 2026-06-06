import { Link, useLocation, useNavigate } from 'react-router-dom'
import { clearToken, hasToken } from '../api.js'
import { useEffect } from 'react'

export default function AdminShell({ children }) {
  const loc = useLocation()
  const nav = useNavigate()

  useEffect(() => {
    if (!hasToken()) nav('/admin/login', { replace: true })
  }, [nav])

  function logout() {
    clearToken()
    nav('/admin/login', { replace: true })
  }

  const is = (p) => loc.pathname === p ? 'active' : ''

  return (
    <div className="admin">
      <div className="container">
        <div className="admin__top">
          <div className="brand">
            <div className="brand__mark">A</div>
            <div className="brand__name">Domik · админ</div>
          </div>
          <div className="admin__nav">
            <Link className={is('/admin/leads')} to="/admin/leads">Заявки</Link>
            <Link className={is('/admin/landing-edit')} to="/admin/landing-edit">Landing-edit</Link>
            <a href="/" target="_blank" rel="noreferrer">Открыть сайт</a>
            <button className="btn btn--ghost" onClick={logout}>Выйти</button>
          </div>
        </div>
        {children}
      </div>
    </div>
  )
}
