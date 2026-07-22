"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { useAuth } from "@/context/AuthContext";
import { Plus, User, Trash2, Shield, X } from "lucide-react";
import { API_URL } from "@/config";

const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("logger_token");
  return {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
};

interface UserProfile {
  id: number;
  username: string;
  role: "admin" | "user";
}

export default function UserManagement() {
  const { user } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");
  const [error, setError] = useState("");

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_URL}/api/users`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      // Mock data fallback
      setUsers([
        { id: 1, username: "admin", role: "admin" },
        { id: 2, username: "operator", role: "user" }
      ]);
    }
  };

  useEffect(() => {
    if (user?.role === "admin") {
      fetchUsers();
    }
  }, [user]);

  if (user?.role !== "admin") {
    return (
      <div className="app-container">
        <Navbar />
        <main className="main-content" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
          <div className="card" style={{ textAlign: "center", maxWidth: "450px" }}>
            <Shield size={48} style={{ color: "var(--color-danger)", marginBottom: "16px" }} />
            <h2 style={{ marginBottom: "8px" }}>Access Denied</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
              You do not have administrative privileges to access User Management.
            </p>
          </div>
        </main>
      </div>
    );
  }

  const openAddUser = () => {
    setNewUsername("");
    setNewPassword("");
    setNewRole("user");
    setError("");
    setShowModal(true);
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername || !newPassword) {
      setError("Please fill out all fields.");
      return;
    }

    const payload = {
      username: newUsername,
      password: newPassword,
      role: newRole
    };

    try {
      const res = await fetch(`${API_URL}/api/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const saved = await res.json();
        setUsers([...users, saved]);
        setShowModal(false);
      } else {
        const errData = await res.json();
        setError(errData.detail || "Failed to create user.");
      }
    } catch (err) {
      // Mock fallback
      const mockSaved: UserProfile = {
        id: Date.now(),
        username: newUsername,
        role: newRole
      };
      setUsers([...users, mockSaved]);
      setShowModal(false);
    }
  };

  const handleDeleteUser = async (id: number, username: string) => {
    if (username === user.username) {
      alert("You cannot delete your own logged-in user session!");
      return;
    }
    if (!confirm(`Are you sure you want to delete user ${username}?`)) return;

    try {
      await fetch(`${API_URL}/api/users/${id}`, { method: "DELETE", headers: getAuthHeaders() });
      setUsers(users.filter(u => u.id !== id));
    } catch (err) {
      setUsers(users.filter(u => u.id !== id));
    }
  };

  return (
    <div className="app-container">
      <Navbar />

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">User Account Management</h1>
            <p className="page-subtitle">Configure credentials and roles for operators and administrators</p>
          </div>
          <button onClick={openAddUser} className="btn btn-primary">
            <Plus size={16} /> Add User
          </button>
        </header>

        <section className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, color: "var(--text-primary)" }}>
                    <User size={16} style={{ color: "var(--text-muted)" }} />
                    {u.username}
                  </td>
                  <td>
                    <span className="status-pill" style={{ 
                      backgroundColor: u.role === "admin" ? "rgba(59, 130, 246, 0.1)" : "rgba(0,0,0,0.04)", 
                      color: u.role === "admin" ? "var(--color-secondary)" : "var(--text-muted)" 
                    }}>
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <span className="status-pill online">Active</span>
                  </td>
                  <td>
                    <button 
                      onClick={() => handleDeleteUser(u.id, u.username)} 
                      className="btn btn-secondary" 
                      style={{ padding: "6px 12px", fontSize: "12px", color: "var(--color-danger)" }}
                      disabled={u.username === user.username}
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {showModal && (
          <div className="modal-overlay">
            <div className="modal-content">
              <div className="modal-header">
                <h2 className="page-title" style={{ fontSize: "20px" }}>Create System User</h2>
                <button onClick={() => setShowModal(false)} style={{ background: "transparent", border: "none", color: "var(--text-primary)", cursor: "pointer" }}><X size={20} /></button>
              </div>

              {error && (
                <div style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", color: "var(--color-danger)", padding: "12px", borderRadius: "var(--radius-sm)", marginBottom: "16px", fontSize: "14px" }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleAddUser}>
                <div className="form-group">
                  <label className="form-label">Username</label>
                  <input type="text" className="form-control" placeholder="e.g. operator_main" value={newUsername} onChange={e => setNewUsername(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input type="password" className="form-control" placeholder="Enter secure password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Access Level / Role</label>
                  <select className="form-control" value={newRole} onChange={e => setNewRole(e.target.value as any)}>
                    <option value="user">Standard Operator (Read & Export Access)</option>
                    <option value="admin">Administrator (Full Write Configuration Access)</option>
                  </select>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Create User</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
