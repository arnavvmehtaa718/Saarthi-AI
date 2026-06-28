from typing import Dict, Any, Union
from app.agents.base import BaseAgent

class AITranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="AI Translator Agent",
            description="Translates government scheme instructions, caseworker notes, and alerts into Hindi."
        )
        
        # High-fidelity static translations for seeded schemes & terms to support 100% offline mock execution
        self.translation_dictionary = {
            "eligible": "पात्र (Eligible)",
            "likely eligible": "संभावित पात्र (Likely Eligible)",
            "missing information": "अपूर्ण जानकारी (Missing Information)",
            "not eligible": "अपात्र (Not Eligible)",
            "aadhaar": "आधार कार्ड (Aadhaar Card)",
            "pan": "पैन कार्ड (PAN Card)",
            "income": "आय प्रमाण पत्र (Income Certificate)",
            "caste": "जाति प्रमाण पत्र (Caste Certificate)",
            "residence": "निवास प्रमाण पत्र (Domicile/Residence Proof)",
            "bank": "बैंक पासबुक (Bank Passbook)",
            "land": "भूमि रिकॉर्ड / खतौनी (Land Records / Khatauni)",
            "disability": "दिव्यांगता प्रमाण पत्र (Disability Certificate)",
            "education": "शैक्षणिक प्रमाण पत्र / मार्कशीट (Educational Marksheet)",
            "other": "अन्य दस्तावेज (Other Document)",
            "farmer": "किसान (Farmer)",
            "student": "छात्र (Student)",
            "street vendor": "रेहड़ी-पटरी विक्रेता / स्ट्रीट वेंडर (Street Vendor)",
            "artisan": "कारीगर / शिल्पकार (Artisan)",
            "business owner": "व्यवसाय मालिक (Business Owner)",
            "unemployed": "बेरोजगार (Unemployed)",
            "salaried": "नौकरीपेशा (Salaried)",
            
            # PM-KISAN
            "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)": "पीएम-किसान (प्रधानमंत्री किसान सम्मान निधि)",
            "A Central Sector scheme to provide income support to all landholding farmer families in the country to enable them to take care of agricultural expenses and domestic needs.": "देश के सभी भूमिधारक किसान परिवारों को कृषि खर्चों और घरेलू जरूरतों को पूरा करने के लिए एक केंद्रीय योजना।",
            "Direct benefit transfer of ₹6,000 per year, paid in three equal installments of ₹2,000 directly into the bank accounts of the beneficiary farmers.": "वार्षिक ₹6,000 का प्रत्यक्ष लाभ हस्तांतरण, जो ₹2,000 की तीन समान किश्तों में सीधे लाभार्थी किसानों के बैंक खातों में भेजा जाता है।",
            
            # Ayushman Bharat
            "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (PM-JAY)": "आयुष्मान भारत - प्रधानमंत्री जन आरोग्य योजना",
            "The largest health assurance scheme in the world, aiming to provide free health cover up to ₹5 Lakh per family per year for secondary and tertiary care hospitalization.": "दुनिया की सबसे बड़ी स्वास्थ्य बीमा योजना, जिसका उद्देश्य प्रति परिवार प्रति वर्ष ₹5 लाख तक का मुफ्त स्वास्थ्य कवर प्रदान करना है।",
            "Cashless and paperless access to healthcare services up to ₹5,00,000 per family per year for over 1,300 medical procedures at empanelled public and private hospitals.": "पैनल में शामिल सरकारी और निजी अस्पतालों में 1,300 से अधिक चिकित्सा प्रक्रियाओं के लिए प्रति परिवार प्रति वर्ष ₹5,00,000 तक कैशलेस और पेपरलेस स्वास्थ्य सेवाएं।",
        }

    def translate(self, text: str, target_lang: str = "hi") -> str:
        """Translate text into the target language."""
        if not text or target_lang.lower() == "en":
            return text
            
        # Try finding in the dictionary first
        if text in self.translation_dictionary:
            return self.translation_dictionary[text]
            
        # Try lowercase check
        if text.lower() in self.translation_dictionary:
            return self.translation_dictionary[text.lower()]

        if self.use_real_ai:
            system_instruction = (
                f"You are a professional government caseworker translator. "
                f"Translate the text accurately into {target_lang} (Devanagari script for Hindi). "
                f"Keep technical scheme names and document names in parenthesis in English for clarity if needed. "
                f"Only return the translated string."
            )
            prompt = f"Translate this text:\n{text}"
            try:
                translated_text = self.run_llm(prompt, system_instruction)
                return translated_text
            except Exception:
                pass # fallback to original

        # Mock translator (pre-appends language code indicator if not in dict)
        if target_lang.lower() == "hi":
            return f"[अनुवादित] {text}"
        return text

    def translate_scheme(self, scheme_data: Dict[str, Any], target_lang: str = "hi") -> Dict[str, Any]:
        """Translates a dictionary of scheme details."""
        if target_lang.lower() == "en":
            return scheme_data
            
        translated = scheme_data.copy()
        
        # Translate main fields
        translated["title"] = self.translate(scheme_data.get("title", ""), target_lang)
        translated["description"] = self.translate(scheme_data.get("description", ""), target_lang)
        translated["benefit_details"] = self.translate(scheme_data.get("benefit_details", ""), target_lang)
        
        if "eli15_explanation" in scheme_data:
            translated["eli15_explanation"] = self.translate(scheme_data["eli15_explanation"], target_lang)
            
        if "steps" in scheme_data:
            translated["steps"] = [self.translate(step, target_lang) for step in scheme_data["steps"]]
            
        return translated
