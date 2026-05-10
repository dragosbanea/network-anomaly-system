import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard', icon: '▣' },
  { to: '/monitor', label: 'Live Monitor', icon: '◉' },
  { to: '/alerts', label: 'Alerts', icon: '⚠' },
  { to: '/history', label: 'History', icon: '≡' },
]

export default function Navbar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        IDS System
        <span>Network Anomaly Detection</span>
      </div>
      <nav>
        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span className="icon">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
