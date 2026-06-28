"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ShieldCheck, UserCheck, Key, Eye, HelpCircle, ArrowRight, UserPlus } from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();
  
  // States
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto redirect if token already exists
  useEffect(() => {
    const token = localStorage.getItem("saarthi_token");
    if (token) {
      router.push("/dashboard");
    }
  }, [router]);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const endpoint = isRegistering ? "signup" : "token";
    const body = isRegistering 
      ? JSON.stringify({ email, password })
      : new URLSearchParams({ username: email, password: password }).toString();
      
    const headers: Record<string, string> = {
      "Content-Type": isRegistering ? "application/json" : "application/x-www-form-urlencoded"
    };

    try {
      const response = await fetch(`http://127.0.0.1:8000/auth/${endpoint}`, {
        method: "POST",
        headers,
        body
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Authentication failed");
      }

      const data = await response.json();
      localStorage.setItem("saarthi_token", data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to authenticate.");
    } finally {
      setLoading(false);
    }
  };

  const handleGuestAccess = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("http://127.0.0.1:8000/auth/guest", {
        method: "POST"
      });
      
      if (!response.ok) {
        throw new Error("Failed to create guest account.");
      }
      
      const data = await response.json();
      localStorage.setItem("saarthi_token", data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Guest initialization failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen relative flex items-center justify-center bg-[#070b13] text-slate-100 overflow-hidden font-sans px-4 py-8">
      {/* Background Gradient Mesh */}
      <div className="absolute top-[-20%] left-[-20%] w-[70%] h-[70%] bg-sky-950/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-emerald-950/15 blur-[100px] rounded-full pointer-events-none" />

      {/* Main Container */}
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 bg-slate-900/50 backdrop-blur-md rounded-2xl border border-slate-800 shadow-2xl overflow-hidden z-10">
        
        {/* Branding Sidebar */}
        <div className="p-8 lg:p-12 bg-gradient-to-br from-sky-900/40 via-slate-900 to-slate-950 flex flex-col justify-between border-b md:border-b-0 md:border-r border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent">
                Saarthi AI
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight leading-tight mb-4">
              Government Benefits, Simplified.
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Saarthi AI is an autonomous, multi-agent digital caseworker designed to help citizens discover, check eligibility for, and apply to central and state welfare benefits.
            </p>
          </div>

          <div className="hidden md:block pt-8 border-t border-slate-800/60 space-y-4">
            <div className="flex gap-3 text-xs text-slate-400">
              <UserCheck className="h-4.5 w-4.5 text-emerald-400 shrink-0" />
              <div>
                <span className="font-semibold text-slate-300 block">Caseworker Intelligence</span>
                Checks eligibility metrics and explains decisions simply.
              </div>
            </div>
            <div className="flex gap-3 text-xs text-slate-400">
              <Key className="h-4.5 w-4.5 text-sky-400 shrink-0" />
              <div>
                <span className="font-semibold text-slate-300 block">Secure Document Vault</span>
                OCR scans classify and extract expiry alerts locally.
              </div>
            </div>
          </div>
        </div>

        {/* Action Panel */}
        <div className="p-8 lg:p-12 flex flex-col justify-center bg-slate-900/30">
          <div className="mb-6">
            <h2 className="text-lg font-bold tracking-tight text-white mb-1">
              {isRegistering ? "Create Citizen Account" : "Caseworker Access"}
            </h2>
            <p className="text-xs text-slate-400">
              {isRegistering ? "Get started to save your profile and vault files." : "Sign in to access your digital navigator portal."}
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg border bg-rose-500/10 border-rose-500/30 text-rose-400 text-xs font-semibold">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleAuthSubmit} className="space-y-4 text-sm">
            <div>
              <label className="text-xs text-slate-400 block mb-1 font-medium">Email Address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="citizen@saarthi.ai"
                className="w-full bg-slate-950/60 border border-slate-800 rounded-md px-3.5 py-2.5 outline-none focus:ring-1 focus:ring-sky-500 text-slate-200 transition-all font-mono"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1 font-medium">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950/60 border border-slate-800 rounded-md pl-3.5 pr-10 py-2.5 outline-none focus:ring-1 focus:ring-sky-500 text-slate-200 transition-all font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-slate-400 hover:text-white"
                >
                  <Eye className="h-4 w-4" />
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-1 py-2.5 bg-sky-500 hover:bg-sky-600 disabled:bg-sky-400 text-white rounded-md font-semibold cursor-pointer shadow-md transition-colors"
            >
              <span>{loading ? "Authenticating..." : isRegistering ? "Register Account" : "Access Caseworker"}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          {/* Toggle Register/Login */}
          <div className="mt-4 text-center text-xs">
            <button
              onClick={() => setIsRegistering(!isRegistering)}
              className="text-sky-400 hover:text-sky-300 font-medium underline"
            >
              {isRegistering ? "Already have an account? Sign In" : "First time citizen? Create an Account"}
            </button>
          </div>

          {/* Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-slate-800/80" />
            </div>
            <span className="relative bg-[#0b0f19] px-3 text-slate-500 text-[10px] uppercase font-bold tracking-wider">
              Or Interactive Demo
            </span>
          </div>

          {/* Guest Login */}
          <button
            onClick={handleGuestAccess}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-800 text-slate-200 border border-slate-700/50 rounded-md font-semibold cursor-pointer shadow-sm transition-colors"
          >
            <UserPlus className="h-4 w-4 text-emerald-400" />
            <span>Launch Quick Guest Mode</span>
          </button>
        </div>
      </div>
    </main>
  );
}
