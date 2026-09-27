import "./globals.css";
import { PropsWithChildren } from "react";

export const metadata = {
  title: "RepoPilot",
  description: "Evidence-backed repository onboarding",
};

export default function RootLayout({children}: PropsWithChildren) {
  return <html lang="en"><body>{children}</body></html>;
}
