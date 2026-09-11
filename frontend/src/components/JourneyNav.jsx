import { Link } from "react-router-dom";

const STEPS = [
  { key: "profile", label: "1. Profile", path: () => "/" },
  {
    key: "eligibility",
    label: "2. Eligible Schemes",
    path: ({ citizenId }) => citizenId && `/citizens/${citizenId}/eligibility`,
  },
  {
    key: "bundle",
    label: "3. Bundle",
    path: ({ citizenId }) => citizenId && `/citizens/${citizenId}/bundle`,
  },
  {
    key: "checklist",
    label: "4. Checklist",
    path: ({ citizenId, bundleId }) =>
      citizenId && bundleId && `/bundles/${bundleId}/checklist?citizen=${citizenId}`,
  },
  {
    key: "trace",
    label: "5. Trace",
    path: ({ citizenId }) => citizenId && `/citizens/${citizenId}/trace`,
  },
];

export default function JourneyNav({ current, citizenId, bundleId }) {
  const currentIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <nav className="journey" aria-label="Application progress">
      {STEPS.map((step, i) => {
        const path = step.path({ citizenId, bundleId });
        const isActive = step.key === current;
        const isDone = i < currentIndex;
        if (!path) {
          return <span key={step.key}>{step.label}</span>;
        }
        return (
          <Link key={step.key} to={path} className={isActive ? "active" : isDone ? "done" : ""}>
            {step.label}
          </Link>
        );
      })}
    </nav>
  );
}
