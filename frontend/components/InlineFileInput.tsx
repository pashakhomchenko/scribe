export default function InlineFileInput() {
  return (
    <input
      className="block h-full w-3/4 text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"
      id="file_input"
      type="file"
      name="file"
      accept=".mp3,.mp4,.txt,.flac,.m4a"
      required
    />
  );
}
