(() => {
  "use strict";

  if (typeof window.Swiper !== "function") return;
  const stage = document.getElementById("v2-stage");
  if (!stage) return;

  const mobileMedia = window.matchMedia("(max-width: 620px)");
  const nativeReplaceChildren = stage.replaceChildren.bind(stage);
  const nativeAppend = stage.append.bind(stage);
  const nativeAppendChild = stage.appendChild.bind(stage);
  const nativeAddEventListener = stage.addEventListener.bind(stage);

  let shell = null;
  let wrapper = null;
  let swiper = null;
  let latestNodes = [];
  let rendererClearedStage = false;
  let navigationLocked = false;
  let userGestureActive = false;

  stage.addEventListener = function boundedStageListener(type, listener, options) {
    if (mobileMedia.matches && (type === "pointerdown" || type === "pointerup")) return undefined;
    return nativeAddEventListener(type, listener, options);
  };

  function inertPreview(node) {
    const clone = node.cloneNode(true);
    clone.removeAttribute?.("id");
    clone.querySelectorAll?.("[id]").forEach(item => item.removeAttribute("id"));
    clone.querySelectorAll?.("button,input,select,textarea,a,[tabindex]").forEach(item => {
      item.setAttribute("tabindex", "-1");
      if ("disabled" in item) item.disabled = true;
    });
    return clone;
  }

  function createSlide(role) {
    const slide = document.createElement("div");
    slide.className = `swiper-slide v2-swiper-slide v3-swiper-slide v3-swiper-slide--${role}`;
    slide.dataset.swiperRole = role;
    if (role !== "current") {
      slide.setAttribute("aria-hidden", "true");
      slide.inert = true;
    }
    return slide;
  }

  function createActionCard() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "v2-swiper-create-card";
    button.setAttribute("aria-label", "Ajouter un nouvel élément");
    button.innerHTML = '<span class="v2-swiper-create-mark">+</span><span class="v2-swiper-create-copy"><strong>Nouvel élément</strong><small>Créer dans la collection courante</small></span>';
    button.addEventListener("click", () => {
      if (window.PantheonInformationCreate?.open) {
        try {
          window.PantheonInformationCreate.open();
          return;
        } catch (error) {
          window.alert(error.message || String(error));
          return;
        }
      }
      stage.dispatchEvent(new CustomEvent("pantheon:create-requested", { bubbles: true }));
    });
    return button;
  }

  function ensureShell() {
    if (shell && shell.isConnected) return;
    shell = document.createElement("div");
    shell.className = "swiper v2-swiper v3-swiper";
    shell.setAttribute("aria-roledescription", "carrousel");

    wrapper = document.createElement("div");
    wrapper.className = "swiper-wrapper v2-swiper-wrapper";
    wrapper.append(createSlide("previous"), createSlide("current"), createSlide("next"));
    shell.append(wrapper);
    nativeReplaceChildren(shell);

    swiper = new window.Swiper(shell, {
      initialSlide: 1,
      speed: 300,
      threshold: 12,
      resistanceRatio: 0.72,
      grabCursor: true,
      watchOverflow: false,
      allowTouchMove: true,
      preventInteractionOnTransition: true,
      keyboard: { enabled: false },
      a11y: {
        enabled: true,
        containerMessage: "Navigation horizontale entre les cartes sœurs",
        slideLabelMessage: "Carte {{index}} sur {{slidesLength}}",
      },
      on: {
        init(instance) {
          instance.slideTo(1, 0, false);
        },
        touchStart() {
          if (!navigationLocked) userGestureActive = true;
        },
        touchEnd(instance) {
          if (instance.activeIndex === 1 && !instance.animating) userGestureActive = false;
        },
        transitionEnd(instance) {
          moveFromSwiper(instance);
        },
      },
    });
  }

  function resetToCurrent(speed = 0) {
    if (swiper && swiper.activeIndex !== 1) swiper.slideTo(1, speed, false);
  }

  function unlockNavigation() {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      navigationLocked = false;
      delete stage.dataset.swiperNavigation;
      resetToCurrent(0);
    }));
  }

  function moveFromSwiper(instance) {
    if (!userGestureActive || navigationLocked || instance.activeIndex === 1) return;
    userGestureActive = false;

    const active = instance.slides[instance.activeIndex];
    if (active?.dataset?.swiperAction === "create") {
      resetToCurrent(180);
      return;
    }

    const button = document.getElementById(instance.activeIndex < 1 ? "v2-previous" : "v2-next");
    navigationLocked = true;
    stage.dataset.swiperNavigation = "true";
    if (button && !button.disabled) button.click();
    else resetToCurrent(180);
    unlockNavigation();
  }

  function replaceSlideContent(slide, node) {
    slide.replaceChildren();
    if (node) slide.append(node);
  }

  function updateMobile(node) {
    ensureShell();
    const previous = wrapper.querySelector('[data-swiper-role="previous"]');
    const current = wrapper.querySelector('[data-swiper-role="current"]');
    const next = wrapper.querySelector('[data-swiper-role="next"]');
    const previousButton = document.getElementById("v2-previous");

    previous.dataset.swiperAction = previousButton && previousButton.disabled ? "create" : "";
    replaceSlideContent(previous, previousButton && previousButton.disabled ? createActionCard() : inertPreview(node));
    replaceSlideContent(current, node);
    replaceSlideContent(next, inertPreview(node));

    swiper.update();
    resetToCurrent(0);
  }

  function mount(nodes) {
    latestNodes = nodes;
    const node = nodes.find(item => item instanceof Node) || null;
    if (!node || node.classList?.contains("v2-empty")) {
      swiper?.destroy(true, true);
      swiper = null;
      shell = null;
      wrapper = null;
      nativeReplaceChildren(...nodes);
      return;
    }

    if (mobileMedia.matches) {
      updateMobile(node);
      return;
    }

    swiper?.destroy(true, true);
    swiper = null;
    shell = null;
    wrapper = null;
    const grid = document.createElement("div");
    grid.className = "v2-card-grid";
    const gridWrapper = document.createElement("div");
    gridWrapper.className = "v2-card-grid-wrapper";
    gridWrapper.append(node);
    grid.append(gridWrapper);
    nativeReplaceChildren(grid);
  }

  stage.replaceChildren = (...nodes) => {
    rendererClearedStage = nodes.length === 0;
    if (rendererClearedStage) return;
    mount(nodes);
  };

  stage.append = (...nodes) => {
    if (rendererClearedStage) {
      rendererClearedStage = false;
      mount(nodes);
      return;
    }
    nativeAppend(...nodes);
  };

  stage.appendChild = node => {
    if (rendererClearedStage) {
      rendererClearedStage = false;
      mount([node]);
      return node;
    }
    return nativeAppendChild(node);
  };

  mobileMedia.addEventListener?.("change", () => {
    if (latestNodes.length) mount(latestNodes);
  });

  window.addEventListener("pagehide", () => swiper?.destroy(true, true), { once: true });
})();
