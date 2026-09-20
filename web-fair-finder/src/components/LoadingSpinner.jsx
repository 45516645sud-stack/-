export default function LoadingSpinner() {
  return (
    <div className="loading-spinner" role="status" aria-label="불러오는 중">
      <div className="spinner" />
      <span>박람회 정보를 불러오는 중...</span>
    </div>
  );
}
