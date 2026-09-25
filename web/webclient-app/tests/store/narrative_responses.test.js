// Store-level tests for narrative response ordinals, responseMarks, and
// single-run tokenization (OpenSpec change webclient-message-pages, task 3.3).
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { responseBlocks, segmentResponses } from "../../lib/message_pages.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

function openActiveSession(store, sender) {
  store.beginTransport(1);
  store.setConnected(true);
  store.setLoggedIn(true);
  store.setSender(sender);
  const result = store.receive(1, "ui_snapshot", [fx.snapshot()], {});
  expect(result.accepted).toBe(true);
  return store;
}

describe("store narrative responses and responseMarks (design D1/D5)", () => {
  let store;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    openActiveSession(store, sender);
  });

  it("forms one response from a typed sendText('look') followed by two out lines", () => {
    expect(store.sendText("look")).toBe(true);
    store.appendText("out", "石板廣場夜色沉靜。");
    store.appendText("out", "遠處霧燈閃爍。");

    // sendText appends an `in` line directly and needs no responseMark.
    expect(store.responseMarks).toEqual([]);
    const responses = segmentResponses(store.narrative, store.responseMarks);
    expect(responses).toHaveLength(1);
    expect(responses[0].header.kind).toBe("in");
    expect(responses[0].header.text).toBe("look");
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual([
      "石板廣場夜色沉靜。",
      "遠處霧燈閃爍。",
    ]);
  });

  it("forms a new headerless response when a silent explore.dialogue_leave is followed by an out line", () => {
    // Earlier response in the log.
    store.sendText("look");
    store.appendText("out", "你在石板廣場上。");

    const reqId = store.dispatchAction("explore.dialogue_leave", {});
    expect(reqId).toBe("session:1");
    // Silent control appends no `in` line, but records a response mark for the next ordinal (3).
    expect(store.narrative).toHaveLength(2);
    expect(store.responseMarks).toEqual([3]);

    // While the reply has not arrived yet, no empty response is opened.
    expect(segmentResponses(store.narrative, store.responseMarks)).toHaveLength(1);

    // Server reply arrives with seq 3 -> begins a new headerless response.
    store.appendText("out", "你結束了對話。");
    const responses = segmentResponses(store.narrative, store.responseMarks);
    expect(responses).toHaveLength(2);
    expect(responses[0].header.text).toBe("look");
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual(["你在石板廣場上。"]);
    expect(responses[1].header).toBe(null);
    expect(responses[1].startSeq).toBe(3);
    expect(responseBlocks(responses[1]).map((b) => b.text)).toEqual(["你結束了對話。"]);
  });

  it("gives exactly one response for an echoing explore.move (the mark equals the echo's seq)", () => {
    store.appendText("out", "連線成功。");

    const reqId = store.dispatchAction(
      "explore.move",
      { exit_ref: "exit-north", current_node: "grid:0:0:0" },
      { exitLabel: "往北" },
    );
    expect(reqId).toBe("session:1");
    const echoLine = store.narrative[store.narrative.length - 1];
    expect(echoLine.kind).toBe("in");
    expect(echoLine.text).toBe("往北");
    expect(store.responseMarks).toEqual([echoLine.seq]);

    store.appendText("out", "你走進了北側走廊。");
    const responses = segmentResponses(store.narrative, store.responseMarks);
    // Leading response ("連線成功。") + the single move response ("往北" -> "你走進了北側走廊。").
    expect(responses).toHaveLength(2);
    expect(responses[1].header).toEqual(echoLine);
    expect(responseBlocks(responses[1]).map((b) => b.text)).toEqual(["你走進了北側走廊。"]);
  });

  it("records no mark when a dispatch is blocked because a mutation is already in flight", () => {
    const first = store.dispatchAction("explore.dialogue_leave", {});
    expect(first).toBe("session:1");
    expect(store.responseMarks).toEqual([1]);

    store.appendText("out", "你結束了對話。");
    // Mutation is still in flight; second dispatch is refused.
    const blocked = store.dispatchAction("explore.dialogue_leave", {});
    expect(blocked).toBe(null);
    expect(store.responseMarks).toEqual([1]);

    // A subsequent server line joins the current response instead of starting a new one.
    store.appendText("out", "微風吹過。");
    const responses = segmentResponses(store.narrative, store.responseMarks);
    expect(responses).toHaveLength(1);
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual([
      "你結束了對話。",
      "微風吹過。",
    ]);
  });

  it("records no mark when sender.sendAction throws synchronously", () => {
    store.setSender({
      sendAction() {
        throw new Error("simulated transport failure");
      },
      sendText() {},
    });
    store.dispatchAction("explore.dialogue_leave", {});
    expect(store.responseMarks).toEqual([]);
    expect(store.narrative).toEqual([]);
  });

  it("keeps seq monotonic across a 510-line flood and drops marks below the oldest retained line", () => {
    // Dispatch a silent action at the start (mark = 1).
    const firstReq = store.dispatchAction("explore.dialogue_leave", {});
    expect(firstReq).toBe("session:1");
    expect(store.responseMarks).toEqual([1]);

    // Release in-flight gate so we can record another mark mid-flood.
    const res = store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: firstReq,
          outcome: "success",
          code: "left",
          message: "你結束了對話。",
          presentation_revision: 1,
        }),
      ],
      {},
    );
    expect(res.accepted).toBe(true);

    for (let i = 1; i <= 250; i += 1) {
      store.appendText("out", `行 ${i}`);
    }
    // Record a second mark at seq 251, which will survive a 510-line flood (oldest retained seq = 11).
    const secondReq = store.dispatchAction("explore.dialogue_leave", {});
    expect(secondReq).toBe("session:2");
    expect(store.responseMarks).toEqual([1, 251]);

    for (let i = 251; i <= 510; i += 1) {
      store.appendText("out", `行 ${i}`);
    }

    expect(store.narrative).toHaveLength(500);
    expect(store.narrative[0].seq).toBe(11);
    expect(store.narrative[store.narrative.length - 1].seq).toBe(510);
    for (let i = 1; i < store.narrative.length; i += 1) {
      expect(store.narrative[i].seq).toBe(store.narrative[i - 1].seq + 1);
    }
    // Mark 1 (< 11) was dropped; mark 251 (>= 11) remains.
    expect(store.responseMarks).toEqual([251]);

    const responses = segmentResponses(store.narrative, store.responseMarks);
    expect(responses).toHaveLength(2);
    expect(responses[0].startSeq).toBe(null);
    expect(responses[0].blocks[0].seq).toBe(11);
    expect(responses[1].startSeq).toBe(251);
    expect(responses[1].blocks[0].seq).toBe(251);
  });

  it("tokenizes out, sys, and err lines once on append and keeps tokens null on in lines", () => {
    const inLine = store.appendText("in", "look");
    const outLine = store.appendText("out", '<span class="color-203">紅</span>字');
    const sysLine = store.appendText("sys", "系統訊息");
    const errLine = store.appendText("err", '<span class="underline">錯誤</span>訊息');

    expect(inLine.tokens).toBe(null);
    expect(Array.isArray(outLine.tokens)).toBe(true);
    expect(Array.isArray(sysLine.tokens)).toBe(true);
    expect(Array.isArray(errLine.tokens)).toBe(true);
    expect(errLine.tokens.some((t) => t.kind === "open")).toBe(true);
  });
});
