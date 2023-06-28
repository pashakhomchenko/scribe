/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/submit',
        destination: `${process.env.SCRIBE_API_URL}/submit/`
      }
    ];
  }
};

module.exports = nextConfig;
