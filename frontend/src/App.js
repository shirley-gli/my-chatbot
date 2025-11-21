import "./App.css";
import { useEffect, useState } from "react";
import { FaPlus, FaTrash } from "react-icons/fa";

const API_BASE = "http://127.0.0.1:5000";

function generateId() {
  return "c-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
}

function loadChatsFromStorage() {
  try {
    const raw = localStorage.getItem("chats_v1");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveChatsToStorage(chats) {
  localStorage.setItem("chats_v1", JSON.stringify(chats));
}

function App() {
  const [chats, setChats] = useState(() => loadChatsFromStorage());
  const [activeChatId, setActiveChatId] = useState(chats.length ? chats[0].id : null);
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    saveChatsToStorage(chats);
    if (!activeChatId && chats.length) setActiveChatId(chats[0].id);
  }, [chats, activeChatId]);

  useEffect(() => {
    if (activeChatId && !chats.find(c => c.id === activeChatId)) {
      setActiveChatId(chats.length ? chats[0].id : null);
    }
  }, [chats, activeChatId]);

  const activeChat = chats.find(c => c.id === activeChatId) || null;

  const createNewChat = () => {
    const id = generateId();
    const newChat = {
      id,
      title: "New Chat",
      createdAt: Date.now(),
      messages: []
    };
    setChats(prev => [newChat, ...prev]);
    setActiveChatId(id);
  };

  const deleteChat = (id) => {
    const confirmed = window.confirm("Delete this chat?");
    if (!confirmed) return;
    setChats(prev => prev.filter(c => c.id !== id));
    if (activeChatId === id) setActiveChatId(null);
  };

  const renameChat = async (id) => {
    const name = prompt("Enter new chat title:");
    if (!name) return;
    setChats(prev => prev.map(c => c.id === id ? { ...c, title: name } : c));
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    let chatId = activeChatId;

    if (!chatId) {
      chatId = generateId();
      const baseChat = { id: chatId, title: "New Chat", createdAt: Date.now(), messages: [] };
      setChats(prev => [baseChat, ...prev]);
      setActiveChatId(chatId);
    }

    const userMsg = { role: "user", text: input, ts: Date.now() };
    setChats(prev => prev.map(c => c.id === chatId ? { ...c, messages: [...c.messages, userMsg] } : c));

    const currentChat = (chats.find(c => c.id === chatId) || { messages: [] });
    const isFirstUserMessage = (currentChat.messages || []).filter(m => m.role === "user").length === 0;

    if (isFirstUserMessage) {
      try {
        const resp = await fetch(`${API_BASE}/generate_title`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: input })
        });
        const data = await resp.json();
        const title = data.title || input.split(".")[0].slice(0, 30);
        setChats(prev => prev.map(c => c.id === chatId ? { ...c, title } : c));
      } catch (err) {
        const fallbackTitle = input.split(".")[0].split(" ").slice(0,6).join(" ");
        setChats(prev => prev.map(c => c.id === chatId ? { ...c, title: fallbackTitle } : c));
      }
    }

    const userQuery = input;
    setInput("");

    try {
      const askResp = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userQuery })
      });
      const askData = await askResp.json();
      const answer = askData.answer || askData.error || null;

      if (answer) {
        const botMsg = { role: "bot", text: answer, ts: Date.now() };
        setChats(prev => prev.map(c => c.id === chatId ? { ...c, messages: [...c.messages, botMsg] } : c));
        return;
      }

      throw new Error("No answer from /ask");
    } catch (err) {
      try {
        const chatResp = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userQuery })
        });
        const chatData = await chatResp.json();
        const reply = chatData.reply || "Backend offline";
        const botMsg = { role: "bot", text: reply, ts: Date.now() };
        setChats(prev => prev.map(c => c.id === chatId ? { ...c, messages: [...c.messages, botMsg] } : c));
      } catch (err2) {
        const botMsg = { role: "bot", text: "Both /ask and /chat failed. Is backend running?", ts: Date.now() };
        setChats(prev => prev.map(c => c.id === chatId ? { ...c, messages: [...c.messages, botMsg] } : c));
      }
    }
  };

  const handleKeyPress = (e) => { 
    if (e.key === "Enter") sendMessage(); 
  };

  const filteredChats = chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="main-container">

      {/* CHAT LIST PANEL */}
      <div className="chat-list-panel">
        <div style={{display:"flex", gap:8, alignItems:"center", marginBottom:12}}>
          <input className="search" placeholder="Search" value={search} onChange={(e)=>setSearch(e.target.value)} />
          <button className="new-chat-btn" onClick={createNewChat} title="New chat"><FaPlus /></button>
        </div>

        <div className="chat-list">
          {filteredChats.length === 0 && <div className="empty-note">No chats yet — click + to start</div>}
          {filteredChats.map(chat => (
            <div
              key={chat.id}
              className={`chat-item ${chat.id === activeChatId ? "selected" : ""}`}
              onClick={() => setActiveChatId(chat.id)}
            >
              <div className="chat-item-left">
                <div className="chat-title">{chat.title}</div>
                <div className="chat-sub">{new Date(chat.createdAt).toLocaleString()}</div>
              </div>
              <div className="chat-actions">
                <button className="small" onClick={(e)=>{e.stopPropagation(); renameChat(chat.id);}}>Rename</button>
                <button className="small" onClick={(e)=>{e.stopPropagation(); deleteChat(chat.id);}}><FaTrash /></button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CHAT WINDOW */}
      <div className="chat-window">
        <div className="chat-title-banner">PharmaSuite Chatbot</div>
        <div className="chat-header">{activeChat ? activeChat.title : "ChatBot"}</div>
        
        <div className="messages-box">
          {!activeChat && <div className="empty-state">Select a chat or start a new one.</div>}
          {activeChat && activeChat.messages.length === 0 && <div className="empty-state">No messages yet. Say hi 👋</div>}
          {activeChat && activeChat.messages.map((m, i) => (
            <div key={i} className={`message ${m.role === "user" ? "user-msg" : "bot-msg"}`}>
              {m.text}
            </div>
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

          <input
            type="file"
            multiple
            id="file-upload"
            style={{ display: "none" }}
            onChange={async (e) => {
              const selectedFiles = e.target.files;
              if (!selectedFiles.length) return;
              const formData = new FormData();
              for (let i = 0; i < selectedFiles.length; i++) formData.append("files", selectedFiles[i]);

              try {
                const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
                const data = await res.json();
                const msg = { role: "bot", text: data.message || "Uploaded", ts: Date.now() };
                if (!activeChatId) createNewChat();
                setChats(prev => prev.map(c => c.id === (activeChatId || prev[0].id) ? { ...c, messages: [...c.messages, msg] } : c));
              } catch {
                const msg = { role: "bot", text: "Upload failed", ts: Date.now() };
                setChats(prev => prev.map(c => c.id === (activeChatId || prev[0].id) ? { ...c, messages: [...c.messages, msg] } : c));
              }

              e.target.value = null;
            }}
          />

          <button className="attach-btn" onClick={() => document.getElementById("file-upload").click()}>➕</button>
          <button className="send-btn" onClick={sendMessage}>➤</button>
        </div>
      </div>
    </div>
  );
}

export default App;
