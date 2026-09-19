// The committed-panel accessors shared by every surface group (C3 design D3:
// panels render only when their backing OOB read model is present — the
// truthful-data scope, roadmap §7; the client never reads uncommitted state).
export function panelOf(store, name) {
  return (store.view.panels && store.view.panels[name]) || null;
}

export function panelAvailableOf(store, name) {
  const p = panelOf(store, name);
  return !!p && p.available !== false;
}

export function usePanelView(store) {
  function panel(name) {
    return panelOf(store, name);
  }

  function panelAvailable(name) {
    return panelAvailableOf(store, name);
  }

  return { panel, panelAvailable };
}
