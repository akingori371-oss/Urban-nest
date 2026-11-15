import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth.js";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await register(username, email, password);
      navigate(params.get("next") || "/houses", { replace: true });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="mx-auto my-8 flex w-full max-w-md flex-col gap-5 rounded-[1.75rem] border border-line bg-white p-7 shadow-soft sm:my-14 sm:p-10" onSubmit={handleSubmit}>
      <div><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">YOUR NEXT STAY STARTS HERE</p><h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">Create an account</h1><p className="mt-2 text-sm text-muted">A few details, then you’re ready to explore.</p></div>
      <label className="grid gap-2 text-sm font-medium text-ink">Username<input className="rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" placeholder="Your name" value={username} onChange={(e) => setUsername(e.target.value)} required /></label>
      <label className="grid gap-2 text-sm font-medium text-ink">Email<input className="rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label className="grid gap-2 text-sm font-medium text-ink">Password<input className="rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="password" placeholder="Create a password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      <button className="rounded-xl bg-nest-800 px-5 py-3.5 font-semibold text-white transition hover:bg-nest-900 active:scale-[.99]">Create account</button>
      {error && <p className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <p className="text-center text-sm text-muted">Already registered? <Link className="font-semibold text-nest-700 hover:text-nest-900" to="/login">Log in</Link></p>
    </form>
  );
}
