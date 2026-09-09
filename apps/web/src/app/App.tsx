import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";

import { AuthProvider } from "../features/auth/AuthProvider";
import { queryClient } from "./queryClient";
import { AppRouter } from "./router";

export function App() {
  return <QueryClientProvider client={queryClient}><BrowserRouter><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></QueryClientProvider>;
}
