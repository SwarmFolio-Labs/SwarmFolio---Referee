import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { getClients } from './api.js'
import Home from './pages/Home.jsx'
import Mandate from './pages/Mandate.jsx'

// Links from the hackathon version (#/client/C04) still land on the right mandate.
function OldClient() {
  const { id } = useParams()
  return <Navigate to={`/m/${id}`} replace />
}

export default function App() {
  const [clients, setClients] = useState(null)
  const [error, setError] = useState(null)
  const { pathname, hash } = useLocation()

  useEffect(() => {
    getClients().then(setClients).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [pathname, hash])

  return (
    <Routes>
      <Route path="/" element={<Home clients={clients} error={error} />} />
      <Route path="/m/:id" element={<Mandate clients={clients} />} />
      <Route path="/client/:id" element={<OldClient />} />
      <Route path="/experiment" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
