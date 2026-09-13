let editModal;

async function loadExpenses() {
  const tbody = document.getElementById("expenseTableBody");
  tbody.innerHTML = `<tr><td colspan="5" class="empty-state"><span class="spinner-border spinner-border-sm text-primary me-2"></span>Loading expenses...</td></tr>`;

  const params = new URLSearchParams();
  const category = document.getElementById("filterCategory").value;
  const month = document.getElementById("filterMonth").value;
  const search = document.getElementById("filterSearch").value;
  const sort = document.getElementById("filterSort").value;

  if (category) params.set("category", category);
  if (month) params.set("month", month);
  if (search) params.set("search", search);
  if (sort) params.set("sort", sort);

  try {
    const expenses = await apiRequest(`/api/expenses?${params.toString()}`);

    if (!expenses.length) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><i class="bi bi-inbox"></i>No expenses found.</div></td></tr>`;
      return;
    }

    tbody.innerHTML = expenses.map((exp) => `
      <tr>
        <td>${exp.date || "—"}</td>
        <td>${exp.merchant || "—"}</td>
        <td><span class="badge text-bg-light border">${exp.category}</span></td>
        <td class="text-end">${formatCurrency(exp.amount)}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-primary action-btn" onclick="openEdit(${exp.id})"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-sm btn-outline-danger action-btn" onclick="deleteExpense(${exp.id})"><i class="bi bi-trash"></i></button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state text-danger"><i class="bi bi-exclamation-triangle"></i>${err.message}</div></td></tr>`;
  }
}

async function openEdit(id) {
  try {
    const exp = await apiRequest(`/api/expenses/${id}`);
    document.getElementById("editId").value = exp.id;
    document.getElementById("editMerchant").value = exp.merchant || "";
    document.getElementById("editAmount").value = exp.amount;
    document.getElementById("editDate").value = exp.date;
    document.getElementById("editCategory").value = exp.category;
    document.getElementById("editDescription").value = exp.description || "";
    editModal.show();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteExpense(id) {
  if (!confirm("Delete this expense? This cannot be undone.")) return;
  try {
    await apiRequest(`/api/expenses/${id}`, { method: "DELETE" });
    showToast("Expense deleted.");
    loadExpenses();
  } catch (err) {
    showToast(err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  editModal = new bootstrap.Modal(document.getElementById("editModal"));

  loadExpenses();
  document.getElementById("applyFilters").addEventListener("click", loadExpenses);

  document.getElementById("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    const id = payload.id;
    delete payload.id;

    try {
      await apiRequest(`/api/expenses/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showToast("Expense updated.");
      editModal.hide();
      loadExpenses();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
});
