import { Link } from "react-router-dom";

export function Brand() {
  return (
    <Link className="brand" to="/" aria-label="SIFT OS home">
      <span className="brand-mark" aria-hidden="true">S</span>
      <span className="brand-word">SIFT <small>OS</small></span>
    </Link>
  );
}
