/* ===================================================
   CropGuard AI — Frontend JavaScript
   =================================================== */

(function () {
  "use strict";

  // ─── Drag & Drop Upload ─────────────────────────
  const dropZone   = document.getElementById("dropZone");
  const fileInput  = document.getElementById("imageInput");
  const preview    = document.getElementById("imagePreview");
  const dropContent= document.getElementById("dropContent");
  const dropIcon   = document.getElementById("dropIcon");
  const fileInfo   = document.getElementById("fileInfo");
  const fileName   = document.getElementById("fileName");
  const clearBtn   = document.getElementById("clearBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const uploadForm = document.getElementById("uploadForm");
  const btnText    = analyzeBtn ? analyzeBtn.querySelector(".btn-text") : null;
  const btnLoader  = analyzeBtn ? analyzeBtn.querySelector(".btn-loader") : null;

  if (!dropZone) return; // Not on index page

  // Click anywhere on drop zone opens file picker
  dropZone.addEventListener("click", (e) => {
    if (e.target !== fileInput) fileInput.click();
  });

  // Drag events
  ["dragenter", "dragover"].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => { e.preventDefault(); dropZone.classList.remove("drag-over"); })
  );
  dropZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  function handleFile(file) {
    const allowed = ["image/png", "image/jpeg", "image/webp", "image/bmp"];
    if (!allowed.includes(file.type)) {
      showToast("Please upload a PNG, JPG, JPEG, or WEBP image.", "error");
      return;
    }
    if (file.size > 16 * 1024 * 1024) {
      showToast("File size must be under 16 MB.", "error");
      return;
    }

    // Preview
    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.classList.remove("hidden");
      dropContent.classList.add("hidden");
      dropIcon.classList.add("hidden");
    };
    reader.readAsDataURL(file);

    // Update UI
    fileName.textContent = file.name;
    fileInfo.classList.remove("hidden");
    analyzeBtn.disabled = false;

    // Sync file input if dropped
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
  }

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      fileInput.value = "";
      preview.src = "";
      preview.classList.add("hidden");
      dropContent.classList.remove("hidden");
      dropIcon.classList.remove("hidden");
      fileInfo.classList.add("hidden");
      analyzeBtn.disabled = true;
    });
  }

  // Submit: show loading state
  if (uploadForm) {
    uploadForm.addEventListener("submit", () => {
      if (!fileInput.files[0]) return;
      analyzeBtn.disabled = true;
      if (btnText) btnText.classList.add("hidden");
      if (btnLoader) btnLoader.classList.remove("hidden");
    });
  }

  // ─── Particle Background ────────────────────────
  const particleContainer = document.getElementById("particles");
  if (particleContainer) {
    const EMOJIS = ["🌿", "🍃", "🌱", "🍀", "🌾"];
    for (let i = 0; i < 18; i++) {
      const p = document.createElement("span");
      p.textContent = EMOJIS[Math.floor(Math.random() * EMOJIS.length)];
      const size = 14 + Math.random() * 20;
      Object.assign(p.style, {
        position:   "absolute",
        left:       Math.random() * 100 + "%",
        top:        Math.random() * 100 + "%",
        fontSize:   size + "px",
        opacity:    0.06 + Math.random() * 0.1,
        animation:  `float ${6 + Math.random() * 8}s ease-in-out infinite alternate`,
        animationDelay: Math.random() * 6 + "s",
        userSelect: "none",
        pointerEvents: "none",
      });
      particleContainer.appendChild(p);
    }

    // Inject float keyframe if missing
    if (!document.getElementById("floatKf")) {
      const style = document.createElement("style");
      style.id = "floatKf";
      style.textContent = "@keyframes float { 0%{transform:translateY(0) rotate(0deg)} 100%{transform:translateY(-30px) rotate(15deg)} }";
      document.head.appendChild(style);
    }
  }

  // ─── Simple Toast Notification ──────────────────
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `flash flash-${type}`;
    toast.style.cssText = "position:fixed;bottom:1.5rem;right:1.5rem;z-index:999;animation:slideIn .3s ease;max-width:360px;";
    toast.innerHTML = `<span>${type === "error" ? "⚠️" : "✅"} ${message}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // ─── Fade-in Cards on Result Page ───────────────
  document.querySelectorAll(".card, .advisory-section, .feature-card").forEach((el, i) => {
    el.style.opacity = "0";
    el.style.transform = "translateY(20px)";
    el.style.transition = "opacity 0.4s ease, transform 0.4s ease";
    setTimeout(() => {
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    }, 100 + i * 80);
  });

})();
