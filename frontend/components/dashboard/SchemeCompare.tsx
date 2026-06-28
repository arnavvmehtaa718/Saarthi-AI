"use client";

import React from "react";
import GlassCard from "../ui/GlassCard";
import { Check, X, Scale, FileText, Clock, ShieldAlert } from "lucide-react";

interface CompareSchemeData {
  id: number;
  title: string;
  benefits: string;
  benefit_type: string;
  eligibility_status: string;
  eligibility_score: number;
  eligibility_explanation: string;
  documents: string[];
  complexity: string;
  timeline_days: number;
  application_steps: string[];
}

interface SchemeCompareProps {
  schemes: CompareSchemeData[];
  onRemove: (id: number) => void;
  onClose: () => void;
}

export default function SchemeCompare({ schemes, onRemove, onClose }: SchemeCompareProps) {
  if (schemes.length === 0) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
      <div className="relative w-full max-w-6xl max-h-[85vh] overflow-hidden flex flex-col bg-slate-900 border border-slate-800 rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-sky-400" />
            <h3 className="text-lg font-bold text-white">Compare Schemes ({schemes.length})</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-md hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-x-auto p-6 scrollbar-thin">
          <table className="w-full text-left text-sm text-slate-300 border-collapse">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="py-3 px-4 font-semibold text-slate-400 w-48">Feature</th>
                {schemes.map((s) => (
                  <th key={s.id} className="py-3 px-4 font-semibold text-white min-w-[250px] relative">
                    <div className="flex justify-between items-start gap-4">
                      <span>{s.title}</span>
                      <button
                        onClick={() => onRemove(s.id)}
                        className="text-xs text-rose-400 hover:text-rose-300 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Status */}
              <tr className="border-b border-slate-800 hover:bg-slate-800/20">
                <td className="py-4 px-4 font-medium text-slate-400">Eligibility Status</td>
                {schemes.map((s) => (
                  <td key={s.id} className="py-4 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                        s.eligibility_status === "Eligible"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : s.eligibility_status === "Likely Eligible"
                          ? "bg-sky-500/10 text-sky-400"
                          : s.eligibility_status === "Missing Information"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-rose-500/10 text-rose-400"
                      }`}
                    >
                      {s.eligibility_status} ({s.eligibility_score.toFixed(0)}%)
                    </span>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-3">{s.eligibility_explanation}</p>
                  </td>
                ))}
              </tr>

              {/* Benefits */}
              <tr className="border-b border-slate-800 hover:bg-slate-800/20">
                <td className="py-4 px-4 font-medium text-slate-400">Benefit Structure</td>
                {schemes.map((s) => (
                  <td key={s.id} className="py-4 px-4 text-xs font-medium text-slate-200">
                    <div className="bg-slate-800/40 border border-slate-700/50 p-2.5 rounded-lg">
                      <span className="text-sky-400 text-[10px] uppercase font-bold tracking-wider mb-1 block">
                        {s.benefit_type}
                      </span>
                      {s.benefits}
                    </div>
                  </td>
                ))}
              </tr>

              {/* Documents */}
              <tr className="border-b border-slate-800 hover:bg-slate-800/20">
                <td className="py-4 px-4 font-medium text-slate-400">Required Documents</td>
                {schemes.map((s) => (
                  <td key={s.id} className="py-4 px-4 text-xs">
                    <ul className="space-y-1.5">
                      {s.documents.map((doc, idx) => (
                        <li key={idx} className="flex items-center gap-1.5 text-slate-300">
                          <FileText className="h-3.5 w-3.5 text-slate-400" />
                          <span>{doc.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                ))}
              </tr>

              {/* Complexity */}
              <tr className="border-b border-slate-800 hover:bg-slate-800/20">
                <td className="py-4 px-4 font-medium text-slate-400">Application Difficulty</td>
                {schemes.map((s) => (
                  <td key={s.id} className="py-4 px-4">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        s.complexity === "Low"
                          ? "bg-green-500/10 text-green-400"
                          : s.complexity === "Medium"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-rose-500/10 text-rose-400"
                      }`}
                    >
                      {s.complexity}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Timeline */}
              <tr className="border-b border-slate-800 hover:bg-slate-800/20">
                <td className="py-4 px-4 font-medium text-slate-400">Estimated Process</td>
                {schemes.map((s) => (
                  <td key={s.id} className="py-4 px-4 text-xs font-medium text-slate-200">
                    <div className="flex items-center gap-1 text-slate-400 mb-1">
                      <Clock className="h-3.5 w-3.5" />
                      <span>~{s.timeline_days} days to approval</span>
                    </div>
                  </td>
                ))}
              </tr>

              {/* Application steps */}
              <tr className="hover:bg-slate-800/20">
                <td className="py-4 px-4 font-medium text-slate-400">Core Actions Required</td>
                {schemes.map((s) => (
                  <td key={s.id} className="py-4 px-4 text-xs">
                    <ol className="list-decimal pl-4 space-y-1 text-slate-400">
                      {s.application_steps.slice(0, 3).map((step, idx) => (
                        <li key={idx} className="line-clamp-2">{step}</li>
                      ))}
                      {s.application_steps.length > 3 && <li>And {s.application_steps.length - 3} more steps...</li>}
                    </ol>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="flex justify-end p-4 border-t border-slate-800 bg-slate-900/80">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors"
          >
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
}
