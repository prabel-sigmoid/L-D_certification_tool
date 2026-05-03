import React, { useState } from "react";
import { logout, getToken } from "../services/auth";
import * as XLSX from "xlsx";

const API_URL = import.meta.env.VITE_API_URL;

function Dashboard() {
  const [certs, setCerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sheetUrl, setSheetUrl] = useState("");
  const [folderUrl, setFolderUrl] = useState("");
  const [syncStatus, setSyncStatus] = useState("");
  const [progress, setProgress] = useState(null); // { done, total } | null
  const [statusFilter, setStatusFilter] = useState("all");

  // ── Determine status label for a valid_to date ──────────────────────────
  const getStatus = (dateString) => {
    if (!dateString) return "no-expiry";
    const diff = (new Date(dateString) - new Date()) / (1000 * 60 * 60 * 24);
    if (diff < 0) return "expired";
    if (diff <= 30) return "expiring";
    return "valid";
  };

  const STATUS_STYLE = {
    "valid":     { bg: "#e8f5e9", label: "✅ Valid" },
    "expiring":  { bg: "#fff3e0", label: "⚠️ Expiring" },
    "expired":   { bg: "#ffebee", label: "❌ Expired" },
    "no-expiry": { bg: "#f5f5f5", label: "➖ No Expiry" },
  };

  // ── Streaming sync handler ───────────────────────────────────────────────
  const handleSync = async () => {
    if (!sheetUrl || !folderUrl) {
      alert("Please provide both Sheet URL and Folder URL");
      return;
    }
    setLoading(true);
    setProgress(null);
    setSyncStatus("Connecting...");
    setCerts([]);

    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ sheet_url: sheetUrl, folder_url: folderUrl }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep any incomplete last line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const event = JSON.parse(line);

            if (event.type === "start") {
              if (event.total_new === 0) {
                setSyncStatus("Loading cached records...");
              } else {
                setSyncStatus(`Processing 0/${event.total_new}...`);
                setProgress({ done: 0, total: event.total_new });
              }
            } else if (event.type === "progress") {
              setProgress({ done: event.done, total: event.total });
              setSyncStatus(`Processing ${event.done}/${event.total}...`);
            } else if (event.type === "complete") {
              setCerts(event.certificates || []);
              setSyncStatus("Sync completed!");
              setProgress(null);
              if (event.errors?.length > 0) {
                console.warn("Sync errors:", event.errors);
              }
            }
          } catch {
            // skip malformed line
          }
        }
      }
    } catch (err) {
      console.error(err);
      if (err.message?.includes("401") || err.message?.toLowerCase().includes("token")) {
        logout();
      }
      setSyncStatus(`Sync Failed: ${err.message}`);
      setProgress(null);
    } finally {
      setLoading(false);
    }
  };

  // ── Excel export ─────────────────────────────────────────────────────────
  const exportToExcel = () => {
    if (certs.length === 0) return;
    const worksheetData = certs.map((c) => {
      const s = getStatus(c.valid_to);
      return {
        Employee: c.employee_name,
        Email: c.email,
        "Certification Name": c.certification_name,
        Issuer: c.issuer,
        "Valid From": c.valid_from,
        "Valid To": c.valid_to,
        Status: STATUS_STYLE[s]?.label.replace(/[^ -~]/g, "").trim() || s,
      };
    });
    const worksheet = XLSX.utils.json_to_sheet(worksheetData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Certificates");
    XLSX.writeFile(workbook, "certificates_report.xlsx");
  };

  // ── Filtered certs ───────────────────────────────────────────────────────
  const filteredCerts =
    statusFilter === "all"
      ? certs
      : certs.filter((c) => getStatus(c.valid_to) === statusFilter);

  // ── Counts for filter badges ─────────────────────────────────────────────
  const counts = certs.reduce((acc, c) => {
    const s = getStatus(c.valid_to);
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ padding: "30px", fontFamily: "sans-serif" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>⚙️ L&D Admin Dashboard</h1>
          <p>Synchronize and review employee certificates securely.</p>
        </div>
        <button
          onClick={logout}
          style={{ padding: "8px 16px", backgroundColor: "#d9534f", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
        >
          Logout
        </button>
      </div>

      {/* Sync Control Panel */}
      <div style={{ border: "1px solid #ccc", padding: "20px", borderRadius: "8px", marginBottom: "30px", backgroundColor: "#f9f9f9" }}>
        <h3>Google Workspace Sync</h3>
        <div style={{ marginBottom: "10px" }}>
          <label style={{ display: "block", fontWeight: "bold", marginBottom: "5px" }}>Google Sheet URL:</label>
          <input
            type="text"
            style={{ width: "100%", padding: "8px" }}
            placeholder="https://docs.google.com/spreadsheets/d/..."
            value={sheetUrl}
            onChange={(e) => setSheetUrl(e.target.value)}
          />
        </div>
        <div style={{ marginBottom: "15px" }}>
          <label style={{ display: "block", fontWeight: "bold", marginBottom: "5px" }}>Google Drive Folder URL:</label>
          <input
            type="text"
            style={{ width: "100%", padding: "8px" }}
            placeholder="https://drive.google.com/drive/folders/..."
            value={folderUrl}
            onChange={(e) => setFolderUrl(e.target.value)}
          />
        </div>
        <button
          onClick={handleSync}
          disabled={loading}
          style={{ padding: "10px 20px", backgroundColor: loading ? "#ccc" : "#0056b3", color: "white", border: "none", borderRadius: "4px", cursor: loading ? "not-allowed" : "pointer" }}
        >
          {loading ? "Syncing..." : "🔄 Run AI Sync"}
        </button>

        {/* Progress bar */}
        {progress && progress.total > 0 && (
          <div style={{ marginTop: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "4px" }}>
              <span>Processing new certificates</span>
              <span style={{ fontWeight: "bold" }}>{progress.done}/{progress.total}</span>
            </div>
            <div style={{ background: "#ddd", borderRadius: "6px", height: "10px", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${Math.round((progress.done / progress.total) * 100)}%`,
                  backgroundColor: "#0056b3",
                  borderRadius: "6px",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          </div>
        )}

        {syncStatus && (
          <p style={{ marginTop: "10px", fontWeight: "bold", color: syncStatus.includes("Failed") ? "red" : "green" }}>
            {syncStatus}
          </p>
        )}
      </div>

      {/* Table Header: title + filter + download */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
        <h2 style={{ margin: 0 }}>Employee Certificates {certs.length > 0 && <span style={{ fontSize: "14px", fontWeight: "normal", color: "#555" }}>({filteredCerts.length}/{certs.length} shown)</span>}</h2>

        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          {/* Status filter */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {[
              { key: "all",      label: "All",        color: "#555" },
              { key: "valid",    label: "✅ Valid",    color: "#2e7d32" },
              { key: "expiring", label: "⚠️ Expiring", color: "#e65100" },
              { key: "expired",  label: "❌ Expired",  color: "#c62828" },
              { key: "no-expiry",label: "➖ No Expiry", color: "#757575" },
            ].map(({ key, label, color }) => (
              <button
                key={key}
                onClick={() => setStatusFilter(key)}
                style={{
                  padding: "5px 12px",
                  borderRadius: "20px",
                  border: `2px solid ${statusFilter === key ? color : "#ccc"}`,
                  backgroundColor: statusFilter === key ? color : "#fff",
                  color: statusFilter === key ? "#fff" : color,
                  cursor: "pointer",
                  fontWeight: statusFilter === key ? "bold" : "normal",
                  fontSize: "13px",
                  transition: "all 0.15s",
                }}
              >
                {label}{key !== "all" && counts[key] ? ` (${counts[key]})` : key === "all" && certs.length ? ` (${certs.length})` : ""}
              </button>
            ))}
          </div>

          {/* Download button */}
          <button
            onClick={exportToExcel}
            disabled={certs.length === 0}
            style={{ padding: "8px 16px", backgroundColor: certs.length === 0 ? "#ccc" : "#28a745", color: "white", border: "none", borderRadius: "4px", cursor: certs.length === 0 ? "not-allowed" : "pointer" }}
          >
            📥 Download EXCEL (.xlsx)
          </button>
        </div>
      </div>

      {/* Certificates Table */}
      <table border="1" cellPadding="10" style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead style={{ backgroundColor: "#333", color: "#fff" }}>
          <tr>
            <th>Employee</th>
            <th>Email</th>
            <th>Certification Name</th>
            <th>Issuer</th>
            <th>Valid From</th>
            <th>Valid To</th>
            <th>Status</th>
            <th>Document</th>
          </tr>
        </thead>
        <tbody>
          {filteredCerts.length === 0 ? (
            <tr>
              <td colSpan="8" style={{ textAlign: "center", padding: "20px" }}>
                {certs.length === 0
                  ? "No records found. Run a Sync to pull records from Google Workspace."
                  : `No records match the "${statusFilter}" filter.`}
              </td>
            </tr>
          ) : (
            filteredCerts.map((c, idx) => {
              const s = getStatus(c.valid_to);
              const { bg, label } = STATUS_STYLE[s];
              return (
                <tr key={idx} style={{ backgroundColor: bg }}>
                  <td><strong>{c.employee_name}</strong></td>
                  <td>{c.email}</td>
                  <td>{c.certification_name || "N/A"}</td>
                  <td>{c.issuer || "N/A"}</td>
                  <td>{c.valid_from || "N/A"}</td>
                  <td>{c.valid_to || "N/A"}</td>
                  <td style={{ textAlign: "center" }}>{label}</td>
                  <td style={{ textAlign: "center" }}>
                    {c.doc_url ? (
                      <a href={c.doc_url} target="_blank" rel="noreferrer">📄 View</a>
                    ) : (
                      "Missing"
                    )}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

export default Dashboard;
