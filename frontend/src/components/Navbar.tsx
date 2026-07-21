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

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: Gauge },
    { name: "Device Manager", href: "/devices", icon: Cpu },
    { name: "Trends & Export", href: "/trends", icon: TrendingUp },
    { name: "Alarms & Logs", href: "/logs", icon: BellRing },
    { name: "Settings & Alerts", href: "/settings", icon: Settings },
  ];

  if (user?.role === "admin") {
    navItems.push({ name: "User Management", href: "/users", icon: Users });
  }

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
          <img 
            src="/mcc_logo.jpg" 
            alt="MCC Logo" 
            style={{ height: "36px", width: "auto", objectFit: "contain", borderRadius: "4px" }} 
          />
          <span style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "0.03em", color: "var(--text-primary)", whiteSpace: "nowrap" }}>
            M-<span style={{ color: "var(--color-primary)" }}>OBSERVER</span>
          </span>
        </div>
        
        <nav>
          <ul className="nav-list" style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <li key={item.name}>
                  <Link 
                    href={item.href} 
                    className={`nav-link ${isActive ? "active" : ""}`}
                  >
                    <Icon size={16} />
                    {item.name}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "var(--bg-main)", padding: "6px 12px", borderRadius: "20px", border: "1px solid var(--border-color)" }}>
            <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--color-primary)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", fontWeight: 700 }}>
              {user?.username ? user.username[0].toUpperCase() : "U"}
            </div>
            <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-primary)" }}>
              {user?.username}
            </span>
            <span style={{ fontSize: "11px", color: "var(--text-muted)", background: "rgba(0,0,0,0.05)", padding: "2px 6px", borderRadius: "10px", textTransform: "capitalize" }}>
              {user?.role}
            </span>
          </div>
          
          <button 
            onClick={logout} 
            className="btn btn-secondary" 
            style={{ padding: "6px 12px", borderRadius: "20px", fontSize: "13px", display: "flex", gap: "6px", alignItems: "center", border: "1px solid var(--border-color)", background: "var(--bg-card)", color: "var(--color-danger)" }}
          >
            <LogOut size={14} />
            Sign Out
          </button>
        </div>
      </div>
    </header>
  );
}
