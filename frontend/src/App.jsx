import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import LiveMonitor from './pages/LiveMonitor.jsx'
import Alerts from './pages/Alerts.jsx'
import History from './pages/History.jsx'

export default function App() {
  return (
    <div className="layout">
      <Navbar />
      <div className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/monitor" element={<LiveMonitor />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </div>
    </div>
  )
}
