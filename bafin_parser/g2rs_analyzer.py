from __future__ import annotations

import re


def analyze_g2rs_eligibility(license_status: str, activity: str) -> tuple[bool, str]:
    if not license_status or license_status.strip().lower() != 'aktiv':
        return False, 'License status is not active.'
        
    activity_lower = activity.lower()
    eligible_keywords = [
        'kreditinstitut', 
        'finanzdienstleistung', 
        'wertpapierinstitut',
        'zahlungsinstitut',
        'e-geld-institut',
        'versicher',
        'kryptowertpapierregister',
        'kwg',
        'zag',
        'wpg'
    ]
    
    is_eligible = any(keyword in activity_lower for keyword in eligible_keywords)
    
    if is_eligible:
        return True, 'Company has an active eligible financial license.'
    else:
        return False, 'Company does not appear to hold a primary financial license required by Google G2RS.'

