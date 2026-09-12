import { useEffect, useRef, useState } from "react";

// Small "ⓘ What does this mean?" trigger used next to less-obvious form fields. Plain,
// generic explanatory copy only — never an invented legal/statutory definition.
export default function HelpPopover({ children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <span className="help-popover-wrap" ref={ref}>
      <button
        type="button"
        className="help-popover-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        ⓘ What does this mean?
      </button>
      {open && (
        <div className="help-popover-panel" role="tooltip">
          {children}
        </div>
      )}
    </span>
  );
}
