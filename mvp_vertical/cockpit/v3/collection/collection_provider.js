// Cockpit V3 — CollectionProvider.
//
// The source of a collection's items. It emits items progressively so the
// CollectionController exercises the real placeholder -> replace -> appendSlide
// lifecycle even when the backing data is already resident. Business logic never
// touches Swiper: the provider only calls the sink hooks.

// Streams a fully-known array of items into a controller, one per animation
// frame, then settles on `index`. Returns a cancel handle so a superseding
// navigation can abort an in-flight stream cleanly.
export function streamArray(controller, collection, itemList, index = 0) {
  const list = Array.isArray(itemList) ? itemList.slice() : [];
  controller.bootstrap(collection);

  let cancelled = false;
  let cursor = 0;
  let frame = 0;

  function pump() {
    if (cancelled) return;
    // Emit a small burst per frame to stay smooth without stalling on large
    // collections.
    const budget = Math.min(cursor + 4, list.length);
    for (; cursor < budget; cursor += 1) controller.push(list[cursor]);
    if (cursor < list.length) {
      frame = window.requestAnimationFrame(pump);
      return;
    }
    controller.settle(index);
  }

  if (!list.length) {
    controller.settle(null);
  } else {
    frame = window.requestAnimationFrame(pump);
  }

  return function cancel() {
    cancelled = true;
    window.cancelAnimationFrame(frame);
  };
}
