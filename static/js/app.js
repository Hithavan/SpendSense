// Shared helpers used across pages

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${type === "error" ? "danger" : "success"} border-0`;
  toast.setAttribute("role", "alert");
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, { delay: 3500 });
  bsToast.show();
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    // no JSON body
  }
  if (!response.ok) {
    const message = (data && data.error) || "Something went wrong. Please try again.";
    throw new Error(message);
  }
  return data;
}

function formatCurrency(amount) {
  return "₹" + Number(amount || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

// Manual expense form (present on the Add Expense page)
document.addEventListener("DOMContentLoaded", () => {
  const manualForm = document.getElementById("manualExpenseForm");
  if (manualForm) {
    manualForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(manualForm);
      const payload = Object.fromEntries(formData.entries());

      if (!payload.amount || Number(payload.amount) <= 0) {
        showToast("Please enter a valid amount.", "error");
        return;
      }

      try {
        await apiRequest("/api/expenses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showToast("Expense saved successfully.");
        manualForm.reset();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // Simple tab switching for Add Expense page
  const tabButtons = document.querySelectorAll("[data-tab]");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.add("d-none"));
      document.getElementById(btn.dataset.tab).classList.remove("d-none");
    });
  });
});
