"""
Generate synthetic emergency response test data for disaster scenarios.
Creates reports with locations distributed around Abingdon, UK.
"""

import json
import random
import math
from datetime import datetime, timedelta

# Abingdon town center coordinates
ABINGDON_CENTER_LAT = 51.6708
ABINGDON_CENTER_LON = -1.2834

# Report types with weighted probabilities
REPORT_TYPES = {
    "BUILDING_COLLAPSE": 15,
    "FIRE": 12,
    "FLOOD": 10,
    "SURVIVORS_RESCUED": 20,
    "MEDICAL_EMERGENCY": 18,
    "MISSING_PERSON": 8,
    "LOOTING": 5,
    "POWER_OUTAGE": 6,
    "GAS_LEAK": 4,
    "ROAD_BLOCKED": 10,
    "BRIDGE_DAMAGE": 3,
    "SHELTER_REQUEST": 12,
    "WATER_CONTAMINATION": 3,
    "TERRORIST_INCIDENT": 1,
    "HAZMAT_SPILL": 2,
    "TRAPPED_VICTIMS": 8,
}

# Personnel types
PERSONNEL_TYPES = [
    "Fire Crew",
    "Police Unit",
    "Paramedic Team",
    "Search & Rescue",
    "Emergency Medical Team",
    "Hazmat Team",
    "Civil Defense",
    "Bomb Squad",
    "K9 Unit",
    "Technical Rescue Team"
]

# Sample street names in Abingdon area
STREET_NAMES = [
    "High Street", "Ock Street", "Bridge Street", "Bath Street", "West St Helen Street",
    "East St Helen Street", "Market Place", "Vineyard", "Park Road", "Radley Road",
    "Oxford Road", "Marcham Road", "Spring Road", "Caldecott Road", "Northcourt Road",
    "Drayton Road", "Wantage Road", "Peachcroft Road", "Thames Street", "Abbey Close"
]

def generate_random_location(center_lat, center_lon, radius_miles):
    """
    Generate random coordinates within a circular radius.
    Uses uniform distribution to avoid clustering at center.
    """
    # Convert radius from miles to degrees (approximate)
    radius_deg = radius_miles / 69.0
    
    # Generate random angle and radius with sqrt for uniform distribution
    angle = random.uniform(0, 2 * math.pi)
    r = math.sqrt(random.uniform(0, 1)) * radius_deg
    
    # Calculate new coordinates
    lat = center_lat + r * math.cos(angle)
    lon = center_lon + r * math.sin(angle) / math.cos(math.radians(center_lat))
    
    return round(lat, 6), round(lon, 6)

def generate_personnel(report_type):
    """Generate appropriate personnel based on report type"""
    personnel = []
    
    if report_type in ["BUILDING_COLLAPSE", "FIRE", "TRAPPED_VICTIMS"]:
        personnel.append({
            "type": "Fire Crew",
            "unit_id": f"FC-{random.randint(100, 999)}",
            "count": random.randint(4, 8)
        })
        personnel.append({
            "type": "Search & Rescue",
            "unit_id": f"SAR-{random.randint(10, 99)}",
            "count": random.randint(3, 6)
        })
    
    if report_type in ["MEDICAL_EMERGENCY", "SURVIVORS_RESCUED", "TRAPPED_VICTIMS"]:
        personnel.append({
            "type": "Paramedic Team",
            "unit_id": f"EMT-{random.randint(100, 999)}",
            "count": random.randint(2, 4)
        })
    
    if report_type in ["LOOTING", "TERRORIST_INCIDENT", "MISSING_PERSON"]:
        personnel.append({
            "type": "Police Unit",
            "unit_id": f"PU-{random.randint(1000, 9999)}",
            "count": random.randint(2, 6)
        })
    
    if report_type in ["GAS_LEAK", "HAZMAT_SPILL"]:
        personnel.append({
            "type": "Hazmat Team",
            "unit_id": f"HZ-{random.randint(10, 99)}",
            "count": random.randint(3, 5)
        })
    
    if report_type == "TERRORIST_INCIDENT":
        personnel.append({
            "type": "Bomb Squad",
            "unit_id": f"BS-{random.randint(1, 20)}",
            "count": random.randint(4, 6)
        })
    
    # Add general support if no specific personnel assigned
    if not personnel:
        personnel.append({
            "type": random.choice(["Police Unit", "Civil Defense"]),
            "unit_id": f"CD-{random.randint(100, 999)}",
            "count": random.randint(2, 4)
        })
    
    return personnel

def generate_description(report_type, street):
    """Generate realistic incident description"""
    descriptions = {
        "BUILDING_COLLAPSE": [
            f"Multi-story residential building collapsed on {street}. Multiple casualties reported, search and rescue operations ongoing.",
            f"Partial building collapse at {street}. Structure unstable, evacuation of adjacent buildings ordered.",
            f"Commercial building on {street} has suffered major structural failure. Heavy machinery required for debris removal."
        ],
        "FIRE": [
            f"Large fire reported at residential property on {street}. Flames visible, smoke affecting nearby areas.",
            f"Commercial building fire on {street}. Multiple units responding, road closures in effect.",
            f"Vehicle fire on {street} has spread to adjacent structures. Evacuations underway."
        ],
        "FLOOD": [
            f"Severe flooding on {street}. Water levels rising, multiple properties affected. Residents trapped on upper floors.",
            f"Flash flooding reported along {street}. Road impassable, vehicles stranded.",
            f"Water main burst on {street} causing significant flooding. Gas and electricity supply interrupted."
        ],
        "SURVIVORS_RESCUED": [
            f"Two survivors extracted from collapsed structure on {street}. Both conscious, receiving medical attention.",
            f"Family of four rescued from flooded property on {street}. Minor injuries, transported to hospital.",
            f"Elderly couple found alive in debris on {street}. Search and rescue team assisted by K9 unit."
        ],
        "MEDICAL_EMERGENCY": [
            f"Mass casualty incident on {street}. Multiple injuries reported, triage area established.",
            f"Cardiac arrest patient stabilized on {street}. Air ambulance requested for transport.",
            f"Multiple trauma patients from incident on {street}. Field hospital being set up."
        ],
        "MISSING_PERSON": [
            f"Child reported missing near {street}. Last seen 2 hours ago wearing blue jacket. Search teams deployed.",
            f"Elderly person with dementia missing from care facility on {street}. Vulnerable adult, immediate search initiated.",
            f"Person unaccounted for following building collapse on {street}. Family providing description."
        ],
        "LOOTING": [
            f"Reports of looting at commercial premises on {street}. Police units responding, securing area.",
            f"Multiple suspects seen entering damaged properties on {street}. Anti-looting patrols increased.",
            f"Store on {street} broken into during evacuation. Suspects fled on foot, investigation ongoing."
        ],
        "POWER_OUTAGE": [
            f"Complete power outage affecting {street} and surrounding area. Estimated 500+ properties affected.",
            f"Transformer failure on {street} has left entire neighborhood without electricity. Repair crews dispatched.",
            f"Downed power lines on {street} creating hazardous conditions. Area cordoned off, power company notified."
        ],
        "GAS_LEAK": [
            f"Major gas leak reported on {street}. 100-meter exclusion zone established, residents evacuated.",
            f"Strong smell of gas on {street}. Gas supply isolated, hazmat team conducting safety checks.",
            f"Gas main damaged by falling debris on {street}. Immediate evacuation ordered, repair crews en route."
        ],
        "ROAD_BLOCKED": [
            f"Road completely blocked on {street} by debris and damaged vehicles. Alternate routes advised.",
            f"Fallen tree blocking all lanes on {street}. Heavy machinery required for clearance.",
            f"Bridge approach on {street} blocked by structural damage. Road closed indefinitely pending assessment."
        ],
        "BRIDGE_DAMAGE": [
            f"Critical structural damage to bridge on {street}. Bridge closed to all traffic, engineers assessing.",
            f"Bridge support compromised on {street}. Immediate closure ordered, risk of collapse assessed as high.",
            f"Visible cracks in bridge structure on {street}. Emergency structural survey in progress."
        ],
        "SHELTER_REQUEST": [
            f"Family evacuated from {street} requiring emergency shelter. 4 adults, 2 children, pet dog.",
            f"Group of 15 residents from {street} need temporary accommodation. Currently at evacuation center.",
            f"Elderly residents from care home on {street} require alternative accommodation. 8 people, medical needs."
        ],
        "WATER_CONTAMINATION": [
            f"Water supply contaminated in {street} area. Boil water notice issued, bottled water being distributed.",
            f"Sewage contamination affecting water supply on {street}. Do not use for drinking or cooking.",
            f"Chemical spill has contaminated water main serving {street}. Alternative water supply being arranged."
        ],
        "TERRORIST_INCIDENT": [
            f"Suspicious package found on {street}. Area evacuated, bomb disposal unit en route.",
            f"Reported explosive device on {street}. EOD team on scene, 500m cordon established.",
            f"Suspected terrorist activity on {street}. Counter-terrorism units deployed, public advised to stay away."
        ],
        "HAZMAT_SPILL": [
            f"Chemical spill reported on {street}. Unknown substance, hazmat team conducting assessment.",
            f"Industrial chemicals leaked on {street} from damaged tanker. Evacuation in progress.",
            f"Toxic fumes detected on {street}. Hazmat crews wearing protective equipment, residents advised to stay indoors."
        ],
        "TRAPPED_VICTIMS": [
            f"Three people trapped in vehicle on {street}. Fire crews using cutting equipment for extraction.",
            f"Person trapped in elevator on {street} following power failure. Technical rescue team responding.",
            f"Multiple victims trapped in basement on {street} due to collapsed stairwell. Heavy rescue equipment deployed."
        ],
    }
    
    return random.choice(descriptions[report_type])

def generate_report(report_id, base_time):
    """Generate a single emergency report"""
    # Select report type based on weighted probabilities
    report_type = random.choices(
        list(REPORT_TYPES.keys()),
        weights=list(REPORT_TYPES.values()),
        k=1
    )[0]
    
    # Generate random location within 2 miles of Abingdon center
    lat, lon = generate_random_location(ABINGDON_CENTER_LAT, ABINGDON_CENTER_LON, 2.0)
    
    # Generate timestamp (spread over 24 hours from base time)
    time_offset = timedelta(hours=random.uniform(0, 24))
    timestamp = base_time + time_offset
    
    # Generate street address
    street = random.choice(STREET_NAMES)
    building_number = random.randint(1, 200)
    
    # Generate personnel
    personnel = generate_personnel(report_type)
    
    # Generate description
    description = generate_description(report_type, street)
    
    # Severity level
    severity = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    if report_type in ["TERRORIST_INCIDENT", "BUILDING_COLLAPSE", "TRAPPED_VICTIMS"]:
        severity = random.choice(["HIGH", "CRITICAL"])
    
    # Status
    status = random.choice(["ACTIVE", "RESPONDING", "RESOLVED", "INVESTIGATING"])
    
    report = {
        "report_id": f"RPT-{report_id:05d}",
        "timestamp": timestamp.isoformat(),
        "report_type": report_type,
        "severity": severity,
        "status": status,
        "location": {
            "latitude": lat,
            "longitude": lon,
            "address": f"{building_number} {street}, Abingdon, Oxfordshire",
            "grid_reference": f"SU{random.randint(40000, 60000)}{random.randint(90000, 99000)}"
        },
        "personnel": personnel,
        "description": description,
        "casualties": {
            "fatalities": random.randint(0, 5) if report_type in ["BUILDING_COLLAPSE", "TERRORIST_INCIDENT"] else 0,
            "injured": random.randint(0, 10) if report_type in ["BUILDING_COLLAPSE", "MEDICAL_EMERGENCY", "TRAPPED_VICTIMS"] else random.randint(0, 3),
            "missing": random.randint(0, 3) if report_type == "MISSING_PERSON" else 0,
            "rescued": random.randint(1, 6) if report_type == "SURVIVORS_RESCUED" else 0
        },
        "resources_needed": generate_resources_needed(report_type),
        "reported_by": {
            "name": f"Officer {random.choice(['Smith', 'Jones', 'Williams', 'Brown', 'Taylor', 'Davies', 'Wilson', 'Evans', 'Thomas', 'Johnson'])}",
            "badge_id": f"{random.choice(['PC', 'FC', 'PMD'])}-{random.randint(1000, 9999)}",
            "contact": f"+44 7{random.randint(100000000, 999999999)}"
        }
    }
    
    return report

def generate_resources_needed(report_type):
    """Generate list of resources needed for incident"""
    resources = []
    
    resource_map = {
        "BUILDING_COLLAPSE": ["Heavy rescue equipment", "Structural engineers", "Medical supplies", "Temporary shelter"],
        "FIRE": ["Water tankers", "Breathing apparatus", "Thermal imaging", "First aid kits"],
        "FLOOD": ["Pumps", "Sandbags", "Rescue boats", "Emergency accommodation"],
        "MEDICAL_EMERGENCY": ["Ambulances", "Medical supplies", "Blood products", "Hospital beds"],
        "GAS_LEAK": ["Gas detection equipment", "Protective suits", "Ventilation equipment"],
        "HAZMAT_SPILL": ["Containment barriers", "Decontamination units", "Protective equipment"],
        "TERRORIST_INCIDENT": ["EOD equipment", "Forensic teams", "Armed support", "Cordon tape"],
        "TRAPPED_VICTIMS": ["Cutting equipment", "Lifting gear", "Medical supplies", "Lighting equipment"],
        "SHELTER_REQUEST": ["Emergency housing", "Food supplies", "Blankets", "Medical screening"],
        "WATER_CONTAMINATION": ["Bottled water", "Water testing kits", "Alternative supply equipment"],
        "ROAD_BLOCKED": ["Heavy machinery", "Traffic management", "Alternative route signs"],
        "BRIDGE_DAMAGE": ["Structural engineers", "Traffic diversion", "Inspection equipment"],
    }
    
    if report_type in resource_map:
        resources = random.sample(resource_map[report_type], k=random.randint(2, len(resource_map[report_type])))
    else:
        resources = ["General supplies", "Personnel support"]
    
    return resources

def main():
    """Generate test data"""
    print("Generating emergency response test data for Abingdon area...")
    
    # Base time (start of disaster scenario)
    base_time = datetime.now() - timedelta(hours=12)
    
    # Generate 50-100 reports
    num_reports = random.randint(50, 100)
    reports = []
    
    for i in range(1, num_reports + 1):
        report = generate_report(i, base_time)
        reports.append(report)
    
    # Save to JSON file
    output_file = "emergency_reports_abingdon.json"
    with open(output_file, 'w') as f:
        json.dump({
            "scenario": "Abingdon Disaster Response Exercise",
            "scenario_start": base_time.isoformat(),
            "location": {
                "name": "Abingdon, Oxfordshire, UK",
                "center_lat": ABINGDON_CENTER_LAT,
                "center_lon": ABINGDON_CENTER_LON,
                "radius_miles": 2.0
            },
            "total_reports": num_reports,
            "reports": reports
        }, f, indent=2)
    
    print(f"\n✓ Generated {num_reports} emergency reports")
    print(f"✓ Saved to: {output_file}")
    
    # Print summary statistics
    report_type_counts = {}
    for report in reports:
        rt = report['report_type']
        report_type_counts[rt] = report_type_counts.get(rt, 0) + 1
    
    print("\nReport Type Distribution:")
    for rt, count in sorted(report_type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {rt}: {count}")
    
    total_casualties = sum(r['casualties']['fatalities'] for r in reports)
    total_injured = sum(r['casualties']['injured'] for r in reports)
    total_rescued = sum(r['casualties']['rescued'] for r in reports)
    
    print(f"\nCasualty Summary:")
    print(f"  Fatalities: {total_casualties}")
    print(f"  Injured: {total_injured}")
    print(f"  Rescued: {total_rescued}")

if __name__ == "__main__":
    main()
