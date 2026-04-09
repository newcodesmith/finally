import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinAlly - AI Trading Workstation",
  description: "AI-powered trading workstation with live market data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body
        className="h-full overflow-hidden font-sans antialiased"
        style={{ backgroundColor: '#0d1117', color: '#e6edf3' }}
      >
        {children}
      </body>
    </html>
  );
}
