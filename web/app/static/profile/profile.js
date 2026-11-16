// Profile/onboarding UI only (no business logic): CV drag & drop on top of a hidden
// file input, and the skills search/counter. The server still validates everything.
(function () {
  const MAX_BYTES = 5 * 1024 * 1024;
  const ALLOWED = /\.(pdf|txt)$/i;

  function initCvUpload(form) {
    const input = form.querySelector("[data-cv-input]");
    const zone = form.querySelector("[data-cv-drop]");
    const title = form.querySelector("[data-cv-title]");
    const sub = form.querySelector("[data-cv-sub]");
    const error = form.querySelector("[data-cv-error]");
    const submit = form.querySelector("[data-cv-submit]");
    const idle = { title: title.textContent, sub: sub.textContent };

    function fail(message) {
      input.value = "";
      error.textContent = message;
      error.hidden = false;
      zone.classList.remove("has-file");
      submit.disabled = true;
      title.textContent = idle.title;
      sub.textContent = idle.sub;
    }

    function accept(file) {
      if (!ALLOWED.test(file.name)) return fail("Please choose a PDF or TXT file.");
      if (file.size > MAX_BYTES) return fail("That file is over 5 MB.");
      error.hidden = true;
      zone.classList.add("has-file");
      title.textContent = file.name;
      sub.textContent = (file.size / 1024 < 1024 ? Math.max(1, Math.round(file.size / 1024)) + " KB" : (file.size / 1048576).toFixed(1) + " MB") + " · tap to change";
      submit.disabled = false;
    }

    zone.addEventListener("click", () => input.click());
    zone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });
    input.addEventListener("change", () => (input.files[0] ? accept(input.files[0]) : fail("No file selected.")));

    ["dragenter", "dragover"].forEach((name) =>
      zone.addEventListener(name, (event) => {
        event.preventDefault();
        zone.classList.add("is-over");
      })
    );
    ["dragleave", "dragend", "drop"].forEach((name) =>
      zone.addEventListener(name, () => zone.classList.remove("is-over"))
    );
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      const file = event.dataTransfer.files[0];
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      accept(file);
    });

    form.addEventListener("submit", (event) => {
      if (!input.files.length) {
        event.preventDefault();
        fail("Choose a CV file first.");
      } else {
        submit.disabled = true;
        submit.textContent = "Analysing…";
      }
    });
  }

  function initSkills(box) {
    const search = box.querySelector("[data-skills-search]");
    const count = box.querySelector("[data-skills-count]");
    const empty = box.querySelector("[data-skills-empty]");
    const options = Array.from(box.querySelectorAll(".skill-option"));

    function refreshCount() {
      const selected = options.filter((option) => option.querySelector("input").checked).length;
      count.textContent = selected + " selected";
    }

    search.addEventListener("input", () => {
      const query = search.value.trim().toLowerCase();
      let shown = 0;
      options.forEach((option) => {
        const match = option.dataset.skill.includes(query);
        option.hidden = !match;
        if (match) shown += 1;
      });
      empty.hidden = shown > 0;
    });
    box.addEventListener("change", refreshCount);
    search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") event.preventDefault(); // Enter in search must not submit the form
    });
    refreshCount();
  }

  document.querySelectorAll("[data-cv-upload]").forEach(initCvUpload);
  document.querySelectorAll("[data-skills]").forEach(initSkills);
})();
