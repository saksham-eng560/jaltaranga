export type Language = 'en' | 'hi';

const messages = {
  en: {
    navCommand: 'Command', navColony: 'Colony', navCompare: 'Compare', navReport: 'Report',
    replay: 'Historical replay', notLive: 'Not a live alert', synthetic: 'Synthetic demo data',
    saveOffline: 'Save for offline', saved: 'Saved for this device', offline: 'Offline',
    waterTime: 'Time to water', noTime: 'Time estimate unavailable', earliest: 'Earliest', latest: 'Latest',
    route: 'Recommended route', shelter: 'Receiving shelter', freeBeds: 'places free',
    avoid: 'Roads to avoid', call: 'Call for help', draft: 'Draft dispatch', approve: 'Approve and send',
    listen: 'Listen in Hindi', deviceVoice: 'Device voice · may need internet',
  },
  hi: {
    navCommand: 'कमांड', navColony: 'बस्ती', navCompare: 'तुलना', navReport: 'रिपोर्ट',
    replay: 'पुरानी बाढ़ का पुनःदृश्य', notLive: 'अभी की चेतावनी नहीं', synthetic: 'डेमो का काल्पनिक डेटा',
    saveOffline: 'ऑफ़लाइन के लिए सहेजें', saved: 'इस डिवाइस पर सहेजा गया', offline: 'ऑफ़लाइन',
    waterTime: 'पानी आने का समय', noTime: 'समय का अनुमान उपलब्ध नहीं', earliest: 'जल्द से जल्द', latest: 'देर से देर',
    route: 'सुरक्षित रास्ता', shelter: 'राहत केंद्र', freeBeds: 'जगह खाली',
    avoid: 'इन रास्तों से बचें', call: 'मदद के लिए कॉल करें', draft: 'संदेश का मसौदा', approve: 'मंज़ूर करें और भेजें',
    listen: 'हिंदी में सुनें', deviceVoice: 'डिवाइस की आवाज़ · इंटरनेट की ज़रूरत हो सकती है',
  },
} as const;

export function translate(language: Language, key: keyof typeof messages.en): string {
  return messages[language][key];
}
