let cariTable;
let ekstreTable;
let currentClientRef;
let currentCari;

function currency(value) {
  return Number(value || 0).toLocaleString("tr-TR", { style: "currency", currency: "TRY" });
}

function updateKpis(rows) {
  let borclu = 0;
  let alacakli = 0;
  let net = 0;
  rows.forEach((row) => {
    const bakiye = Number(row.bakiye || 0);
    net += bakiye;
    if (bakiye < 0) borclu += 1;
    if (bakiye > 0) alacakli += 1;
  });
  document.querySelector("#totalCariler").textContent = rows.length;
  document.querySelector("#borcluCariler").textContent = borclu;
  document.querySelector("#alacakliCariler").textContent = alacakli;
  document.querySelector("#netBakiye").textContent = currency(net);
}

function loadEkstre() {
  if (!currentClientRef) return;
  if (ekstreTable) ekstreTable.destroy();
  const params = new URLSearchParams({
    startDate: document.querySelector("#startDate")?.value || "",
    endDate: document.querySelector("#endDate")?.value || "",
  });
  ekstreTable = $("#ekstreTable").DataTable({
    ajax: {
      url: `/api/ekstre/${currentClientRef}?${params.toString()}`,
      dataSrc: "data",
    },
    columns: [
      { data: 0, title: "Tarih" },
      { data: 1, title: "Fis no" },
      { data: 2, title: "Fis turu" },
      { data: 3, title: "Tutar", render: (v) => currency(v) },
      { data: 4, title: "Borc / Alacak" },
    ],
    order: [[0, "asc"]],
    pageLength: 50,
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
  cariTable = $("#cariTable").DataTable({
    ajax: {
      url: "/api/cariler",
      dataSrc: (payload) => {
        const rows = payload.data || [];
        updateKpis(rows);
        return rows;
      },
    },
    columns: [
      { data: "carikodu", title: "Cari kodu" },
      { data: "unvan", title: "Unvan" },
      { data: "borc", title: "Borc", render: (v) => currency(v) },
      { data: "alacak", title: "Alacak", render: (v) => currency(v) },
      { data: "bakiye", title: "Bakiye", render: (v) => currency(v) },
      { data: "durum", title: "Durum" },
    ],
    order: [[4, "desc"]],
    pageLength: 25,
    language: { 
      search: "Ara:",
      lengthMenu: "_MENU_ kayit",
      info: "_TOTAL_ kayit",
      paginate: { next: "Sonraki", previous: "Onceki" }
    }
  });

  $("#cariTable tbody").on("click", "tr", function () {
    const row = cariTable.row(this).data();
    if (!row?.clientref) return;
    currentClientRef = row.clientref;
    currentCari = row;
    const titleEl = document.querySelector("#ekstreTitle");
    if (titleEl) titleEl.textContent = `${row.carikodu} - ${row.unvan}`;
    const statusEl = document.querySelector("#mailStatus");
    if (statusEl) statusEl.textContent = "";
    const dialog = document.querySelector("#ekstreDialog");
    if (dialog) {
      dialog.showModal();
      loadEkstre();
    }
  });

  document.querySelector("#reloadEkstreBtn")?.addEventListener("click", loadEkstre);
  
  document.querySelector("#sendEkstreMailBtn")?.addEventListener("click", async () => {
    if (!currentClientRef || !currentCari) return;
    const status = document.querySelector("#mailStatus");
    const button = document.querySelector("#sendEkstreMailBtn");
    if (status) status.textContent = "Mail hazirlaniyor...";
    button.disabled = true;
    try {
      const response = await fetch(`/api/send-ekstre-mail/${currentClientRef}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          carikodu: currentCari.carikodu,
          unvan: currentCari.unvan,
          startDate: document.querySelector("#startDate")?.value || "",
          endDate: document.querySelector("#endDate")?.value || "",
        }),
      });
      const payload = await response.json();
      if (!response.ok || payload.success === false) throw new Error(payload.error || "Mail gonderilemedi.");
      if (status) status.textContent = payload.message || "Mail gonderildi.";
    } catch (error) {
      if (status) status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
  
  document.querySelector("#closeEkstreBtn")?.addEventListener("click", () => {
    const dialog = document.querySelector("#ekstreDialog");
    if (dialog) dialog.close();
  });
});