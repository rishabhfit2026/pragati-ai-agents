"""Synthetic demo tenders (section 29/30). All entities, tender numbers, and
figures are FICTIONAL — clearly labelled DEMO DATA in the UI — used only to
exercise the pipeline. Content is written in a style typical of Indian
government/defence procurement documents so the extraction heuristics have
something realistic to parse."""

DEMO_TENDERS: list[dict] = [
    {
        "key": "helmet-flagship",
        "meta": {
            "title": "Procurement of Ballistic Combat Helmets for Infantry Battalions",
            "tender_number": "IA/ORD/2026/HEL-014",
            "issuing_organization": "Indian Army - Directorate of Ordnance",
            "issue_date": "02 Aug 2026",
            "submission_deadline": "10 Oct 2026",
            "delivery_deadline": "12 months from date of contract signing",
            "geography": "Pan-India, consignee depots as per Annexure A",
            "estimated_quantity": "12,000 units",
            "product_category": "Combat Helmet",
        },
        "sections": [
            {"heading": "BALLISTIC AND TECHNICAL REQUIREMENTS", "items": [
                "The helmet shall provide ballistic protection at NIJ Level IIIA standalone as a mandatory baseline.",
                "The helmet shall be capable of defeating AK-47 API BZ threats when fitted with an appliqué upgrade.",
                "Back-face deformation shall not exceed 16mm under standard test conditions.",
                "The helmet shall be compatible with night vision goggle mounting rails.",
                "The helmet shell weight should not exceed 1.1 kg for the base configuration.",
            ]},
            {"heading": "MATERIAL AND PERFORMANCE REQUIREMENTS", "items": [
                "Helmet shell material shall be aramid or ceramic-composite based construction.",
                "Retention system shall provide a secure multi-point fit adjustable across standard head sizes.",
                "Shelf life of the helmet shall be a minimum of 7 years from date of manufacture.",
            ]},
            {"heading": "CERTIFICATION AND ELIGIBILITY REQUIREMENTS", "items": [
                "Bidder shall submit valid NIJ 0101.06 certification for the offered helmet model.",
                "Bidder must be an OEM with its own manufacturing facility for ballistic helmets.",
            ]},
            {"heading": "DOCUMENTATION REQUIREMENTS", "items": [
                "Bidder shall submit a technical datasheet for the offered helmet model.",
            ]},
        ],
    },
    {
        "key": "vest-capf",
        "meta": {
            "title": "Supply of Bullet Resistant Jackets for Frontline Personnel",
            "tender_number": "CAPF/PROC/2026/BRJ-221",
            "issuing_organization": "Central Armed Police Force",
            "issue_date": "14 Jul 2026",
            "submission_deadline": "05 Sep 2026",
            "delivery_deadline": "45 days from date of contract",
            "geography": "India",
            "estimated_quantity": "4,500 units",
            "product_category": "Body Armour / Bullet Resistant Jacket",
        },
        "sections": [
            {"heading": "BALLISTIC AND TECHNICAL REQUIREMENTS", "items": [
                "The jacket shall provide protection at NIJ Level IV front, back and side panels.",
                "The jacket shall include detachable throat and groin protection panels.",
                "Jacket weight shall not exceed 10.5 kg for the complete kit including plates.",
                "The carrier shall provide 360 degree MOLLE webbing for pouch attachment.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder shall submit valid BIS certification for the offered ballistic panels.",
                "Bidder shall submit accredited third-party ballistic test reports for the current production batch.",
                "Bidder shall hold ISO 9001:2015 certification for its manufacturing unit.",
            ]},
            {"heading": "ELIGIBILITY CRITERIA", "items": [
                "Bidder must be an OEM manufacturer with in-house production facility.",
                "Bidder shall have a minimum annual turnover of INR 20 crore in each of the last 3 years.",
            ]},
            {"heading": "DELIVERY REQUIREMENTS", "items": [
                "Complete quantity shall be delivered within 45 days of contract signature.",
            ]},
        ],
    },
    {
        "key": "shield-state-police",
        "meta": {
            "title": "Procurement of Riot and Ballistic Shields for Rapid Action Force",
            "tender_number": "SP/RAF/2026/SHD-088",
            "issuing_organization": "State Police - Rapid Action Force",
            "issue_date": "20 Jun 2026",
            "submission_deadline": "18 Aug 2026",
            "delivery_deadline": "6 months from date of contract",
            "geography": "India",
            "estimated_quantity": "600 units",
            "product_category": "Ballistic Shield",
        },
        "sections": [
            {"heading": "BALLISTIC AND TECHNICAL REQUIREMENTS", "items": [
                "The shield shall provide protection at NIJ Level IV / BIS L6 against rifle threats.",
                "The shield shall include an integrated viewport of minimum 20x10 cm, replaceable in the field.",
                "The shield shall be capable of stopping multiple 7.62x39 API BZ hits without failure.",
                "In-hand carry weight of the shield should not exceed 6 kg for extended operations.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder shall submit valid NIJ or BIS certification for the offered shield model.",
                "Bidder should submit an independent ballistic test report from an accredited laboratory.",
            ]},
            {"heading": "ELIGIBILITY CRITERIA", "items": [
                "Bidder must be an OEM with its own manufacturing facility for ballistic shields.",
            ]},
        ],
    },
    {
        "key": "vehicle-armour-bsf",
        "meta": {
            "title": "Supply and Fitment of Vehicle Armour Retrofit Kits",
            "tender_number": "BSF/VEH/2026/ARM-305",
            "issuing_organization": "Border Security Force",
            "issue_date": "01 Jul 2026",
            "submission_deadline": "30 Sep 2026",
            "delivery_deadline": "9 months from date of contract",
            "geography": "Border outposts, Northern and Western sectors",
            "estimated_quantity": "180 vehicle kits",
            "product_category": "Vehicle Protection / Platform Armour",
        },
        "sections": [
            {"heading": "BALLISTIC AND TECHNICAL REQUIREMENTS", "items": [
                "The armour kit shall meet STANAG 4569 Level 2 protection against 7.62x51 AP threats.",
                "The armour kit shall provide protection against 14.5mm API B32 threats for command vehicles.",
                "The kit shall be retrofittable without permanent modification to the vehicle chassis.",
                "The kit shall include underbelly blast protection against anti-tank mine threats.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder shall submit STANAG 4569 test certification from a recognized testing agency.",
                "Bidder shall hold DGQA approval for supply of vehicle armour to defence forces.",
            ]},
            {"heading": "MANUFACTURING REQUIREMENTS", "items": [
                "Bidder shall demonstrate manufacturing capacity for 180 vehicle kits within the delivery period.",
            ]},
            {"heading": "ELIGIBILITY CRITERIA", "items": [
                "Bidder must be an OEM with its own manufacturing facility for composite armour panels.",
            ]},
        ],
    },
    {
        "key": "riot-combo-municipal",
        "meta": {
            "title": "Supply of Riot Control Helmets and Shields for Municipal Security Wing",
            "tender_number": "MC/SEC/2026/RIOT-047",
            "issuing_organization": "Municipal Corporation Security Wing",
            "issue_date": "11 May 2026",
            "submission_deadline": "25 Jun 2026",
            "delivery_deadline": "60 days from date of contract",
            "geography": "India",
            "estimated_quantity": "1,200 units combined",
            "product_category": "Riot Gear / Helmets and Shields",
        },
        "sections": [
            {"heading": "TECHNICAL REQUIREMENTS", "items": [
                "The helmet shall provide impact and fragment protection suitable for riot control duty.",
                "The shield shall provide NIJ III+ multi-hit protection against handgun rounds.",
                "Equipment weight should be minimized to allow extended patrol duty.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder should submit test certification for the offered helmet and shield models.",
            ]},
            {"heading": "ELIGIBILITY CRITERIA", "items": [
                "Bidder should have prior experience supplying protective equipment to government bodies.",
            ]},
            {"heading": "DELIVERY REQUIREMENTS", "items": [
                "Full quantity shall be delivered within 60 days of contract signature.",
            ]},
        ],
    },
    {
        "key": "counter-drone-mod",
        "meta": {
            "title": "Request for Proposal - Counter-UAS Drone Detection and Neutralization System",
            "tender_number": "MOD/UAS/2026/CD-019",
            "issuing_organization": "Ministry of Defence",
            "issue_date": "05 Aug 2026",
            "submission_deadline": "20 Sep 2026",
            "delivery_deadline": "18 months from date of contract",
            "geography": "Pan-India, forward operating bases",
            "estimated_quantity": "40 systems",
            "product_category": "Counter-Drone / UAV Defence System",
        },
        "sections": [
            {"heading": "TECHNICAL REQUIREMENTS", "items": [
                "The system shall detect and track hostile drones using integrated radar and RF sensors.",
                "The system shall provide soft-kill jamming capability against commercial and military drone frequencies.",
                "The system shall integrate with existing air defence command and control software.",
                "The system shall provide 24x7 autonomous surveillance coverage of a 10km radius.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder shall submit DRDO or MoD-approved test certification for the counter-drone system.",
                "Bidder shall hold prior supply record of counter-UAS systems to a national defence force.",
            ]},
            {"heading": "ELIGIBILITY CRITERIA", "items": [
                "Bidder must have demonstrated radar and electronic warfare systems manufacturing experience.",
            ]},
        ],
    },
    {
        "key": "naval-craft-armour",
        "meta": {
            "title": "Armour Plating for Combatant Craft and Rigid Inflatable Boats",
            "tender_number": "NAVY/CRAFT/2026/ARM-132",
            "issuing_organization": "Naval Command",
            "issue_date": "18 Jun 2026",
            "submission_deadline": "12 Aug 2026",
            "delivery_deadline": "10 months from date of contract",
            "geography": "Western and Eastern Naval Command bases",
            "estimated_quantity": "35 craft",
            "product_category": "Naval Platform Armour",
        },
        "sections": [
            {"heading": "TECHNICAL REQUIREMENTS", "items": [
                "The armour system shall provide kinetic energy protection suitable for small combatant craft hulls.",
                "The armour system shall include an overmatch liner to prevent spall injury to crew.",
                "The armour system shall be compatible with marine environment corrosion resistance standards.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder shall submit test certification confirming armour performance in a marine environment.",
                "Bidder should hold prior experience supplying armour systems for naval platforms.",
            ]},
            {"heading": "MANUFACTURING REQUIREMENTS", "items": [
                "Bidder shall demonstrate capacity to armour 35 craft within the delivery schedule.",
            ]},
        ],
    },
    {
        "key": "sf-fast-track-helmet",
        "meta": {
            "title": "Fast Track Procurement of Lightweight Ballistic Helmets for Special Operations",
            "tender_number": "SF/OPS/2026/HEL-077",
            "issuing_organization": "Special Forces Training Command",
            "issue_date": "22 Aug 2026",
            "submission_deadline": "05 Sep 2026",
            "delivery_deadline": "30 days from date of contract",
            "geography": "India",
            "estimated_quantity": "350 units",
            "product_category": "Combat Helmet",
        },
        "sections": [
            {"heading": "TECHNICAL REQUIREMENTS", "items": [
                "The helmet shall weigh under 1 kilogram in the base configuration for extended mobility.",
                "The helmet shall defeat 9x19mm and .44 MAG threats at close range.",
                "The helmet shall be compatible with communications headsets and NVG mounts.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder should submit test certification for the offered helmet model.",
            ]},
            {"heading": "DELIVERY REQUIREMENTS", "items": [
                "Full quantity shall be delivered within 30 days of contract signature to meet operational timelines.",
            ]},
        ],
    },
    {
        "key": "export-armour-overseas",
        "meta": {
            "title": "Overseas Ministry of Defence Body Armour Supply Programme",
            "tender_number": "INTL/DEF/2026/BA-410",
            "issuing_organization": "Overseas Ministry of Defence Procurement Agency",
            "issue_date": "10 Jul 2026",
            "submission_deadline": "15 Sep 2026",
            "delivery_deadline": "8 months from date of contract",
            "geography": "Southeast Asia region",
            "estimated_quantity": "3,000 units",
            "product_category": "Body Armour",
        },
        "sections": [
            {"heading": "TECHNICAL REQUIREMENTS", "items": [
                "The vest shall provide NIJ Level IV protection at front and back panel positions.",
                "The carrier shall be compatible with regional climate conditions including high humidity.",
            ]},
            {"heading": "CERTIFICATION AND ELIGIBILITY REQUIREMENTS", "items": [
                "Bidder shall hold a valid export license for defence equipment from its home country.",
                "Bidder shall submit NIJ certification for the offered ballistic panel.",
                "Bidder must have prior experience exporting body armour to overseas government buyers.",
            ]},
        ],
    },
    {
        "key": "paramilitary-large-volume",
        "meta": {
            "title": "Large Volume Supply of Combined Body Armour and Ballistic Plates",
            "tender_number": "PMF/PROC/2026/BAP-560",
            "issuing_organization": "Paramilitary Force Procurement Directorate",
            "issue_date": "28 Jun 2026",
            "submission_deadline": "22 Aug 2026",
            "delivery_deadline": "14 months from date of contract, phased delivery",
            "geography": "Pan-India",
            "estimated_quantity": "25,000 units",
            "product_category": "Body Armour and Ballistic Plates",
        },
        "sections": [
            {"heading": "BALLISTIC AND TECHNICAL REQUIREMENTS", "items": [
                "The ballistic plate shall provide NIJ Level IV protection against 7.62 caliber AP threats.",
                "The plate shall be capable of defeating six hits of .30 caliber AP ammunition on a single plate.",
                "The carrier vest shall provide front, back and side panel coverage with MOLLE webbing.",
                "Plate weight should not exceed 4.5 kg per plate for operational mobility.",
            ]},
            {"heading": "CERTIFICATION AND TESTING REQUIREMENTS", "items": [
                "Bidder shall submit valid NIJ 0101.06 certification for the offered plates.",
                "Bidder should submit third-party accredited test reports for the current production lot.",
            ]},
            {"heading": "MANUFACTURING REQUIREMENTS", "items": [
                "Bidder shall demonstrate manufacturing capacity sufficient for 25,000 units within the delivery schedule.",
            ]},
            {"heading": "ELIGIBILITY CRITERIA", "items": [
                "Bidder must be an OEM with its own manufacturing facility for ballistic plates and carriers.",
            ]},
        ],
    },
]
