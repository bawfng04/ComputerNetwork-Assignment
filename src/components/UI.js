import { useState, useEffect } from "react";
import { files, fileTypes } from "./files";
import "./UI.css";

const UI = () => {
  const [downloadFile, setDownloadFile] = useState("");
  const [downloadFileType, setDownloadFileType] = useState([]);
  const [selectedAll, setSelecetedAll] = useState(false);

  const handleSelectedAll = () => {
    setSelecetedAll((prevSelectedAll) => {
      const newSelectedAll = !prevSelectedAll;

      if (newSelectedAll) {
        // Add all file types for the selected file to the state
        const typesToSelect = fileTypes.filter(
          (file) => file.filename === downloadFile
        )[0]?.filetype;

        setDownloadFileType(typesToSelect || []);
      } else {
        // Deselect all file types
        setDownloadFileType([]);
      }

      return newSelectedAll;
    });
  };

  const handleDownloadChange = (e) => {
    setDownloadFile(e.target.value);
    setDownloadFileType([]); // Reset selected file types when file changes
    setSelecetedAll(false); // Reset the "Select all" state
  };

  const handleDownloadTypeChange = (e) => {
    const { value, checked } = e.target;
    setDownloadFileType((prev) => {
      if (checked) {
        // Add the checked value to the array
        return [...prev, value];
      } else {
        // Remove the unchecked value from the array
        return prev.filter((type) => type !== value);
      }
    });
  };

  const handleDownloadFile = () => {
    console.log("Downloading file: ", downloadFile);
    console.log("Selected file types: ", downloadFileType);
  };

  useEffect(() => {
    if (downloadFileType.length > 0) {
      const typesToSelect = fileTypes.filter(
        (file) => file.filename === downloadFile
      )[0]?.filetype;

      if (
        typesToSelect &&
        typesToSelect.length === downloadFileType.length &&
        typesToSelect.every((type) => downloadFileType.includes(type))
      ) {
        setSelecetedAll(true);
      } else {
        setSelecetedAll(false);
      }
    }
  }, [downloadFileType, downloadFile]);

  useEffect(() => {
    console.log("selected types: ", downloadFileType);
  }, [downloadFileType]);

  return (
    <div className="UI">
      <div className="renderDownloadBar">
        <select className="select1" onChange={handleDownloadChange}>
          <option value="selectedFile">Select file</option>
          {files.map((file) => (
            <option key={file.filename} value={file.filename}>
              {file.filename}
            </option>
          ))}
        </select>

        {downloadFile && (
          <div className="checkbox-group">
            <div className="headSelect">
              <label>Select file type</label>

              <button className="selectedAll" onClick={handleSelectedAll}>
                {selectedAll ? "Deselect all" : "Select all"}
              </button>
            </div>

            {fileTypes
              .filter((file) => file.filename === downloadFile)[0]
              ?.filetype.map((type, index) => (
                <div key={index} className="selectType">
                  <input
                    type="checkbox"
                    id={`checkbox-${index}`}
                    value={type}
                    onChange={handleDownloadTypeChange}
                    checked={downloadFileType.includes(type)}
                  />
                  <label htmlFor={`checkbox-${index}`}>
                    {type} (
                    {
                      fileTypes.filter(
                        (file) => file.filename === downloadFile
                      )[0]?.filesize[index]
                    }{" "}
                    KB)
                  </label>
                </div>
              ))}
          </div>
        )}

        <div className="downloadButton">
          <button onClick={handleDownloadFile} className="downloadButton">
            Download
          </button>
        </div>
      </div>
    </div>
  );
};

export default UI;
