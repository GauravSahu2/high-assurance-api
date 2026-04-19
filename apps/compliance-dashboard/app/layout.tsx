import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "HSA Compliance Dashboard",
  description: "Real-time 32-tier high-assurance validation portal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0A0A0A] text-[#EDEDED] antialiased`}>
        {children}
      </body>
    </html>
  );
}
