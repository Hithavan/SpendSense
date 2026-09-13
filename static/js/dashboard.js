async function loadDashboard() {
  try {
    const summary = await apiRequest("/api/dashboard/summary");
    document.getElementById("statTotal").textContent = formatCurrency(summary.total_expenses);
    document.getElementById("statMonth").textContent = formatCurrency(summary.this_month);
    document.getElementById("statCategory").textContent = summary.highest_category || "—";
    document.getElementById("statCount").textContent = summary.number_of_expenses;

    const categoryLabels = Object.keys(summary.category_totals);
    const categoryValues = Object.values(summary.category_totals);

    new Chart(document.getElementById("categoryChart"), {
      type: "pie",
      data: {
        labels: categoryLabels.length ? categoryLabels : ["No data"],
        datasets: [{
          data: categoryValues.length ? categoryValues : [1],
          backgroundColor: ["#4361ee", "#4cc9f0", "#f72585", "#ffb703", "#06d6a0", "#7209b7", "#fb8500", "#8d99ae"],
        }],
      },
      options: { responsive: true },
    });
  } catch (err) {
    showToast(err.message, "error");
  }

  try {
    const monthly = await apiRequest("/api/dashboard/monthly");
    new Chart(document.getElementById("monthlyChart"), {
      type: "bar",
      data: {
        labels: monthly.labels.length ? monthly.labels : ["No data"],
        datasets: [{
          label: "Spending",
          data: monthly.values.length ? monthly.values : [0],
          backgroundColor: "#4361ee",
        }],
      },
      options: { responsive: true, scales: { y: { beginAtZero: true } } },
    });
  } catch (err) {
    showToast(err.message, "error");
  }

  try {
    const recent = await apiRequest("/api/dashboard/recent?limit=6");
    const list = document.getElementById("recentList");
    if (!recent.length) {
      list.innerHTML = `<li class="list-group-item"><div class="empty-state py-2"><i class="bi bi-inbox"></i>No expenses yet.</div></li>`;
      return;
    }
    list.innerHTML = recent.map((exp) => `
      <li class="list-group-item d-flex justify-content-between align-items-center">
        <span>${exp.date || "—"} — ${exp.merchant || "Unknown"} <span class="badge text-bg-light border">${exp.category}</span></span>
        <strong>${formatCurrency(exp.amount)}</strong>
      </li>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
