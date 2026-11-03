import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The shared accessibility engine is imported from the repository-level
  // packages/ directory. Trace from the repository root for monorepo deploys.
  outputFileTracingRoot: path.join(__dirname, "../../"),
};

export default nextConfig;
