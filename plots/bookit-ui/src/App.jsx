import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Houses from "./pages/Houses.jsx";
import MyBookings from "./pages/MyBookings.jsx";
import BookingCard from "./pages/BookingCard.jsx";

function Protected({ children }) {
  const { username } = useAuth();
  return username ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <>
      <nav className="nav">
        <div>
          <Link to="/dashboard" className="brand">Urban Nest</Link>
          {username && <Link to="/dashboard">Dashboard</Link>}
          {username && <Link to="/houses">Houses</Link>}
          {username && <Link to="/bookings">My bookings</Link>}
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
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/houses" element={<Protected><Houses /></Protected>} />
          <Route path="/bookings" element={<Protected><MyBookings /></Protected>} />
          <Route path="/bookings/:id" element={<Protected><BookingCard /></Protected>} />
        </Routes>
      </main>
    </>
  );
}
