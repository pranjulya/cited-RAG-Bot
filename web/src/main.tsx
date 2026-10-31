import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { ChatApp } from "./chat/ChatApp";
import "./styles.css";

const isChat = /^\/chat(\/|$)/.test(window.location.pathname);

createRoot(document.getElementById("root")!).render(
  <StrictMode>{isChat ? <ChatApp /> : <App />}</StrictMode>,
);
