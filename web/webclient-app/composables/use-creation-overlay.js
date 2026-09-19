// The CreationOverlay wiring facade: composes the cohesive behavior groups
// (each watch stays with the state it mutates) into the single flat binding
// set the CreationOverlay template consumes, so the SFC itself stays a thin,
// passive renderer. Group call order preserves the original watcher
// registration order (touched/mode + draft resync -> proposal fill -> result
// and gate settlement -> stage mirror), and the mount-time proposal fill runs
// at the end of setup exactly as the original SFC did.
import { useCreationForm } from "./use-creation-form.js";
import { useCreationCustom } from "./use-creation-custom.js";
import { useCreationProposal } from "./use-creation-proposal.js";
import { useCreationDispatch } from "./use-creation-dispatch.js";
import { useCreationStage } from "./use-creation-stage.js";

export function useCreationOverlay(props, emit) {
  const form = useCreationForm(props);
  const custom = useCreationCustom(props, form, emit);
  const proposal = useCreationProposal(props, form, custom);
  const dispatch = useCreationDispatch(props, form, emit);
  const stage = useCreationStage(props, form, emit);
  // Mount-time proposal fill: a panel that already carries an unconsumed
  // proposal (a same-session remount) pre-fills the form before first paint.
  proposal.applyProposal();
  return {
    ...form,
    ...custom,
    ...proposal,
    ...dispatch,
    ...stage,
  };
}
