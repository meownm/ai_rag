import { NavLink } from 'react-router-dom';

const items = [
  { to: '/query', label: 'Query Workspace' },
  { to: '/ingestion', label: 'Ingestion Admin' },
  { to: '/diagnostics', label: 'Diagnostics' },
];

export function SideNav() {
  return (
    <nav className="w-60 border-r bg-white p-3">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `mb-2 block rounded p-2 text-sm ${isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-100'}`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
