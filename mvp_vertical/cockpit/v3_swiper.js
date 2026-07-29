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
  let currentNode = null;
  let previousProjection = null;
  let nextProjection = null;
  let rendererClearedStage = false;
  let pendingClearToken = 0;
  let navigationLocked = false;
  let userGestureActive = false;
  let pendingDirection = 0;
  let navigationTimeout = 0;

  stage.addEventListener = function boundedStageListener(type, listener, options) {
    if (mobileMedia.matches && (type === "pointerdown" || type === "pointerup")) return undefined;
    return nativeAddEventListener(type, listener, options);
  };

  function cardIdentity(node) {
    if (!(node instanceof Element)) return "";
    return node.dataset.entityId
      || node.getAttribute("data-card-id")
      || node.querySelector("[data-entity-id]")?.dataset.entityId
      || node.querySelector("h1,h2,h3,.v2-card-title")?.textContent?.trim()
      || "";
  }

  function inertPreview(node) {
    if (!node) return null;
    const clone = node.cloneNode(true);
    clone.removeAttribute?.("id");
    clone.removeAttribute?.("data-v3-flip-bound");
    clone.querySelectorAll?.("[id]").forEach(item => item.removeAttribute("id"));
    clone.querySelectorAll?.("[data-v3-flip-bound]").forEach(item => item.removeAttribute("data-v3-flip-bound"));
    clone.querySelectorAll?.("button,input,select,textarea,a,[tabindex]").forEach(item => {
      item.setAttribute("tabindex", "-1");
      if ("disabled" in item) item.disabled = true;
    });
    return clone;
  }

  function createPlaceholder() {
    const placeholder = document.createElement("div");
    placeholder.className = "v3-stack-placeholder";
    placeholder.dataset.v3Placeholder = "true";
    placeholder.setAttribute("aria-hidden", "true");
    return placeholder;
  }

  function createStack(node) {
    const stack = document.createElement("div");
    stack.className = "v3-card-stack";
    stack.append(createPlaceholder(), createPlaceholder());
    if (node) stack.prepend(node);
    return stack;
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
        try { window.PantheonInformationCreate.open(); return; }
        catch (error) { window.alert(error.message || String(error)); return; }
      }
      stage.dispatchEvent(new CustomEvent("pantheon:create-requested", { bubbles: true }));
    });
    return button;
  }

  function restoreCurrentSlide(instance = swiper, speed = 0) {
    if (instance && instance.activeIndex !== 1) instance.slideTo(1, speed, false);
  }

  function ensureShell() {
    if (shell?.isConnected) return;
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
      observer: false,
      observeParents: false,
      resizeObserver: true,
      keyboard: { enabled: false },
      a11y: {
        enabled: true,
        containerMessage: "Navigation horizontale entre les cartes sœurs",
        slideLabelMessage: "Carte {{index}} sur {{slidesLength}}",
      },
      on: {
        init(instance) {
          instance.slideTo(1, 0, false);
          requestAnimationFrame(() => requestAnimationFrame(() => restoreCurrentSlide(instance, 0)));
        },
        touchStart() {
          if (!navigationLocked) userGestureActive = true;
        },
        touchEnd(instance) {
          if (instance.activeIndex === 1 && !instance.animating) userGestureActive = false;
        },
        transitionStart() { stage.dataset.swiperTransition = "true"; },
        transitionEnd(instance) {
          delete stage.dataset.swiperTransition;
          moveFromSwiper(instance);
        },
      },
    });
  }

  function replaceSlideContent(slide, node) {
    const current = slide.firstElementChild;
    if (current && node && cardIdentity(current.querySelector?.(".v2-card") || current) === cardIdentity(node)) return;
    slide.replaceChildren(createStack(node));
  }

  function finishNavigation() {
    window.clearTimeout(navigationTimeout);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      restoreCurrentSlide(swiper, 0);
      navigationLocked = false;
      pendingDirection = 0;
      userGestureActive = false;
      delete stage.dataset.swiperNavigation;
    }));
  }

  function moveFromSwiper(instance) {
    if (!userGestureActive || navigationLocked || instance.activeIndex === 1) return;
    userGestureActive = false;
    const active = instance.slides[instance.activeIndex];
    if (active?.dataset?.swiperAction === "create") {
      restoreCurrentSlide(instance, 180);
      return;
    }

    pendingDirection = instance.activeIndex < 1 ? -1 : 1;
    const button = document.getElementById(pendingDirection < 0 ? "v2-previous" : "v2-next");
    navigationLocked = true;
    stage.dataset.swiperNavigation = "true";
    if (button && !button.disabled) {
      button.click();
      navigationTimeout = window.setTimeout(finishNavigation, 900);
    } else {
      restoreCurrentSlide(instance, 180);
      finishNavigation();
    }
  }

  function updateMobile(node) {
    ensureShell();
    const previous = wrapper.querySelector('[data-swiper-role="previous"]');
    const current = wrapper.querySelector('[data-swiper-role="current"]');
    const next = wrapper.querySelector('[data-swiper-role="next"]');
    const previousButton = document.getElementById("v2-previous");

    if (currentNode && cardIdentity(currentNode) !== cardIdentity(node)) {
      if (pendingDirection > 0) previousProjection = inertPreview(currentNode);
      if (pendingDirection < 0) nextProjection = inertPreview(currentNode);
    }
    currentNode = node;

    previous.dataset.swiperAction = previousButton?.disabled ? "create" : "";
    replaceSlideContent(previous, previousButton?.disabled ? createActionCard() : (previousProjection || inertPreview(node)));
    replaceSlideContent(current, node);
    replaceSlideContent(next, nextProjection || inertPreview(node));

    swiper.updateSize();
    swiper.updateSlides();
    swiper.updateProgress();
    swiper.updateSlidesClasses();
    restoreCurrentSlide(swiper, 0);
    requestAnimationFrame(() => requestAnimationFrame(() => restoreCurrentSlide(swiper, 0)));
    if (navigationLocked) finishNavigation();
  }

  function destroyProjection() {
    window.clearTimeout(navigationTimeout);
    swiper?.destroy(true, true);
    swiper = null;
    shell = null;
    wrapper = null;
    latestNodes = [];
    currentNode = null;
    previousProjection = null;
    nextProjection = null;
    userGestureActive = false;
    navigationLocked = false;
    pendingDirection = 0;
    delete stage.dataset.swiperNavigation;
    delete stage.dataset.swiperTransition;
  }

  function mount(nodes) {
    pendingClearToken += 1;
    rendererClearedStage = false;
    latestNodes = nodes;
    const node = nodes.find(item => item instanceof Node) || null;
    if (!node || node.classList?.contains("v2-empty")) {
      destroyProjection();
      nativeReplaceChildren(...nodes);
      return;
    }

    if (mobileMedia.matches) {
      updateMobile(node);
      return;
    }

    destroyProjection();
    latestNodes = nodes;
    const grid = document.createElement("div");
    grid.className = "v2-card-grid";
    const gridWrapper = document.createElement("div");
    gridWrapper.className = "v2-card-grid-wrapper";
    gridWrapper.append(createStack(node));
    grid.append(gridWrapper);
    nativeReplaceChildren(grid);
  }

  function scheduleConfirmedClear() {
    const token = ++pendingClearToken;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (!rendererClearedStage || token !== pendingClearToken) return;
      destroyProjection();
      nativeReplaceChildren();
    }));
  }

  stage.replaceChildren = (...nodes) => {
    rendererClearedStage = nodes.length === 0;
    if (rendererClearedStage) { scheduleConfirmedClear(); return; }
    mount(nodes);
  };

  stage.append = (...nodes) => {
    if (rendererClearedStage) {
      rendererClearedStage = false;
      pendingClearToken += 1;
      mount(nodes);
      return;
    }
    nativeAppend(...nodes);
  };

  stage.appendChild = node => {
    if (rendererClearedStage) {
      rendererClearedStage = false;
      pendingClearToken += 1;
      mount([node]);
      return node;
    }
    return nativeAppendChild(node);
  };

  mobileMedia.addEventListener?.("change", () => { if (latestNodes.length) mount(latestNodes); });
  window.addEventListener("pagehide", destroyProjection, { once: true });
})();
