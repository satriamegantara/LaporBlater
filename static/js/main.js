// Main application helper utilities for LaporBlater

function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Format ISO date to Indonesian readable format
function formatDate(dateStr) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

// Get badge markup
function getStatusBadge(code, name) {
  const c = (code || "").toUpperCase();
  let cls = "badge-menunggu";
  if (c === "DIVERIFIKASI") cls = "badge-diverifikasi";
  else if (c === "DIPROSES") cls = "badge-diproses";
  else if (c === "SELESAI") cls = "badge-selesai";
  return `<span class="badge ${cls}">${name || code}</span>`;
}

function getSeverityBadge(sev) {
  if (!sev) return `<span class="badge badge-menunggu">-</span>`;
  const s = sev.toLowerCase();
  let cls = "badge-ringan";
  if (s === "berat") cls = "badge-berat";
  else if (s === "sedang") cls = "badge-sedang";
  return `<span class="badge ${cls}">${sev}</span>`;
}

function getFacilityBadge(code, name) {
  const c = (code || "").toUpperCase();
  let cls = "badge-jalan";
  if (c === "PJU") cls = "badge-pju";
  else if (c === "DRAINASE") cls = "badge-drainase";
  return `<span class="badge ${cls}">${name || code}</span>`;
}
