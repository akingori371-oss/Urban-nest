import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.js";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await register(username, email, password);
      navigate("/houses");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="card narrow" onSubmit={handleSubmit}>
      <h2>Create an account</h2>
      <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button>Register</button>
      {error && <p className="error">{error}</p>}
      <p>Already registered? <Link to="/login">Log in</Link></p>
    </form>
  );
}
