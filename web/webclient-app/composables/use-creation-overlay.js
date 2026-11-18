// The CreationOverlay wiring facade: composes the cohesive behavior groups
// (each watch stays with the state it mutates) into the single flat binding
// set the CreationOverlay template consumes, so the SFC itself stays a thin,
// passive renderer. Group call order preserves the original watcher
// registration order (touched/mode + draft resync -> proposal fill -> result
// and gate settlement -> stage mirror -> portrait request), and the mount-time proposal fill runs
// at the end of setup exactly as the original SFC did.
import { useCreationForm } from "./use-creation-form.js";
import { useCreationCustom } from "./use-creation-custom.js";
import { useCreationProposal } from "./use-creation-proposal.js";
import { useCreationDispatch } from "./use-creation-dispatch.js";
import { useCreationStage } from "./use-creation-stage.js";
import { useCreationSteps } from "./use-creation-steps.js";
import { useCreationPortrait } from "./use-creation-portrait.js";

export function useCreationOverlay(props, emit) {
  const form = useCreationForm(props);
  const custom = useCreationCustom(props, form, emit);
  // The custom form's local step (registers no watcher), created before the
  // proposal group so a fresh concept apply can land on the first step.
  const steps = useCreationSteps({ errorFields: custom.formErrorFields });
  const proposal = useCreationProposal(props, form, custom, steps);
  const dispatch = useCreationDispatch(props, form, emit);
  const stage = useCreationStage(props, form, emit, { rollPending: dispatch.rollPending });
  // The portrait request owner (creation-draft-portrait): local drawer and
  // request UI only, composed after the existing form state.
  const portrait = useCreationPortrait(props, form, emit);
  // Mount-time proposal fill: a panel that already carries an unconsumed
  // proposal (a same-session remount) pre-fills the form before first paint.
  proposal.applyProposal();
  return {
    ...form,
    ...custom,
    ...proposal,
    ...dispatch,
    ...stage,
    ...steps,
    ...portrait,
  };
}
