import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import Admin from "./pages/Admin";
import Bundle from "./pages/Bundle";
import Checklist from "./pages/Checklist";
import Dashboard from "./pages/Dashboard";
import EligibleSchemes from "./pages/EligibleSchemes";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Register from "./pages/Register";
import Trace from "./pages/Trace";
import { clearSession, getUser, isLoggedIn, subscribe } from "./auth/session";

function SessionNav() {
  const [user, setUser] = useState(getUser());

  useEffect(() => subscribe(() => setUser(getUser())), []);

  return (
    <nav className="session-nav">
      {isLoggedIn() && user ? (
        <>
          <span>
            Logged in as {user.email} ({user.role})
          </span>
          <button type="button" className="secondary" onClick={clearSession}>
            Log out
          </button>
        </>
      ) : (
        <>
          <Link to="/login">Log in</Link>
          <Link to="/register">Register</Link>
        </>
      )}
    </nav>
  );
}

function App() {
  return (
    <>
      <SessionNav />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/citizens/:citizenId/eligibility" element={<EligibleSchemes />} />
        <Route path="/citizens/:citizenId/bundle" element={<Bundle />} />
        <Route path="/bundles/:bundleId/checklist" element={<Checklist />} />
        <Route path="/citizens/:citizenId/trace" element={<Trace />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </>
  );
}

export default App;
