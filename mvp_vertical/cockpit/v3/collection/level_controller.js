// Cockpit V3 — LevelController (demo two-axis navigation).
//
// Owns two Swiper instances, each initialized once and never destroyed:
//   - a vertical Swiper with three stable slides (parent · current · child);
//   - one horizontal CollectionController hosted inside the current slide.
//
// Level changes recycle the three vertical slots in place (parent/child are
// cheap static previews) and re-`load()` the single horizontal controller onto
// the new collection. There is no `destroy()`, no wrapper recreation and no
// nested Swiper churn.

import { createCollectionController } from "./collection_controller.js";
import { renderPreview } from "./card_renderer.js";
import { streamArray } from "./collection_provider.js";

export function createLevelController({
  stage,
  renderItem,
  renderNew,
  renderPlaceholder,
  onActiveChange = () => {},
  onCommit = () => {},
  onMoveState = () => {},
}) {
  const shell = document.createElement("div");
  shell.className = "swiper v3-level-swiper";
  const wrapper = document.createElement("div");
  wrapper.className = "swiper-wrapper v3-level-wrapper";

  const slides = {
    parent: levelSlide("parent"),
    current: levelSlide("current"),
    child: levelSlide("child"),
  };
  wrapper.append(slides.parent, slides.current, slides.child);
  shell.append(wrapper);
  stage.replaceChildren(shell);

  // The single horizontal controller lives in the current level slide.
  const collectionHost = document.createElement("div");
  collectionHost.className = "v3-collection-host";
  slides.current.append(collectionHost);

  const horizontal = createCollectionController({
    mount: collectionHost,
    renderItem,
    renderNew,
    renderPlaceholder,
    onActiveChange,
    onMoveState,
  });

  let cancelStream = null;
  let allowPrev = false;
  let allowNext = false;
  let transitionLocked = false;

  const vertical = new window.Swiper(shell, {
    direction: "vertical",
    nested: true,
    initialSlide: 1,
    slidesPerView: 1,
    threshold: 12,
    touchAngle: 35,
    resistanceRatio: 0.62,
    observer: false,
    observeParents: false,
    observeSlideChildren: false,
    resizeObserver: true,
    roundLengths: true,
    touchReleaseOnEdges: true,
    noSwiping: true,
    noSwipingSelector: "button,input,select,textarea,a,[contenteditable='true']",
    a11y: { enabled: true, containerMessage: "Navigation verticale entre les niveaux", slideLabelMessage: "Niveau {{index}} sur {{slidesLength}}" },
    on: {
      touchStart() { onMoveState(true); },
      sliderMove() { onMoveState(true); },
      touchEnd(instance) { if (!instance.animating) onMoveState(false); },
      slideChangeTransitionEnd(instance) {
        onMoveState(false);
        commit(instance);
      },
    },
  });

  function commit(instance) {
    if (transitionLocked || instance.activeIndex === 1) return;
    transitionLocked = true;
    if (instance.activeIndex === 2 && allowNext) {
      onCommit(1);
      return;
    }
    if (instance.activeIndex === 0 && allowPrev) {
      onCommit(-1);
      return;
    }
    // No valid target: snap back to the current level.
    instance.slideTo(1, 160, false);
    transitionLocked = false;
  }

  // Render (or re-render) the deck for the current stack position. Reuses both
  // Swiper instances; only slot contents change.
  function render({ collection, items, index = 0, parentItem = null, childItem = null, canAscend = false, canDescend = false }) {
    transitionLocked = false;
    allowPrev = Boolean(canAscend);
    allowNext = Boolean(canDescend);

    slides.parent.replaceChildren(renderPreview(parentItem));
    slides.child.replaceChildren(renderPreview(childItem));

    cancelStream?.();
    cancelStream = streamArray(horizontal, collection, items, index);

    vertical.allowSlidePrev = allowPrev;
    vertical.allowSlideNext = allowNext;
    vertical.slideTo(1, 0, false);
    vertical.update();
  }

  function updateDescendability(canDescend) {
    allowNext = Boolean(canDescend);
    vertical.allowSlideNext = allowNext;
  }

  return Object.freeze({
    render,
    updateDescendability,
    horizontal,
    descend() { vertical.slideNext(); },
    ascend() { vertical.slidePrev(); },
    slidePrevCard() { horizontal.slide(-1); },
    slideNextCard() { horizontal.slide(1); },
    destroy() {
      cancelStream?.();
      horizontal.destroy();
      vertical.destroy(true, true);
    },
  });
}

function levelSlide(role) {
  const slide = document.createElement("div");
  slide.className = `swiper-slide v3-level-slide v3-level-slide--${role}`;
  slide.dataset.levelRole = role;
  return slide;
}
