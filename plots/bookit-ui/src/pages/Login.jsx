
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth.js";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const user = await login(email, password);

      navigate(
        params.get("next") || (user.is_manager ? "/manager" : "/houses"),
        { replace: true }
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form
      className="mx-auto my-8 flex w-full max-w-md flex-col gap-5 rounded-[1.75rem] border border-line bg-white p-7 shadow-soft sm:my-14 sm:p-10"
      onSubmit={handleSubmit}
    >
      <div>
        <p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">
          WELCOME BACK
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
          Log in
        </h1>
        <p className="mt-2 text-sm text-muted">
          Pick up where you left off.
        </p>
      </div>

      <label className="grid gap-2 text-sm font-medium text-ink">
        Email
        <input
          className="rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isLoading}
        />
      </label>

      <label className="grid gap-2 text-sm font-medium text-ink">
        Password
        <input
          className="rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100"
          type="password"
          placeholder="Your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={isLoading}
        />
      </label>

      <Link
        className="-mt-3 self-end text-sm font-semibold text-nest-700 hover:text-nest-900"
        to="/forgot-password"
      >
        Forgot password?
      </Link>

      <button
        type="submit"
        disabled={isLoading}
        aria-busy={isLoading}
        className={`login-button relative overflow-hidden rounded-xl px-5 py-3.5 font-semibold text-white transition active:scale-[.99] disabled:cursor-not-allowed ${
          isLoading
            ? "login-button-loading"
            : "bg-nest-800 hover:bg-nest-900"
        }`}
      >
        {isLoading && <span className="login-sweep" />}

        <span className="relative z-10">
          {isLoading ? "Signing in..." : "Log in"}
        </span>
      </button>

      {error && (
        <p className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <p className="text-center text-sm text-muted">
        New to Urban Nest?{" "}
        <Link
          className="font-semibold text-nest-700 hover:text-nest-900"
          to="/register"
        >
          Create an account
        </Link>
      </p>
    </form>
  );
}