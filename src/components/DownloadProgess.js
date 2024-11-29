import "./DownloadProgess.css";

const DownloadProgess = ({ fileName, progress }) => {
  return (
    <div className="download-progress">
      <h2>{fileName}</h2>
      <progress value={progress} max="100" />
    </div>
  );
};

export default DownloadProgess;
