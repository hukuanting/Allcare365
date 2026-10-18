import React from 'react';
import { BRAND_SIZE, BRAND_RECTS, BRAND_CENTRE, BRAND_PAPER } from '../config/brand';
export default function Brand({ compact = false }) {
  return <span className="atlas-brand"><svg className="atlas-brand-mark" viewBox={`0 0 ${BRAND_SIZE} ${BRAND_SIZE}`} aria-hidden="true">{BRAND_RECTS.map((rect, index) => <rect key={index} {...rect} fill="currentColor"/>)}<rect {...BRAND_CENTRE} fill={`var(--atlas-mark-centre, var(--atlas-paper, ${BRAND_PAPER}))`}/></svg>{!compact && <span>allcare<span className="brand-number">365</span></span>}</span>;
}
