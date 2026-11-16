// Swipe tab UI only (no business logic): gestures, card animation and the
// match overlay (shown when the server flagged the card as a strong match).
// Swipes go to POST /api/swipe. When the stack is empty the page reloads and
// the server renders the next cards.
(function () {
  const stack = document.getElementById("swipe-stack");
  const overlay = document.getElementById("match-overlay");
  const THRESHOLD = 100; // px of horizontal drag that counts as a swipe

  const topCard = () => stack.querySelector(".job-card:not(.is-gone)");

  function showMatch(card) {
    const copy = (name, selector) => {
      overlay.querySelector(`[data-match="${name}"]`).textContent =
        card.querySelector(selector).textContent;
    };
    copy("title", ".job-card__title");
    copy("salary", ".job-card__salary");
    copy("percent", ".job-card__percent");
    copy("logo", ".job-card__logo");
    overlay.hidden = false;
    document.getElementById("match-close").focus();
  }

  function reloadIfEmpty() {
    if (!topCard() && overlay.hidden) window.location.reload();
  }

  function sendSwipe(card, action) {
    card.classList.add("is-gone", action === "like" ? "is-liked" : "is-skipped");
    card.style.transform = "";
    if (action === "like" && card.dataset.strongMatch === "true") showMatch(card);
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

  document.getElementById("match-close").addEventListener("click", () => {
    overlay.hidden = true;
    reloadIfEmpty();
  });

  let startX = 0, deltaX = 0, dragging = null;

  stack.addEventListener("pointerdown", (event) => {
    const card = topCard();
    if (!card || !card.contains(event.target) || event.target.closest("a")) return;
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
