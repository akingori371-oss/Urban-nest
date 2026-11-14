import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./auth.js";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Houses from "./pages/Houses.jsx";
import HouseDetail from "./pages/HouseDetail.jsx";
import MyBookings from "./pages/MyBookings.jsx";
import Landing from "./pages/Landing.jsx";
import BookingCard from "./pages/BookingCard.jsx";
import ManagerArea, { InvitationAccept } from "./pages/Manager.jsx";

function Protected({ children }) {
  const { username, ready } = useAuth();
  if (!ready) return <p role="status">Loading your account...</p>;
  return username ? children : <Navigate to="/login" replace />;
}

function ManagerProtected() {
  const { username, isManager, ready } = useAuth();
  if (!ready) return <p role="status">Loading your account...</p>;
  if (!username) return <Navigate to="/login" replace />;
  return isManager ? <ManagerArea /> : <Navigate to="/dashboard" replace />;
}

export default function App() {
  const { username, isManager, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <>
      <nav className="nav">
        <div>
          <Link to="/dashboard" className="brand">Urban Nest</Link>
          {username && <Link to="/dashboard">Dashboard</Link>}
          {username && <Link to="/houses">Houses</Link>}
          {username && <Link to="/bookings">My bookings</Link>}
          {username && isManager && <Link to="/manager">Manager</Link>}
        </div>
        <div>
          {username ? (
            <>
              <span>{username}</span>
              <button onClick={() => { logout(); navigate("/login"); }}>Log out</button>
            </>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/register">Register</Link>
            </>
          )}
        </div>
      </nav>

      <main className="container">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/houses" element={<Protected><Houses /></Protected>} />
          <Route path="/houses/:id" element={<Protected><HouseDetail /></Protected>} />
          <Route path="/bookings" element={<Protected><MyBookings /></Protected>} />
          <Route path="/bookings/:id" element={<Protected><BookingCard /></Protected>} />
          <Route path="/manager/invitations/accept/:token" element={<InvitationAccept />} />
          <Route path="/manager/*" element={<ManagerProtected />} />
        </Routes>
      </main>
    </>
  );
}


