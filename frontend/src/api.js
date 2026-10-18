// All calls to api.py. In dev Vite proxies /api to :8000; in production api.py serves this app itself.
const BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* not JSON */
    }
    const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    err.status = res.status
    throw err
  }
  return res.json()
}

export const getClients = () => request('/clients')
export const getDemo = (id) => request(`/demo/${id}`)
export const getPrices = (id) => request(`/prices/${id}`)
export const getExperiment = () => request('/experiment')
export const checkProposal = (clientId, weights) =>
  request('/referee', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: clientId,
      proposal: { weights, thesis: 'Checked from the web app', reasons: {} },
    }),
  })
