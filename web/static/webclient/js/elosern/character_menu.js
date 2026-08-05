/*
 * Elosern DOM-independent character-menu model.
 *
 * Reduces a validated `character` panel into a flat list of read-only display
 * rows (traits, passives, equipment, disguise, guild, wallet). Every value is
 * true state; the disguise section describes the outwardly displayed values
 * without ever substituting them for true traits. Rows are focusable for
 * scrolling but never submit (the panel is read-only).
 *
 * No `document` or `window` access at load time; Node tests exercise the model
 * directly and the GoldenLayout character dock binds it to the keyboard router.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.CharacterMenu = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function displayItem(key, label, description) {
    return {
      key: key,
      label: label,
      enabled: false,
      actionId: null,
      payload: null,
      display: true,
      description: description || null,
    };
  }

  function sectionItem(key, label) {
    return {
      key: key,
      label: label,
      enabled: false,
      actionId: null,
      payload: null,
      display: true,
      section: true,
      description: null,
    };
  }

  // One trait row: gauges report current/maximum, statics report the base.
  function traitLabel(row) {
    var value = row.max === null ? String(row.current) : row.current + " / " + row.max;
    return row.label + "：" + value;
  }

  function buildMenu(panel) {
    var items = [];
    var traits = (panel && panel.traits) || [];
    if (traits.length > 0) {
      items.push(sectionItem("section-traits", "屬性"));
      traits.forEach(function (row, index) {
        items.push(displayItem("trait-" + index, traitLabel(row), null));
      });
    }
    var passives = (panel && panel.passives) || [];
    if (passives.length > 0) {
      items.push(sectionItem("section-passives", "被動技能"));
      passives.forEach(function (row, index) {
        items.push(displayItem("passive-" + index, row.label, null));
      });
    }
    var equipment = (panel && panel.equipment) || [];
    if (equipment.length > 0) {
      items.push(sectionItem("section-equipment", "裝備"));
      equipment.forEach(function (row, index) {
        items.push(displayItem("equipment-" + index, row.slot + "：" + row.display_name, null));
      });
    }
    var disguise = panel && panel.disguise;
    if (disguise && disguise.active) {
      items.push(sectionItem("section-disguise", "偽裝"));
      items.push(displayItem("disguise-desc", disguise.description || "", null));
      (disguise.displayed || []).forEach(function (row, index) {
        items.push(
          displayItem("disguise-" + index, row.label + "：" + row.value, null)
        );
      });
    }
    var guild = panel && panel.guild;
    var rankText = guild && guild.rank ? guild.rank : "未加入公會";
    items.push(sectionItem("section-guild", "公會"));
    items.push(displayItem("guild-rank", "階級：" + rankText, null));
    items.push(displayItem("guild-merit", "功績：" + ((guild && guild.merit) || 0), null));
    items.push(displayItem("wallet", "錢包：" + ((panel && panel.wallet) || 0) + " 銅", null));
    return { items: items, focusKey: null, panel: panel };
  }

  return {
    buildMenu: buildMenu,
    traitLabel: traitLabel,
  };
});
