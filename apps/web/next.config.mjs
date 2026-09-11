/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow opening the studio via http://127.0.0.1:3000 in addition to localhost.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Same-origin proxy so the browser never has to resolve localhost→IPv6 against the API.
  async rewrites() {
    const target = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(
      /\/$/,
      "",
    );
    return [
      {
        source: "/platform-api/:path*",
        destination: `${target}/:path*`,
      },
    ];
  },
};

export default nextConfig;
