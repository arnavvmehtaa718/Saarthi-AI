"use client";

import React, { useState, useEffect } from "react";
import GlassCard from "../ui/GlassCard";
import { Accessibility, Mic, Volume2, Type, Eye, VolumeX, MicOff } from "lucide-react";
import { t, Language } from "../../lib/translations";

interface AccessibilityControlsProps {
  language: Language;
  onVoiceSearch: (transcript: string) => void;
  voiceOutputActive: boolean;
  onToggleVoiceOutput: (active: boolean) => void;
}

export default function AccessibilityControls({
  language,
  onVoiceSearch,
  voiceOutputActive,
  onToggleVoiceOutput
}: AccessibilityControlsProps) {
  const [isListening, setIsListening] = useState<boolean>(false);
  const [fontSize, setFontSize] = useState<"normal" | "large" | "extra-large">("normal");
  const [highContrast, setHighContrast] = useState<boolean>(false);

  // Handle Speech Recognition
  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert(language === "hi"
        ? "इस ब्राउज़र में वॉइस इनपुट समर्थित नहीं है। कृपया Google Chrome आज़माएं।"
        : "Voice input is not supported in this browser. Please try Google Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
    recognition.interimResults = false;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onVoiceSearch(transcript);
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  // Font size adjustment
  useEffect(() => {
    const docElement = document.documentElement;
    docElement.classList.remove("text-normal", "text-lg", "text-xl");
    if (fontSize === "normal") {
      docElement.classList.add("text-normal");
    } else if (fontSize === "large") {
      docElement.classList.add("text-lg");
    } else if (fontSize === "extra-large") {
      docElement.classList.add("text-xl");
    }
  }, [fontSize]);

  // High contrast adjustment
  const toggleHighContrast = () => {
    const nextVal = !highContrast;
    setHighContrast(nextVal);
    const body = document.body;
    if (nextVal) {
      body.classList.add("contrast-200", "saturate-200");
    } else {
      body.classList.remove("contrast-200", "saturate-200");
    }
  };

  return (
    <GlassCard className="border-slate-800/80 py-4 px-6">
      <div className="flex flex-wrap items-center justify-between gap-4 text-xs font-semibold text-slate-200">
        <div className="flex items-center gap-1.5">
          <Accessibility className="h-4 w-4 text-sky-400" />
          <span>{t("accessibility_label", language)}</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Voice input button */}
          <button
            onClick={startListening}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md transition-all cursor-pointer border ${
              isListening
                ? "bg-rose-500 border-rose-500 text-white animate-pulse"
                : "bg-slate-900 border-slate-800 hover:bg-slate-800 text-slate-200 hover:text-white"
            }`}
            title={language === "hi" ? "वॉइस से पूछें" : "Ask via Voice input"}
          >
            {isListening ? <MicOff className="h-3.5 w-3.5 text-rose-200" /> : <Mic className="h-3.5 w-3.5 text-sky-400" />}
            <span>{isListening ? t("listening", language) : t("voice_input", language)}</span>
          </button>

          {/* Voice output toggle */}
          <button
            onClick={() => onToggleVoiceOutput(!voiceOutputActive)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md transition-all cursor-pointer border ${
              voiceOutputActive
                ? "bg-sky-500 border-sky-500 text-white"
                : "bg-slate-900 border-slate-800 hover:bg-slate-800 text-slate-200 hover:text-white"
            }`}
            title={language === "hi" ? "वॉइस रीड टॉगल करें" : "Toggle read aloud explanations"}
          >
            {voiceOutputActive ? <Volume2 className="h-3.5 w-3.5 text-sky-100" /> : <VolumeX className="h-3.5 w-3.5 text-slate-400" />}
            <span>{voiceOutputActive ? t("voice_on", language) : t("voice_off", language)}</span>
          </button>

          {/* Font scale adjuster */}
          <button
            onClick={() => {
              setFontSize((cur) => (cur === "normal" ? "large" : cur === "large" ? "extra-large" : "normal"));
            }}
            className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 hover:text-white transition-all cursor-pointer"
            title={language === "hi" ? "टेक्स्ट साइज़ बदलें" : "Adjust text size"}
          >
            <Type className="h-3.5 w-3.5 text-sky-400" />
            <span>
              {t("text_size", language)} {fontSize === "normal" ? "100%" : fontSize === "large" ? "120%" : "140%"}
            </span>
          </button>

          {/* High Contrast */}
          <button
            onClick={toggleHighContrast}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md transition-all cursor-pointer border ${
              highContrast
                ? "bg-amber-500 border-amber-500 text-slate-950 font-bold"
                : "bg-slate-900 border-slate-800 hover:bg-slate-800 text-slate-200 hover:text-white"
            }`}
            title={language === "hi" ? "कंट्रास्ट मोड टॉगल करें" : "Toggle contrast mode"}
          >
            <Eye className="h-3.5 w-3.5" />
            <span>{highContrast ? t("contrast_max", language) : t("contrast_normal", language)}</span>
          </button>
        </div>
      </div>
    </GlassCard>
  );
}
