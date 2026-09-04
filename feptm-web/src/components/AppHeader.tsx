export function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <img
          src="/foreach-partners-logo.png"
          alt=""
          width={32}
          height={32}
          className="app-header__logo"
        />
        <span className="app-header__wordmark">ForEach Partners</span>
      </div>
    </header>
  );
}
