"""Editable catalog suggestions, not an exhaustive/authoritative aircraft register.

The ICAO Doc 8643 aircraft-type tool is the reference for aircraft designators.
Airline suggestions follow the Skytrax World Airline Awards 2026 Top 10.
This catalog is a maintained curated snapshot; users may enter other models.
"""
from fastapi import APIRouter

catalog_router = APIRouter(prefix='/api/catalog', tags=['Reference catalog'])

AIRLINES_2026 = [
    'Singapore Airlines', 'Qatar Airways', 'Cathay Pacific',
    'ANA All Nippon Airways', 'Turkish Airlines', 'Emirates',
    'Air France', 'Hainan Airlines', 'Japan Airlines', 'Korean Air',
]
# Full real-world catalogs contain many thousands of aircraft, military and
# historical variants. A concise curated civil aircraft index remains usable.
FAMILIES: dict[str, dict[str, list[str]]] = {
    'Airbus': {
        'regional': ['A220-100','A220-300'],
        'narrow_body': ['A318','A319','A319neo','A320','A320neo','A321','A321neo','A321LR','A321XLR'],
        'wide_body': ['A300B2','A300B4','A300-600','A310-200','A310-300','A330-200','A330-300','A330-800neo','A330-900neo',
                      'A340-200','A340-300','A340-500','A340-600','A350-900','A350-1000','A380-800','BelugaXL'],
    },
    'Boeing': {
        'narrow_body': ['717-200','727-100','727-200','737-100','737-200','737-300','737-400','737-500','737-600','737-700','737-800','737-900',
                        '737-700ER','737-900ER','737 MAX 7','737 MAX 8','737 MAX 8-200','737 MAX 9','737 MAX 10','757-200','757-300'],
        'wide_body': ['707-120','707-320','767-200','767-300','767-300F','767-400ER','747-100','747-200','747-300','747-400',
                      '747-400F','747-8','747-8F','777-200','777-200ER','777-200LR','777-300','777-300ER','777F','777-8','777-9',
                      '787-8','787-9','787-10'],
    },
    'Embraer': {
        'regional': ['EMB 110 Bandeirante','EMB 120 Brasilia','ERJ 135','ERJ 140','ERJ 145','E170','E175','E175-E2','E190','E190-E2','E195','E195-E2'],
    },
    'ATR': {
        'regional': ['ATR 42-300','ATR 42-320','ATR 42-400','ATR 42-500','ATR 42-600',
                     'ATR 72-200','ATR 72-210','ATR 72-500','ATR 72-600'],
    },
    'Bombardier': {
        'regional': ['CRJ100','CRJ200','CRJ440','CRJ550','CRJ700','CRJ900','CRJ1000','Dash 8-100','Dash 8-200','Dash 8-300','Dash 8 Q400'],
    },
    'De Havilland Canada': {
        'regional': ['DHC-2 Beaver','DHC-3 Otter','DHC-4 Caribou','DHC-6 Twin Otter','Dash 7','Dash 8-100','Dash 8-200','Dash 8-300','Dash 8-400'],
    },
    'COMAC': {
        'regional': ['ARJ21-700','C909'], 'narrow_body': ['C919'], 'wide_body': ['C929'],
    },
    'Sukhoi': {'regional': ['Superjet 100','SSJ100-95','SJ-100']},
    'Tupolev': {'narrow_body': ['Tu-134','Tu-154','Tu-204','Tu-214'], 'wide_body': ['Tu-144']},
    'Ilyushin': {'regional': ['Il-114'], 'wide_body': ['Il-62','Il-76','Il-86','Il-96-300']},
    'Antonov': {'regional': ['An-24','An-26','An-28','An-38','An-140','An-148','An-158'],
                'wide_body': ['An-124','An-225']},
    'Fokker': {'regional': ['F27 Friendship','F28 Fellowship','F50','F70','F100']},
    'BAe': {'regional': ['Jetstream 31','Jetstream 41','BAe 146-100','BAe 146-200','BAe 146-300','Avro RJ70','Avro RJ85','Avro RJ100']},
    'Saab': {'regional': ['Saab 340','Saab 2000']},
    'Dornier': {'regional': ['Do 228','Do 328','328JET']},
    'Mitsubishi': {'regional': ['SpaceJet M90','SpaceJet M100']},
    'Lockheed': {'wide_body': ['L-1011 TriStar','L-1011-500']},
    'McDonnell Douglas': {'narrow_body': ['DC-9-10','DC-9-30','MD-80','MD-81','MD-82','MD-83','MD-87','MD-88','MD-90'],
                          'wide_body': ['DC-10-10','DC-10-30','MD-11','MD-11F']},
    'Cessna': {'regional': ['208 Caravan','208B Grand Caravan','Citation CJ1','Citation CJ2','Citation CJ3','Citation CJ4','Citation XLS','Citation Latitude','Citation Longitude']},
    'Beechcraft': {'regional': ['1900D','King Air 90','King Air 200','King Air 250','King Air 350','King Air 360']},
    'Pilatus': {'regional': ['PC-6','PC-12','PC-24']},
    'Gulfstream': {'regional': ['G280','G450','G500','G550','G600','G650','G650ER','G700','G800']},
    'Dassault': {'regional': ['Falcon 50','Falcon 900','Falcon 2000','Falcon 6X','Falcon 7X','Falcon 8X','Falcon 10X']},
    'Airbus Defence': {'regional': ['C295'], 'wide_body': ['A400M']},
}

def entries() -> list[dict]:
    return sorted([
        {'manufacturer': manufacturer, 'model': model, 'category': category}
        for manufacturer, cats in FAMILIES.items()
        for category, models in cats.items()
        for model in models
    ], key=lambda item: (item['manufacturer'], item['model']))

@catalog_router.get('/aircraft-models')
def aircraft_models():
    return {'models': entries(), 'free_entry_allowed': True,
            'note': 'Catalogue civil sélectif, non exhaustif ; saisie libre autorisée.',
            'reference': 'https://www.icao.int/operational-safety/Designators-and-indicators'}

@catalog_router.get('/airlines')
def airlines():
    return {'airlines': AIRLINES_2026, 'free_entry_allowed': True,
            'ranking': 'Skytrax World Airline Awards 2026',
            'reference': 'https://www.worldairlineawards.com/worlds-top-100-airlines-2026/'}
