/**
 * Bilingual translation dictionary for Saarthi AI Navigator Portal.
 * Supports English (en) and Hindi (hi).
 */

export type Language = "en" | "hi";

const translations = {
  // Branding
  brand_name: { en: "Saarthi AI", hi: "सारथी AI" },
  brand_subtitle: { en: "NAVIGATOR PORTAL", hi: "नेविगेटर पोर्टल" },

  // Sidebar Navigation
  nav_dashboard: { en: "Dashboard", hi: "डैशबोर्ड" },
  nav_agent: { en: "Caseworker Agent", hi: "केसवर्कर एजेंट" },
  nav_explorer: { en: "Scheme Explorer", hi: "योजना खोजकर्ता" },
  nav_vault: { en: "Document Vault", hi: "दस्तावेज़ वॉल्ट" },
  nav_compare: { en: "Scheme Comparison", hi: "योजना तुलना" },
  nav_timeline: { en: "Active Timeline", hi: "सक्रिय समयरेखा" },
  trigger_sos: { en: "TRIGGER SOS", hi: "SOS ट्रिगर करें" },

  // Header Titles
  header_dashboard: { en: "Dashboard Analytics", hi: "डैशबोर्ड विश्लेषिकी" },
  header_agent: { en: "Caseworker Agent Panel", hi: "केसवर्कर एजेंट पैनल" },
  header_explorer: { en: "Interactive Scheme Explorer", hi: "इंटरैक्टिव योजना खोजकर्ता" },
  header_vault: { en: "Secure Document Vault", hi: "सुरक्षित दस्तावेज़ वॉल्ट" },
  header_compare: { en: "Scheme Comparison Hub", hi: "योजना तुलना केंद्र" },
  header_timeline: { en: "Welfare Milestone Timeline", hi: "कल्याण मील का पत्थर समयरेखा" },

  // Top bar
  eli15_label: { en: "ELI15", hi: "सरल भाषा" },
  consumer_id_label: { en: "Consumer ID", hi: "उपभोक्ता आईडी" },
  exit_label: { en: "Exit", hi: "बाहर" },

  // Dashboard tab
  empowering_badge: { en: "Empowering Indian Citizens", hi: "भारतीय नागरिकों का सशक्तिकरण" },
  empowering_title: { en: "Empowering Farmers, Students, Artisans, & Families", hi: "किसानों, छात्रों, कारीगरों और परिवारों का सशक्तिकरण" },
  empowering_desc: {
    en: "Saarthi AI links your demographic indicators directly to active central government schemes. Run the interactive simulator, upload documents, and let your digital caseworker navigate approvals.",
    hi: "सारथी AI आपके जनसांख्यिकीय संकेतकों को सीधे सक्रिय केंद्र सरकार की योजनाओं से जोड़ता है। इंटरैक्टिव सिम्युलेटर चलाएं, दस्तावेज़ अपलोड करें, और अपने डिजिटल केसवर्कर को अनुमोदन प्राप्त करने दें।"
  },

  // Analytics KPIs
  kpi_benefits: { en: "Estimated Benefits", hi: "अनुमानित लाभ" },
  kpi_benefits_note: {
    en: "Estimated maximum value. Not a guarantee of payment or approval.",
    hi: "अनुमानित अधिकतम मूल्य। भुगतान या स्वीकृति की गारंटी नहीं।"
  },
  kpi_matches: { en: "Matches Found", hi: "मिलान पाए गए" },
  kpi_schemes: { en: "Schemes", hi: "योजनाएं" },
  kpi_missing_docs: { en: "Missing Documents", hi: "लापता दस्तावेज़" },
  kpi_files: { en: "Files", hi: "फाइलें" },
  kpi_milestones: { en: "Upcoming Milestones", hi: "आगामी मील के पत्थर" },
  kpi_deadlines: { en: "Deadlines", hi: "समय सीमा" },
  chart_title: { en: "Estimated Value by Scheme", hi: "योजना के अनुसार अनुमानित मूल्य" },
  chart_empty: { en: "No active benefit schemes matched yet.", hi: "अभी तक कोई सक्रिय लाभ योजना मिलान नहीं हुई।" },
  chart_benefit_amount: { en: "Estimated value", hi: "अनुमानित मूल्य" },
  status_breakdown_title: { en: "Eligibility Breakdown", hi: "पात्रता विवरण" },
  alerts_title: { en: "Critical Alerts & Deadlines", hi: "महत्वपूर्ण अलर्ट और समय सीमा" },
  alerts_clear: { en: "All alerts verified! No upcoming expirations.", hi: "सभी अलर्ट सत्यापित! कोई आगामी समाप्ति नहीं।" },

  // Agent / Chat tab
  agent_title: { en: "Caseworker AI Assistant", hi: "केसवर्कर AI सहायक" },
  agent_status_prefix: { en: "Status:", hi: "स्थिति:" },
  agent_idle: { en: "Caseworker orchestrator idle.", hi: "केसवर्कर ऑर्केस्ट्रेटर निष्क्रिय।" },
  agent_welcome: {
    en: "Hello! I am your Caseworker Advisor. Ask me welfare-related queries. E.g., \"I am a disabled farmer from Bihar. What loans can I get?\". The collaborative agents will update your profile and checklists instantly.",
    hi: "नमस्ते! मैं आपका केसवर्कर सलाहकार हूं। मुझसे कल्याण से जुड़े प्रश्न पूछें। उदा., \"मैं बिहार का एक विकलांग किसान हूं। मुझे कौन से ऋण मिल सकते हैं?\" सहयोगी एजेंट आपकी प्रोफाइल और चेकलिस्ट तुरंत अपडेट करेंगे।"
  },
  citizen_label: { en: "Citizen", hi: "नागरिक" },
  agent_name_default: { en: "Saarthi Agent", hi: "सारथी एजेंट" },
  chat_placeholder: { en: "Type or click Voice Input to speak query...", hi: "क्वेरी टाइप करें या वॉइस इनपुट क्लिक करें..." },

  // Explorer tab
  simulator_title: { en: "Interactive Eligibility Simulator", hi: "इंटरैक्टिव पात्रता सिम्युलेटर" },
  matched_benefits: { en: "Matched Welfare Benefits", hi: "मिलान कल्याण लाभ" },
  benefit_label: { en: "Benefit:", hi: "लाभ:" },
  save_btn: { en: "Save", hi: "सहेजें" },
  apply_btn: { en: "Apply", hi: "आवेदन करें" },
  checklist_title: { en: "Detailed Casework Checklist", hi: "विस्तृत केसवर्क चेकलिस्ट" },
  eligibility_fine_print: { en: "Eligibility Fine Print", hi: "पात्रता विवरण" },
  cover_letter_title: { en: "Cover Letter Draft", hi: "कवर लेटर मसौदा" },
  verification_checklist: { en: "Verification Checklist", hi: "सत्यापन चेकलिस्ट" },
  readiness_label: { en: "Readiness:", hi: "तैयारी:" },
  missing_info_title: { en: "Information still needed", hi: "अभी आवश्यक जानकारी" },
  official_source: { en: "Official source", hi: "आधिकारिक स्रोत" },
  disclaimer_label: { en: "Important", hi: "महत्वपूर्ण" },
  timeline_label: { en: "Estimated Timeline", hi: "अनुमानित समयरेखा" },
  days_to_approval: { en: "days to approval", hi: "अनुमोदन तक दिन" },
  duration_label: { en: "Duration:", hi: "अवधि:" },
  updates_instant: { en: "Updates matched instantly", hi: "अपडेट तुरंत मिलान" },

  // Profile Simulator labels
  sim_name: { en: "Full Name (optional)", hi: "पूरा नाम (वैकल्पिक)" },
  sim_name_placeholder: { en: "Used only in your application draft", hi: "केवल आपके आवेदन मसौदे में उपयोग" },
  sim_state: { en: "Residency (State)", hi: "निवास (राज्य)" },
  sim_age: { en: "Age", hi: "आयु" },
  sim_years: { en: "Years", hi: "वर्ष" },
  sim_income: { en: "Annual Household Income (₹)", hi: "वार्षिक घरेलू आय (₹)" },
  sim_income_lakh: { en: "Lakh per year", hi: "लाख प्रति वर्ष" },
  sim_occupation: { en: "Occupation", hi: "व्यवसाय" },
  sim_category: { en: "Community Category", hi: "सामुदायिक श्रेणी" },
  sim_student: { en: "Are you a Student?", hi: "क्या आप छात्र हैं?" },
  sim_land: { en: "Own Cultivable Land?", hi: "क्या आपके पास खेती योग्य भूमि है?" },
  sim_land_area: { en: "Land Area (Hectares)", hi: "भूमि क्षेत्र (हेक्टेयर)" },
  sim_disabled: { en: "Person with Disability?", hi: "विकलांग व्यक्ति?" },
  sim_disability_pct: { en: "Disability Percentage", hi: "विकलांगता प्रतिशत" },
  sim_severity: { en: "severity", hi: "गंभीरता" },
  sim_ration_card: { en: "Has a Ration Card?", hi: "क्या राशन कार्ड है?" },
  sim_rural: { en: "Residence Type", hi: "निवास प्रकार" },
  sim_rural_option: { en: "Rural", hi: "ग्रामीण" },
  sim_urban_option: { en: "Urban", hi: "शहरी" },
  sim_owns_house: { en: "Owns a Pucca House?", hi: "क्या पक्का घर है?" },
  sim_family_beneficiaries: { en: "Family Members Already Covered", hi: "पहले से लाभान्वित परिवार सदस्य" },
  sim_business_plan: { en: "Has a Business Plan?", hi: "क्या व्यवसाय योजना है?" },
  sim_govt_employee: { en: "Government Employee?", hi: "सरकारी कर्मचारी?" },
  sim_unknown: { en: "Not sure", hi: "पता नहीं" },
  sim_yes: { en: "Yes", hi: "हाँ" },
  sim_no: { en: "No", hi: "नहीं" },

  // Vault tab
  vault_title: { en: "Citizen Document Vault", hi: "नागरिक दस्तावेज़ वॉल्ट" },
  vault_files: { en: "Files", hi: "फ़ाइलें" },
  vault_category_label: { en: "Verify Category for OCR Mapping", hi: "OCR मैपिंग के लिए श्रेणी सत्यापित करें" },
  vault_upload: { en: "Upload Document", hi: "दस्तावेज़ अपलोड करें" },
  vault_scanning: { en: "Scanning OCR...", hi: "OCR स्कैनिंग..." },
  vault_empty: {
    en: "No documents uploaded yet. Upload documents (Aadhaar, PAN, Caste, Land) to complete scheme application checklists.",
    hi: "अभी तक कोई दस्तावेज़ अपलोड नहीं किया गया। योजना आवेदन चेकलिस्ट पूरी करने के लिए दस्तावेज़ (आधार, पैन, जाति, भूमि) अपलोड करें।"
  },
  vault_doc_name: { en: "Document Name", hi: "दस्तावेज़ का नाम" },
  vault_category: { en: "Category", hi: "श्रेणी" },
  vault_metadata: { en: "Metadata Extracted", hi: "मेटाडेटा निकाला गया" },
  vault_actions: { en: "Actions", hi: "कार्रवाई" },
  vault_confidence: { en: "OCR confidence", hi: "OCR विश्वास" },
  vault_review_required: { en: "Needs manual review", hi: "मैन्युअल समीक्षा आवश्यक" },
  vault_verified: { en: "Extraction looks clear", hi: "निष्कर्षण स्पष्ट लगता है" },
  vault_download: { en: "Download", hi: "डाउनलोड" },
  vault_private_note: {
    en: "Files are private to your account. Raw document bytes are never sent to a hosted AI provider.",
    hi: "फ़ाइलें केवल आपके खाते के लिए निजी हैं। कच्चे दस्तावेज़ बाइट्स किसी होस्टेड AI प्रदाता को नहीं भेजे जाते।"
  },

  // Compare tab
  compare_title: { en: "Compare Matched Schemes", hi: "मिलान योजनाओं की तुलना करें" },
  compare_selected: { en: "Compare Selected", hi: "चयनित की तुलना करें" },
  compare_desc: {
    en: "Choose multiple schemes using the compare checkboxes in the Scheme Explorer tab, then trigger the comparison matrix here.",
    hi: "योजना खोजकर्ता टैब में तुलना चेकबॉक्स का उपयोग करके कई योजनाएं चुनें, फिर यहां तुलना मैट्रिक्स ट्रिगर करें।"
  },
  compare_empty: {
    en: "No schemes selected for comparison. Go to Scheme Explorer and check schemes.",
    hi: "तुलना के लिए कोई योजना नहीं चुनी गई। योजना खोजकर्ता पर जाएं और योजनाएं चेक करें।"
  },

  // Timeline tab
  timeline_title: { en: "Upcoming Deadlines & Milestones", hi: "आगामी समय सीमा और मील के पत्थर" },
  timeline_empty: {
    en: "No timeline events mapped yet. Apply to schemes in Scheme Explorer to view milestone events.",
    hi: "अभी तक कोई समयरेखा घटना मैप नहीं हुई। मील के पत्थर की घटनाओं को देखने के लिए योजना खोजकर्ता में योजनाओं पर आवेदन करें।"
  },
  timeline_type: { en: "Type", hi: "प्रकार" },
  timeline_status: { en: "Status", hi: "स्थिति" },
  timeline_complete: { en: "Complete", hi: "पूर्ण" },
  timeline_pending: { en: "Pending", hi: "लंबित" },

  // SOS Modal
  sos_title: { en: "Caseworker support alert transmitted", hi: "केसवर्कर सहायता अलर्ट प्रेषित" },
  sos_desc: {
    en: "An urgent assistance request has been logged. A caseworker is reviewing your saved citizen profile.",
    hi: "एक तत्काल सहायता अनुरोध दर्ज किया गया है। एक केसवर्कर आपकी सहेजी गई नागरिक प्रोफ़ाइल की समीक्षा कर रहा है।"
  },
  sos_officer: { en: "Assigned Casework Officer:", hi: "नियुक्त केसवर्क अधिकारी:" },
  sos_name: { en: "Name: Director R. K. Sharma", hi: "नाम: निदेशक आर. के. शर्मा" },
  sos_desk: { en: "Grievance Desk: 1800-11-2026 (Welfare Division)", hi: "शिकायत डेस्क: 1800-11-2026 (कल्याण प्रभाग)" },
  sos_status: { en: "Reviewing matching parameters", hi: "मिलान पैरामीटर की समीक्षा" },
  sos_helpdesk: { en: "Direct Helpdesk Hotlines:", hi: "सीधी हेल्पडेस्क हॉटलाइन:" },
  sos_close: { en: "Close assistance panel", hi: "सहायता पैनल बंद करें" },

  // Accessibility
  accessibility_label: { en: "Accessibility Caseworker Assist:", hi: "सुगम्यता केसवर्कर सहायता:" },
  voice_input: { en: "Voice Input", hi: "वॉइस इनपुट" },
  listening: { en: "Listening...", hi: "सुन रहा है..." },
  voice_on: { en: "Voice Read: ON", hi: "वॉइस रीड: चालू" },
  voice_off: { en: "Voice Read: OFF", hi: "वॉइस रीड: बंद" },
  text_size: { en: "Text:", hi: "टेक्स्ट:" },
  contrast_max: { en: "Contrast: Max", hi: "कंट्रास्ट: अधिकतम" },
  contrast_normal: { en: "Contrast: Normal", hi: "कंट्रास्ट: सामान्य" },

  // Scheme statuses
  status_verified: { en: "Verified", hi: "सत्यापित" },
  status_missing: { en: "Missing", hi: "लापता" },
  status_eligible: { en: "Eligible", hi: "पात्र" },
  status_potentially_eligible: { en: "Potentially Eligible", hi: "संभावित पात्र" },
  status_insufficient: { en: "Insufficient Information", hi: "अपर्याप्त जानकारी" },
  status_not_eligible: { en: "Not Eligible", hi: "पात्र नहीं" },

  // Document categories
  cat_other: { en: "Other / Unclassified", hi: "अन्य / अवर्गीकृत" },
  cat_aadhaar: { en: "Aadhaar Card", hi: "आधार कार्ड" },
  cat_pan: { en: "PAN Card", hi: "पैन कार्ड" },
  cat_income: { en: "Income Certificate", hi: "आय प्रमाण पत्र" },
  cat_caste: { en: "Caste Certificate", hi: "जाति प्रमाण पत्र" },
  cat_residence: { en: "Residence/Domicile", hi: "निवास/अधिवास" },
  cat_bank: { en: "Bank Passbook", hi: "बैंक पासबुक" },
  cat_land: { en: "Land Record / Khatauni", hi: "भूमि रिकॉर्ड / खतौनी" },
  cat_disability: { en: "Disability Certificate", hi: "दिव्यांगता प्रमाण पत्र" },
  cat_education: { en: "Marksheet / Certificate", hi: "मार्कशीट / प्रमाण पत्र" },
  cat_ration: { en: "Ration Card", hi: "राशन कार्ड" },
  cat_voter: { en: "Voter ID", hi: "मतदाता पहचान पत्र" },
  cat_business: { en: "Business Proof", hi: "व्यवसाय प्रमाण" },
  cat_vendor: { en: "Vendor Certificate", hi: "विक्रेता प्रमाण पत्र" },

  // States
  state_all: { en: "All", hi: "सभी" },
  state_up: { en: "Uttar Pradesh", hi: "उत्तर प्रदेश" },
  state_bihar: { en: "Bihar", hi: "बिहार" },
  state_maha: { en: "Maharashtra", hi: "महाराष्ट्र" },
  state_karnataka: { en: "Karnataka", hi: "कर्नाटक" },
  state_mp: { en: "Madhya Pradesh", hi: "मध्य प्रदेश" },
  state_raj: { en: "Rajasthan", hi: "राजस्थान" },
  state_guj: { en: "Gujarat", hi: "गुजरात" },
  state_delhi: { en: "Delhi", hi: "दिल्ली" },

  // Occupations
  occ_unemployed: { en: "Unemployed", hi: "बेरोजगार" },
  occ_farmer: { en: "Farmer", hi: "किसान" },
  occ_student: { en: "Student", hi: "छात्र" },
  occ_artisan: { en: "Artisan", hi: "कारीगर" },
  occ_business: { en: "Business Owner", hi: "व्यवसाय मालिक" },
  occ_vendor: { en: "Street Vendor", hi: "रेहड़ी-पटरी विक्रेता" },
  occ_salaried: { en: "Salaried", hi: "नौकरीपेशा" },

  // Categories
  cat_general: { en: "General", hi: "सामान्य" },
  cat_obc: { en: "OBC", hi: "अन्य पिछड़ा वर्ग" },
  cat_sc: { en: "SC", hi: "अनुसूचित जाति" },
  cat_st: { en: "ST", hi: "अनुसूचित जनजाति" },
  cat_ews: { en: "EWS", hi: "आर्थिक रूप से कमजोर वर्ग" },

  // Provider status and shared states
  provider_live: { en: "Live AI", hi: "लाइव AI" },
  provider_mock: { en: "Mock / rules", hi: "मॉक / नियम" },
  provider_unconfigured: { en: "AI not configured", hi: "AI कॉन्फ़िगर नहीं" },
  loading: { en: "Loading...", hi: "लोड हो रहा है..." },
  load_error: { en: "Could not load data. Check the backend connection.", hi: "डेटा लोड नहीं हो सका। बैकएंड कनेक्शन जांचें।" },
  retry: { en: "Retry", hi: "पुनः प्रयास" },

  // Misc
  scheme_saved_msg: {
    en: "Scheme saved to your Citizen Dashboard!",
    hi: "योजना आपके नागरिक डैशबोर्ड में सहेजी गई!"
  },
  scheme_applied_msg: {
    en: "Application submitted! Moving to Welfare Milestone Timeline...",
    hi: "आवेदन जमा किया गया! कल्याण मील का पत्थर समयरेखा पर ले जाया जा रहा है..."
  },
} as const;

export type TranslationKey = keyof typeof translations;

export function t(key: TranslationKey, lang: Language): string {
  const entry = translations[key];
  if (!entry) return key;
  return entry[lang] || entry["en"];
}

export default translations;
