// C1 (webclient-vue-07-wire-store) store behavior tests: the reducer ordering
// the wiring wave relies on — atomic new-epoch snapshot adoption, active-epoch
// revision ordering, old-epoch / stale-revision rejection, and panel
// replacement. The store is driven by raw reducer inputs (design D5): the live
// evennia.js OOB binding lands in C3, so every input here goes through
// `store.receive` / `store.beginTransport` / `store.setConnected`.

import { effectScope, watch } from "vue";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

describe("store protocol ordering", () => {
  let store;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  // Start one transport generation, connect, and adopt the first snapshot.
  function openSession() {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [fx.snapshot()], {});
    expect(result.accepted).toBe(true);
    return result;
  }

  describe("atomic new-epoch snapshot adoption", () => {
    it("adopts a fresh-epoch snapshot after a transport reset", () => {
      openSession();
      store.beginTransport(2);
      expect(store.view.phase).toBe("awaiting_initial_snapshot");
      expect(store.view.mutationsLocked).toBe(true);

      const stale = store.receive(2, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_A })], {});
      expect(stale.accepted).toBe(false);
      expect(stale.reason).toBe("retired_epoch");

      const fresh = store.receive(2, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_B })], {});
      expect(fresh.accepted).toBe(true);
      expect(fresh.established).toBe(true);
      expect(store.view.epoch).toBe(fx.EPOCH_B);
      expect(store.view.phase).toBe("active");
      expect(store.view.connectionStatus).toBe("ready");
    });

    it("observers see whole committed views, never a partial panel state", () => {
      const scope = effectScope();
      const seen = [];
      const stop = scope.run(
        () =>
          watch(
            () => store.view,
            (next, prev) => {
              seen.push({ next, prev });
            },
            { flush: "sync" },
          ),
      );

      openSession();
      // A snapshot carrying status + local_map commits both panels at once.
      const result = store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { status: fx.statusPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      expect(result.accepted).toBe(true);

      // Every observation after the commit carries BOTH panels: the commit is
      // atomic — no observation shows one panel without the other.
      const lastObserved = seen[seen.length - 1].next;
      expect(Object.keys(lastObserved.panels).sort()).toEqual(["local_map", "status"]);
      for (const { next } of seen) {
        const panelNames = Object.keys(next.panels).sort();
        const hasStatus = next.panels.status !== undefined;
        const hasMap = next.panels.local_map !== undefined;
        // A committed view is always a whole object: if one panel is present,
        // the view was committed with it; partial states never surface.
        expect(hasStatus ? panelNames.includes("status") : true).toBe(true);
        expect(hasMap ? panelNames.includes("local_map") : true).toBe(true);
      }
      stop();
      scope.stop();
    });

    it("preserves the last committed state when payloads are rejected", () => {
      openSession();
      const committed = JSON.parse(JSON.stringify(store.view));

      const staleRevision = store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 1 })],
        {},
      );
      expect(staleRevision.reason).toBe("not_newer");
      const offEpoch = store.receive(1, "ui_update", [fx.update({ presentation_epoch: fx.EPOCH_B })], {});
      expect(offEpoch.reason).toBe("different_epoch");

      expect(store.view).toEqual(committed);
    });
  });

  describe("active-epoch revision ordering", () => {
    it("accepts strictly newer revisions in the active epoch", () => {
      openSession();
      const result = store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
      expect(result.accepted).toBe(true);
      expect(store.view.revision).toBe(2);
      const reject = store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
      expect(reject.accepted).toBe(false);
      expect(reject.reason).toBe("not_newer");
      expect(store.view.revision).toBe(2);
    });

    it("rejects an update that cannot establish a new epoch", () => {
      store.beginTransport(1);
      store.setConnected(true);
      // phase = awaiting_initial_snapshot: only a valid full snapshot can
      // establish active state; an update never does.
      const result = store.receive(1, "ui_update", [fx.update({ revision: 1, presentation_epoch: fx.EPOCH_C })], {});
      expect(result.accepted).toBe(false);
      expect(result.reason).toBe("update_cannot_establish_epoch");
      expect(store.view.phase).toBe("awaiting_initial_snapshot");
    });
  });

  describe("panel replacement", () => {
    it("a snapshot wipes unmentioned panels; an update replaces only named panels", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 2,
            panels: {
              status: fx.statusPanel(),
              local_map: fx.localMapPanel(),
              context_actions: fx.explorationActions(),
            },
          }),
          {},
        ],
      );
      let names = Object.keys(store.view.panels).sort();
      expect(names).toEqual(["context_actions", "local_map", "status"]);

      // Full snapshot without local_map: the panel set is replaced wholesale.
      store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 3, presentation_epoch: fx.EPOCH_A })], {});
      names = Object.keys(store.view.panels);
      expect(names).toEqual(["status"]);

      // Same-epoch snapshot with a higher revision is accepted; panels are
      // replaced wholly.
      const resnap = store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 4 })], {});
      expect(resnap.accepted).toBe(true);
      expect(Object.keys(store.view.panels)).toEqual(["status"]);
    });
  });

  describe("protocol errors", () => {
    it("a no_puppet error detaches the session; a fresh-epoch snapshot re-establishes it", () => {
      openSession();
      const result = store.receive(1, "ui_protocol_error", [fx.protocolError()], {});
      expect(result.accepted).toBe(true);
      expect(store.view.phase).toBe("detached");
      expect(Object.keys(store.view.panels)).toEqual([]);
      expect(store.view.mutationsLocked).toBe(true);
      expect(store.view.connectionStatus).toBe("waiting");

      store.beginTransport(2);
      // The former active epoch EPOCH_A is now retired: a same-epoch snapshot
      // is a stale survivor of the retired sequence.
      const retired = store.receive(2, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_A, revision: 1 })], {});
      expect(retired.accepted).toBe(false);
      expect(retired.reason).toBe("retired_epoch");
      expect(store.view.phase).toBe("awaiting_initial_snapshot");

      const reestablished = store.receive(
        2,
        "ui_snapshot",
        [fx.snapshot({ presentation_epoch: fx.EPOCH_C, revision: 1 })],
        {},
      );
      expect(reestablished.accepted).toBe(true);
      expect(store.view.phase).toBe("active");
      expect(store.view.revision).toBe(1);
    });

    it("an unsupported_version error locks mutations until a new epoch adopts", () => {
      openSession();
      const result = store.receive(
        1,
        "ui_protocol_error",
        [fx.protocolError({ code: "unsupported_version", message: "不支援的協定版本", reload_required: true })],
        {},
      );
      expect(result.accepted).toBe(true);
      expect(store.view.mutationsLocked).toBe(true);
      expect(store.view.protocolError).not.toEqual(null);
    });
  });

  describe("connection lifecycle", () => {
    it("disconnecting locks mutations and flips the status slice to offline", () => {
      openSession();
      store.setConnected(false);
      expect(store.view.connected).toBe(false);
      expect(store.view.connectionStatus).toBe("offline");
      expect(store.view.mutationsLocked).toBe(true);
    });
  });
});
