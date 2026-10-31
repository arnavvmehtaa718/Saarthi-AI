"use client";

import React from "react";
import GlassCard from "../ui/GlassCard";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { TrendingUp, Award, Clock, FileText, CheckCircle2 } from "lucide-react";
import { t, Language } from "../../lib/translations";

interface AnalyticsData {
  unlocked_benefit_amount: number;
  estimated_benefit_amount?: number;
  benefit_estimate_note?: string;
  schemes_discovered_count: number;
  schemes_evaluated_count?: number;
  status_breakdown?: Record<string, number>;
  benefit_breakdown?: Array<{ name: string; value: number }>;
  pending_documents_count: number;
  documents_count?: number;
  upcoming_deadlines_count: number;
  success_rate: number | null;
  applied_count?: number;
  approved_count?: number;
  alerts: Array<{
    type: string;
    severity: string;
    title: string;
    description: string;
  }>;
}

interface AnalyticsDashboardProps {
  data: AnalyticsData;
  language: Language;
}

export default function AnalyticsDashboard({ data, language }: AnalyticsDashboardProps) {
  // Format numbers for Indian currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(value);
  };

  const benefitAmount = data.estimated_benefit_amount ?? data.unlocked_benefit_amount;
  const chartData = (data.benefit_breakdown || []).filter((item) => item.value > 0);
  const statusBreakdown = data.status_breakdown || {};
  const statusRows = [
    { key: "Eligible", label: t("status_eligible", language), color: "text-emerald-400" },
    { key: "Potentially Eligible", label: t("status_potentially_eligible", language), color: "text-sky-400" },
    { key: "Insufficient Information", label: t("status_insufficient", language), color: "text-amber-400" },
    { key: "Not Eligible", label: t("status_not_eligible", language), color: "text-rose-400" },
  ];

  // Colors for columns
  const COLORS = ["#38bdf8", "#0284c7", "#10b981", "#fbbf24", "#f43f5e"];

  return (
    <div className="space-y-6">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Unlocked Benefits */}
        <GlassCard className="border-slate-800/85 flex items-center gap-4 py-4 px-5">
          <div className="p-3 rounded-lg bg-emerald-950/20 text-emerald-400">
            <TrendingUp className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block font-medium">{t("kpi_benefits", language)}</span>
            <span className="text-xl font-bold font-mono tracking-tight text-white">
              {formatCurrency(benefitAmount)}
            </span>
            <span className="text-[9px] text-slate-500 block leading-tight mt-0.5">
              {t("kpi_benefits_note", language)}
            </span>
          </div>
        </GlassCard>

        {/* Matching Schemes */}
        <GlassCard className="border-slate-800/85 flex items-center gap-4 py-4 px-5">
          <div className="p-3 rounded-lg bg-sky-950/20 text-sky-400">
            <Award className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block font-medium">{t("kpi_matches", language)}</span>
            <span className="text-xl font-bold tracking-tight text-white">
              {data.schemes_discovered_count} {t("kpi_schemes", language)}
            </span>
          </div>
        </GlassCard>

        {/* Pending Actions */}
        <GlassCard className="border-slate-800/85 flex items-center gap-4 py-4 px-5">
          <div className="p-3 rounded-lg bg-rose-950/20 text-rose-400">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block font-medium">{t("kpi_missing_docs", language)}</span>
            <span className="text-xl font-bold tracking-tight text-white">
              {data.pending_documents_count} {t("kpi_files", language)}
            </span>
          </div>
        </GlassCard>

        {/* Approvals Success Rate */}
        <GlassCard className="border-slate-800/85 flex items-center gap-4 py-4 px-5">
          <div className="p-3 rounded-lg bg-amber-950/20 text-amber-400">
            <Clock className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block font-medium">{t("kpi_milestones", language)}</span>
            <span className="text-xl font-bold tracking-tight text-white">
              {data.upcoming_deadlines_count} {t("kpi_deadlines", language)}
            </span>
          </div>
        </GlassCard>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Benefit distribution column chart */}
        <GlassCard className="lg:col-span-2 border-sky-950/20">
          <h3 className="text-sm font-semibold mb-4 text-slate-300">{t("chart_title", language)}</h3>
          <div className="h-56 w-full">
            {chartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                {t("chart_empty", language)}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#94a3b8", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(val) => `₹${val / 1000}k`}
                    tick={{ fill: "#94a3b8", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(value) => [formatCurrency(Number(value)), t("chart_benefit_amount", language)]}
                    cursor={{ fill: "rgba(255, 255, 255, 0.06)" }}
                    contentStyle={{
                      backgroundColor: "#000000",
                      borderRadius: "8px",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      color: "#ffffff",
                      fontSize: "12px",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.5)"
                    }}
                    labelStyle={{
                      color: "#ffffff",
                      fontWeight: 600,
                      marginBottom: "4px"
                    }}
                    itemStyle={{
                      color: "#ffffff"
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="mt-3 pt-3 border-t border-slate-800/80">
            <h4 className="text-[11px] font-semibold text-slate-400 mb-2">
              {t("status_breakdown_title", language)}
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {statusRows.map((row) => (
                <div key={row.key} className="rounded-md border border-slate-800 bg-slate-900/40 px-2.5 py-2">
                  <span className={`text-base font-bold font-mono ${row.color}`}>
                    {statusBreakdown[row.key] ?? 0}
                  </span>
                  <span className="text-[9px] text-slate-400 block leading-tight">{row.label}</span>
                </div>
              ))}
            </div>
          </div>
        </GlassCard>

        {/* Active Reminders & Alerts */}
        <GlassCard className="border-sky-950/20">
          <h3 className="text-sm font-semibold mb-4 text-slate-300">{t("alerts_title", language)}</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            {data.alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <CheckCircle2 className="h-8 w-8 text-emerald-500 mb-1 opacity-80" />
                <p className="text-[11px] font-medium text-emerald-500">{t("alerts_clear", language)}</p>
              </div>
            ) : (
              data.alerts.map((alert, index) => (
                <div
                  key={index}
                  className="flex gap-2.5 p-3 rounded-lg border bg-slate-900/40 text-xs border-border"
                >
                  <div className="shrink-0 text-amber-500 mt-0.5">
                    <Clock className="h-4 w-4" />
                  </div>
                  <div className="space-y-0.5">
                    <h4 className="font-semibold text-slate-200">{alert.title}</h4>
                    <p className="text-slate-400 text-[10px] leading-relaxed">{alert.description}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
