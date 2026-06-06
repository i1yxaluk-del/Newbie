const API = import.meta.env.VITE_API_URL || ''

function tokenHeader() {
  const t = localStorage.getItem('domik_token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function jsonFetch(url, options = {}) {
  const res = await fetch(`${API}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...tokenHeader(),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

async function formFetch(url, formData) {
  const res = await fetch(`${API}${url}`, {
    method: 'POST',
    headers: tokenHeader(),
    body: formData,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

function uploadDeletePath(url) {
  const m = String(url || '').match(/^\/uploads\/([^/]+)\/([^/]+)$/)
  return m ? `/api/uploads/${m[1]}/${m[2]}` : null
}

export const api = {
  getContent: () => jsonFetch('/api/content'),
  updateContent: (items) => jsonFetch('/api/content', { method: 'PUT', body: JSON.stringify({ items }) }),
  createLead: (data) => jsonFetch('/api/leads', { method: 'POST', body: JSON.stringify(data) }),
  listLeads: () => jsonFetch('/api/leads'),
  updateLeadStatus: (id, status) => jsonFetch(`/api/leads/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  deleteLead: (id) => jsonFetch(`/api/leads/${id}`, { method: 'DELETE' }),
  login: (email, password) => jsonFetch('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  uploadFile: (file, scope = 'general') => {
    const fd = new FormData()
    fd.append('file', file)
    return formFetch(`/api/uploads?scope=${encodeURIComponent(scope)}`, fd)
  },
  deleteUpload: (url) => {
    const path = uploadDeletePath(url)
    return path ? jsonFetch(path, { method: 'DELETE' }) : Promise.resolve({ ok: true })
  },
}

export function setToken(t) { localStorage.setItem('domik_token', t) }
export function clearToken() { localStorage.removeItem('domik_token') }
export function hasToken() { return !!localStorage.getItem('domik_token') }
