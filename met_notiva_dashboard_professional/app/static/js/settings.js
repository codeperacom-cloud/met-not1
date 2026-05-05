const keys = [
  "SQL_SERVER",
  "SQL_DRIVER",
  "SQL_USER",
  "SQL_PASSWORD",
  "SQL_ENCRYPT",
  "SQL_TRUST_SERVER_CERTIFICATE",
  "ERP_DATABASE",
  "USER_DATABASE",
  "SMTP_HOST",
  "SMTP_PORT",
  "SMTP_USER",
  "SMTP_PASSWORD",
  "SMTP_FROM",
  "SMTP_USE_SSL",
];

async function api(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.error || "Islem basarisiz.");
  return payload;
}

function collect(ids) {
  const data = {};
  ids.forEach((id) => {
    const element = document.querySelector(`#${id}`);
    if (element) data[id] = element.value;
  });
  return data;
}

function fillSettings(settings) {
  keys.forEach((key) => {
    const element = document.querySelector(`#${key}`);
    if (element) element.value = settings[key] || "";
  });
}

function renderLicense(status) {
  const valid = status.valid;
  const record = status.license || {};
  document.querySelector("#licenseBadge").textContent = valid ? `Lisans aktif - ${status.days_left} gun kaldi` : status.reason;
  document.querySelector("#licenseBadge").classList.toggle("invalid", !valid);
  document.querySelector("#licenseState").textContent = valid ? "Aktif" : "Pasif";
  document.querySelector("#licenseDates").textContent = record.start_date
    ? `${record.start_date} / ${record.end_date} (${record.period})`
    : "Lisans girilmedi";
}

async function loadSettings() {
  const payload = await api("/api/settings");
  fillSettings(payload.data.settings);
  renderLicense(payload.data.license);
}

async function saveSettings(ids, statusId) {
  const status = document.querySelector(`#${statusId}`);
  status.textContent = "Kaydediliyor...";
  try {
    const payload = await api("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collect(ids)),
    });
    status.textContent = payload.message || "Kaydedildi.";
  } catch (error) {
    status.textContent = error.message;
  }
}

document.querySelector("#testSqlBtn")?.addEventListener("click", async () => {
  const status = document.querySelector("#sqlStatus");
  status.textContent = "Baglanti test ediliyor...";
  try {
    const payload = await api("/api/settings/test-sql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collect(["SQL_SERVER", "SQL_DRIVER", "SQL_USER", "SQL_PASSWORD", "SQL_ENCRYPT", "SQL_TRUST_SERVER_CERTIFICATE", "ERP_DATABASE"])),
    });
    status.textContent = `${payload.message} Bulunan firma sayisi: ${payload.data.firm_count}`;
  } catch (error) {
    status.textContent = error.message;
  }
});

document.querySelector("#saveSqlBtn")?.addEventListener("click", () => {
  saveSettings(["SQL_SERVER", "SQL_DRIVER", "SQL_USER", "SQL_PASSWORD", "SQL_ENCRYPT", "SQL_TRUST_SERVER_CERTIFICATE", "ERP_DATABASE", "USER_DATABASE"], "sqlStatus");
});

document.querySelector("#saveMailBtn")?.addEventListener("click", () => {
  saveSettings(["SMTP_HOST", "SMTP_PORT", "SMTP_FROM", "SMTP_USER", "SMTP_PASSWORD", "SMTP_USE_SSL"], "mailSettingsStatus");
});

document.querySelector("#saveLicenseBtn")?.addEventListener("click", async () => {
  const status = document.querySelector("#licenseStatus");
  status.textContent = "Lisans kaydediliyor...";
  try {
    const payload = await api("/api/license", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key: document.querySelector("#licenseKey").value,
        period: document.querySelector("#licensePeriod").value,
      }),
    });
    status.textContent = payload.message || "Lisans kaydedildi.";
    const fresh = await api("/api/license");
    renderLicense(fresh.data);
  } catch (error) {
    status.textContent = error.message;
  }
});

loadSettings();
