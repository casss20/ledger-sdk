import { AppRouter } from "./router";
import { QueryProvider } from "./providers";

export function App() {
  return (
    <QueryProvider>
      <AppRouter />
    </QueryProvider>
  );
}
