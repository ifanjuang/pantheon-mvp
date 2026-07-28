(() => {
  "use strict";

  const toggle = document.getElementById("v2-hermes-toggle");
  const dock = document.getElementById("v2-hermes-dock");
  const close = document.getElementById("v2-hermes-close");
  if (!toggle || !dock) return;

  function setOpen(open) {
    dock.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("v2-hermes-open", open);
    if (open) {
      requestAnimationFrame(() => document.getElementById("v2-handoff-question")?.focus());
    } else {
      toggle.focus();
    }
  }

  toggle.addEventListener("click", () => setOpen(dock.hidden));
  close?.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !dock.hidden) setOpen(false);
  });
})();
