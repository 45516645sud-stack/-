import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header className="site-header">
      <Link to="/" className="brand">
        🎪 박람회 찾기
      </Link>
    </header>
  );
}
