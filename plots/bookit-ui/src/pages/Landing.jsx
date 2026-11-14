import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth.js";

const features = [
  { icon: "ðŸ“…", title: "Search by date", text: "Pick your check-in and check-out dates and see only the houses that are free. No more guessing or phoning around." },
  { icon: "ðŸ’°", title: "Clear prices", text: "The total is worked out for you from the nightly price and the number of nights, so there are no surprises." },
  { icon: "ðŸ“²", title: "Pay with M-Pesa", text: "Pay straight from your phone with an M-Pesa prompt, and get a receipt as soon as the payment is confirmed." },
  { icon: "ðŸ—“ï¸", title: "Staying longer? Pay monthly", text: "Stays over 30 nights get a payment card split into 30-day periods, so you pay month by month instead of all at once." },
  { icon: "ðŸ”’", title: "Your bookings stay yours", text: "Every booking is tied to your account. Only you can see, pay for or cancel your own bookings." },
  { icon: "ðŸ“¢", title: "Updates from the owner", text: "Important notices appear on your dashboard when you log in, so you never miss news about your stay." },
];

const steps = [
  { title: "Create an account", text: "Register with your email in under a minute." },
  { title: "Find and book a house", text: "Search your dates, pick a free house and confirm the booking." },
  { title: "Pay with M-Pesa", text: "Enter your phone number, approve the prompt, and you're done." },
];

export default function Landing() {
  const { username } = useAuth();

  // Logged-in users skip the advert and go straight to their dashboard.
  if (username) return <Navigate to="/dashboard" replace />;

  return (
    <div>
      {/* Hero */}
      <section className="rounded-3xl bg-[linear-gradient(135deg,#151a2d_0%,#3730a3_60%,#4f46e5_100%)] px-6 py-16 text-center text-white shadow-xl sm:px-10 sm:py-20">
        <span className="mb-5 inline-block rounded-full bg-white/15 px-4 py-1.5 text-sm font-semibold">
          House booking made simple
        </span>
        <h1 className="mb-4 text-4xl font-bold leading-tight sm:text-5xl">
          Find a free house.<br />Book it in minutes.
        </h1>
        <p className="mx-auto mb-8 max-w-xl text-lg text-indigo-100">
          Urban Nest shows apartments that are free on your dates, works out the price for you,
          and lets you pay with M-Pesa. Staying longer than a month? Pay month by month.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link to="/register" className="inline-block rounded-xl bg-white px-7 py-3 font-bold text-indigo-800 hover:bg-indigo-50 hover:no-underline">
            Get started free
          </Link>
          <Link to="/login" className="inline-block rounded-xl border-2 border-white/70 px-7 py-3 font-bold text-white hover:bg-white/10 hover:no-underline">
            Log in
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="mt-14">
        <h2 className="mb-1 text-center text-3xl font-bold">Everything you need to book a stay</h2>
        <p className="mb-7 text-center text-slate-500">From searching to paying, in one place.</p>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <div className="mb-2 text-3xl">{f.icon}</div>
              <h3 className="mb-1 text-lg font-bold">{f.title}</h3>
              <p className="text-slate-600">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mt-14">
        <h2 className="mb-1 text-center text-3xl font-bold">How it works</h2>
        <p className="mb-7 text-center text-slate-500">Three steps from sign-up to keys in hand.</p>
        <div className="grid gap-5 md:grid-cols-3">
          {steps.map((s, i) => (
            <div key={s.title} className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
              <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-indigo-600 font-bold text-white">
                {i + 1}
              </div>
              <h3 className="mb-1 text-lg font-bold">{s.title}</h3>
              <p className="text-slate-600">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final call to action */}
      <section className="mt-14 rounded-3xl border border-slate-200 bg-white px-6 py-12 text-center shadow-sm">
        <h2 className="mb-1 text-3xl font-bold">Ready to find your next stay?</h2>
        <p className="mb-6 text-slate-500">Create a free account and start searching today.</p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link to="/register" className="inline-block rounded-xl bg-indigo-600 px-7 py-3 font-bold text-white hover:bg-indigo-700 hover:no-underline">
            Create an account
          </Link>
          <Link to="/login" className="inline-block rounded-xl border-2 border-indigo-600 px-7 py-3 font-bold text-indigo-600 hover:bg-indigo-50 hover:no-underline">
            I already have an account
          </Link>
        </div>
      </section>

      <p className="my-10 text-center text-sm text-slate-500">© Urban Nest · Built with Django and React</p>
    </div>
  );
}

