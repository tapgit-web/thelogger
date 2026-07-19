"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  Gauge, 
  Cpu, 
  TrendingUp, 
  Settings, 
  Users, 
  LogOut,
  Terminal,
  BellRing
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: Gauge },
    { name: "Device Manager", href: "/devices", icon: Cpu },
    { name: "Trends & Export", href: "/trends", icon: TrendingUp },
    { name: "Alarms & Logs", href: "/logs", icon: BellRing },
    { name: "Settings & Alerts", href: "/settings", icon: Settings },
  ];

  // Admin only items
  if (user?.role === "admin") {
    navItems.push({ name: "User Management", href: "/users", icon: Users });
  }

  return (
    <aside className="sidebar">
      <div className="brand-title">
        <Terminal size={24} />
        THE <span>LOGGER</span>
      </div>
      
      <nav style={{ flexGrow: 1 }}>
        <ul className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <Link 
                  href={item.href} 
                  className={`nav-link ${isActive ? "active" : ""}`}
                >
                  <Icon size={18} />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ padding: "0 16px", fontSize: "13px" }}>
            <span style={{ color: "var(--text-muted)" }}>Logged in as:</span>
            <div style={{ fontWeight: 600, color: "var(--text-primary)", marginTop: "2px" }}>
              {user?.username} ({user?.role})
            </div>
          </div>
          
          <button 
            onClick={logout} 
            className="btn btn-secondary" 
            style={{ width: "100%", justifyContent: "flex-start", gap: "12px", border: "none", background: "transparent", color: "var(--color-danger)" }}
          >
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </div>
    </aside>
  );
}
