import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing.jsx'
import AdminLogin from './pages/AdminLogin.jsx'
import AdminLeads from './pages/AdminLeads.jsx'
import AdminCalendar from './pages/AdminCalendar.jsx'
import LandingEdit from './pages/LandingEdit.jsx'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/admin" element={<Navigate to="/admin/leads" replace />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/leads" element={<AdminLeads />} />
        <Route path="/admin/calendar" element={<AdminCalendar />} />
        <Route path="/admin/landing-edit" element={<LandingEdit />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
