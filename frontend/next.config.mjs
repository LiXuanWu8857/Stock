/** @type {import('next').NextConfig} */
const nextConfig = {
  // "standalone" is for Docker only — Vercel handles output automatically
  ...(process.env.NEXT_OUTPUT === "standalone" && { output: "standalone" }),
};

export default nextConfig;
