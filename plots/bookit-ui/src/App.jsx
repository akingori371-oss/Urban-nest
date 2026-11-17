
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./auth.js";
import Login from "./pages/Login.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Houses from "./pages/Houses.jsx";
import HouseDetail from "./pages/HouseDetail.jsx";
import MyBookings from "./pages/MyBookings.jsx";
import Landing from "./pages/Landing.jsx";
import BookingCard from "./pages/BookingCard.jsx";
import Notifications from "./pages/Notifications.jsx";
import ManagerArea, { InvitationAccept } from "./pages/Manager.jsx";
import ListProperty from "./pages/ListProperty.jsx";
import MyProperties from "./pages/MyProperties.jsx";
import EditProperty from "./pages/EditProperty.jsx";

function Protected({ children }) {
  const { username, ready } = useAuth();

  if (!ready) {
    return (
      <p role="status" className="mx-auto max-w-7xl px-6 py-16 text-muted">
        Loading your account…
      </p>
    );
  }

  return username ? children : <Navigate to="/login" replace />;
}

function ManagerProtected() {
  const { username, isManager, ready } = useAuth();

  if (!ready) {
    return (
      <p role="status" className="mx-auto max-w-7xl px-6 py-16 text-muted">
        Loading your account…
      </p>
    );
  }

  if (!username) return <Navigate to="/login" replace />;

  return isManager ? <ManagerArea /> : <Navigate to="/dashboard" replace />;
}

export default function App() {
  const { username, isManager, logout } = useAuth();
  const navigate = useNavigate();

  const navLink =
    "rounded-full px-4 py-2 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white";

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-white/10 bg-nest-900/95 text-white shadow-lg shadow-nest-900/10 backdrop-blur-xl">
        <nav
          className="mx-auto flex min-h-[76px] max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8"
          aria-label="Main navigation"
        >
          <div className="flex flex-wrap items-center gap-1">
            <Link
              to={username ? "/dashboard" : "/"}
              className="mr-3 flex items-center gap-2 rounded-full px-1 py-1 text-lg font-bold tracking-tight text-white hover:text-white"
            >
              <span className="grid size-9 place-items-center rounded-xl bg-nest-200 text-sm font-black text-nest-900">
                U
              </span>
              Urban Nest
            </Link>

            {username && (
              <>
                <Link className={navLink} to="/dashboard">
                  Dashboard
                </Link>

                <Link className={navLink} to="/houses">
                  Homes
                </Link>

                <Link className={navLink} to="/bookings">
                  My stays
                </Link>

                <Link className={navLink} to="/my-properties">
                  My properties
                </Link>

                <Link className={navLink} to="/list-property">
                  List a property
                </Link>

                <Link className={navLink} to="/notifications">
                  Notifications
                </Link>

                {isManager && (
                  <Link className={navLink} to="/manager">
                    Manager
                  </Link>
                )}
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            {username ? (
              <>
                <span className="hidden pr-2 text-sm text-white/65 sm:inline">
                  {username}
                </span>

                <button
                  className="rounded-full border border-white/20 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/50 hover:bg-white/10"
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link className={navLink} to="/login">
                  Log in
                </Link>

                <Link
                  className="rounded-full bg-nest-200 px-4 py-2 text-sm font-bold text-nest-900 transition hover:bg-white"
                  to="/register"
                >
                  Create account
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      <main className="mx-auto min-h-[calc(100vh-76px)] w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/dashboard"
            element={
              <Protected>
                <Dashboard />
              </Protected>
            }
          />

          <Route
            path="/houses"
            element={
              <Protected>
                <Houses />
              </Protected>
            }
          />

          <Route
            path="/houses/:id"
            element={
              <Protected>
                <HouseDetail />
              </Protected>
            }
          />

          <Route
            path="/bookings"
            element={
              <Protected>
                <MyBookings />
              </Protected>
            }
          />

          <Route
            path="/bookings/:id"
            element={
              <Protected>
                <BookingCard />
              </Protected>
            }
          />

          <Route
            path="/my-properties"
            element={
              <Protected>
                <MyProperties />
              </Protected>
            }
          />

          <Route
            path="/list-property"
            element={
              <Protected>
                <ListProperty />
              </Protected>
            }
          />

          <Route
            path="/edit-property/:id"
            element={
              <Protected>
                <EditProperty />
              </Protected>
            }
          />

          <Route
            path="/notifications"
            element={
              <Protected>
                <Notifications />
              </Protected>
            }
          />

          <Route
            path="/manager/invitations/accept/:token"
            element={<InvitationAccept />}
          />

          <Route path="/manager/*" element={<ManagerProtected />} />
        </Routes>
      </main>
    </>
  );
}
