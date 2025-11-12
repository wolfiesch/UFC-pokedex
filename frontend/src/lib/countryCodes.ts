import countries from "i18n-iso-countries";
import enLocale from "i18n-iso-countries/langs/en.json";

countries.registerLocale(enLocale);

const DEMONYM_TO_ISO: Record<string, string> = {
  american: "US",
  argentine: "AR",
  argentinian: "AR",
  australian: "AU",
  brazilian: "BR",
  british: "GB",
  canadian: "CA",
  chilean: "CL",
  chinese: "CN",
  colombian: "CO",
  cuban: "CU",
  danish: "DK",
  dominican: "DO",
  dutch: "NL",
  english: "GB",
  french: "FR",
  german: "DE",
  ghanaian: "GH",
  irish: "IE",
  italian: "IT",
  jamaican: "JM",
  japanese: "JP",
  mexican: "MX",
  moroccan: "MA",
  "new zealander": "NZ",
  nigerian: "NG",
  norwegian: "NO",
  peruvian: "PE",
  polish: "PL",
  portuguese: "PT",
  russian: "RU",
  scottish: "GB",
  serbian: "RS",
  "south african": "ZA",
  spanish: "ES",
  swedish: "SE",
  swiss: "CH",
  turkish: "TR",
  welsh: "GB",
};

export function toCountryIsoCode(countryOrDemonym?: string | null): string | null {
  if (!countryOrDemonym) {
    return null;
  }

  const normalized = countryOrDemonym.trim();
  if (!normalized) {
    return null;
  }

  const isoFromName = countries.getAlpha2Code(normalized, "en");
  if (isoFromName) {
    return isoFromName.toUpperCase();
  }

  const isoFromDemonym = DEMONYM_TO_ISO[normalized.toLowerCase()];
  return isoFromDemonym ?? null;
}
