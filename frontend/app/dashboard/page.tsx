"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  ShieldCheck, LogOut, Award, CheckCircle2, AlertCircle, FileText, 
  HelpCircle, Sparkles, Send, RefreshCcw, Scale, ClipboardList, BookOpen,
  LayoutDashboard, MessageSquareCode, Compass, FolderClosed, BarChart4,
  Clock, AlertOctagon, HelpCircle as HelpIcon, BellRing
} from "lucide-react";
import GlassCard from "../../components/ui/GlassCard";
import ProfileSimulator, { ProfileData } from "../../components/dashboard/ProfileSimulator";
import DocumentVault, { VaultDocument } from "../../components/dashboard/DocumentVault";
import AccessibilityControls from "../../components/dashboard/AccessibilityControls";
import AnalyticsDashboard from "../../components/dashboard/AnalyticsDashboard";
import SchemeCompare from "../../components/dashboard/SchemeCompare";
import { t, Language } from "../../lib/translations";
import { API_BASE_URL } from "../../lib/config";

type ActiveTabType = "dashboard" | "agent" | "explorer" | "vault" | "compare" | "timeline";

export default function DashboardPage() {
  const router = useRouter();

  // Authentication check
  const [token, setToken] = useState<string | null>(null);

  // App Toggles
  const [language, setLanguage] = useState<Language>("en");
  const [eli15Mode, setEli15Mode] = useState<boolean>(false);
  const [voiceOutputActive, setVoiceOutputActive] = useState<boolean>(false);
  const [consumerId, setConsumerId] = useState<string>("");
  
  // Navigation State
  const [activeTab, setActiveTab] = useState<ActiveTabType>("dashboard");

  // Data States
  const [profile, setProfile] = useState<ProfileData>({
    state: "All",
    age: 25,
    annual_income: 150000,
    occupation: "Unemployed",
    category: "General",
    is_student: false,
    owns_land: false,
    land_area_hectares: 0,
    is_disabled: false,
    disability_percentage: 0
  });

  const [schemes, setSchemes] = useState<any[]>([]);
  const [vaultDocs, setVaultDocs] = useState<VaultDocument[]>([]);
  const [selectedScheme, setSelectedScheme] = useState<any | null>(null);
  const [analytics, setAnalytics] = useState<any>({
    unlocked_benefit_amount: 0,
    schemes_discovered_count: 0,
    pending_documents_count: 0,
    upcoming_deadlines_count: 0,
    success_rate: 85,
    alerts: [],
    timeline_events: []
  });

  // Compare schemes list
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [compareData, setCompareData] = useState<any[]>([]);
  const [showCompareModal, setShowCompareModal] = useState<boolean>(false);
  const [showSosModal, setShowSosModal] = useState<boolean>(false);

  // Chat States
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState<string>("");
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [agentLog, setAgentLog] = useState<string>(t("agent_idle", "en"));

  // Fetch initial token
  useEffect(() => {
    const savedToken = localStorage.getItem("saarthi_token");
    if (!savedToken) {
      router.push("/");
    } else {
      setToken(savedToken);
    }
  }, [router]);

  // Load and reload all data
  const loadAllData = async (activeToken: string, currentLang: string = language) => {
    try {
      const headers = { Authorization: `Bearer ${activeToken}` };

      // 1. Fetch Profile
      const profRes = await fetch(`${API_BASE_URL}/profile`, { headers });
      if (profRes.ok) {
        const profData = await profRes.json();
        setProfile(profData);
      }

      // Fetch Consumer ID
      try {
        const identityRes = await fetch(`${API_BASE_URL}/profile/me`, { headers });
        if (identityRes.ok) {
          const identityData = await identityRes.json();
          setConsumerId(identityData.consumer_id);
        }
      } catch (err) {
        console.error("Error fetching consumer identity:", err);
      }

      // 2. Fetch Vault Documents
      const docsRes = await fetch(`${API_BASE_URL}/vault`, { headers });
      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setVaultDocs(docsData);
      }

      // 3. Fetch Recommendations
      const recomRes = await fetch(`${API_BASE_URL}/schemes/recommendations?lang=${currentLang}`, { headers });
      if (recomRes.ok) {
        const recomData = await recomRes.json();
        setSchemes(recomData);
        if (recomData.length > 0 && !selectedScheme) {
          // Auto select first match
          loadSchemeDetail(recomData[0].id, activeToken, currentLang);
        }
      }

      // 4. Fetch Analytics
      const analyRes = await fetch(`${API_BASE_URL}/analytics`, { headers });
      if (analyRes.ok) {
        const analyData = await analyRes.json();
        setAnalytics(analyData);
      }

      // 5. Fetch Chat History
      const chatRes = await fetch(`${API_BASE_URL}/chat/history`, { headers });
      if (chatRes.ok) {
        const chatData = await chatRes.json();
        setChatMessages(chatData);
      }

    } catch (err) {
      console.error("Error loading dashboard data:", err);
    }
  };

  useEffect(() => {
    if (token) {
      loadAllData(token, language);
    }
  }, [token]);

  // Refresh schemes on language or ELI15 toggle
  useEffect(() => {
    if (token) {
      loadAllData(token, language);
      if (selectedScheme) {
        loadSchemeDetail(selectedScheme.id, token, language);
      }
    }
  }, [language, eli15Mode]);

  // Handle Profile Updates from Simulator
  const handleProfileChange = async (updated: ProfileData) => {
    setProfile(updated);
    if (!token) return;

    try {
      const headers = { 
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      };

      const res = await fetch(`${API_BASE_URL}/profile`, {
        method: "PUT",
        headers,
        body: JSON.stringify(updated)
      });

      if (res.ok) {
        // Trigger recommendation re-fetch
        const recomRes = await fetch(`${API_BASE_URL}/schemes/recommendations?lang=${language}`, { headers });
        if (recomRes.ok) {
          const recomData = await recomRes.json();
          setSchemes(recomData);
          
          // Re-evaluate selected scheme details if present
          if (selectedScheme) {
            loadSchemeDetail(selectedScheme.id, token, language);
          }
        }

        // Re-fetch analytics
        const analyRes = await fetch(`${API_BASE_URL}/analytics`, { headers });
        if (analyRes.ok) {
          const analyData = await analyRes.json();
          setAnalytics(analyData);
        }
      }
    } catch (err) {
      console.error("Failed to update profile simulator:", err);
    }
  };

  // Load specific scheme details for application guide
  const loadSchemeDetail = async (schemeId: number, activeToken: string, currentLang: string = language) => {
    try {
      const headers = { Authorization: `Bearer ${activeToken}` };
      const compRes = await fetch(`${API_BASE_URL}/schemes/compare?ids=${schemeId}&lang=${currentLang}`, { headers });
      if (compRes.ok) {
        const detail = await compRes.json();
        if (detail.length > 0) {
          setSelectedScheme(detail[0]);
        }
      }
    } catch (err) {
      console.error("Error loading scheme details:", err);
    }
  };

  // Save scheme to favorites or apply
  const handleSchemeAction = async (schemeId: number, status: "saved" | "applied") => {
    if (!token) return;
    try {
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      };

      const res = await fetch(`${API_BASE_URL}/schemes/status`, {
        method: "POST",
        headers,
        body: JSON.stringify({ scheme_id: schemeId, status })
      });

      if (res.ok) {
        await loadAllData(token);
        if (selectedScheme && selectedScheme.id === schemeId) {
          await loadSchemeDetail(schemeId, token);
        }
        if (status === "applied") {
          setActiveTab("timeline");
        }
        alert(status === "applied" 
          ? t("scheme_applied_msg", language)
          : t("scheme_saved_msg", language)
        );
      }
    } catch (err) {
      console.error("Failed to update scheme status:", err);
    }
  };

  // Upload Vault Document
  const handleDocUpload = async (file: File, category: string) => {
    if (!token) return;
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("category_override", category);

      const res = await fetch(`${API_BASE_URL}/vault/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Upload failed");
      }

      await loadAllData(token);
      if (selectedScheme) {
        loadSchemeDetail(selectedScheme.id, token);
      }
    } catch (err: any) {
      throw err;
    }
  };

  // Delete Vault Document
  const handleDocDelete = async (id: number) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/vault/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        await loadAllData(token, language);
        if (selectedScheme) {
          loadSchemeDetail(selectedScheme.id, token, language);
        }
      }
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  // Compare schemes logic
  const handleCompareCheckbox = (schemeId: number, checked: boolean) => {
    if (checked) {
      setCompareIds((cur) => [...cur, schemeId]);
    } else {
      setCompareIds((cur) => cur.filter((id) => id !== schemeId));
    }
  };

  const triggerComparison = async () => {
    if (compareIds.length === 0) return;
    if (!token) return;

    try {
      const idsQuery = compareIds.map((id) => `ids=${id}`).join("&");
      const res = await fetch(`${API_BASE_URL}/schemes/compare?${idsQuery}&lang=${language}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCompareData(data);
        setShowCompareModal(true);
      }
    } catch (err) {
      console.error("Comparison fetch failed:", err);
    }
  };

  // Send Chat message
  const handleSendChatMessage = async (msgText: string) => {
    if (!msgText.trim() || !token) return;
    
    setChatLoading(true);
    setChatInput("");
    
    // Add user message locally first
    const tempUserMsg = { id: Date.now(), role: "user", content: msgText };
    setChatMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await fetch(`${API_BASE_URL}/chat/message`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: msgText,
          language,
          eli15_mode: eli15Mode
        })
      });

      if (res.ok) {
        const data = await res.json();
        
        // Add assistant message and agent logging
        const tempAssistantMsg = { 
          id: Date.now() + 1, 
          role: "assistant", 
          content: data.assistant_reply,
          agent_name: "Caseworker Orchestrator"
        };
        setChatMessages((prev) => [...prev, tempAssistantMsg]);
        setAgentLog(data.agent_collaboration_log || t("agent_idle", language));
        
        // Speak out the assistant reply if voice output is active
        if (voiceOutputActive) {
          speakAloud(data.assistant_reply);
        }

        // Auto reload profile simulator & schemes matches if agents altered them
        if (data.profile) {
          setProfile(data.profile);
        }
        if (data.schemes) {
          setSchemes(data.schemes);
        }
        
        // Refresh analytics in background
        const analyRes = await fetch(`${API_BASE_URL}/analytics`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (analyRes.ok) {
          const analyData = await analyRes.json();
          setAnalytics(analyData);
        }
      }
    } catch (err) {
      console.error("Chat failure:", err);
    } finally {
      setChatLoading(false);
    }
  };

  // Speech Synthesizer read aloud helper
  const speakAloud = (text: string) => {
    if (!window.speechSynthesis) return;
    const cleanText = text.replace(/[\*#_`\-]/g, "");
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = language === "hi" ? "hi-IN" : "en-IN";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  // Logout trigger
  const handleLogout = () => {
    localStorage.removeItem("saarthi_token");
    router.push("/");
  };

  // Navigation items with translated labels
  const navItems = [
    { id: "dashboard", labelKey: "nav_dashboard" as const, icon: LayoutDashboard },
    { id: "agent", labelKey: "nav_agent" as const, icon: MessageSquareCode },
    { id: "explorer", labelKey: "nav_explorer" as const, icon: Compass },
    { id: "vault", labelKey: "nav_vault" as const, icon: FolderClosed },
    { id: "compare", labelKey: "nav_compare" as const, icon: Scale },
    { id: "timeline", labelKey: "nav_timeline" as const, icon: Clock },
  ];

  // Header title based on active tab
  const headerTitleKey = {
    dashboard: "header_dashboard",
    agent: "header_agent",
    explorer: "header_explorer",
    vault: "header_vault",
    compare: "header_compare",
    timeline: "header_timeline",
  } as const;

  return (
    <main className="min-h-screen bg-[#070b13] text-slate-200 flex overflow-hidden font-sans">
      
      {/* 1. Left Sidebar Navigation */}
      <aside className="w-64 bg-[#0a0e17] border-r border-slate-800 flex flex-col justify-between select-none shrink-0 z-30">
        <div>
          {/* Logo Brand Header */}
          <div className="px-6 py-5 border-b border-slate-800/80 flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <span className="text-sm font-bold tracking-tight bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent">
                {t("brand_name", language)}
              </span>
              <span className="text-[9px] uppercase font-bold tracking-wider text-slate-500 block">
                {t("brand_subtitle", language)}
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5 text-xs font-semibold">
            {navItems.map((link) => {
              const Icon = link.icon;
              const isActive = activeTab === link.id;
              return (
                <button
                  key={link.id}
                  onClick={() => setActiveTab(link.id as ActiveTabType)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-left cursor-pointer ${
                    isActive 
                      ? "bg-sky-500/10 border border-sky-500/30 text-sky-400" 
                      : "border border-transparent text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-4.5 w-4.5 shrink-0" />
                  <span>{t(link.labelKey, language)}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer SOS Button */}
        <div className="p-4 border-t border-slate-800/80">
          <button
            onClick={() => setShowSosModal(true)}
            className="w-full py-2.5 flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold shadow-md cursor-pointer transition-colors"
          >
            <AlertOctagon className="h-4 w-4" />
            <span>{t("trigger_sos", language)}</span>
          </button>
        </div>
      </aside>

      {/* 2. Main content container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto relative pb-12">
        {/* Background gradient mesh */}
        <div className="absolute top-0 right-0 w-[50%] h-[35%] bg-sky-950/5 blur-[120px] pointer-events-none" />

        {/* Top Navbar Header */}
        <header className="sticky top-0 z-20 bg-[#070b13]/85 backdrop-blur-md border-b border-slate-800/80 px-6 py-4 flex justify-between items-center shadow-md">
          {/* Breadcrumb Tab Title */}
          <div>
            <h1 className="text-base font-bold text-white tracking-tight uppercase">
              {t(headerTitleKey[activeTab], language)}
            </h1>
          </div>

          {/* Action Row */}
          <div className="flex items-center gap-4 text-xs font-semibold">
            {/* Language Selector */}
            <div className="flex items-center bg-slate-900 border border-slate-800 rounded-md overflow-hidden">
              <button
                onClick={() => setLanguage("en")}
                className={`px-3 py-1 cursor-pointer transition-colors ${language === "en" ? "bg-sky-500 text-white" : "text-slate-500 hover:text-slate-300"}`}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage("hi")}
                className={`px-3 py-1 cursor-pointer transition-colors ${language === "hi" ? "bg-sky-500 text-white" : "text-slate-500 hover:text-slate-300"}`}
              >
                HI
              </button>
            </div>

            {/* Consumer ID Badge */}
            {consumerId && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-sky-500/30 bg-sky-500/10 text-sky-400 font-mono">
                <ShieldCheck className="h-3.5 w-3.5 text-sky-400" />
                <span className="text-[10px] text-slate-400 font-sans tracking-wide">
                  {t("consumer_id_label", language)}:
                </span>
                <span className="font-bold tracking-wider">{consumerId}</span>
              </div>
            )}

            {/* Exit button */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-800 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-400 hover:text-rose-400 cursor-pointer transition-all"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>{t("exit_label", language)}</span>
            </button>
          </div>
        </header>

        {/* Tab content panel */}
        <div className="max-w-6xl w-full mx-auto px-6 py-8 space-y-8 flex-1">
          
          {/* Accessibility Assist Header */}
          <AccessibilityControls
            language={language}
            onVoiceSearch={handleSendChatMessage}
            voiceOutputActive={voiceOutputActive}
            onToggleVoiceOutput={(active) => {
              setVoiceOutputActive(active);
              if (!active) window.speechSynthesis.cancel();
            }}
          />

          {/* Render Tab Contents */}
          {activeTab === "dashboard" && (
            <div className="space-y-8 animate-fadeIn">
              {/* Onboarding Welcome Banner with generated beneficiaries illustration */}
              <GlassCard className="border-slate-800/80 overflow-hidden relative p-0">
                <div className="grid grid-cols-1 md:grid-cols-12 items-center">
                  <div className="p-8 md:col-span-8 space-y-4">
                    <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 font-semibold text-[10px]">
                      <Sparkles className="h-3 w-3" />
                      <span>{t("empowering_badge", language)}</span>
                    </div>
                    <h2 className="text-xl font-bold text-white tracking-tight leading-tight">
                      {t("empowering_title", language)}
                    </h2>
                    <p className="text-slate-300 text-xs leading-relaxed max-w-lg">
                      {t("empowering_desc", language)}
                    </p>
                  </div>
                  <div className="md:col-span-4 h-48 md:h-full relative overflow-hidden flex items-center justify-center p-4">
                    <img 
                      src="/images/beneficiaries.png" 
                      alt="Indian Beneficiaries" 
                      className="object-cover w-full h-full rounded-lg max-h-[160px] border border-slate-800"
                    />
                  </div>
                </div>
              </GlassCard>

              <AnalyticsDashboard data={analytics} language={language} />
            </div>
          )}

          {activeTab === "agent" && (
            <div className="grid grid-cols-1 gap-8 animate-fadeIn">
              <GlassCard className="border-sky-500/15">
                <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-sky-400 shrink-0" />
                    <div>
                      <h3 className="text-sm font-bold text-white">{t("agent_title", language)}</h3>
                      <span className="text-[9px] text-slate-500 block font-mono">{t("agent_status_prefix", language)} {agentLog}</span>
                    </div>
                  </div>
                </div>

                {/* Message transcript */}
                <div className="h-96 overflow-y-auto pr-1 space-y-3.5 text-xs mb-4 scrollbar-thin">
                  {chatMessages.length === 0 ? (
                    <div className="h-full flex flex-col justify-center items-center text-slate-500 text-center px-12">
                      <Sparkles className="h-10 w-10 text-sky-500 mb-3 opacity-55 stroke-1" />
                      <p className="text-[11px] leading-relaxed max-w-sm">
                        {t("agent_welcome", language)}
                      </p>
                    </div>
                  ) : (
                    chatMessages.map((msg, index) => (
                      <div
                        key={index}
                        className={`flex gap-2.5 p-3.5 rounded-lg ${
                          msg.role === "user"
                            ? "bg-sky-950/20 ml-12 border border-sky-950/40"
                            : "bg-slate-900/40 mr-12 border border-slate-800/80"
                        }`}
                      >
                        <div className="space-y-1">
                          <span className="text-[9px] uppercase font-extrabold tracking-wider text-sky-400 block">
                            {msg.role === "user" ? t("citizen_label", language) : msg.agent_name || t("agent_name_default", language)}
                          </span>
                          <div className="leading-relaxed text-slate-300 font-sans whitespace-pre-line">
                            {msg.content}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Chat Input form */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendChatMessage(chatInput);
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={chatInput}
                    disabled={chatLoading}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder={t("chat_placeholder", language)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-md px-3.5 py-3 outline-none text-xs focus:ring-1 focus:ring-sky-500 text-slate-200 transition-all font-sans"
                  />
                  <button
                    type="submit"
                    disabled={chatLoading}
                    className="p-3 bg-sky-500 hover:bg-sky-600 disabled:bg-sky-400 text-white rounded-md cursor-pointer transition-colors shadow-sm"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </GlassCard>
            </div>
          )}

          {activeTab === "explorer" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-fadeIn">
              
              {/* Simulator Column */}
              <div className="lg:col-span-4">
                <ProfileSimulator
                  profile={profile}
                  onProfileChange={handleProfileChange}
                  language={language}
                />
              </div>

              {/* Matches list Column */}
              <div className="lg:col-span-8 space-y-6">
                <GlassCard className="border-slate-800/80">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                      <Award className="h-4.5 w-4.5 text-sky-400" />
                      {t("matched_benefits", language)}
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {schemes.map((sch) => {
                      const isSelected = selectedScheme && selectedScheme.id === sch.id;
                      return (
                        <div
                          key={sch.id}
                          onClick={() => token && loadSchemeDetail(sch.id, token)}
                          className={`cursor-pointer p-4 rounded-lg border transition-all duration-200 text-xs flex flex-col justify-between ${
                            isSelected 
                              ? "bg-sky-500/10 border-sky-500 text-slate-100 font-medium" 
                              : "bg-slate-900/40 border-slate-800 hover:border-slate-700 text-slate-300"
                          }`}
                        >
                          <div>
                            <div className="flex justify-between items-start mb-2">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  sch.eligibility_status === "Eligible" || sch.eligibility_status === "पात्र (Eligible)"
                                    ? "bg-emerald-500/10 text-emerald-400"
                                    : sch.eligibility_status === "Likely Eligible" || sch.eligibility_status === "संभावित पात्र (Likely Eligible)"
                                    ? "bg-sky-500/10 text-sky-400"
                                    : "bg-amber-500/10 text-amber-400"
                                }`}
                              >
                                {sch.eligibility_status}
                              </span>
                              <input
                                type="checkbox"
                                checked={compareIds.includes(sch.id)}
                                onClick={(e) => e.stopPropagation()}
                                onChange={(e) => handleCompareCheckbox(sch.id, e.target.checked)}
                                className="h-3.5 w-3.5 rounded border-slate-800 bg-slate-950 text-sky-500"
                              />
                            </div>
                            <h4 className="font-bold text-slate-100 mb-1">{sch.title}</h4>
                            <p className="text-slate-400 leading-relaxed line-clamp-3 mb-2">{sch.description}</p>
                          </div>

                          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400 mt-2">
                            <span>{t("benefit_label", language)} {sch.benefit_type}</span>
                            <div className="flex gap-2">
                              <button
                                onClick={(e) => { e.stopPropagation(); handleSchemeAction(sch.id, "saved"); }}
                                className="text-sky-400 hover:underline font-semibold"
                              >
                                {t("save_btn", language)}
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleSchemeAction(sch.id, "applied"); }}
                                className="text-emerald-400 hover:underline font-semibold"
                              >
                                {t("apply_btn", language)}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </GlassCard>

                {/* Selected scheme detailed guide */}
                {selectedScheme && (
                  <GlassCard className="border-emerald-500/20 bg-[#090e16]/80 animate-fadeIn">
                    <div className="flex justify-between items-center border-b border-slate-850 pb-3 mb-4">
                      <div>
                        <span className="text-[10px] text-sky-400 uppercase font-bold tracking-wider block">
                          {t("checklist_title", language)}
                        </span>
                        <h3 className="text-sm font-bold text-white">{selectedScheme.title}</h3>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-slate-400">
                          {t("readiness_label", language)} {selectedScheme.readiness_score?.toFixed(0)}%
                        </span>
                        <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-emerald-400 h-full transition-all duration-300"
                            style={{ width: `${selectedScheme.readiness_score || 0}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs leading-relaxed text-slate-300">
                      {/* Left: eligibility reasoning, letter */}
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-semibold text-slate-100 flex items-center gap-1.5 mb-1.5">
                            <BookOpen className="h-4 w-4 text-amber-400" />
                            {t("eligibility_fine_print", language)}
                          </h4>
                          <p className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/80 leading-relaxed font-sans text-slate-300">
                            {selectedScheme.eligibility_explanation}
                          </p>
                        </div>

                        <div>
                          <h4 className="font-semibold text-slate-100 flex items-center gap-1.5 mb-1.5">
                            <FileText className="h-4 w-4 text-sky-400" />
                            {t("cover_letter_title", language)}
                          </h4>
                          <pre className="bg-slate-950/60 p-3 rounded-lg border border-slate-850 text-slate-300 font-mono text-[9px] overflow-auto max-h-48 whitespace-pre-wrap">
                            {selectedScheme.cover_letter}
                          </pre>
                        </div>
                      </div>

                      {/* Right: checklist verification */}
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-semibold text-slate-100 flex items-center gap-1.5 mb-2">
                            <ClipboardList className="h-4 w-4 text-emerald-400" />
                            {t("verification_checklist", language)}
                          </h4>
                          <div className="space-y-1.5">
                            {selectedScheme.checklist?.map((item: any, idx: number) => (
                              <div
                                key={idx}
                                className="flex justify-between items-center p-2 rounded bg-slate-950/30 border border-slate-800/50"
                              >
                                <span className="font-medium text-slate-200">{item.required_label}</span>
                                <div className="flex items-center gap-1.5">
                                  {item.status === "Verified" ? (
                                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                                  ) : (
                                    <AlertCircle className="h-4 w-4 text-rose-400" />
                                  )}
                                  <span className={item.status === "Verified" ? "text-emerald-400" : "text-rose-400"}>
                                    {item.status === "Verified" ? t("status_verified", language) : t("status_missing", language)}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Timeline stages */}
                        {selectedScheme.timeline && (
                          <div>
                            <h4 className="font-semibold text-slate-100 flex items-center gap-1.5 mb-2">
                              <Clock className="h-4 w-4 text-sky-400" />
                              {t("timeline_label", language)} (~{selectedScheme.timeline.estimated_days} {t("days_to_approval", language)})
                            </h4>
                            <div className="space-y-2 border-l-2 border-slate-800 pl-4 py-1 ml-2">
                              {selectedScheme.timeline.stages?.map((stg: any, idx: number) => (
                                <div key={idx} className="relative">
                                  <div className="absolute top-1 -left-[21px] w-2.5 h-2.5 rounded-full bg-sky-500" />
                                  <div className="font-bold text-slate-200">{stg.name}</div>
                                  <div className="text-[10px] text-slate-400">{t("duration_label", language)} {stg.duration}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </GlassCard>
                )}
              </div>
            </div>
          )}

          {activeTab === "vault" && (
            <div className="space-y-8 animate-fadeIn">
              <DocumentVault
                documents={vaultDocs}
                onUpload={handleDocUpload}
                onDelete={handleDocDelete}
                language={language}
              />
            </div>
          )}

          {activeTab === "compare" && (
            <div className="space-y-8 animate-fadeIn">
              <GlassCard className="border-slate-850">
                <div className="flex justify-between items-center border-b border-slate-850 pb-3 mb-6">
                  <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                    <Scale className="h-4.5 w-4.5 text-sky-400" />
                    {t("compare_title", language)}
                  </h3>
                  {compareIds.length > 0 && (
                    <button
                      onClick={triggerComparison}
                      className="px-4 py-2 bg-sky-500 hover:bg-sky-600 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-sm transition-colors"
                    >
                      {t("compare_selected", language)} ({compareIds.length})
                    </button>
                  )}
                </div>

                <div className="text-xs text-slate-400 max-w-lg mb-6 leading-relaxed">
                  {t("compare_desc", language)}
                </div>

                {compareIds.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                    <Scale className="h-10 w-10 mb-2 opacity-50 stroke-1" />
                    <p className="text-[11px]">{t("compare_empty", language)}</p>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-3">
                    {compareIds.map((cid) => {
                      const matchedSch = schemes.find((s) => s.id === cid);
                      return (
                        <div
                          key={cid}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-slate-200"
                        >
                          <span>{matchedSch ? matchedSch.title : `Scheme #${cid}`}</span>
                          <button
                            onClick={() => handleCompareCheckbox(cid, false)}
                            className="text-slate-400 hover:text-rose-400 font-bold"
                          >
                            ×
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </GlassCard>
            </div>
          )}

          {activeTab === "timeline" && (
            <div className="space-y-8 animate-fadeIn">
              <GlassCard className="border-slate-850">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-850 pb-3">
                  <BellRing className="h-5 w-5 text-sky-500" />
                  <h2 className="text-sm font-bold tracking-tight text-white">{t("timeline_title", language)}</h2>
                </div>

                {analytics.timeline_events?.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 text-xs">
                    {t("timeline_empty", language)}
                  </div>
                ) : (
                  <div className="relative border-l-2 border-slate-800 pl-6 space-y-6 py-2 ml-4">
                    {analytics.timeline_events?.map((ev: any, idx: number) => (
                      <div key={idx} className="relative text-xs">
                        <div className="absolute top-1 -left-[31px] w-4 h-4 rounded-full border border-sky-500 bg-[#070b13] flex items-center justify-center">
                          <div className={`w-1.5 h-1.5 rounded-full ${ev.completed ? "bg-emerald-500" : "bg-sky-500"}`} />
                        </div>
                        <span className="text-[10px] text-slate-500 block mb-0.5 font-mono">{ev.date}</span>
                        <h4 className="font-bold text-slate-100">{ev.title}</h4>
                        <span className="text-[10px] text-slate-400 mt-0.5 block uppercase tracking-wider">
                          {t("timeline_type", language)}: {ev.type} | {t("timeline_status", language)}: {ev.completed ? t("timeline_complete", language) : t("timeline_pending", language)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </GlassCard>
            </div>
          )}

        </div>

      </div>

      {/* Compare Schemes Modal */}
      {showCompareModal && (
        <SchemeCompare
          schemes={compareData}
          onRemove={(id) => {
            setCompareData((cur) => cur.filter((s) => s.id !== id));
            setCompareIds((cur) => cur.filter((cid) => cid !== id));
          }}
          onClose={() => setShowCompareModal(false)}
        />
      )}

      {/* Custom Assistance SOS Modal */}
      {showSosModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fadeIn">
          <div className="relative w-full max-w-lg bg-[#0e1422] border border-slate-800 rounded-xl shadow-2xl overflow-hidden p-6 text-sm">
            <div className="flex items-center gap-3 mb-4 text-rose-500 border-b border-slate-800 pb-3">
              <AlertOctagon className="h-6 w-6 shrink-0" />
              <h3 className="text-lg font-bold text-white">{t("sos_title", language)}</h3>
            </div>
            
            <div className="space-y-4 leading-relaxed text-slate-300">
              <p>{t("sos_desc", language)}</p>
              
              <div className="bg-slate-950/60 border border-slate-800/80 p-3.5 rounded-lg text-xs">
                <span className="font-semibold text-white block mb-1">{t("sos_officer", language)}</span>
                <div>{t("sos_name", language)}</div>
                <div>{t("sos_desk", language)}</div>
                <div>{t("timeline_status", language)}: <span className="text-emerald-400 font-bold">{t("sos_status", language)}</span></div>
              </div>

              <div>
                <span className="font-semibold text-white block mb-1.5">{t("sos_helpdesk", language)}</span>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  <li>🧑‍🌾 {language === "hi" ? "किसान सहायता" : "Kisan (Farmer) Support"}: 1800-180-1551</li>
                  <li>🎓 {language === "hi" ? "छात्रवृत्ति हेल्पडेस्क" : "Scholarships helpdesk"}: 0120-6619540</li>
                  <li>👩 {language === "hi" ? "महिला सशक्तिकरण" : "Women Empowerment"}: 1091 / 181</li>
                  <li>🏢 {language === "hi" ? "व्यापार ऋण (मुद्रा)" : "Business Loans (Mudra)"}: 1800-180-1111</li>
                </ul>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowSosModal(false)}
                className="px-4 py-2 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-lg transition-colors cursor-pointer"
              >
                {t("sos_close", language)}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
