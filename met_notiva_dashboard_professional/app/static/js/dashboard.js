const settingsDialog = document.querySelector("#settingsDialog");
const firmSelect = document.querySelector("#firmSelect");
const periodSelect = document.querySelector("#periodSelect");
const activeFirmDisplay = document.querySelector("#activeFirmDisplay");

let agingChart;
let riskChart;

async function apiJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || "Islem tamamlanamadi.");
  }
  return payload;
}

function money(value) {
  return Number(value || 0).toLocaleString("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  });
}

function number(value) {
  return Number(value || 0).toLocaleString("tr-TR");
}

async function loadCurrentFirm() {
  try {
    const payload = await apiJson("/api/current-firm");
    const current = payload.data;
    activeFirmDisplay.textContent = `${current.firm} / ${current.period} - ${current.label}`;
  } catch (error) {
    activeFirmDisplay.textContent = "Firma bilgisi alinamadi";
  }
}

async function loadFirms() {
  firmSelect.innerHTML = "<option>Yukleniyor...</option>";
  const payload = await apiJson("/api/firms");
  const firms = payload.firms || payload.data || [];
  firmSelect.innerHTML = '<option value="">Firma secin</option>';
  firms.forEach((firm) => {
    const option = document.createElement("option");
    option.value = firm.nr;
    option.textContent = `${firm.nr} - ${firm.title || firm.name || ""}`;
    firmSelect.appendChild(option);
  });
}

async function loadPeriods(firmNr) {
  periodSelect.innerHTML = "<option>Yukleniyor...</option>";
  const payload = await apiJson(`/api/periods/${firmNr}`);
  const periods = payload.periods || payload.data || [];
  periodSelect.innerHTML = '<option value="">Donem secin</option>';
  periods.forEach((period) => {
    const option = document.createElement("option");
    option.value = period.nr;
    option.textContent = `${period.nr} - ${period.begdate} / ${period.enddate}`;
    periodSelect.appendChild(option);
  });
}

function renderPriorityList(items) {
  const list = document.querySelector("#priorityList");
  list.innerHTML = "";
  items.slice(0, 5).forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "priority-row";
    row.innerHTML = `
      <div class="priority-badge">${index + 1}</div>
      <div>
        <strong>${item.code || "Cari"} - ${item.name}</strong>
        <span>Tahsilat onceligi, acik bakiye: ${money(item.amount)}</span>
      </div>
      <b>${money(item.amount)}</b>
    `;
    list.appendChild(row);
  });
}

function renderReceivables(items) {
  const list = document.querySelector("#topReceivables");
  list.innerHTML = "";
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "receivable-row";
    row.innerHTML = `
      <span>${index + 1}</span>
      <div><strong>${item.name}</strong><small>${item.code}</small></div>
      <b>${money(item.amount)}</b>
    `;
    list.appendChild(row);
  });
}

function renderOrders(items) {
  const list = document.querySelector("#recentOrders");
  list.innerHTML = "";
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "activity-row";
    row.innerHTML = `
      <strong>${item.fiche}</strong>
      <span>${item.customer}</span>
      <small>${item.date} - ${money(item.amount)}</small>
    `;
    list.appendChild(row);
  });
}

function renderActions(items) {
  const list = document.querySelector("#actionList");
  list.innerHTML = "";
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "activity-row";
    row.innerHTML = `<strong>${item.title}</strong><span>${item.text}</span><small>Bugun</small>`;
    list.appendChild(row);
  });
}

function renderCharts(data) {
  const risk = data.risk || {};
  const top = data.top_receivables || [];
  const labels = top.slice(0, 6).map((x) => x.code || x.name);
  const amounts = top.slice(0, 6).map((x) => x.amount || 0);

  if (agingChart) agingChart.destroy();
  agingChart = new Chart(document.querySelector("#agingChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Acik alacak",
        data: amounts,
        backgroundColor: "#3b82f6",
        borderRadius: 4,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { callback: (value) => number(value) } } },
    },
  });

  if (riskChart) riskChart.destroy();
  riskChart = new Chart(document.querySelector("#riskChart"), {
    type: "doughnut",
    data: {
      labels: ["Dusuk", "Orta", "Yuksek"],
      datasets: [{
        data: [risk.low || 0, risk.medium || 0, risk.high || 0],
        backgroundColor: ["#3b82f6", "#f59e0b", "#ef4444"],
        borderWidth: 0,
      }],
    },
    options: { cutout: "62%" },
  });
}

async function loadDashboard() {
  const payload = await apiJson("/api/dashboard-summary");
  const data = payload.data;
  const metrics = data.metrics;
  const priority = data.priority;

  document.querySelector("#kpiReceivable").textContent = money(metrics.total_receivable);
  document.querySelector("#kpiDebt").textContent = money(metrics.total_debt);
  document.querySelector("#kpiDueToday").textContent = money(metrics.due_today);
  document.querySelector("#kpiRisk").textContent = `${number(metrics.high_risk_count)} cari`;
  document.querySelector("#kpiCustomerCount").textContent = `${number(metrics.customer_count)} cari`;
  document.querySelector("#summaryDate").textContent = data.today;
  document.querySelector("#openAccounts").textContent = number(priority.open_accounts);
  document.querySelector("#criticalAccounts").textContent = number(priority.critical_accounts);
  document.querySelector("#riskAnalyzed").textContent = number(priority.open_accounts);
  document.querySelector("#riskHigh").textContent = number(priority.critical_accounts);
  document.querySelector("#riskScore").textContent = priority.critical_accounts ? "95" : "0";
  document.querySelector("#riskProgress").style.width = priority.open_accounts
    ? `${Math.min(100, Math.round(priority.critical_accounts / priority.open_accounts * 100))}%`
    : "0%";

  renderPriorityList(data.top_receivables || []);
  renderReceivables(data.top_receivables || []);
  renderOrders(data.recent_orders || []);
  renderActions(data.actions || []);
  renderCharts(data);
}

document.querySelector("#firmSettingsBtn")?.addEventListener("click", async () => {
  settingsDialog.showModal();
  await loadFirms();
});

firmSelect?.addEventListener("change", () => {
  if (firmSelect.value) loadPeriods(firmSelect.value);
});

document.querySelector("#saveSettingsBtn")?.addEventListener("click", async () => {
  await apiJson("/api/set-current-settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ firm: firmSelect.value, period: periodSelect.value }),
  });
  settingsDialog.close();
  await loadCurrentFirm();
  await loadDashboard();
});

loadCurrentFirm();
loadDashboard();
