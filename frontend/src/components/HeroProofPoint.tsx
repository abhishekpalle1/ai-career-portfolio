import type { HeroProofPoint as HeroProofPointModel } from '../types/portfolio';

interface HeroProofPointProps {
  proofPoint: HeroProofPointModel;
}

export function HeroProofPoint({ proofPoint }: HeroProofPointProps) {
  return (
    <li className="proof-point">
      {proofPoint.value ? <span className="proof-point__value">{proofPoint.value}</span> : null}
      <span className="proof-point__label">{proofPoint.label}</span>
    </li>
  );
}
