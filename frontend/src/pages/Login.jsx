import React, { useEffect } from "react";
import { login, handleAuthCallback } from "../services/auth";

function Login() {
  useEffect(() => {
    handleAuthCallback().then((data) => {
      if (data) {
        window.location.href = "/";
      }
    });
  }, []);

  return (
    <div style={{ textAlign: "center", marginTop: "100px" }}>
      <h2>🔐 Sign in to Certificate Portal</h2>
      <button
        onClick={login}
        style={{ padding: "10px 20px", marginTop: "20px" }}
      >
        Sign in with Google
      </button>
    </div>
  );
}

export default Login;
