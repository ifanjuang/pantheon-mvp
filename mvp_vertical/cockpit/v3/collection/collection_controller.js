// Cockpit — CollectionController.
//
// Binds the three independent pieces together and owns none of their concerns:
//
//   NavigationState (data) · CollectionProvider (source) · MotionAdapter (motion)
//
// The rest of the cockpit talks to this controller, never to Swiper. Only the
// active projection and its two neighbours are ever mounted; the collection
// itself stays in NavigationState as data.

import { createNavigationState } from "./navigation_state.js";
import { createWindowedMotion } from "./motion_adapter.js";
import { loadCollection } from "./collection_provider.js";

export function createCollectionController({
  mount,
  renderItem,
  renderNew = () => null,
  renderPlaceholder,
  renderEmpty = null,
  onActiveChange = () => {},
  onMoveState = () => {},
  state = null,
  label = "",
}) {
  if (typeof renderItem !== "function") throw new Error("CollectionController requires renderItem");
  if (typeof renderPlaceholder !== "function") throw new Error("CollectionController requires renderPlaceholder");

  const navigation = state || createNavigationState();
  let collection = { id: null, title: "", canCreate: false };
  let cancelLoad = null;
  let syncing = false;
  let refreshFrame = 0;

  const offset = () => (collection.canCreate ? 1 : 0);

  function renderAt(virtualIndex) {
    if (offset() && virtualIndex === 0) return renderNew(collection);

    const itemIndex = virtualIndex - offset();
    const item = navigation.itemAt(itemIndex);
    if (!item) {
      const snapshot = navigation.snapshot();
      if (snapshot.loading || !renderEmpty) return renderPlaceholder();
      return renderEmpty(collection);
    }
    return renderItem(item, {
      active: itemIndex === navigation.snapshot().activeIndex,
      index: itemIndex,
    });
  }

  const motion = createWindowedMotion({
    mount,
    renderAt,
    label,
    onMoveState,
    onIndexChange(virtualIndex) {
      if (offset() && virtualIndex === 0) {
        onActiveChange(null, -1, { synthetic: "create", collection });
        return;
      }
      syncing = true;
      navigation.setIndex(virtualIndex - offset());
      syncing = false;
      scheduleRefresh();
      const snapshot = navigation.snapshot();
      onActiveChange(snapshot.activeItem, snapshot.activeIndex, { synthetic: null, collection });
    },
  });

  // Re-produce the mounted window so the newly active projection becomes the
  // interactive one and its neighbours fall back to inert previews.
  function scheduleRefresh() {
    window.cancelAnimationFrame(refreshFrame);
    refreshFrame = window.requestAnimationFrame(() => {
      refreshFrame = 0;
      motion.refresh();
    });
  }

  function projectionCount() {
    const snapshot = navigation.snapshot();
    return offset() + (snapshot.itemCount || 1);
  }

  function syncMotion({ reposition = true } = {}) {
    const snapshot = navigation.snapshot();
    motion.mount(projectionCount(), Math.max(0, snapshot.activeIndex) + offset());
    if (reposition) motion.goTo(Math.max(0, snapshot.activeIndex) + offset(), { animate: false });
  }

  navigation.subscribe(() => {
    if (syncing) return;
    // Items arrived (or the collection changed) while we were not driving.
    motion.extendTo(projectionCount());
    scheduleRefresh();
  });

  // Load a collection. `source` is an Array (applied at once) or an
  // AsyncIterable (consumed as it yields).
  function load(nextCollection, source, index = 0) {
    cancelLoad?.();
    collection = {
      id: nextCollection?.id ?? null,
      title: nextCollection?.title ?? "",
      canCreate: Boolean(nextCollection?.canCreate),
      spaceId: nextCollection?.spaceId ?? null,
    };
    cancelLoad = loadCollection(navigation, collection, source, index);
    syncMotion();
    const snapshot = navigation.snapshot();
    onActiveChange(snapshot.activeItem, snapshot.activeIndex, { synthetic: null, collection });
  }

  return Object.freeze({
    state: navigation,
    load,
    move(delta) { motion.move(delta); },
    goTo(index) { motion.goTo(index + offset(), { animate: false }); },
    refresh() { motion.refresh(); },
    activeElement() { return motion.activeElement(); },
    lock() { motion.lock(); },
    unlock() { motion.unlock(); },
    dispose() {
      cancelLoad?.();
      window.cancelAnimationFrame(refreshFrame);
      motion.dispose();
    },
    get collection() { return collection; },
  });
}
