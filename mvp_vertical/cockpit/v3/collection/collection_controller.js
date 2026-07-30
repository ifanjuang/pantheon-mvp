// Cockpit V3 — CollectionController.
//
// Owns exactly one horizontal Swiper for the lifetime of a stage. Swiper is
// initialized once and is never destroyed between collections; it is only a
// navigation engine. Business logic lives outside (CollectionProvider) and the
// DOM is produced outside (Renderer). This is the "Swiper lifecycle" contract of
// issue #108:
//
//   - init once, with exactly two slides: `New` + `Placeholder`;
//   - the first arriving item replaces the placeholder content;
//   - every following item is added with `appendSlide()` only;
//   - switching collection reuses the same instance (`removeAllSlides()` +
//     re-bootstrap), never `destroy()` and never a wrapper rebuild.
//
// The controller is transport-agnostic: a provider pushes items in through
// `bootstrap()` / `push()` / `settle()`.

const DEFAULT_SWIPER_OPTIONS = Object.freeze({
  slidesPerView: 1,
  threshold: 8,
  touchAngle: 35,
  resistanceRatio: 0.62,
  // Pantheon owns every DOM mutation explicitly, so the observers stay off.
  observer: false,
  observeParents: false,
  observeSlideChildren: false,
  resizeObserver: true,
  roundLengths: true,
  // Let Swiper own the first swipe / edge release on iOS.
  touchReleaseOnEdges: true,
  preventClicks: true,
  preventClicksPropagation: true,
  noSwiping: true,
  noSwipingSelector: "button,input,select,textarea,a,[contenteditable='true']",
});

export function createCollectionController({
  mount,
  renderItem,
  renderNew = () => null,
  renderPlaceholder,
  onActiveChange = () => {},
  onMoveState = () => {},
  swiperOptions = {},
  a11y = {},
}) {
  if (typeof window.Swiper !== "function") throw new Error("Swiper runtime unavailable");
  if (!mount) throw new Error("CollectionController requires a mount element");
  if (typeof renderItem !== "function") throw new Error("CollectionController requires renderItem");
  if (typeof renderPlaceholder !== "function") throw new Error("CollectionController requires renderPlaceholder");

  const shell = document.createElement("div");
  shell.className = "swiper v3-swiper v3-collection-swiper";
  shell.setAttribute("role", "region");
  shell.setAttribute("aria-roledescription", "carrousel");
  const wrapper = document.createElement("div");
  wrapper.className = "swiper-wrapper v2-swiper-wrapper";
  shell.append(wrapper);
  mount.append(shell);

  let collection = null;
  let items = [];
  let hasReal = false; // first real item has replaced the placeholder
  let activeIndex = 0; // index within `items`
  let settleTarget = null; // desired item index once loading is done
  let placeholderSlide = null;

  function slideElement(role) {
    const slide = document.createElement("div");
    slide.className = "swiper-slide v2-swiper-slide v3-swiper-slide";
    if (role) slide.dataset.swiperRole = role;
    return slide;
  }

  function createOffset() {
    // Number of leading synthetic slides (the `New` slide) before real items.
    return collection?.canCreate ? 1 : 0;
  }

  const swiper = new window.Swiper(shell, {
    ...DEFAULT_SWIPER_OPTIONS,
    ...swiperOptions,
    init: false,
    initialSlide: 0,
    runCallbacksOnInit: false,
    a11y: { enabled: true, ...a11y },
    on: {
      touchStart() { onMoveState(true); },
      sliderMove() { onMoveState(true); },
      touchEnd(instance) { if (!instance.animating) onMoveState(false); },
      slideChange(instance) { handleSlideChange(instance); },
      slideChangeTransitionEnd() { onMoveState(false); },
    },
  });
  swiper.init();

  function handleSlideChange(instance) {
    const offset = createOffset();
    const raw = instance.activeIndex;
    if (offset && raw < offset) {
      // `New` slide is active — no real item selected.
      activeIndex = -1;
      onActiveChange(null, -1, { synthetic: "create", collection });
      return;
    }
    activeIndex = raw - offset;
    onActiveChange(items[activeIndex] || null, activeIndex, { synthetic: null, collection });
  }

  // Reset to the two-slide bootstrap (`New` + `Placeholder`) reusing the
  // instance. No destroy, no wrapper recreation.
  function bootstrap(nextCollection) {
    collection = nextCollection || { id: "collection", canCreate: false, title: "" };
    items = [];
    hasReal = false;
    activeIndex = 0;
    settleTarget = null;

    swiper.removeAllSlides();

    if (collection.canCreate) {
      const created = renderNew(collection);
      if (created) {
        const newSlide = slideElement("create");
        newSlide.dataset.synthetic = "create";
        newSlide.append(created);
        swiper.appendSlide(newSlide);
      }
    }

    placeholderSlide = slideElement("placeholder");
    placeholderSlide.dataset.placeholder = "true";
    placeholderSlide.append(renderPlaceholder());
    swiper.appendSlide(placeholderSlide);

    // Open on the placeholder (the `New` slide sits prepended to its left), so
    // the first card the user sees is the one whose content the first item will
    // replace in place.
    swiper.slideTo(createOffset(), 0, false);
  }

  // Add one item. The first real item hydrates the placeholder in place; the
  // rest are appended.
  function push(item) {
    items.push(item);
    if (!hasReal) {
      hasReal = true;
      placeholderSlide.dataset.placeholder = "false";
      placeholderSlide.dataset.entityId = item.id ?? "";
      placeholderSlide.replaceChildren(renderItem(item, { active: false, index: 0 }));
      swiper.update();
      return;
    }
    const slide = slideElement();
    slide.dataset.entityId = item.id ?? "";
    slide.append(renderItem(item, { active: false, index: items.length - 1 }));
    swiper.appendSlide(slide);
  }

  // Called once the provider has emitted every item. Positions on the desired
  // index (or the first real item) and reports the active item once.
  function settle(index = null) {
    settleTarget = index;
    swiper.update();
    const offset = createOffset();
    if (!items.length) {
      swiper.slideTo(0, 0, false);
      onActiveChange(null, -1, { synthetic: offset ? "create" : "empty", collection });
      return;
    }
    const target = clamp(index == null ? 0 : index, 0, items.length - 1);
    activeIndex = target;
    swiper.slideTo(target + offset, 0, false);
    onActiveChange(items[target], target, { synthetic: null, collection });
  }

  function slide(delta) {
    if (delta < 0) swiper.slidePrev();
    else swiper.slideNext();
  }

  function slideToItem(index) {
    const offset = createOffset();
    swiper.slideTo(clamp(index, 0, Math.max(0, items.length - 1)) + offset, 0, false);
  }

  function destroy() {
    swiper.destroy(true, true);
    shell.remove();
  }

  return Object.freeze({
    swiper,
    bootstrap,
    push,
    settle,
    slide,
    slideToItem,
    refreshActive,
    destroy,
    get activeIndex() { return activeIndex; },
    get items() { return items.slice(); },
    get collection() { return collection; },
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number.isFinite(value) ? value : min));
}
