document.addEventListener("DOMContentLoaded", () => {
  const receiptForm = document.getElementById("receiptForm");
  const reviewCard = document.getElementById("reviewCard");
  const reviewForm = document.getElementById("reviewForm");
  const ocrLoading = document.getElementById("ocrLoading");
  const reviewWarning = document.getElementById("reviewWarning");

  if (!receiptForm) return;

  receiptForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(receiptForm);

    ocrLoading.classList.remove("d-none");
    reviewCard.classList.add("d-none");
    reviewWarning.classList.add("d-none");

    try {
      const response = await fetch("/api/receipts/extract", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        showToast(data.error || "Could not read this receipt.", "error");
        // Even on OCR failure, let the user fall back to manual entry for this image
        if (data.receipt_image) {
          document.getElementById("reviewReceiptImage").value = data.receipt_image;
          reviewCard.classList.remove("d-none");
        }
        return;
      }

      document.getElementById("reviewMerchant").value = data.merchant || "";
      document.getElementById("reviewAmount").value = data.amount || "";
      document.getElementById("reviewDate").value = data.date || "";
      document.getElementById("reviewCategory").value = data.category || "Other";
      document.getElementById("reviewReceiptImage").value = data.receipt_image || "";

      if (data.warning) {
        reviewWarning.textContent = data.warning;
        reviewWarning.classList.remove("d-none");
      }

      reviewCard.classList.remove("d-none");
      showToast("Receipt read. Please review before saving.");
    } catch (err) {
      showToast("We couldn't reach the server. Please try again.", "error");
    } finally {
      ocrLoading.classList.add("d-none");
    }
  });

  reviewForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(reviewForm);
    const payload = Object.fromEntries(formData.entries());

    if (!payload.amount || Number(payload.amount) <= 0) {
      showToast("Please enter a valid amount before saving.", "error");
      return;
    }

    try {
      await apiRequest("/api/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showToast("Expense saved successfully.");
      reviewForm.reset();
      reviewCard.classList.add("d-none");
      receiptForm.reset();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
});
