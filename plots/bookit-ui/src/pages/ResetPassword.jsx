import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../Api.js";

const fieldClass = "rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100";
const buttonClass = "rounded-xl bg-nest-800 px-5 py-3.5 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-60";

export default function ResetPassword() {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const response = await api("/auth/password-reset/complete/", {
        method: "POST",
        auth: false,
        credentials: "include",
        body: JSON.stringify({ password }),
      });
      if (!response.ok) throw new Error(errorText(response.data));
      setComplete(true);
      setPassword("");
      setConfirmation("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto my-8 w-full max-w-md rounded-[1.75rem] border border-line bg-white p-7 shadow-soft sm:my-14 sm:p-10">
      <p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">ACCOUNT RECOVERY</p>
      {complete ? (
        <div className="mt-3 flex flex-col gap-5">
          <div><h1 className="text-3xl font-semibold tracking-tight text-ink">Password updated</h1><p className="mt-2 text-sm text-muted" role="status">Your password has been changed. You can now log in with your new password.</p></div>
          <Link className={`${buttonClass} text-center`} to="/login">Back to login</Link>
        </div>
      ) : (
        <form className="mt-3 flex flex-col gap-5" onSubmit={handleSubmit}>
          <div><h1 className="text-3xl font-semibold tracking-tight text-ink">Set a new password</h1><p className="mt-2 text-sm text-muted">Choose a password that meets the account security requirements.</p></div>
          <label className="grid gap-2 text-sm font-medium text-ink">New password<span className="flex gap-2"><input className={`${fieldClass} min-w-0 flex-1`} type={showPassword ? "text" : "password"} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required /><button className="rounded-xl border border-line px-3 text-sm text-nest-700" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide new password" : "Show new password"}>{showPassword ? "Hide" : "Show"}</button></span></label>
          <label className="grid gap-2 text-sm font-medium text-ink">Confirm password<span className="flex gap-2"><input className={`${fieldClass} min-w-0 flex-1`} type={showConfirmation ? "text" : "password"} autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /><button className="rounded-xl border border-line px-3 text-sm text-nest-700" type="button" onClick={() => setShowConfirmation((value) => !value)} aria-label={showConfirmation ? "Hide password confirmation" : "Show password confirmation"}>{showConfirmation ? "Hide" : "Show"}</button></span></label>
          <button className={buttonClass} disabled={loading}>{loading ? "Updating…" : "Update password"}</button>
          {error && <p className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</p>}
        </form>
      )}
    </section>
  );
}
