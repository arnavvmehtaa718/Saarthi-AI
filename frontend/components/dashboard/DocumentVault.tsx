"use client";

import React, { useRef, useState } from "react";
import GlassCard from "../ui/GlassCard";
import { Folder, Upload, Trash2, Calendar, FileText, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react";
import { t, Language } from "../../lib/translations";

export interface VaultDocument {
  id: number;
  file_name: string;
  category: string;
  document_id_number: string | null;
  owner_name: string | null;
  expiry_date: string | null;
  is_valid: boolean;
  extracted_metadata: {
    ocr_method?: string;
    summary?: string;
  };
}

interface DocumentVaultProps {
  documents: VaultDocument[];
  onUpload: (file: File, category: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  language: Language;
}

export default function DocumentVault({ documents, onUpload, onDelete, language }: DocumentVaultProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("other");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const categories = [
    { value: "other", labelKey: "cat_other" as const },
    { value: "aadhaar", labelKey: "cat_aadhaar" as const },
    { value: "pan", labelKey: "cat_pan" as const },
    { value: "income", labelKey: "cat_income" as const },
    { value: "caste", labelKey: "cat_caste" as const },
    { value: "residence", labelKey: "cat_residence" as const },
    { value: "bank", labelKey: "cat_bank" as const },
    { value: "land", labelKey: "cat_land" as const },
    { value: "disability", labelKey: "cat_disability" as const },
    { value: "education", labelKey: "cat_education" as const },
  ];

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      await onUpload(file, selectedCategory);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err: any) {
      setUploadError(err.message || (language === "hi" ? "दस्तावेज़ अपलोड विफल।" : "Failed to upload document."));
    } finally {
      setIsUploading(false);
    }
  };

  const triggerUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Get translated category label from value
  const getCategoryLabel = (catValue: string): string => {
    const found = categories.find((c) => c.value === catValue);
    return found ? t(found.labelKey, language) : catValue;
  };

  return (
    <GlassCard className="h-full border-sky-950/20">
      <div className="flex justify-between items-center mb-4 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <Folder className="h-5 w-5 text-sky-500" />
          <h2 className="text-lg font-bold tracking-tight">{t("vault_title", language)}</h2>
        </div>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-950 text-sky-500">
          {documents.length} {t("vault_files", language)}
        </span>
      </div>

      {/* Upload Zone */}
      <div className="mb-6 p-4 border border-dashed border-border rounded-lg bg-slate-900/20 flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-slate-400 block mb-1 font-medium">{t("vault_category_label", language)}</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-slate-900 border border-border rounded-md px-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-sky-500 text-slate-200"
            >
              {categories.map((cat) => (
                <option key={cat.value} value={cat.value}>{t(cat.labelKey, language)}</option>
              ))}
            </select>
          </div>
          
          <button
            onClick={triggerUploadClick}
            disabled={isUploading}
            className="flex items-center justify-center gap-1.5 px-4 py-2 bg-sky-500 hover:bg-sky-600 disabled:bg-sky-400 text-white rounded-md text-xs font-medium cursor-pointer transition-colors shadow-sm h-[34px] mt-[18px]"
          >
            {isUploading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Upload className="h-3.5 w-3.5" />
            )}
            <span>{isUploading ? t("vault_scanning", language) : t("vault_upload", language)}</span>
          </button>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileChange}
          className="hidden"
        />
        
        {uploadError && (
          <div className="text-rose-500 text-xs mt-1 font-medium bg-rose-950/20 p-2 rounded-md border border-rose-950/40">
            {uploadError}
          </div>
        )}
      </div>

      {/* Documents Table */}
      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-slate-400">
          <FileText className="h-10 w-10 mb-2 stroke-1 opacity-60 text-slate-400" />
          <p className="text-xs">{t("vault_empty", language)}</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-border text-slate-400">
                <th className="py-2 pb-2.5 font-semibold">{t("vault_doc_name", language)}</th>
                <th className="py-2 pb-2.5 font-semibold">{t("vault_category", language)}</th>
                <th className="py-2 pb-2.5 font-semibold">{t("vault_metadata", language)}</th>
                <th className="py-2 pb-2.5 font-semibold text-right">{t("vault_actions", language)}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                return (
                  <tr key={doc.id} className="border-b border-border/40 hover:bg-slate-900/10">
                    <td className="py-3 font-medium max-w-[150px] truncate">
                      <div className="flex items-center gap-1.5">
                        <FileText className="h-4 w-4 text-sky-500 shrink-0" />
                        <span className="truncate" title={doc.file_name}>{doc.file_name}</span>
                      </div>
                    </td>
                    <td className="py-3">
                      <span className="inline-block px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">
                        {getCategoryLabel(doc.category)}
                      </span>
                    </td>
                    <td className="py-3">
                      <div className="space-y-0.5 text-[10px]">
                        {doc.document_id_number && (
                          <div>
                            <span className="text-slate-400">ID: </span>
                            <span className="font-mono text-slate-300 font-semibold">
                              {doc.document_id_number}
                            </span>
                          </div>
                        )}
                        {doc.expiry_date && (
                          <div className="flex items-center gap-0.5 text-amber-500">
                            <Calendar className="h-3 w-3" />
                            <span>{language === "hi" ? "समाप्ति:" : "Expires:"} {doc.expiry_date.split("T")[0]}</span>
                          </div>
                        )}
                        {doc.owner_name && (
                          <div>
                            <span className="text-slate-400">{language === "hi" ? "धारक:" : "Holder:"} </span>
                            <span className="text-slate-300 font-medium">{doc.owner_name}</span>
                          </div>
                        )}
                        {!doc.document_id_number && !doc.expiry_date && !doc.owner_name && (
                          <span className="text-slate-400 italic">
                            {language === "hi" ? "कोई संरचित फ़ील्ड नहीं निकाली गई" : "No structured fields extracted"}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => onDelete(doc.id)}
                        className="text-slate-400 hover:text-rose-500 transition-colors p-1 rounded-md hover:bg-rose-950/20"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </GlassCard>
  );
}
