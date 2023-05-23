export default function About() {
  return (
    <section className="bg-black text-white flex justify-center items-center flex-col gap-8 py-10 h-screen min-h-[600px] px-8">
      <h2 className="text-4xl font-bold">How Scribe works</h2>
      <div>
        <div className="text-2xl">1. You upload a recording</div>
        <div className="text-2xl">
          2. Our AI generates an intelligent summary
        </div>
        <div className="text-2xl">
          3. We will email you the summary and the transcript
        </div>
      </div>
      <div className="text-xl">
        A summary should land in your inbox within 24 hours, although it's
        usually much quicker.
      </div>
    </section>
  );
}
