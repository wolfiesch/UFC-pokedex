import CountryFlag from '@/components/CountryFlag';

export default function TestFlagsPage() {
  const countries = ['US', 'BR', 'IE', 'RU', 'GB', 'CA', 'MX', 'AU'];

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Country Flags Test</h1>
      <div className="space-y-2">
        {countries.map((code) => (
          <div key={code} className="flex items-center gap-2">
            <CountryFlag countryCode={code} alt={code} />
            <span>{code}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
