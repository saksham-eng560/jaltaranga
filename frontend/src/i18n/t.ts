import hi from './hi.json';
import en from './en.json';

const dictionaries = { hi, en };

export function t(key: keyof typeof hi, lang: 'hi' | 'en' = 'hi'): string {
  const dict = dictionaries[lang] || dictionaries.hi;
  return dict[key] || key;
}
