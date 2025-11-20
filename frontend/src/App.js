import "./App.css";
import { useState } from "react";
import { FaHome, FaComments, FaStar, FaChartBar, FaCog, FaUser } from "react-icons/fa";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState([]);

  const sendMessage = async () => {
    if (input.trim() === "") return;

    const userMsg = { sender: "user", text: input };
    setMessages(prev => [...prev, userMsg]);

    try {
      const askResponse = await fetch("http://127.0.0.1:5000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input })
      });
      const askData = await askResponse.json();
      const answer = askData.answer || askData.error;
      setMessages(prev => [...prev, { sender: "bot", text: answer }]);
    } catch (error) {
      const chatResponse = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input })
      });
      const chatData = await chatResponse.json();
      setMessages(prev => [...prev, { sender: "bot", text: chatData.reply || "Backend offline" }]);
    }

    setInput("");
  };

  const handleKeyPress = (e) => { if (e.key === "Enter") sendMessage(); };

  const handleFileChange = async (e) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles.length) return;

    const formData = new FormData();
    for (let i = 0; i < selectedFiles.length; i++) formData.append("files", selectedFiles[i]);

    try {
      const res = await fetch("http://127.0.0.1:5000/upload", { method: "POST", body: formData });
      const data = await res.json();
      setMessages(prev => [...prev, { sender: "bot", text: data.message }]);
      setFiles([]);
    } catch (err) {
      setMessages(prev => [...prev, { sender: "bot", text: "Upload failed" }]);
    }
  };

  return (
    <div className="main-container">

      {/* LEFT SIDEBAR */}
      <div className="sidebar">
        <div className="icon active"><FaHome color="white" size={18} /></div>
        <div className="icon"><FaComments color="white" size={18} /></div>
        <div className="icon"><FaStar color="white" size={18} /></div>
        <div className="icon"><FaChartBar color="white" size={18} /></div>
        <div className="icon"><FaCog color="white" size={18} /></div>
        <div className="profile-icon"><FaUser color="white" size={20} /></div>
      </div>

      {/* CHAT LIST PANEL */}
      <div className="chat-list-panel">
        <input className="search" placeholder="Search" />
      </div>

      {/* CHAT WINDOW */}
      <div className="chat-window">
        <div className="chat-header">ChatBot</div>

        <div className="messages-box">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.sender}-msg`}>{msg.text}</div>
          ))}
        </div>

        {/* INPUT AREA */}
        <div className="input-area">
          <input
            className="chat-input"
            placeholder="Message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
          />

          {/* Hidden file input */}
          <input
            type="file"
            multiple
            id="file-upload"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />

          {/* Attachment button */}
          <button
            className="attach-btn"
            onClick={() => document.getElementById("file-upload").click()}
          >
            📎
          </button>

          {/* Send button */}
          <button className="send-btn" onClick={sendMessage}>➤</button>
        </div>
      </div>
    </div>
  );
}

export default App;
