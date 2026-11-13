import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { useAuth } from "../AuthContext.jsx";

export default function Dashboard() {
  const { username } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      const res = await api("/dashboard/");
      const body = await res.json();
      if (res.ok) setData(body);
      else setError(errorText(body));
    }
    load();
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading...</p>;

  return (
    <div>
      <h2>Hello, {username}</h2>

      {data.payments_due > 0 && (
        <div className="card">
          <p>
            You have <strong>{data.payments_due}</strong> payment
            {data.payments_due === 1 ? "" : "s"} due on your payment cards.{" "}
            <Link to="/bookings">View my bookings</Link>
          </p>
        </div>
      )}

      <h3>Announcements</h3>
      <div className="grid">
        {data.announcements.map((a, i) => (
          <div className="card" key={i}>
            <h4>{a.title}</h4>
            <p>{a.message}</p>
            <small>{new Date(a.created_at).toLocaleString()}</small>
          </div>
        ))}
        {data.announcements.length === 0 && <p>No announcements right now.</p>}
      </div>

      <p>
        <Link to="/houses">Find a house</Link> · <Link to="/bookings">My bookings</Link>
      </p>
    </div>
  );
}