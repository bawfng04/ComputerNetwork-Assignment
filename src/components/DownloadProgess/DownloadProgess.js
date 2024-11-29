import "./DownloadProgess.css";

const DownloadProgess = ({ fileName, fileSize, currentDownload }) => {
  return (
    <div className="download-progress">
      <div className="downloadTitle">
        <h2>{fileName}</h2>
        <p>
          {currentDownload} / {fileSize} KB
        </p>
      </div>
      <progress value={(currentDownload / fileSize) * 100} max="100" />
    </div>
  );
};

export default DownloadProgess;
