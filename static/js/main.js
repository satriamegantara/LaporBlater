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

// Escape HTML utility to prevent XSS in dynamic popups
function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Generate modern, tidy HTML markup for Leaflet Pinpoint Popup
function renderReportPopup(props, isDashboard = false) {
  const facCode = (props.facility_code || "").toUpperCase();
  let facIcon = "fa-road";
  let facLabel = "Jalan";
  let facClass = "tag-fac-jalan";
  let bannerClass = "banner-jalan";
  
  if (facCode === "PJU" || (props.facility_type && props.facility_type.toLowerCase().includes("pju"))) {
    facIcon = "fa-lightbulb";
    facLabel = "Lampu PJU";
    facClass = "tag-fac-pju";
    bannerClass = "banner-pju";
  } else if (facCode === "DRAINASE" || (props.facility_type && props.facility_type.toLowerCase().includes("drainase"))) {
    facIcon = "fa-water";
    facLabel = "Saluran Drainase";
    facClass = "tag-fac-drainase";
    bannerClass = "banner-drainase";
  }

  // Status handling
  const statusCode = (props.status_code || "MENUNGGU_VERIFIKASI").toUpperCase();
  let statusLabel = props.status || "Menunggu Verifikasi";
  if (statusCode === "MENUNGGU_VERIFIKASI") statusLabel = "Menunggu Verifikasi";
  else if (statusCode === "DIVERIFIKASI") statusLabel = "Diverifikasi";
  else if (statusCode === "DIPROSES") statusLabel = "Sedang Diproses";
  else if (statusCode === "SELESAI") statusLabel = "Selesai";

  // Severity handling
  const sev = (props.severity || "ringan").toLowerCase();
  let sevLabel = "Rusak Ringan";
  let sevClass = "tag-sev-ringan";
  let sevIcon = "fa-circle-check";
  if (sev === "berat") {
    sevLabel = "Rusak Berat";
    sevClass = "tag-sev-berat";
    sevIcon = "fa-triangle-exclamation";
  } else if (sev === "sedang") {
    sevLabel = "Rusak Sedang";
    sevClass = "tag-sev-sedang";
    sevIcon = "fa-triangle-exclamation";
  } else if (sev === "ringan") {
    sevLabel = "Rusak Ringan";
    sevClass = "tag-sev-ringan";
    sevIcon = "fa-circle-check";
  } else {
    sevLabel = props.severity || "Belum Ditentukan";
    sevClass = "tag-sev-sedang";
    sevIcon = "fa-circle-info";
  }

  const safeDesc = escapeHtml(props.description || "Laporan kerusakan fasilitas desa.");
  const ticketId = `#LB-${String(props.id).padStart(4, '0')}`;
  const createdAt = props.created_at || "-";
  const actionUrl = isDashboard ? `/dashboard/laporan/${props.id}` : `/laporan/${props.id}`;
  const actionLabel = isDashboard ? "Kelola Laporan" : "Lihat Status Penanganan";

  const headerHtml = props.photo_url ? `
    <div class="report-popup-photo-container">
      <img src="${props.photo_url}" alt="Foto Kerusakan" class="report-popup-photo" onerror="this.closest('.report-popup-photo-container').style.display='none'">
      <div class="report-popup-photo-overlay">
        <span class="report-popup-status-pill status-${statusCode}">
          <span class="status-pulse-dot"></span>
          <span>${statusLabel}</span>
        </span>
      </div>
    </div>
  ` : `
    <div class="report-popup-banner ${bannerClass}">
      <div class="report-popup-banner-icon">
        <i class="fa-solid ${facIcon}"></i>
      </div>
      <span class="report-popup-status-pill status-${statusCode}">
        <span class="status-pulse-dot"></span>
        <span>${statusLabel}</span>
      </span>
    </div>
  `;

  return `
    <div class="report-popup-card">
      ${headerHtml}
      <div class="report-popup-body">
        <div class="report-popup-tags">
          <span class="report-popup-tag ${facClass}">
            <i class="fa-solid ${facIcon}"></i> ${facLabel}
          </span>
          <span class="report-popup-tag ${sevClass}">
            <i class="fa-solid ${sevIcon}"></i> ${sevLabel}
          </span>
        </div>
        
        <p class="report-popup-desc" title="${safeDesc}">
          ${safeDesc}
        </p>

        <div class="report-popup-meta">
          <span class="report-popup-date">
            <i class="fa-regular fa-calendar-days"></i> ${createdAt}
          </span>
          <span class="report-popup-ticket">${ticketId}</span>
        </div>

        <a href="${actionUrl}" class="report-popup-btn">
          <i class="fa-solid fa-circle-info"></i>
          <span>${actionLabel}</span>
          <i class="fa-solid fa-chevron-right btn-arrow"></i>
        </a>
      </div>
    </div>
  `;
}
