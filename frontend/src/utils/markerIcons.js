import L from 'leaflet';

/**
 * Emergency Response / Military-style Map Markers
 * Based on NATO APP-6 and emergency response symbology
 */

// Define color schemes for different incident categories
const COLORS = {
  fire: '#FF4444',           // Red - fire/explosion
  fireCritical: '#CC0000',   // Dark red - critical fire
  flood: '#4488FF',          // Blue - water incidents
  medical: '#44FF44',        // Green - medical/rescue
  security: '#333333',       // Black - security threats
  infrastructure: '#FFAA00', // Orange/yellow - utilities
  support: '#AA44FF',        // Purple - support services
  default: '#3388FF',        // Default blue
};

// Create SVG icon for each marker type
function createMarkerIcon(type, color, symbol) {
  const size = type.includes('critical') ? 32 : 24;
  const svg = `
    <svg width="${size}" height="${size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <!-- Drop shadow -->
      <defs>
        <filter id="shadow-${type}" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="1"/>
          <feOffset dx="1" dy="1" result="offsetblur"/>
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.4"/>
          </feComponentTransfer>
          <feMerge>
            <feMergeNode/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      <!-- Outer circle (background) -->
      <circle cx="12" cy="12" r="10" fill="${color}" stroke="#000" stroke-width="1.5" filter="url(#shadow-${type})"/>
      
      <!-- Inner symbol -->
      <g transform="translate(12, 12)" fill="#FFF">
        ${symbol}
      </g>
      
      ${type.includes('critical') ? `
        <!-- Critical indicator (pulsing ring) -->
        <circle cx="12" cy="12" r="11" fill="none" stroke="${color}" stroke-width="2" opacity="0.6">
          <animate attributeName="r" values="11;14;11" dur="2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite"/>
        </circle>
      ` : ''}
    </svg>
  `;
  
  return L.divIcon({
    html: svg,
    className: 'custom-marker-icon',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

// Symbol definitions (SVG paths centered at 0,0)
const SYMBOLS = {
  fire: '<path d="M-4,-6 Q-6,-3 -4,0 Q-2,2 0,4 Q2,2 4,0 Q6,-3 4,-6 Q2,-8 0,-6 Q-2,-8 -4,-6 Z"/>',
  buildingDamage: '<rect x="-5" y="-5" width="10" height="10" stroke="#FFF" stroke-width="1.5" fill="none"/><line x1="-5" y1="-5" x2="5" y2="5" stroke="#FFF" stroke-width="2"/><line x1="-5" y1="5" x2="5" y2="-5" stroke="#FFF" stroke-width="2"/>',
  hazmat: '<path d="M0,-6 L5,3 L-5,3 Z" stroke="#FFF" stroke-width="1.5" fill="none"/><text x="0" y="2" text-anchor="middle" font-size="8" font-weight="bold" fill="#FFF">!</text>',
  flood: '<path d="M-6,2 Q-4,0 -2,2 Q0,4 2,2 Q4,0 6,2" stroke="#FFF" stroke-width="1.5" fill="none"/><path d="M-6,-2 Q-4,-4 -2,-2 Q0,0 2,-2 Q4,-4 6,-2" stroke="#FFF" stroke-width="1.5" fill="none"/>',
  waterDamage: '<path d="M0,-6 Q2,-4 2,-2 Q2,0 0,2 Q-2,0 -2,-2 Q-2,-4 0,-6 Z" fill="#FFF"/><line x1="-4" y1="3" x2="4" y2="3" stroke="#FFF" stroke-width="1.5"/>',
  medical: '<rect x="-1.5" y="-5" width="3" height="10" fill="#FFF"/><rect x="-5" y="-1.5" width="10" height="3" fill="#FFF"/>',
  rescue: '<circle cx="0" cy="-3" r="2" fill="#FFF"/><line x1="0" y1="-1" x2="0" y2="4" stroke="#FFF" stroke-width="2"/><line x1="0" y1="1" x2="-3" y2="3" stroke="#FFF" stroke-width="2"/><line x1="0" y1="1" x2="3" y2="3" stroke="#FFF" stroke-width="2"/>',
  trapped: '<rect x="-5" y="-5" width="10" height="10" stroke="#FFF" stroke-width="2" fill="none"/><circle cx="0" cy="0" r="2" fill="#FFF"/>',
  securityThreat: '<path d="M0,-6 L-5,2 L5,2 Z" fill="#FFF"/><rect x="-1" y="0" width="2" height="4" fill="#FFF"/>',
  terrorist: '<circle cx="0" cy="0" r="6" fill="none" stroke="#FFF" stroke-width="2"/><line x1="0" y1="-6" x2="0" y2="6" stroke="#FFF" stroke-width="2"/><line x1="-6" y1="0" x2="6" y2="0" stroke="#FFF" stroke-width="2"/>',
  missingPerson: '<circle cx="0" cy="-3" r="2.5" fill="#FFF"/><line x1="0" y1="-0.5" x2="0" y2="4" stroke="#FFF" stroke-width="2"/><text x="0" y="3" text-anchor="middle" font-size="10" font-weight="bold" fill="#FFF">?</text>',
  powerOut: '<path d="M-2,-6 L-4,0 L-1,0 L-3,6 L4,-2 L1,-2 L3,-6 Z" fill="#FFF"/>',
  gasLeak: '<circle cx="0" cy="0" r="5" fill="none" stroke="#FFF" stroke-width="1.5"/><circle cx="0" cy="0" r="2" fill="#FFF"/><path d="M0,-5 L0,-7" stroke="#FFF" stroke-width="1.5"/><path d="M0,5 L0,7" stroke="#FFF" stroke-width="1.5"/><path d="M-5,0 L-7,0" stroke="#FFF" stroke-width="1.5"/><path d="M5,0 L7,0" stroke="#FFF" stroke-width="1.5"/>',
  roadBlocked: '<rect x="-5" y="-2" width="10" height="4" fill="none" stroke="#FFF" stroke-width="1.5"/><line x1="-5" y1="-2" x2="5" y2="2" stroke="#FFF" stroke-width="2"/>',
  bridgeDamage: '<path d="M-6,2 L-6,4 L6,4 L6,2" stroke="#FFF" stroke-width="1.5" fill="none"/><rect x="-5" y="-2" width="3" height="4" stroke="#FFF" stroke-width="1" fill="none"/><rect x="2" y="-2" width="3" height="4" stroke="#FFF" stroke-width="1" fill="none"/><line x1="-6" y1="2" x2="6" y2="2" stroke="#FFF" stroke-width="2" stroke-dasharray="2,2"/>',
  shelter: '<path d="M0,-6 L-5,2 L5,2 Z" fill="none" stroke="#FFF" stroke-width="1.5"/><rect x="-3" y="0" width="6" height="5" fill="none" stroke="#FFF" stroke-width="1.5"/>',
  default: '<circle cx="0" cy="0" r="4" fill="#FFF"/>',
};

// Marker icon cache
const iconCache = {};

/**
 * Get or create a marker icon for a given type
 */
export function getMarkerIcon(markerType = 'default') {
  // Return cached icon if available
  if (iconCache[markerType]) {
    return iconCache[markerType];
  }
  
  // Parse marker type and determine color/symbol
  let color = COLORS.default;
  let symbol = SYMBOLS.default;
  let type = markerType.toLowerCase();
  
  // Map marker types to colors and symbols
  if (type.includes('fire')) {
    color = type.includes('critical') ? COLORS.fireCritical : COLORS.fire;
    symbol = SYMBOLS.fire;
  } else if (type.includes('building-damage')) {
    color = type.includes('critical') ? COLORS.fireCritical : COLORS.fire;
    symbol = SYMBOLS.buildingDamage;
  } else if (type.includes('hazmat')) {
    color = type.includes('critical') ? COLORS.fireCritical : COLORS.fire;
    symbol = SYMBOLS.hazmat;
  } else if (type.includes('flood')) {
    color = COLORS.flood;
    symbol = SYMBOLS.flood;
  } else if (type.includes('water-damage')) {
    color = COLORS.flood;
    symbol = SYMBOLS.waterDamage;
  } else if (type.includes('medical')) {
    color = COLORS.medical;
    symbol = SYMBOLS.medical;
  } else if (type.includes('rescue')) {
    color = COLORS.medical;
    symbol = SYMBOLS.rescue;
  } else if (type.includes('trapped')) {
    color = type.includes('critical') ? COLORS.fireCritical : COLORS.medical;
    symbol = SYMBOLS.trapped;
  } else if (type.includes('security-threat')) {
    color = COLORS.security;
    symbol = SYMBOLS.securityThreat;
  } else if (type.includes('terrorist')) {
    color = COLORS.security;
    symbol = SYMBOLS.terrorist;
  } else if (type.includes('missing-person')) {
    color = COLORS.security;
    symbol = SYMBOLS.missingPerson;
  } else if (type.includes('power-out')) {
    color = COLORS.infrastructure;
    symbol = SYMBOLS.powerOut;
  } else if (type.includes('gas-leak')) {
    color = COLORS.infrastructure;
    symbol = SYMBOLS.gasLeak;
  } else if (type.includes('road-blocked')) {
    color = COLORS.infrastructure;
    symbol = SYMBOLS.roadBlocked;
  } else if (type.includes('bridge-damage')) {
    color = COLORS.infrastructure;
    symbol = SYMBOLS.bridgeDamage;
  } else if (type.includes('shelter')) {
    color = COLORS.support;
    symbol = SYMBOLS.shelter;
  }
  
  // Create and cache the icon
  const icon = createMarkerIcon(type, color, symbol);
  iconCache[markerType] = icon;
  
  return icon;
}

/**
 * Get legend information for all marker types
 */
export function getMarkerLegend() {
  return [
    { type: 'fire', label: 'Fire/Explosion', color: COLORS.fire },
    { type: 'building-damage', label: 'Building Collapse', color: COLORS.fire },
    { type: 'hazmat', label: 'Hazmat Spill', color: COLORS.fire },
    { type: 'flood', label: 'Flood', color: COLORS.flood },
    { type: 'water-damage', label: 'Water Contamination', color: COLORS.flood },
    { type: 'medical', label: 'Medical Emergency', color: COLORS.medical },
    { type: 'rescue', label: 'Survivors Rescued', color: COLORS.medical },
    { type: 'trapped', label: 'Trapped Victims', color: COLORS.medical },
    { type: 'security-threat', label: 'Security Threat/Looting', color: COLORS.security },
    { type: 'terrorist', label: 'Terrorist Incident', color: COLORS.security },
    { type: 'missing-person', label: 'Missing Person', color: COLORS.security },
    { type: 'power-out', label: 'Power Outage', color: COLORS.infrastructure },
    { type: 'gas-leak', label: 'Gas Leak', color: COLORS.infrastructure },
    { type: 'road-blocked', label: 'Road Blocked', color: COLORS.infrastructure },
    { type: 'bridge-damage', label: 'Bridge Damage', color: COLORS.infrastructure },
    { type: 'shelter', label: 'Shelter Request', color: COLORS.support },
  ];
}
