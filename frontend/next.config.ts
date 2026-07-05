import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: process.cwd(),
  transpilePackages: ["@splinetool/react-spline", "@splinetool/runtime"],
};

export default nextConfig;
