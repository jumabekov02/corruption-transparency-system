import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./styles.css";

// Find the <div id="root"> in index.html and render the React app inside it.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
