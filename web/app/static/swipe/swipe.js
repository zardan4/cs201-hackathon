// Swipe tab UI only (no business logic): gestures and card animation.
// Swipes go to POST /api/swipe. When the stack is empty the page reloads and
// the server renders the next cards.
(function () {
  const stack = document.getElementById("swipe-stack");
  const THRESHOLD = 100; // px of horizontal drag that counts as a swipe

  // Confetti on a like (canvas-confetti, vendored in static/vendor, ISC license).
  // The canvas lives inside the app frame so the confetti never spills outside it.
  const confettiCanvas = document.getElementById("confetti-canvas");
  const fireConfetti = window.confetti && confettiCanvas
    ? window.confetti.create(confettiCanvas, { resize: true, useWorker: false })
    : null;

  // Confetti rises from the bottom edge across the whole screen (three staggered volleys).
  const CONFETTI_COLORS = ["#ff3d81", "#ff8a3d", "#ffffff", "#ffd166", "#7b5cff"];

  function celebrate() {
    if (!fireConfetti) return;
    const volley = (x, angle, delay) =>
      setTimeout(() => {
        fireConfetti({
          particleCount: 55,
          angle,
          spread: 75,
          startVelocity: 58,
          decay: 0.92,
          gravity: 0.95,
          ticks: 230,
          scalar: 1,
          origin: { x, y: 1.02 },
          colors: CONFETTI_COLORS,
          disableForReducedMotion: true,
        });
      }, delay);
    const pop = document.querySelector(".like-mascot");
    if (pop) {
      pop.classList.remove("is-popping");
      void pop.offsetWidth; // restart the animation
      pop.classList.add("is-popping");
    }
    volley(0.5, 90, 0);
    volley(0.12, 65, 120);
    volley(0.88, 115, 120);
  }

  const topCard = () => stack.querySelector(".job-card:not(.is-gone)");

  function reloadIfEmpty() {
    if (!topCard()) window.location.reload();
  }

  function sendSwipe(card, action) {
    card.classList.add("is-gone", action === "like" ? "is-liked" : "is-skipped");
    card.style.transform = "";
    if (action === "like") celebrate();
    fetch("/api/swipe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: card.dataset.jobId, action: action }),
    })
      .catch(() => {})
      .finally(reloadIfEmpty);
  }

  document.querySelectorAll(".swipe-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const card = topCard();
      if (card) sendSwipe(card, button.dataset.action);
    });
  });

  // "Full description" bottom sheet: content is rendered by the server in a <template> per card.
  const sheet = document.getElementById("job-sheet");
  const sheetContent = document.getElementById("job-sheet-content");
  let sheetOpener = null;

  function openSheet(card, opener) {
    const template = card.querySelector(".job-card__detail");
    if (!template) return;
    sheetContent.replaceChildren(template.content.cloneNode(true));
    sheet.hidden = false;
    sheet.querySelector(".job-sheet__scroll").scrollTop = 0;
    sheetOpener = opener;
    sheet.querySelector(".job-sheet__close").focus();
  }

  function closeSheet() {
    if (sheet.hidden) return;
    sheet.hidden = true;
    if (sheetOpener) sheetOpener.focus();
  }

  stack.querySelectorAll("[data-details]").forEach((button) =>
    button.addEventListener("click", () => openSheet(button.closest(".job-card"), button))
  );
  sheet.querySelectorAll("[data-sheet-close]").forEach((element) => element.addEventListener("click", closeSheet));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSheet();
  });

  let startX = 0, deltaX = 0, dragging = null;

  stack.addEventListener("pointerdown", (event) => {
    const card = topCard();
    if (!card || !card.contains(event.target) || event.target.closest("a, button")) return;
    dragging = card;
    startX = event.clientX;
    deltaX = 0;
    card.setPointerCapture(event.pointerId);
    card.classList.add("is-dragging");
  });

  stack.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    deltaX = event.clientX - startX;
    dragging.style.transform = `translateX(${deltaX}px) rotate(${deltaX / 15}deg)`;
    dragging.classList.toggle("show-like", deltaX > THRESHOLD / 2);
    dragging.classList.toggle("show-skip", deltaX < -THRESHOLD / 2);
  });

  function endDrag() {
    if (!dragging) return;
    const card = dragging;
    dragging = null;
    card.classList.remove("is-dragging", "show-like", "show-skip");
    if (Math.abs(deltaX) > THRESHOLD) {
      sendSwipe(card, deltaX > 0 ? "like" : "skip");
    } else {
      card.style.transform = "";
    }
  }

  stack.addEventListener("pointerup", endDrag);
  stack.addEventListener("pointercancel", endDrag);
})();
