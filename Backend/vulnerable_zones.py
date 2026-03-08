"""
Hardcoded vulnerable population zones for Central Valley counties.
Sources: USDA agricultural census, CA DOE school data, known farmworker housing areas.
"""

VULNERABLE_ZONES = {
    "Kern": [
        {"name": "Arvin Farmworker Housing", "type": "farm", "lat": 35.2094, "lon": -118.8289, "population_estimate": 8500},
        {"name": "Wasco Labor Camp Area", "type": "farm", "lat": 35.5933, "lon": -119.3408, "population_estimate": 4200},
        {"name": "Delano Agricultural Zone", "type": "farm", "lat": 35.7688, "lon": -119.2471, "population_estimate": 12000},
        {"name": "Shafter Farmworker District", "type": "farm", "lat": 35.5005, "lon": -119.2718, "population_estimate": 3800},
        {"name": "McFarland Elementary School", "type": "school", "lat": 35.6799, "lon": -119.2291, "population_estimate": 620},
        {"name": "Earlimart School District", "type": "school", "lat": 35.8849, "lon": -119.2718, "population_estimate": 890},
        {"name": "Kern County Fairgrounds Worksite", "type": "worksite", "lat": 35.3872, "lon": -119.0117, "population_estimate": 2100},
        {"name": "Bakersfield Oil Field Workers Zone", "type": "worksite", "lat": 35.3733, "lon": -119.0187, "population_estimate": 5600},
        {"name": "Taft Oilfield Construction Site", "type": "worksite", "lat": 35.1422, "lon": -119.4593, "population_estimate": 1800},
    ],
    "Fresno": [
        {"name": "Fresno Westside Farmworker Housing", "type": "farm", "lat": 36.7468, "lon": -120.0532, "population_estimate": 9200},
        {"name": "Sanger Agricultural Labor Zone", "type": "farm", "lat": 36.7080, "lon": -119.5549, "population_estimate": 5400},
        {"name": "Selma Farm Camp", "type": "farm", "lat": 36.5710, "lon": -119.6124, "population_estimate": 3100},
        {"name": "Firebaugh Migrant Housing", "type": "farm", "lat": 36.8580, "lon": -120.4574, "population_estimate": 4700},
        {"name": "Roosevelt High School Fresno", "type": "school", "lat": 36.7263, "lon": -119.7842, "population_estimate": 2400},
        {"name": "McLane High School", "type": "school", "lat": 36.7879, "lon": -119.8284, "population_estimate": 2100},
        {"name": "Fresno Construction Corridor", "type": "worksite", "lat": 36.7372, "lon": -119.7871, "population_estimate": 3200},
    ],
    "Tulare": [
        {"name": "Visalia Ag Worker Housing", "type": "farm", "lat": 36.3302, "lon": -119.2921, "population_estimate": 6800},
        {"name": "Porterville Farm District", "type": "farm", "lat": 36.0653, "lon": -119.0168, "population_estimate": 4900},
        {"name": "Lindsay Orange Grove Workers", "type": "farm", "lat": 36.2030, "lon": -119.0899, "population_estimate": 2800},
        {"name": "Tulare County Head Start", "type": "school", "lat": 36.2077, "lon": -119.0539, "population_estimate": 450},
        {"name": "Farmersville Elementary", "type": "school", "lat": 36.3005, "lon": -119.2099, "population_estimate": 680},
        {"name": "Exeter Packing House Workers", "type": "worksite", "lat": 36.2916, "lon": -119.1421, "population_estimate": 1400},
    ],
    "Kings": [
        {"name": "Hanford Farmworker Colony", "type": "farm", "lat": 36.3274, "lon": -119.6457, "population_estimate": 3200},
        {"name": "Lemoore Agricultural Labor Camp", "type": "farm", "lat": 36.3002, "lon": -119.7829, "population_estimate": 2100},
        {"name": "Avenal Migrant Housing", "type": "farm", "lat": 36.0030, "lon": -120.1285, "population_estimate": 1800},
        {"name": "Corcoran Elementary Schools", "type": "school", "lat": 36.0977, "lon": -119.5591, "population_estimate": 920},
        {"name": "Kings County Cotton Fields Worksite", "type": "worksite", "lat": 36.2000, "lon": -119.8500, "population_estimate": 2600},
    ],
    "Merced": [
        {"name": "Livingston Farm Labor Housing", "type": "farm", "lat": 37.3874, "lon": -120.7238, "population_estimate": 4100},
        {"name": "Los Banos Migrant Camp", "type": "farm", "lat": 36.6060, "lon": -120.8496, "population_estimate": 3600},
        {"name": "Dos Palos Agricultural Zone", "type": "farm", "lat": 36.9849, "lon": -120.6260, "population_estimate": 2200},
        {"name": "Merced Union High School", "type": "school", "lat": 37.3022, "lon": -120.4830, "population_estimate": 2800},
        {"name": "UC Merced (Outdoor Research Sites)", "type": "worksite", "lat": 37.3647, "lon": -120.4252, "population_estimate": 8500},
        {"name": "Atwater Orchard Workers Zone", "type": "worksite", "lat": 37.3474, "lon": -120.6096, "population_estimate": 1900},
    ],
    "Madera": [
        {"name": "Madera Farmworker Housing District", "type": "farm", "lat": 36.9613, "lon": -120.0607, "population_estimate": 5100},
        {"name": "Chowchilla Labor Camp", "type": "farm", "lat": 37.1227, "lon": -120.2607, "population_estimate": 2800},
        {"name": "Madera High School", "type": "school", "lat": 36.9627, "lon": -120.0573, "population_estimate": 2200},
        {"name": "Ripperdan State School", "type": "school", "lat": 36.9500, "lon": -120.1900, "population_estimate": 340},
        {"name": "Madera Vineyard Seasonal Workers", "type": "worksite", "lat": 36.8800, "lon": -120.1600, "population_estimate": 3100},
    ],
    "Stanislaus": [
        {"name": "Modesto Farmworker Zone", "type": "farm", "lat": 37.5630, "lon": -120.9877, "population_estimate": 7800},
        {"name": "Turlock Migrant Labor Housing", "type": "farm", "lat": 37.4946, "lon": -120.8466, "population_estimate": 4500},
        {"name": "Patterson Agricultural Workers", "type": "farm", "lat": 37.4713, "lon": -121.1285, "population_estimate": 2900},
        {"name": "Modesto High School", "type": "school", "lat": 37.6391, "lon": -120.9969, "population_estimate": 2600},
        {"name": "CSU Stanislaus (Outdoor Areas)", "type": "school", "lat": 37.5246, "lon": -120.8549, "population_estimate": 9500},
        {"name": "Ceres Construction Workers", "type": "worksite", "lat": 37.5949, "lon": -120.9577, "population_estimate": 2100},
    ],
    "San Joaquin": [
        {"name": "Stockton Farmworker Housing", "type": "farm", "lat": 37.9577, "lon": -121.2908, "population_estimate": 8900},
        {"name": "Lodi Vineyard Labor Zone", "type": "farm", "lat": 38.1302, "lon": -121.2722, "population_estimate": 5200},
        {"name": "Tracy Agricultural Workers", "type": "farm", "lat": 37.7397, "lon": -121.4252, "population_estimate": 3400},
        {"name": "Edison High School Stockton", "type": "school", "lat": 37.9688, "lon": -121.3211, "population_estimate": 2900},
        {"name": "UOP Outdoor Athletics", "type": "school", "lat": 37.9774, "lon": -121.3108, "population_estimate": 3600},
        {"name": "Port of Stockton Outdoor Workers", "type": "worksite", "lat": 37.9549, "lon": -121.3060, "population_estimate": 2800},
    ],
}


def get_zones_for_county(county: str) -> list:
    return VULNERABLE_ZONES.get(county, [])


def get_all_zones() -> dict:
    return VULNERABLE_ZONES
