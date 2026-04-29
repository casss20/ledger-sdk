import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import { QueryProvider } from "./app/providers";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryProvider>
      <BrowserRouter basename="/demo">
        <App />
      </BrowserRouter>
    </QueryProvider>
  </React.StrictMode>
);
