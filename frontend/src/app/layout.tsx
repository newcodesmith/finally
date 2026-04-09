import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'FinAlly - AI Trading Workstation',
  description: 'AI-powered trading workstation with live market data and portfolio management',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-terminal-bg text-terminal-text font-mono antialiased">
        {children}
      </body>
    </html>
  );
}
