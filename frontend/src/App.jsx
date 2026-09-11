import { Route, Routes } from "react-router-dom";
import Admin from "./pages/Admin";
import Bundle from "./pages/Bundle";
import Checklist from "./pages/Checklist";
import EligibleSchemes from "./pages/EligibleSchemes";
import ProfileIntake from "./pages/ProfileIntake";
import Trace from "./pages/Trace";

function App() {
  return (
    <Routes>
      <Route path="/" element={<ProfileIntake />} />
      <Route path="/citizens/:citizenId/eligibility" element={<EligibleSchemes />} />
      <Route path="/citizens/:citizenId/bundle" element={<Bundle />} />
      <Route path="/bundles/:bundleId/checklist" element={<Checklist />} />
      <Route path="/citizens/:citizenId/trace" element={<Trace />} />
      <Route path="/admin" element={<Admin />} />
    </Routes>
  );
}

export default App;
