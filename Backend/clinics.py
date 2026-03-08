"""
Hardcoded healthcare clinic/hospital data for the 8 Central Valley counties.
Focuses on facilities with Valley Fever expertise or general urgent/primary care.
"""

CLINICS = {
    "Kern": [
        {"name": "Kern Medical Center", "type": "hospital", "lat": 35.3816, "lon": -119.0233, "phone": "(661) 326-2000", "note": "Valley Fever expertise", "address": "1700 Mount Vernon Ave, Bakersfield"},
        {"name": "Dignity Health – Mercy Hospital", "type": "hospital", "lat": 35.3780, "lon": -119.0321, "phone": "(661) 632-5000", "note": "Regional trauma center", "address": "2215 Truxtun Ave, Bakersfield"},
        {"name": "Clinica Sierra Vista – Bakersfield", "type": "clinic", "lat": 35.3938, "lon": -119.1012, "phone": "(661) 635-3050", "note": "Community health center", "address": "7427 Meany Ave, Bakersfield"},
        {"name": "Adventist Health Bakersfield", "type": "hospital", "lat": 35.3561, "lon": -119.1003, "phone": "(661) 654-2000", "note": "Urgent & specialty care", "address": "2615 Eye St, Bakersfield"},
        {"name": "Valley Republic Medical Group", "type": "clinic", "lat": 35.4010, "lon": -119.0890, "phone": "(661) 321-0580", "note": "Primary care", "address": "9900 Stockdale Hwy, Bakersfield"},
    ],
    "Fresno": [
        {"name": "Community Regional Medical Center", "type": "hospital", "lat": 36.7410, "lon": -119.7847, "phone": "(559) 459-6000", "note": "Level 1 Trauma, Valley Fever cases", "address": "2823 Fresno St, Fresno"},
        {"name": "Valley Children's Hospital", "type": "hospital", "lat": 36.8088, "lon": -119.7734, "phone": "(559) 353-3000", "note": "Pediatric Valley Fever", "address": "9300 Valley Children's Pl, Madera"},
        {"name": "Fresno County Dept of Public Health", "type": "clinic", "lat": 36.7392, "lon": -119.7825, "phone": "(559) 600-3271", "note": "Free Valley Fever testing", "address": "1221 Fulton St, Fresno"},
        {"name": "Clinica Sierra Vista – Fresno", "type": "clinic", "lat": 36.7550, "lon": -119.7900, "phone": "(559) 228-4150", "note": "Sliding scale fees", "address": "3461 W Shields Ave, Fresno"},
        {"name": "Saint Agnes Medical Center", "type": "hospital", "lat": 36.7855, "lon": -119.8164, "phone": "(559) 450-3000", "note": "General & urgent care", "address": "1303 E Herndon Ave, Fresno"},
    ],
    "Tulare": [
        {"name": "Adventist Health Tulare", "type": "hospital", "lat": 36.2086, "lon": -119.0504, "phone": "(559) 688-0821", "note": "Primary & urgent care", "address": "869 N Cherry St, Tulare"},
        {"name": "Kaweah Health Medical Center", "type": "hospital", "lat": 36.3306, "lon": -119.2953, "phone": "(559) 624-2000", "note": "Regional Valley Fever care", "address": "400 W Mineral King Ave, Visalia"},
        {"name": "Porterville Sierra View Hospital", "type": "hospital", "lat": 36.0620, "lon": -119.0117, "phone": "(559) 784-1110", "note": "General acute care", "address": "465 W Putnam Ave, Porterville"},
        {"name": "Tulare County Health & Human Services", "type": "clinic", "lat": 36.2077, "lon": -119.0539, "phone": "(559) 624-7400", "note": "Public health testing", "address": "5957 S Mooney Blvd, Visalia"},
    ],
    "Kings": [
        {"name": "Adventist Health Hanford", "type": "hospital", "lat": 36.3292, "lon": -119.6402, "phone": "(559) 582-9000", "note": "Valley Fever diagnosis & treatment", "address": "115 Mall Dr, Hanford"},
        {"name": "Corcoran District Hospital", "type": "hospital", "lat": 36.0970, "lon": -119.5581, "phone": "(559) 992-5051", "note": "Rural acute care", "address": "1310 Hanna Ave, Corcoran"},
        {"name": "Kings Community Action Organization", "type": "clinic", "lat": 36.3100, "lon": -119.6450, "phone": "(559) 582-4386", "note": "Community health services", "address": "1222 W Lacey Blvd, Hanford"},
    ],
    "Merced": [
        {"name": "Dignity Health – Mercy Medical Center", "type": "hospital", "lat": 37.3018, "lon": -120.4821, "phone": "(209) 564-5000", "note": "Regional hospital, Valley Fever care", "address": "333 Mercy Ave, Merced"},
        {"name": "UC Merced Student Health", "type": "clinic", "lat": 37.3647, "lon": -120.4252, "phone": "(209) 228-2273", "note": "Student & faculty health", "address": "5200 N Lake Rd, Merced"},
        {"name": "Merced County Public Health", "type": "clinic", "lat": 37.3060, "lon": -120.4800, "phone": "(209) 381-1200", "note": "Free testing & prevention", "address": "260 E 15th St, Merced"},
        {"name": "Golden Valley Health Centers", "type": "clinic", "lat": 37.3100, "lon": -120.4870, "phone": "(209) 385-2500", "note": "FQHC, sliding scale fees", "address": "1525 W Main St, Merced"},
    ],
    "Madera": [
        {"name": "Madera Community Hospital", "type": "hospital", "lat": 36.9611, "lon": -120.0603, "phone": "(559) 675-5555", "note": "General & emergency care", "address": "1250 E Almond Ave, Madera"},
        {"name": "Valley Children's Hospital – Madera", "type": "hospital", "lat": 36.9550, "lon": -120.0600, "phone": "(559) 353-3000", "note": "Pediatric Valley Fever", "address": "9300 Valley Children's Pl, Madera"},
        {"name": "Madera County Public Health", "type": "clinic", "lat": 36.9627, "lon": -120.0573, "phone": "(559) 675-7893", "note": "Valley Fever education & testing", "address": "2037 W Cleveland Ave, Madera"},
    ],
    "Stanislaus": [
        {"name": "Memorial Medical Center", "type": "hospital", "lat": 37.6390, "lon": -120.9965, "phone": "(209) 526-4500", "note": "Level 2 Trauma", "address": "1700 Coffee Rd, Modesto"},
        {"name": "Doctors Medical Center", "type": "hospital", "lat": 37.6522, "lon": -121.0070, "phone": "(209) 578-1211", "note": "General acute care", "address": "1441 Florida Ave, Modesto"},
        {"name": "Stanislaus County Dept of Health", "type": "clinic", "lat": 37.6417, "lon": -120.9927, "phone": "(209) 558-7000", "note": "Public health, free Valley Fever info", "address": "830 Scenic Dr, Modesto"},
        {"name": "Central California Faculty Medical Group", "type": "clinic", "lat": 37.6350, "lon": -120.9900, "phone": "(209) 559-6000", "note": "Primary care", "address": "1700 Coffee Rd, Modesto"},
    ],
    "San Joaquin": [
        {"name": "San Joaquin General Hospital", "type": "hospital", "lat": 37.9780, "lon": -121.3020, "phone": "(209) 468-6000", "note": "Public hospital, Valley Fever care", "address": "500 W Hospital Rd, French Camp"},
        {"name": "St. Joseph's Medical Center", "type": "hospital", "lat": 37.9627, "lon": -121.3104, "phone": "(209) 943-2000", "note": "Level 2 Trauma center", "address": "1800 N California St, Stockton"},
        {"name": "Dameron Hospital", "type": "hospital", "lat": 37.9755, "lon": -121.3106, "phone": "(209) 944-5550", "note": "General & urgent care", "address": "525 W Acacia St, Stockton"},
        {"name": "San Joaquin County Public Health", "type": "clinic", "lat": 37.9577, "lon": -121.2908, "phone": "(209) 468-3439", "note": "Free Valley Fever testing", "address": "1601 E Hazelton Ave, Stockton"},
        {"name": "Asian Pacific Health Care Venture", "type": "clinic", "lat": 37.9600, "lon": -121.3000, "phone": "(209) 468-6000", "note": "Multilingual community health", "address": "201 E Center St, Stockton"},
    ],
}

CLINIC_TYPE_COLORS = {
    "hospital": "#ef4444",
    "clinic":   "#3b82f6",
    "urgent":   "#f97316",
}

def get_clinics_for_county(county: str) -> list:
    return CLINICS.get(county, [])

def get_all_clinics() -> list:
    all_clinics = []
    for county, items in CLINICS.items():
        for c in items:
            all_clinics.append({**c, "county": county})
    return all_clinics
