// let salesChart;
let detailTable;
let modalCariTable;
let modalUrunTable;
let modalHareketTable;
let selectedSalesman = "";
let lastModalData;
let allPersonnel = [];
let originalPersonnel = []; // Orijinal veriyi sakla

const monthNames = {
  "01": "Ocak", "02": "Subat", "03": "Mart", "04": "Nisan",
  "05": "Mayis", "06": "Haziran", "07": "Temmuz", "08": "Agustos",
  "09": "Eylul", "10": "Ekim", "11": "Kasim", "12": "Aralik",
};

function currency(value) {
  return Number(value || 0).toLocaleString("tr-TR", { style: "currency", currency: "TRY" });
}

function initials(name) {
  return String(name || "N")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function getAvatarColor(name) {
  const colors = [
    "linear-gradient(135deg, #2563eb, #3b82f6)",
    "linear-gradient(135deg, #ea580c, #f97316)",
    "linear-gradient(135deg, #7c3aed, #a855f7)",
    "linear-gradient(135deg, #059669, #10b981)",
    "linear-gradient(135deg, #db2777, #ec4899)",
    "linear-gradient(135deg, #0891b2, #06b6d4)",
  ];
  let hash = 0;
  for (let i = 0; i < (name || "").length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function getCurrentMonthName() {
  const month = new Date().getMonth() + 1;
  return monthNames[String(month).padStart(2, "0")] || "Guncel";
}

async function json(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.error || "API hatasi");
  return payload;
}

// Personel Tablosu Render
function renderPersonnelTable(rows) {
  const tbody = document.querySelector("#personnelTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  if (rows.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; padding: 40px; color: var(--muted);">
          <i class="fas fa-search" style="font-size: 24px; margin-bottom: 12px; display: block;"></i>
          Sonuc bulunamadi
        </td>
      </tr>
    `;
    return;
  }
  
  rows.forEach((row) => {
    const name = row.satis_eleman || "Belirtilmemis";
    const tr = document.createElement("tr");
    tr.className = "personnel-row";
    tr.innerHTML = `
      <td>
        <div class="personnel-cell">
          <div class="personnel-avatar-small" style="background: ${getAvatarColor(name)}">${initials(name)}</div>
          <span class="personnel-name">${name}</span>
        </div>
      </td>
      <td><strong>${Number(row.miktar || 0).toLocaleString("tr-TR")}</strong> <span class="unit">adet</span></td>
      <td><strong class="amount">${currency(row.net_tutar || 0)}</strong></td>
      <td>
        <button class="button secondary detail-btn" data-salesman="${name}">
          <i class="fas fa-eye"></i> Detaylar
        </button>
      </td>
    `;
    
    const detailBtn = tr.querySelector(".detail-btn");
    detailBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openPersonnelModal(row);
    });
    
    tbody.appendChild(tr);
  });
}

// Search functionality - FIX: silindiğinde eski haline dön
document.querySelector("#personnelSearch")?.addEventListener("input", (e) => {
  const term = e.target.value.toLowerCase().trim();
  
  if (!term) {
    // Boşsa orijinal veriyi göster
    renderPersonnelTable(originalPersonnel);
    return;
  }
  
  const filtered = allPersonnel.filter(p => 
    (p.satis_eleman || "").toLowerCase().includes(term)
  );
  renderPersonnelTable(filtered);
});

async function openPersonnelModal(row) {
  selectedSalesman = row.satis_eleman || "Belirtilmemis";
  const modal = document.querySelector("#personnelModal");
  if (!modal) return;
  
  const avatar = document.querySelector("#modalAvatar");
  if (avatar) {
    avatar.textContent = initials(selectedSalesman);
    avatar.style.background = getAvatarColor(selectedSalesman);
  }
  const nameEl = document.querySelector("#modalName");
  if (nameEl) nameEl.textContent = selectedSalesman;
  
  const currentMonth = getCurrentMonthName();
  const monthLabel = document.querySelector("#currentMonthLabel");
  if (monthLabel) monthLabel.textContent = currentMonth;
  const cariMonthLabel = document.querySelector("#cariMonthLabel");
  if (cariMonthLabel) cariMonthLabel.textContent = currentMonth + " Ayi";
  const urunMonthLabel = document.querySelector("#urunMonthLabel");
  if (urunMonthLabel) urunMonthLabel.textContent = currentMonth + " Ayi";
  
  // Reset ay secici
  const monthSelector = document.querySelector("#monthSelector");
  if (monthSelector) monthSelector.value = "";
  
  await loadModalData();
  modal.showModal();
}

async function loadModalData() {
  const month = document.querySelector("#monthSelector")?.value || "";
  const params = new URLSearchParams({ salesman: selectedSalesman, month });
  const payload = await json(`/api/sales-performance/modal-summary?${params.toString()}`);
  const data = payload.data || {};
  lastModalData = data;

  const monthAmount = document.querySelector("#modalMonthAmount");
  if (monthAmount) monthAmount.textContent = currency(data.month_total_amount);
  
  const monthQty = document.querySelector("#modalMonthQty");
  if (monthQty) monthQty.textContent = Number(data.month_total_qty || 0).toLocaleString("tr-TR") + " Adet";
  
  const monthOrders = document.querySelector("#modalMonthOrders");
  if (monthOrders) monthOrders.textContent = Number(data.month_order_count || 0).toLocaleString("tr-TR") + " Siparis";

  const yearAmount = document.querySelector("#modalYearAmount");
  if (yearAmount) yearAmount.textContent = currency(data.year_total_amount);
  
  const yearQty = document.querySelector("#modalYearQty");
  if (yearQty) yearQty.textContent = Number(data.year_total_qty || 0).toLocaleString("tr-TR") + " Adet";
  
  const avgOrder = document.querySelector("#modalAvgOrder");
  if (avgOrder) avgOrder.textContent = currency(data.year_avg_order || 0);
  
  const yearOrders = document.querySelector("#modalYearOrders");
  if (yearOrders) yearOrders.textContent = Number(data.year_order_count || 0).toLocaleString("tr-TR") + " Siparis";

  initModalTables(data);
}

function initModalTables(data) {
  if (modalCariTable) modalCariTable.destroy();
  modalCariTable = $("#modalCariTable").DataTable({
    data: data.cari_data || [],
    columns: [
      { data: "cari_unvan", title: "Cari", className: "dt-left" },
      { data: "tutar", title: "Tutar", render: (v) => currency(v), className: "dt-right" },
    ],
    pageLength: 25,
    searching: true,
    info: true,
    destroy: true,
    scrollY: "calc(90vh - 400px)",
    scrollCollapse: true,
    language: { 
      search: "Ara:",
      lengthMenu: "_MENU_",
      info: "_START_-_END_ / _TOTAL_",
      paginate: { next: ">", previous: "<" }
    }
  });

  if (modalUrunTable) modalUrunTable.destroy();
  modalUrunTable = $("#modalUrunTable").DataTable({
    data: data.urun_data || [],
    columns: [
      { data: "urun_kodu", title: "Kod", className: "dt-left" },
      { data: "urun_adi", title: "Urun", className: "dt-left" },
      { data: "miktar", title: "Miktar", render: (v) => Number(v || 0).toLocaleString("tr-TR"), className: "dt-right" },
    ],
    pageLength: 25,
    searching: true,
    info: true,
    destroy: true,
    scrollY: "calc(90vh - 400px)",
    scrollCollapse: true,
    language: { 
      search: "Ara:",
      lengthMenu: "_MENU_",
      info: "_START_-_END_ / _TOTAL_",
      paginate: { next: ">", previous: "<" }
    }
  });

  if (modalHareketTable) modalHareketTable.destroy();
  modalHareketTable = $("#modalHareketTable").DataTable({
    data: data.hareket_data || data.detail_data || [],
    columns: [
      { data: "tarih", title: "Tarih", className: "dt-left" },
      { data: "cari_unvan", title: "Cari", className: "dt-left" },
      { data: "urun_kodu", title: "Kod", className: "dt-left" },
      { data: "urun_adi", title: "Urun", className: "dt-left" },
      { data: "miktar", title: "Miktar", className: "dt-right" },
      { data: "net_tutar", title: "Net tutar", render: (v) => currency(v), className: "dt-right" },
    ],
    pageLength: 25,
    searching: true,
    info: true,
    destroy: true,
    scrollY: "calc(90vh - 400px)",
    scrollCollapse: true,
    language: { 
      search: "Ara:",
      lengthMenu: "_MENU_",
      info: "_START_-_END_ / _TOTAL_",
      paginate: { next: ">", previous: "<" }
    }
  });
}

// Tab switching
document.querySelectorAll(".modal-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".modal-tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    const tabId = "tab" + btn.dataset.tab.charAt(0).toUpperCase() + btn.dataset.tab.slice(1);
    const tabEl = document.querySelector("#" + tabId);
    if (tabEl) tabEl.classList.add("active");
    
    // Tablo yeniden çizim (scroll düzeltmesi için)
    setTimeout(() => {
      if (modalCariTable) modalCariTable.columns.adjust();
      if (modalUrunTable) modalUrunTable.columns.adjust();
      if (modalHareketTable) modalHareketTable.columns.adjust();
    }, 50);
  });
});

// Ay secici degisimi
document.querySelector("#monthSelector")?.addEventListener("change", async () => {
  const selectedMonth = document.querySelector("#monthSelector").value;
  const monthName = selectedMonth ? monthNames[selectedMonth] : getCurrentMonthName();
  
  const cariMonthLabel = document.querySelector("#cariMonthLabel");
  if (cariMonthLabel) cariMonthLabel.textContent = monthName + " Ayi";
  const urunMonthLabel = document.querySelector("#urunMonthLabel");
  if (urunMonthLabel) urunMonthLabel.textContent = monthName + " Ayi";
  const currentMonthLabel = document.querySelector("#currentMonthLabel");
  if (currentMonthLabel) currentMonthLabel.textContent = monthName;
  
  await loadModalData();
});

async function loadCards() {
  try {
    const payload = await json("/api/sales-performance/summary");
    originalPersonnel = payload.data || []; // Orijinal veriyi sakla
    allPersonnel = [...originalPersonnel];
    renderPersonnelTable(originalPersonnel);
  } catch (e) {
    console.error("Kartlar yuklenemedi:", e);
  }
}

async function loadChart() {
  try {
    const payload = await json("/api/sales-performance/monthly");
    const rows = payload.data || [];
    const months = [...new Set(rows.map((r) => r.ay))].sort();
    const salesmen = [...new Set(rows.map((r) => r.satis_eleman))];
    const datasets = salesmen.map((salesman) => ({
      label: salesman,
      data: months.map((month) => rows.find((r) => r.ay === month && r.satis_eleman === salesman)?.net_tutar || 0),
      backgroundColor: getAvatarColor(salesman).match(/#[a-f0-9]{6}/i)?.[0] || "#3b82f6",
      borderRadius: 6,
    }));

    if (salesChart) salesChart.destroy();
    salesChart = new Chart(document.querySelector("#monthlyChart"), {
      type: "bar",
      data: { labels: months.map(m => monthNames[m] || m), datasets },
      options: { 
        responsive: true, 
        maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: { y: { ticks: { callback: (v) => Number(v).toLocaleString("tr-TR") } } }
      },
    });
  } catch (e) {
    console.error("Grafik yuklenemedi:", e);
  }
}

async function loadFilters() {
  try {
    const [salesmenRes, carilerRes] = await Promise.all([
      fetch("/api/sales-performance/salesmen"),
      fetch("/api/sales-performance/cariler")
    ]);
    const salesmen = await salesmenRes.json();
    const cariler = await carilerRes.json();
    
    const salesmanSelect = document.querySelector("#filterSalesman");
    const cariSelect = document.querySelector("#filterCari");
    if (salesmanSelect) {
      salesmanSelect.innerHTML = '<option value="">Tumu</option>';
      (salesmen.salesmen || []).forEach((x) => salesmanSelect.add(new Option(x, x)));
    }
    if (cariSelect) {
      cariSelect.innerHTML = '<option value="">Tumu</option>';
      (cariler.cariler || []).forEach((x) => cariSelect.add(new Option(x, x)));
    }
  } catch (e) {
    console.error("Filtreler yuklenemedi:", e);
  }
}

function initTable() {
  detailTable = $("#detailSalesTable").DataTable({
    ajax: {
      url: "/api/sales-performance/detail",
      data: (data) => {
        data.startDate = document.querySelector("#startDate")?.value || "";
        data.endDate = document.querySelector("#endDate")?.value || "";
        data.salesman = document.querySelector("#filterSalesman")?.value || "";
        data.cari = document.querySelector("#filterCari")?.value || "";
      },
      dataSrc: "data",
    },
    columns: [
      { data: "satis_eleman", title: "Satis elemani" },
      { data: "cari_unvan", title: "Cari" },
      { data: "urun_kodu", title: "Kod" },
      { data: "urun_adi", title: "Urun" },
      { data: "miktar", title: "Miktar" },
      { data: "net_tutar", title: "Net tutar", render: (v) => currency(v) },
    ],
    pageLength: 25,
    destroy: true,
    language: { 
      search: "Ara:",
      lengthMenu: "_MENU_ kayit",
      info: "_TOTAL_ kayit",
      paginate: { next: "Sonraki", previous: "Onceki" }
    }
  });
}

document.querySelector("#applyFiltersBtn")?.addEventListener("click", () => {
  if (detailTable) detailTable.ajax.reload();
});

document.querySelector("#closeModalBtn")?.addEventListener("click", () => {
  const modal = document.querySelector("#personnelModal");
  if (modal) modal.close();
});

document.querySelector("#exportExcelBtn")?.addEventListener("click", () => {
  if (!lastModalData) return;
  const wb = XLSX.utils.book_new();
  const month = document.querySelector("#monthSelector")?.value || String(new Date().getMonth() + 1).padStart(2, "0");
  const monthName = monthNames[month] || getCurrentMonthName();
  XLSX.utils.book_append_sheet(
    wb,
    XLSX.utils.json_to_sheet([
      { Metrik: "Yillik satis", Deger: lastModalData.year_total_amount },
      { Metrik: "Yillik miktar", Deger: lastModalData.year_total_qty },
      { Metrik: "Yillik siparis", Deger: lastModalData.year_order_count },
      { Metrik: "Yillik ortalama siparis", Deger: lastModalData.year_avg_order },
      { Metrik: `${monthName} satis`, Deger: lastModalData.month_total_amount },
      { Metrik: `${monthName} miktar`, Deger: lastModalData.month_total_qty },
      { Metrik: `${monthName} siparis`, Deger: lastModalData.month_order_count },
    ]),
    "Ozet",
  );
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(lastModalData.cari_data || []), "Cariye Gore");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(lastModalData.urun_data || []), "Urune Gore");
  XLSX.writeFile(wb, `${selectedSalesman}_${monthName}_raporu.xlsx`);
});

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  loadCards();
  loadChart();
  loadFilters();
  initTable();
});