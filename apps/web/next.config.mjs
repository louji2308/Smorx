const apiBaseUrl = process.env.API_BASE_URL || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // eslint-config-next is wired in Phase 5; web lint is not a Phase 0 exit gate.
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/health",
        destination: `${apiBaseUrl}/health`,
      },
    ];
  },
};

export default nextConfig;