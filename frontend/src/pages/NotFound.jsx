import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
      data-testid="not-found"
    >
      <div style={{ textAlign: "center", maxWidth: 480 }}>
        <div
          className="font-display"
          style={{ fontSize: 100, color: "var(--forest)", lineHeight: 1, marginBottom: 12 }}
        >
          404
        </div>
        <h1 className="font-display" style={{ fontSize: 32, fontWeight: 500, marginBottom: 10 }}>
          Страница не найдена
        </h1>
        <p style={{ fontSize: 15, color: "var(--stone)", marginBottom: 28 }}>
          Возможно, ссылка устарела или вы ошиблись в адресе. Вернёмся на главную.
        </p>
        <Link to="/" className="btn-core btn-primary">
          ← На главную
        </Link>
      </div>
    </div>
  );
}
