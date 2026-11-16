import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorText } from "../Api.js";

const fieldClass = "rounded-xl border border-line bg-nest-50/50 px-4 py-3 text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100";
const buttonClass = "rounded-xl bg-nest-800 px-5 py-3.5 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-60";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState("email");
  const [cooldown, setCooldown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  async function requestCode(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const response = await api("/auth/password-reset/request/", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ email }),
      });
      if (!response.ok) throw new Error(errorText(response.data));
      setStep("otp");
      setCooldown(60);
      setMessage("If an account exists for that email, a verification code has been sent.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function verifyCode(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const response = await api("/auth/password-reset/verify/", {
        method: "POST",
        auth: false,
        credentials: "include",
        body: JSON.stringify({ email, otp }),
      });
      if (!response.ok) throw new Error(errorText(response.data));
      navigate("/reset-password", { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function resendCode() {
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const response = await api("/auth/password-reset/request/", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ email }),
      });
      if (!response.ok) throw new Error(errorText(response.data));
      setCooldown(60);
      setMessage("If an account exists for that email, a verification code has been sent.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto my-8 w-full max-w-md rounded-[1.75rem] border border-line bg-white p-7 shadow-soft sm:my-14 sm:p-10">
      <p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">ACCOUNT RECOVERY</p>
      {step === "email" ? (
        <form className="mt-3 flex flex-col gap-5" onSubmit={requestCode}>
          <div><h1 className="text-3xl font-semibold tracking-tight text-ink">Forgot password?</h1><p className="mt-2 text-sm text-muted">Enter your email and we’ll send a verification code if an account matches.</p></div>
          <label className="grid gap-2 text-sm font-medium text-ink">Email<input className={fieldClass} type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <button className={buttonClass} disabled={loading}>{loading ? "Sending…" : "Send verification code"}</button>
        </form>
      ) : (
        <form className="mt-3 flex flex-col gap-5" onSubmit={verifyCode}>
          <div><h1 className="text-3xl font-semibold tracking-tight text-ink">Check your email</h1><p className="mt-2 text-sm text-muted">Enter the six-digit code sent to {email}.</p></div>
          <label className="grid gap-2 text-sm font-medium text-ink">Six-digit code<input className={`${fieldClass} text-center text-xl tracking-[.35em]`} type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} placeholder="000000" value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))} required /></label>
          <button className={buttonClass} disabled={loading || otp.length !== 6}>{loading ? "Verifying…" : "Verify code"}</button>
          <button className="text-sm font-semibold text-nest-700 hover:text-nest-900 disabled:cursor-not-allowed disabled:text-muted" type="button" onClick={resendCode} disabled={loading || cooldown > 0}>{cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}</button>
        </form>
      )}
      {message && <p className="mt-4 rounded-xl border border-nest-100 bg-nest-50 px-4 py-3 text-sm text-nest-800" role="status" aria-live="polite">{message}</p>}
      {error && <p className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</p>}
      <p className="mt-6 text-center text-sm text-muted"><Link className="font-semibold text-nest-700 hover:text-nest-900" to="/login">Back to login</Link></p>
    </section>
  );
}
