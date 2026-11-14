import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.js";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/houses");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="card narrow" onSubmit={handleSubmit}>
      <h2>Log in</h2>
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button>Log in</button>
      {error && <p className="error">{error}</p>}
      <p>No account? <Link to="/register">Register</Link></p>
    </form>
  );
}
