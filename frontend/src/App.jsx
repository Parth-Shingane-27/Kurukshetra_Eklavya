import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import Activity from "./pages/Activity";
import Admin from "./pages/Admin";
import AdminAnalytics from "./pages/AdminAnalytics";
import AdminFraud from "./pages/AdminFraud";
import AdminGrievances from "./pages/AdminGrievances";
import AdminSchemeReports from "./pages/AdminSchemeReports";
import Bundle from "./pages/Bundle";
import Checklist from "./pages/Checklist";
import ConversationalIntake from "./pages/ConversationalIntake";
import Dashboard from "./pages/Dashboard";
import EligibleSchemes from "./pages/EligibleSchemes";
import Grievances from "./pages/Grievances";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Profile from "./pages/Profile";
import QuickChecker from "./pages/QuickChecker";
import NationalSchemeSearch from "./pages/NationalSchemeSearch";
import RagCandidates from "./pages/RagCandidates";
import Register from "./pages/Register";
import SavedSchemes from "./pages/SavedSchemes";
import SchemeCatalog from "./pages/SchemeCatalog";
import Trace from "./pages/Trace";
import { clearSession, getUser, isLoggedIn, subscribe } from "./auth/session";
import ProtectedRoute from "./auth/ProtectedRoute";
import { clearStoredCitizenId } from "./lib/storage";

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
          <button
            type="button"
            className="secondary"
            onClick={() => {
              clearSession();
              clearStoredCitizenId();
            }}
          >
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
        <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/converse" element={<ConversationalIntake />} />
        <Route path="/quick-check" element={<QuickChecker />} />
        <Route path="/catalog" element={<SchemeCatalog />} />
        <Route path="/national-search" element={<NationalSchemeSearch />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route
          path="/citizens/:citizenId/eligibility"
          element={<ProtectedRoute><EligibleSchemes /></ProtectedRoute>}
        />
        <Route path="/citizens/:citizenId/bundle" element={<ProtectedRoute><Bundle /></ProtectedRoute>} />
        <Route path="/bundles/:bundleId/checklist" element={<ProtectedRoute><Checklist /></ProtectedRoute>} />
        <Route path="/citizens/:citizenId/trace" element={<ProtectedRoute><Trace /></ProtectedRoute>} />
        <Route path="/grievances" element={<ProtectedRoute><Grievances /></ProtectedRoute>} />
        <Route path="/saved-schemes" element={<ProtectedRoute><SavedSchemes /></ProtectedRoute>} />
        <Route path="/activity" element={<ProtectedRoute><Activity /></ProtectedRoute>} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/admin/rag-candidates" element={<RagCandidates />} />
        <Route path="/admin/grievances" element={<AdminGrievances />} />
        <Route path="/admin/fraud" element={<AdminFraud />} />
        <Route path="/admin/analytics" element={<AdminAnalytics />} />
        <Route path="/admin/scheme-reports" element={<AdminSchemeReports />} />
      </Routes>
    </>
  );
}

export default App;
