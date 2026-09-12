import { useState } from "react";

// "Ask Sahayak" — a lightweight, honest help layer. This is a static FAQ, not a live model
// call: there's no backend endpoint wired for conversational help, and this codebase is
// deliberate elsewhere (see ApplyLink) about never presenting a capability that isn't real.
const FAQ = [
  {
    q: "What does annual household income mean?",
    a: "Your total income from all household members over one year. Some schemes look at gross income, others at income after deductions — check the specific scheme's criteria if you're unsure which applies.",
  },
  {
    q: "Why am I marked as 'Needs verification'?",
    a: "It means your profile matches most of a scheme's conditions, but at least one condition couldn't be checked automatically from the details you've given — usually because a document or exact figure is still missing.",
  },
  {
    q: "Which document should I upload first?",
    a: "Start with whichever document is needed by the most schemes in your bundle — your Application Plan page groups documents by scheme so you can see the overlap at a glance.",
  },
  {
    q: "What happens when schemes conflict?",
    a: "Some schemes can't be held together under their own rules. When that happens, we keep the combination that covers the most needs without breaking any rule, and show you what was left out and why.",
  },
];

export default function HelpDrawer() {
  const [open, setOpen] = useState(false);
  const [answerIndex, setAnswerIndex] = useState(null);

  if (!open) {
    return (
      <button type="button" className="help-fab" onClick={() => setOpen(true)}>
        💬 Ask Sahayak
      </button>
    );
  }

  return (
    <>
      <div className="help-drawer-backdrop" onClick={() => setOpen(false)} />
      <div className="help-drawer" role="dialog" aria-label="Ask Sahayak">
        <div className="help-drawer-header">
          <div>
            <h2 style={{ marginBottom: "0.15rem" }}>Ask Sahayak</h2>
            <p style={{ margin: 0, fontSize: "0.85rem" }}>
              I can explain questions, eligibility terms, and application requirements in simple language.
            </p>
          </div>
          <button type="button" className="help-drawer-close" onClick={() => setOpen(false)} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="help-drawer-prompts">
          {FAQ.map((item, i) => (
            <button key={item.q} type="button" className="help-drawer-prompt" onClick={() => setAnswerIndex(i)}>
              {item.q}
            </button>
          ))}
        </div>

        {answerIndex !== null && (
          <div className="help-drawer-answer">
            <strong>{FAQ[answerIndex].q}</strong>
            {FAQ[answerIndex].a}
          </div>
        )}

        <p className="hint" style={{ marginTop: "auto" }}>
          This is a quick-reference guide, not a live conversation — for anything specific to your
          case, use Help &amp; Support.
        </p>
      </div>
    </>
  );
}
