"use client";

import React from "react";
import GlassCard from "../ui/GlassCard";
import { UserCheck, Sliders, MapPin, IndianRupee, HelpCircle } from "lucide-react";
import { t, Language } from "../../lib/translations";

export interface ProfileData {
  state: string;
  age: number;
  annual_income: number;
  occupation: string;
  category: string;
  is_student: boolean;
  owns_land: boolean;
  land_area_hectares: number;
  is_disabled: boolean;
  disability_percentage: number;
}

interface ProfileSimulatorProps {
  profile: ProfileData;
  onProfileChange: (updated: ProfileData) => void;
  language: Language;
}

export default function ProfileSimulator({ profile, onProfileChange, language }: ProfileSimulatorProps) {
  const handleChange = (key: keyof ProfileData, value: any) => {
    const updated = { ...profile, [key]: value };
    
    // Automatically toggle flags depending on fields
    if (key === "occupation" && value === "Student") {
      updated.is_student = true;
    }
    if (key === "is_disabled" && value === false) {
      updated.disability_percentage = 0;
    }
    if (key === "owns_land" && value === false) {
      updated.land_area_hectares = 0;
    }
    
    onProfileChange(updated);
  };

  // State options — values are always English (sent to backend), labels are translated
  const states = [
    { value: "All", labelKey: "state_all" as const },
    { value: "Uttar Pradesh", labelKey: "state_up" as const },
    { value: "Bihar", labelKey: "state_bihar" as const },
    { value: "Maharashtra", labelKey: "state_maha" as const },
    { value: "Karnataka", labelKey: "state_karnataka" as const },
    { value: "Madhya Pradesh", labelKey: "state_mp" as const },
    { value: "Rajasthan", labelKey: "state_raj" as const },
    { value: "Gujarat", labelKey: "state_guj" as const },
    { value: "Delhi", labelKey: "state_delhi" as const },
  ];
  
  const occupations = [
    { value: "Unemployed", labelKey: "occ_unemployed" as const },
    { value: "Farmer", labelKey: "occ_farmer" as const },
    { value: "Student", labelKey: "occ_student" as const },
    { value: "Artisan", labelKey: "occ_artisan" as const },
    { value: "Business Owner", labelKey: "occ_business" as const },
    { value: "Street Vendor", labelKey: "occ_vendor" as const },
    { value: "Salaried", labelKey: "occ_salaried" as const },
  ];
  
  const categories = [
    { value: "General", labelKey: "cat_general" as const },
    { value: "OBC", labelKey: "cat_obc" as const },
    { value: "SC", labelKey: "cat_sc" as const },
    { value: "ST", labelKey: "cat_st" as const },
    { value: "EWS", labelKey: "cat_ews" as const },
  ];

  return (
    <GlassCard className="h-full border-sky-950/20">
      <div className="flex items-center gap-2 mb-4 border-b border-border pb-3">
        <Sliders className="h-5 w-5 text-sky-500" />
        <h2 className="text-lg font-bold tracking-tight">{t("simulator_title", language)}</h2>
      </div>

      <div className="space-y-4 text-sm">
        {/* State Selection */}
        <div>
          <label className="flex items-center gap-1.5 font-medium text-slate-300 mb-1">
            <MapPin className="h-4 w-4 text-sky-500" />
            {t("sim_state", language)}
          </label>
          <select
            value={profile.state}
            onChange={(e) => handleChange("state", e.target.value)}
            className="w-full bg-slate-900 border border-border rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-sky-500 transition-all text-slate-200"
          >
            {states.map((s) => (
              <option key={s.value} value={s.value}>{t(s.labelKey, language)}</option>
            ))}
          </select>
        </div>

        {/* Age Slider */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="font-medium text-slate-300">{t("sim_age", language)} ({profile.age} {t("sim_years", language)})</label>
          </div>
          <input
            type="range"
            min="5"
            max="90"
            value={profile.age}
            onChange={(e) => handleChange("age", parseInt(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>

        {/* Annual Income Input */}
        <div>
          <label className="flex items-center gap-1.5 font-medium text-slate-300 mb-1">
            <IndianRupee className="h-4 w-4 text-sky-500" />
            {t("sim_income", language)}
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              step="5000"
              value={profile.annual_income}
              onChange={(e) => handleChange("annual_income", parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-900 border border-border rounded-md pl-8 pr-3 py-2 outline-none focus:ring-1 focus:ring-sky-500 transition-all font-mono text-slate-200"
            />
            <span className="absolute left-3 top-2.5 text-slate-400">₹</span>
          </div>
          <span className="text-xs text-slate-400 mt-1 block">
            ₹{(profile.annual_income / 100000).toFixed(2)} {t("sim_income_lakh", language)}
          </span>
        </div>

        {/* Occupation Select */}
        <div>
          <label className="font-medium text-slate-300 mb-1 block">{t("sim_occupation", language)}</label>
          <select
            value={profile.occupation}
            onChange={(e) => handleChange("occupation", e.target.value)}
            className="w-full bg-slate-900 border border-border rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-sky-500 transition-all text-slate-200"
          >
            {occupations.map((o) => (
              <option key={o.value} value={o.value}>{t(o.labelKey, language)}</option>
            ))}
          </select>
        </div>

        {/* Social Category Select */}
        <div>
          <label className="font-medium text-slate-300 mb-1 block">{t("sim_category", language)}</label>
          <select
            value={profile.category}
            onChange={(e) => handleChange("category", e.target.value)}
            className="w-full bg-slate-900 border border-border rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-sky-500 transition-all text-slate-200"
          >
            {categories.map((c) => (
              <option key={c.value} value={c.value}>{t(c.labelKey, language)}</option>
            ))}
          </select>
        </div>

        {/* Switches / Checkboxes */}
        <div className="pt-2 border-t border-border space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-300">{t("sim_student", language)}</span>
            <input
              type="checkbox"
              checked={profile.is_student}
              onChange={(e) => handleChange("is_student", e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-sky-500 focus:ring-sky-500 accent-sky-500"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-300">{t("sim_land", language)}</span>
              <input
                type="checkbox"
                checked={profile.owns_land}
                onChange={(e) => handleChange("owns_land", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-sky-500 focus:ring-sky-500 accent-sky-500"
              />
            </div>
            {profile.owns_land && (
              <div className="pl-4">
                <label className="text-xs text-slate-400 block mb-0.5">{t("sim_land_area", language)}</label>
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={profile.land_area_hectares}
                  onChange={(e) => handleChange("land_area_hectares", parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-border rounded-md px-2 py-1 outline-none text-xs focus:ring-1 focus:ring-sky-500 text-slate-200"
                />
              </div>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-300">{t("sim_disabled", language)}</span>
              <input
                type="checkbox"
                checked={profile.is_disabled}
                onChange={(e) => handleChange("is_disabled", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-sky-500 focus:ring-sky-500 accent-sky-500"
              />
            </div>
            {profile.is_disabled && (
              <div className="pl-4">
                <label className="text-xs text-slate-400 block mb-0.5">{t("sim_disability_pct", language)}</label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="5"
                  value={profile.disability_percentage}
                  onChange={(e) => handleChange("disability_percentage", parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-800 cursor-pointer accent-sky-500"
                />
                <span className="text-xs text-slate-400 block mt-1">{profile.disability_percentage}% {t("sim_severity", language)}</span>
              </div>
            )}
          </div>
        </div>

        <div className="pt-2 flex justify-end text-xs text-slate-400 gap-1 items-center">
          <UserCheck className="h-3 w-3 text-emerald-500" />
          <span>{t("updates_instant", language)}</span>
        </div>
      </div>
    </GlassCard>
  );
}
