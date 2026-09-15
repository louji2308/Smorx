import type { Metadata } from 'next';
import { Plus_Jakarta_Sans, Gruppo, JetBrains_Mono, Ubuntu } from 'next/font/google';
import './globals.css';

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-sans',
  display: 'swap',
});

const ubuntu = Ubuntu({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-display',
  display: 'swap',
});

const gruppo = Gruppo({
  subsets: ['latin'],
  weight: '400',
  variable: '--font-brand',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Smorx — Software Evolution Intelligence System',
  description: 'Behavioral operating system for software evolution: Discover, Govern, Define, Analyze, Develop, Verify, Decide, Certify',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${plusJakarta.variable} ${ubuntu.variable} ${gruppo.variable} ${jetbrainsMono.variable} antialiased`}
    >
      <body className="min-h-screen bg-[var(--color-smoke)] text-[var(--color-text-primary)]">
        {children}
      </body>
    </html>
  );
}
