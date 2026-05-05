let ordersTable;
let linesTable;

function currency(value) {
  return Number(value || 0).toLocaleString("tr-TR", { style: "currency", currency: "TRY" });
}

function updateKpis(rows) {
  let pending = 0;
  let partial = 0;
  let completed = 0;
  rows.forEach((row) => {
    const amount = Number(row.siparis_miktar || 0);
    const shipped = Number(row.sevk_edilen || 0);
    if (amount > 0 && shipped >= amount) completed += 1;
    else if (shipped > 0) partial += 1;
    else pending += 1;
  });
  document.querySelector("#totalOrders").textContent = rows.length;
  document.querySelector("#pendingOrders").textContent = pending;
  document.querySelector("#partialOrders").textContent = partial;
  document.querySelector("#completedOrders").textContent = completed;
}

function openLines(fisNo) {
  const dialog = document.querySelector("#linesDialog");
  const titleEl = document.querySelector("#linesTitle");
  if (titleEl) titleEl.textContent = `Siparis detayi: ${fisNo}`;
  if (dialog) dialog.showModal();

  if (linesTable) linesTable.destroy();
  linesTable = $("#linesTable").DataTable({
    ajax: {
      url: `/api/order-lines/${encodeURIComponent(fisNo)}`,
      dataSrc: "data",
    },
    columns: [
      { data: 2, title: "Tarih" },
      { data: 4, title: "Kod" },
      { data: 5, title: "Urun" },
      { data: 6, title: "Miktar" },
      { data: 7, title: "Sevk" },
      { data: 9, title: "Birim", render: (v) => currency(v) },
      { data: 13, title: "Net", render: (v) => currency(v) },
      { data: 14, title: "Satis elemani" },
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

document.addEventListener("DOMContentLoaded", () => {
  ordersTable = $("#ordersTable").DataTable({
    ajax: {
      url: "/api/orders",
      dataSrc: (payload) => {
        const rows = payload.data || [];
        updateKpis(rows);
        return rows;
      },
    },
    columns: [
      { data: "tarih", title: "Tarih" },
      { data: "fis_no", title: "Fis no" },
      { data: "cari_unvan", title: "Cari" },
      { data: "net_tutar", title: "Net tutar", render: (v) => currency(v) },
      { data: "siparis_miktar", title: "Siparis" },
      { data: "sevk_edilen", title: "Sevk" },
      { data: "bekleyen", title: "Bekleyen" },
      { data: "satis_eleman", title: "Satis elemani" },
      { data: "siparis_durumu", title: "Durum" },
    ],
    order: [[0, "desc"]],
    pageLength: 25,
    language: { 
      search: "Ara:",
      lengthMenu: "_MENU_ kayit",
      info: "_TOTAL_ kayit",
      paginate: { next: "Sonraki", previous: "Onceki" }
    }
  });

  $("#ordersTable tbody").on("click", "tr", function () {
    const row = ordersTable.row(this).data();
    if (row?.fis_no) openLines(row.fis_no);
  });

  document.querySelector("#closeLinesBtn")?.addEventListener("click", () => {
    const dialog = document.querySelector("#linesDialog");
    if (dialog) dialog.close();
  });
});