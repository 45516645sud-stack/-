export default function ErrorBanner({ noApiKey, message }) {
  if (noApiKey) {
    return (
      <div className="banner banner-info">
        공공데이터포털 API 키가 설정되지 않아 <strong>샘플 데이터</strong>를 보여드리고 있어요.
        실제 박람회 데이터를 연동하려면 프로젝트 루트의 <code>.env</code> 파일에{' '}
        <code>VITE_TOUR_API_KEY</code>를 설정하세요. (자세한 방법은 README 참고)
      </div>
    );
  }

  return (
    <div className="banner banner-error">
      데이터를 불러오지 못해 샘플 데이터를 보여드리고 있어요. {message && `(${message})`}
    </div>
  );
}
