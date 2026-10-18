// The two desktop viewports the window primitives are reviewed at
// (party member management design §11): the 1451×790 reference and
// 1920×1080. Each primitive's story file exports one story per viewport
// through these helpers, so the review is side by side with the approved
// Design/PartyMemberManagement prototype at the same sizes.
export const WINDOW_VIEWPORTS = {
  reference: { name: "Reference 1451×790", styles: { width: "1451px", height: "790px" }, type: "desktop" },
  fullHd: { name: "Full HD 1920×1080", styles: { width: "1920px", height: "1080px" }, type: "desktop" },
};

export const windowViewportParameters = { viewport: { options: WINDOW_VIEWPORTS } };

export const atReference = { globals: { viewport: { value: "reference", isRotated: false } } };
export const atFullHd = { globals: { viewport: { value: "fullHd", isRotated: false } } };
