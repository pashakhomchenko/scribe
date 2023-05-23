/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/summarize',
        destination: `${process.env.SCRIBE_API_URL}/summarize/`
      }
    ];
  }
};

module.exports = nextConfig;
