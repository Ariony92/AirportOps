import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export type CatalogModel = { manufacturer: string; model: string; category: 'regional' | 'narrow_body' | 'wide_body' };

export function useAviationCatalog() {
  const [airlines, setAirlines] = useState<string[]>([]);
  const [models, setModels] = useState<CatalogModel[]>([]);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetch(`${API}/api/catalog/airlines`).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
      fetch(`${API}/api/catalog/aircraft-models`).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
    ]).then(([a, m]) => {
      if (active) {
        setAirlines(a.airlines as string[]);
        setModels(m.models as CatalogModel[]);
      }
    }).catch(() => {
      // Entries remain manually editable if suggestions are unavailable.
    });
    return () => { active = false; };
  }, []);
  return { airlines, models };
}
