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
        const busy = form.querySelector("[data-cv-busy]");
        if (busy) busy.hidden = false;
      }
    });
  }

  function initSkills(box) {
    const search = box.querySelector("[data-skills-search]");
    const count = box.querySelector("[data-skills-count]");
    const empty = box.querySelector("[data-skills-empty]");
    const selectedBox = box.querySelector("[data-skills-selected]");
    const catalog = box.querySelector("[data-skills-catalog]");
    const toggle = box.querySelector("[data-skills-toggle]");
    const groups = Array.from(box.querySelectorAll("[data-skill-group]"));
    const options = Array.from(box.querySelectorAll(".skill-option"));

    function setExpanded(expanded) {
      catalog.classList.toggle("is-collapsed", !expanded);
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.textContent = expanded ? "Hide catalogue" : "Browse catalogue";
    }

    // Selected skills as removable chips above the catalogue.
    function renderSelected() {
      const checked = options.filter((option) => option.querySelector("input").checked);
      count.textContent = checked.length + " selected";
      selectedBox.replaceChildren();
      if (!checked.length) {
        const none = document.createElement("span");
        none.className = "skills-selected__none";
        none.textContent = "Nothing selected yet";
        selectedBox.append(none);
      }
      checked.forEach((option) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "skill-chip";
        chip.setAttribute("aria-label", "Remove " + option.dataset.skill);
        chip.append(option.dataset.skill + " ");
        const cross = document.createElement("span");
        cross.textContent = "×";
        cross.setAttribute("aria-hidden", "true");
        chip.append(cross);
        chip.addEventListener("click", () => {
          option.querySelector("input").checked = false;
          renderSelected();
        });
        selectedBox.append(chip);
      });
    }

    function filter() {
      const query = search.value.trim().toLowerCase();
      let shown = 0;
      options.forEach((option) => {
        const match = option.dataset.skill.includes(query);
        option.hidden = !match;
        if (match) shown += 1;
      });
      groups.forEach((group) => {
        const any = Array.from(group.querySelectorAll(".skill-option")).some((option) => !option.hidden);
        group.hidden = !any;
        if (query && any) group.open = true;
      });
      empty.hidden = shown > 0;
      if (query) setExpanded(true);
    }

    toggle.hidden = false;
    toggle.addEventListener("click", () => setExpanded(toggle.getAttribute("aria-expanded") !== "true"));
    setExpanded(false);
    search.addEventListener("input", filter);
    search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") event.preventDefault(); // Enter in search must not submit the form
    });
    box.addEventListener("change", renderSelected);
    renderSelected();
  }

  // "Edit skills" next to the Stack list opens the edit form and jumps to the skills picker.
  document.querySelectorAll("[data-open-edit]").forEach((link) =>
    link.addEventListener("click", (event) => {
      const fold = document.getElementById("edit-profile");
      const picker = fold && fold.querySelector("[data-skills]");
      if (!picker) return;
      event.preventDefault();
      fold.open = true;
      picker.scrollIntoView({ behavior: "smooth", block: "center" });
      picker.querySelector("[data-skills-search]").focus({ preventScroll: true });
    })
  );

  // "Clear all" saved jobs asks "Remove all N? Yes / Cancel" inline instead of a native dialog.
  document.querySelectorAll("[data-clear-form]").forEach((form) => {
    const ask = form.querySelector("[data-clear-ask]");
    const box = form.querySelector("[data-clear-confirm]");
    ask.addEventListener("click", (event) => {
      event.preventDefault();
      ask.hidden = true;
      box.hidden = false;
      box.querySelector("button[type=submit]").focus();
    });
    form.querySelector("[data-clear-cancel]").addEventListener("click", () => {
      box.hidden = true;
      ask.hidden = false;
      ask.focus();
    });
  });

  // Short splash with the mascot, once per browser tab session (skipped for reduced motion).
  const splash = document.querySelector("[data-splash]");
  let seen = true;
  try {
    seen = sessionStorage.getItem("splash-seen") === "1";
    sessionStorage.setItem("splash-seen", "1");
  } catch (error) {
    seen = true; // storage blocked: never show it
  }
  if (splash && !seen && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const hide = () => {
      splash.classList.add("is-leaving");
      setTimeout(() => (splash.hidden = true), 350);
    };
    splash.hidden = false;
    splash.addEventListener("click", hide);
    setTimeout(hide, 1100);
  }

  document.querySelectorAll("[data-cv-upload]").forEach(initCvUpload);
  document.querySelectorAll("[data-skills]").forEach(initSkills);
})();
