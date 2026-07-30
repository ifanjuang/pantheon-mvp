// Cockpit V3 live adapter.
//
// Bridges the live schema renderer (`v2_app_schema.js`) to the shared
// CollectionController. The renderer hands over the whole sibling collection;
// this adapter materializes one real Swiper slide per sibling and lets Swiper
// own navigation. Swiper is initialized once and reused across collections
// (`bootstrap()` + stream), never destroyed between renders.
//
// Invariant preserved for the rest of the live cockpit: exactly one interactive
// `.v2-card` exists at a time (the active slide). Neighbours are inert
// `.v2-card-preview` clones so `#v2-stage .v2-card` keeps resolving to the
// active card that the other modules target.

import { createCollectionController } from "./v3/collection/collection_controller.js";
import { streamArray } from "./v3/collection/collection_provider.js";

const stage = document.getElementById("v2-stage");

if (stage && typeof window.Swiper === "function") {
  let controller = null;
  let currentKey = null;
  let renderCard = null; // provided by the live renderer per present()
  let appOnActive = null;
  let lastActive = null;
  let cancelStream = null;

  function makePreview(node) {
    const clone = node.cloneNode(true);
    clone.classList.remove("v2-card");
    clone.classList.add("v2-card-preview");
    clone.removeAttribute("id");
    clone.removeAttribute("tabindex");
    clone.dataset.flipped = "false";
    clone.setAttribute("aria-hidden", "true");
    clone.inert = true;
    clone.querySelectorAll("[id]").forEach(item => item.removeAttribute("id"));
    clone.querySelectorAll("button,input,select,textarea,a,[tabindex]").forEach(item => {
      item.setAttribute("tabindex", "-1");
      if ("disabled" in item) item.disabled = true;
    });
    return clone;
  }

  function renderSlideContent(model, active) {
    const node = renderCard(model, { active });
    return active ? node : makePreview(node);
  }

  function renderPlaceholder() {
    const placeholder = document.createElement("div");
    placeholder.className = "v3-card-shell v3-collection-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    const dot = document.createElement("div");
    dot.className = "v3-stack-placeholder";
    placeholder.append(dot);
    return placeholder;
  }

  function writeSlide(itemIndex, active) {
    if (itemIndex < 0) return;
    const offset = controller.collection?.canCreate ? 1 : 0;
    const slide = controller.swiper.slides[itemIndex + offset];
    const model = controller.items[itemIndex];
    if (!slide || !model) return;
    slide.replaceChildren(renderSlideContent(model, active));
  }

  function handleActive(model, index, meta) {
    // Keep a single interactive card: downgrade the previous active slide first,
    // then upgrade the newly active one.
    if (lastActive != null && lastActive !== index) writeSlide(lastActive, false);
    if (index >= 0) writeSlide(index, true);
    lastActive = index;
    if (index >= 0 && appOnActive) appOnActive(model, index, meta);
  }

  function ensureController() {
    if (controller) return;
    stage.replaceChildren();
    controller = createCollectionController({
      mount: stage,
      renderItem: (model, opts) => renderSlideContent(model, Boolean(opts?.active)),
      renderNew: () => null,
      renderPlaceholder,
      onActiveChange: handleActive,
      onMoveState(moving) {
        if (moving) {
          stage.dataset.swiperMoving = "true";
          stage.dataset.swiperNavigation = "true";
        } else {
          delete stage.dataset.swiperMoving;
          delete stage.dataset.swiperNavigation;
        }
      },
    });
  }

  function present({ key, siblings = [], index = 0, motion = "", renderCard: renderer, onActiveChange }) {
    renderCard = renderer;
    appOnActive = onActiveChange;
    if (motion) stage.dataset.motion = motion;
    ensureController();

    if (key !== currentKey || !siblings.length) {
      // New collection: reuse the instance and stream the siblings in, one per
      // frame (New prepend is disabled on the live path; server-authorized
      // creation stays out of this projection).
      cancelStream?.();
      lastActive = null;
      currentKey = key;
      cancelStream = streamArray(controller, { id: key, canCreate: false, title: "" }, siblings, index);
      return;
    }
    // Same collection re-presented (e.g. project reload): reposition only.
    controller.slideToItem(index);
  }

  function slide(delta) {
    controller?.slide(delta);
  }

  window.PantheonLiveCollection = Object.freeze({ present, slide });
  window.addEventListener("pagehide", () => { cancelStream?.(); controller?.destroy(); }, { once: true });
}
